import math
import os

import clipboard
import numpy
import soundfile
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QMenu, QMessageBox, QTableWidgetItem

import globals.global_variables as gv
from libraries.multi_thread import batch_processor
from libraries.table_view.table_cell_data import CellSeverity
from libraries.table_view.table_number_item import NumberTableItem
from libraries.table_view.table_severity_delegate import SeverityTableDelegate
from libraries.utils import audio_utils, path_utils, user_config
from libraries.utils.qt_utils import resize_table_and_window
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import audio_source_utils, localization_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType
from table.wwise_table_context_menu import add_common_object_actions, connect_double_click_select
from ui.MultiLanguageCompare_ui import Ui_MultiLanguageCompare

# 响度标准 / 宽容度沿用响度调整工具的持久化设置（同一个 user_config 项）
LOUDNESS_SETTINGS_KEY = 'loudness_adjustment'

# 参考语言来自全局设置（设置窗口 → 工具行为 → 本地化），这里不再单独建节点

# 时长偏差（相对参考语言）的 warning / danger 阈值
DURATION_WARNING_RATIO = 0.2
DURATION_DANGER_RATIO = 0.5

# 响度标准下拉项的取值（顺序与 .ui 中的条目一致）
LOUDNESS_STANDARDS = (audio_utils.LoudnessStandard.RMS, audio_utils.LoudnessStandard.LUFS)

# 不出现削波的音频峰值上限
CLIP_LIMIT_PEAK = 1.0

# 表格列：选中 / Sound名称 / Sound路径 + 每个语言两列（响度、时长）
COL_CHECK = 0
COL_NAME = 1
COL_PATH = 2
COL_METRIC_START = 3

METRIC_LOUDNESS = 'loudness'
METRIC_DURATION = 'duration'


# 批量取回的属性里读语言名：audioSource:language 是引用属性，取 name；取不到按 SFX 处理
def language_from_properties(properties: dict) -> str:
    language = (properties or {}).get('audioSource:language')
    if isinstance(language, dict):
        name = language.get('name')
        if name:
            return str(name)
    elif isinstance(language, str) and language:
        return language
    return localization_utils.SFX_LANGUAGE_NAME


# 多语言对比：一行一个非 SFX Sound，每种语言显示该语言 AudioSource 的响度与时长
class MultiLanguageCompareWindow(QDialog, Ui_MultiLanguageCompare):

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # 输入对象在 refresh_rows 里从主窗口临时获取，保证与表格同步
        self.__input_sounds: list = []
        # 每行：{'key', 'row', 'sound', 'sources': {语言: AudioSource},
        #        'loudness': {语言: 值}, 'duration': {语言: 秒}}
        self.__rows: list = []
        self.__languages: list = []
        self.__analyzed = []
        self.__adjust_results = []
        self.__standard = audio_utils.LoudnessStandard.RMS
        self.__tolerance = 1.0
        self.__reference_language = ''
        self.__loading_settings = False
        self.load_settings()
        self.tblCompare.setItemDelegate(SeverityTableDelegate(self.tblCompare))
        self.setup_triggers()
        self.refresh_rows()

    def setup_triggers(self):
        self.btnRefresh.clicked.connect(self.refresh_rows)
        self.btnUnifyLoudness.clicked.connect(self.unify_loudness)
        self.cbxSelectAll.toggled.connect(self.toggle_select_all)
        self.cbbReferenceLanguage.currentTextChanged.connect(self.save_reference_language)
        self.cbbLoudnessStandard.currentIndexChanged.connect(self.on_standard_changed)
        self.spbTolerance.valueChanged.connect(self.save_loudness_settings)
        self.tblCompare.setSortingEnabled(True)
        self.tblCompare.horizontalHeader().sortIndicatorChanged.connect(self.sync_row_indexes)
        self.tblCompare.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tblCompare.customContextMenuRequested.connect(self.show_context_menu)
        connect_double_click_select(self.tblCompare, self.objects_at_row)

    # 读取共享设置（响度标准 / 宽容度）与本窗口的参考语言
    def load_settings(self):
        self.__loading_settings = True
        settings = user_config.get_window_settings(LOUDNESS_SETTINGS_KEY)
        standard_name = str(settings.get('loudness_standard', audio_utils.LoudnessStandard.RMS.value))
        index = next((i for i, item in enumerate(LOUDNESS_STANDARDS) if item.value == standard_name), 0)
        self.cbbLoudnessStandard.setCurrentIndex(index)
        self.__standard = LOUDNESS_STANDARDS[index]
        self.spbTolerance.setValue(float(settings.get('tolerance_db', 1.0)))
        self.__tolerance = self.spbTolerance.value()
        # 参考语言优先取全局设置（勾了「使用工程默认」时就是工程参考语言）
        self.__reference_language = localization_utils.get_reference_language_name()
        self.__loading_settings = False

    # 保存共享设置：写回响度调整工具的同一个 user_config 项
    def save_loudness_settings(self, *_args):
        if self.__loading_settings:
            return
        self.__tolerance = self.spbTolerance.value()
        current = dict(user_config.get_window_settings(LOUDNESS_SETTINGS_KEY))
        current['loudness_standard'] = self.__standard.value
        current['tolerance_db'] = self.__tolerance
        user_config.set_window_settings(LOUDNESS_SETTINGS_KEY, current)
        self.refresh_severity()
        self.log_state()

    # 保存参考语言（写回全局设置；「使用工程默认」由设置窗口控制）
    def save_reference_language(self, language: str):
        if self.__loading_settings:
            return
        self.__reference_language = language
        user_config.set_configured_reference_language(language)
        # 参考语言变了，severity 的基准跟着变，需要重算
        self.refresh_severity()
        self.log_state()

    # 响度标准变化：读写共享设置并重新测量
    def on_standard_changed(self, index: int):
        self.__standard = LOUDNESS_STANDARDS[index] if 0 <= index < len(LOUDNESS_STANDARDS) \
            else audio_utils.LoudnessStandard.RMS
        self.save_loudness_settings()
        if not self.__loading_settings and self.__rows:
            Logger().info(f'响度标准已切换为 {self.__standard.name}，正在重新测量')
            self.analyze_loudness()

    # 是否已有批处理在运行
    @staticmethod
    def is_busy() -> bool:
        processor = gv.batch_processor
        return bool(processor) and getattr(processor, 'isRunning', lambda: False)()

    # 采集表格数据：每个 Sound 找直系 AudioSource 子对象并按语言归类（带进度条）
    def refresh_rows(self):
        if self.is_busy():
            return
        # 每次刷新都临时取主窗口当前 Sound，保证与表格同步
        self.__input_sounds = gv.get_tool_targets(WwiseObjectType.Sound)
        if not self.__input_sounds:
            Logger().warning('表格中没有可用于「多语言对比」的 Sound')
            return
        self.__rows = []
        batch_processor.create_async(
            self.__input_sounds,
            self.collect_sound_sources,
            '查找多语言音频源',
            'name',
            on_finished=self.on_sources_collected,
        )

    # 工作线程：收集单个 Sound 下各语言的 AudioSource（只保留非 SFX 的 Sound）
    #
    # 一个语言下可能有多个 AudioFileSource（重复导入、多源 Sound 等），WAAPI 没有可直接读取的
    # 「in use」标记，这里按下面的顺序判定实际生效的那一个：
    #   1) 优先取磁盘上已导入 wav 的源（没有导入的语言槽没法播放）；
    #   2) 仍有多条时取第一个（与 localization_utils.get_sound_language 的口径一致），
    #      并把该语言标记为多源，界面 tooltip 与日志里列出全部候选。
    #
    # 这里的 WAAPI 往返是整表读取的大头，因此把「子对象列表」和「语言 / 路径 / 裁剪属性」各压成一次批量查询，
    # 属性结果跟着行数据一起带到测量阶段，测量时不再发起 WAAPI 查询。
    def collect_sound_sources(self, index: int, sound: WwiseObject):
        children = waapi_utils.get_child_objects(sound)
        grouped = {}
        properties_by_id = audio_source_utils.get_source_analysis_properties([sound] + children)
        languages = []
        for child in children:
            if child.type != WwiseObjectType.AudioSource:
                continue
            properties = properties_by_id.get(child.id, {})
            language = language_from_properties(properties)
            languages.append(language)
            grouped.setdefault(language, []).append((child, bool(properties.get('originalFilePath'))))
        # 没有音频源、或首个源是 SFX 时按 SFX 处理，与 localization_utils.get_sound_language 口径一致
        if not languages or languages[0] == localization_utils.SFX_LANGUAGE_NAME:
            return True
        # 实际在用的源：优先读 WorkUnit 的 ActiveSourceList（与语言无关、最准确），
        # 取不到时退回 WAAPI 的 activeSource（只覆盖当前语言）
        workunit_path = properties_by_id.get(sound.id, {}).get('workUnit.filePath')
        active_ids = {obj.id for obj in audio_source_utils.get_active_sources(
            sound, children=children, workunit_path=workunit_path)}
        sources = {}
        ambiguous = {}
        guessed = {}
        for language, candidates in grouped.items():
            matched = [child for child, _installed in candidates if child.id in active_ids]
            if matched:
                # 该语言里有 Wwise 认定的在用源（正常情况只有 1 个）
                sources[language] = matched[0]
                if len(matched) > 1:
                    ambiguous[language] = [child.name for child in matched]
                continue
            # ActiveSourceList 里没有该语言的源（例如工程里刚改还没保存）：按已导入优先取第一个
            usable = [child for child, installed in candidates if installed] \
                or [child for child, _installed in candidates]
            sources[language] = usable[0]
            if len(usable) > 1:
                ambiguous[language] = [child.name for child in usable]
                guessed[language] = [child.name for child in usable]
        if guessed:
            detail = '；'.join(f'{language}: {"、".join(names)}' for language, names in guessed.items())
            Logger().warning(f'[{sound.name}] 这些语言在 ActiveSourceList 里没有匹配的源（{detail}），'
                             '暂按「已导入优先、其次取第一个」统计，可能不是 in use 的那个')
        if ambiguous:
            detail = '；'.join(f'{language}: {"、".join(names)}' for language, names in ambiguous.items())
            Logger().debug(f'[{sound.name}] 同语言多个 AudioSource：{detail}')
        self.__rows.append({'sound': sound, 'sources': sources, 'ambiguous': ambiguous,
                            'properties': properties_by_id, 'loudness': {}, 'duration': {}})
        return True

    # 主线程：确定语言列并填充表格，然后开始测量
    def on_sources_collected(self):
        self.__rows = [row for row in self.__rows if row['sources']]
        for index, row in enumerate(self.__rows):
            row['key'] = row['sound'].id
            row['row'] = index
        self.__languages = self.__collect_languages()
        self.__rebuild_table()
        self.analyze_loudness()

    # 语言列顺序：工程里的语言顺序优先，其余按名称排序
    def __collect_languages(self) -> list:
        found = {language for row in self.__rows for language in row['sources']}
        ordered = [name for name in localization_utils.get_all_language_names() if name in found]
        ordered += sorted(found - set(ordered))
        return ordered

    # 重建表头与行：选中 / Sound名称 / Sound路径 + 每个语言（响度、时长）
    def __rebuild_table(self):
        self.tblCompare.clear()
        headers = ['选中', 'Sound名称', 'Sound路径']
        for language in self.__languages:
            headers += [f'{language} 响度', f'{language} 时长']
        self.tblCompare.setColumnCount(len(headers))
        self.tblCompare.setHorizontalHeaderLabels(headers)
        self.tblCompare.setRowCount(len(self.__rows))
        for row_data in self.__rows:
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            check_item.setCheckState(
                Qt.CheckState.Checked if self.cbxSelectAll.isChecked() else Qt.CheckState.Unchecked
            )
            check_item.setData(Qt.ItemDataRole.UserRole, row_data['key'])
            self.tblCompare.setItem(row_data['row'], COL_CHECK, check_item)
            name_item = QTableWidgetItem(row_data['sound'].name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.tblCompare.setItem(row_data['row'], COL_NAME, name_item)
            path_item = QTableWidgetItem(path_utils.get_display_path(row_data['sound'].path))
            path_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.tblCompare.setItem(row_data['row'], COL_PATH, path_item)
        self.__sync_reference_languages()
        resize_table_and_window(self.tblCompare, self)

    # 参考语言下拉：按当前语言列重建，尽量保留上次的选择
    def __sync_reference_languages(self):
        self.cbbReferenceLanguage.blockSignals(True)
        self.cbbReferenceLanguage.clear()
        self.cbbReferenceLanguage.addItems(self.__languages)
        index = self.cbbReferenceLanguage.findText(self.__reference_language)
        self.cbbReferenceLanguage.setCurrentIndex(index if index >= 0 else 0)
        self.cbbReferenceLanguage.blockSignals(False)
        self.__reference_language = self.cbbReferenceLanguage.currentText()
        self.log_state()

    # 当前状态记录到日志（表格上不再放提示标签）
    def log_state(self):
        Logger().debug(
            f'多语言对比：{len(self.__rows)} 个非 SFX Sound，{len(self.__languages)} 种语言，'
            f'{self.__standard.name}，宽容度 {self.__tolerance} dB，'
            f'参考语言 {self.__reference_language or "未选择"}'
        )

    # 列号 -> (语言, 指标)；不是语言列时返回 (None, None)
    def metric_at_column(self, column: int):
        offset = column - COL_METRIC_START
        if offset < 0:
            return None, None
        language = self.__languages[offset // 2]
        return language, (METRIC_LOUDNESS if offset % 2 == 0 else METRIC_DURATION)

    # 某一行的数据（按选中列里存的 key 取，排序后行号会变）
    def row_data_at(self, row: int):
        item = self.tblCompare.item(row, COL_CHECK)
        key = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return next((row_data for row_data in self.__rows if row_data['key'] == key), None)

    # 某一行的对象列表（Sound + 各语言 AudioSource），供双击 / 右键使用
    def objects_at_row(self, row: int) -> list:
        row_data = self.row_data_at(row)
        if row_data is None:
            return []
        return [row_data['sound']] + list(row_data['sources'].values())

    # 排序后表格行会变，按 key 重新对齐行号
    def sync_row_indexes(self, *_args):
        for row in range(self.tblCompare.rowCount()):
            row_data = self.row_data_at(row)
            if row_data is not None:
                row_data['row'] = row

    # 勾选的行（分析 / 统一响度只处理这些行）
    def get_selected_rows(self) -> list:
        selected = []
        for row in range(self.tblCompare.rowCount()):
            check_item = self.tblCompare.item(row, COL_CHECK)
            if check_item is None or check_item.checkState() != Qt.CheckState.Checked:
                continue
            row_data = self.row_data_at(row)
            if row_data is not None:
                selected.append(row_data)
        return selected

    # 全选 checkbox：勾选则全部选中，取消则全部取消
    def toggle_select_all(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.tblCompare.rowCount()):
            check_item = self.tblCompare.item(row, COL_CHECK)
            if check_item is not None:
                check_item.setCheckState(state)

    # 测量勾选行的响度与时长（都按 Source Editor 的裁剪区间），带进度条
    def analyze_loudness(self):
        if self.is_busy():
            return
        rows = self.get_selected_rows()
        if not rows:
            Logger().warning('没有勾选任何 Sound，请先勾选需要分析的 Sound')
            return
        items = [(row_data, language, row_data['sources'][language])
                 for row_data in rows for language in self.__languages
                 if language in row_data['sources']]
        if not items:
            return
        self.__analyzed = [None] * len(items)
        batch_processor.create_async(
            items,
            self.measure_item,
            '测量多语言响度与时长',
            on_finished=self.on_measured,
        )

    # 工作线程：测量单个 AudioSource 的（裁剪后）响度与时长
    def measure_item(self, index: int, item: tuple):
        row_data, language, source = item
        # 裁剪属性随行数据一起带过来，测量阶段不再查询 WAAPI
        properties = row_data.get('properties', {}).get(source.id, {})
        loudness, _duration = audio_source_utils.measure_trimmed_audio(source, self.__standard, properties)
        duration = audio_source_utils.get_trimmed_duration(source, properties)
        self.__analyzed[index] = (row_data['key'], language, loudness, duration)
        return True

    # 主线程：把测量结果填入表格
    def on_measured(self):
        self.sync_row_indexes()
        row_data_by_key = {row_data['key']: row_data for row_data in self.__rows}
        measured_keys = set()
        for result in self.__analyzed:
            if result is None:
                continue
            key, language, loudness, duration = result
            row_data = row_data_by_key.get(key)
            if row_data is None:
                continue
            measured_keys.add(key)
            row_data['loudness'][language] = loudness
            row_data['duration'][language] = duration
        self.refresh_metric_cells(measured_keys)
        Logger().info(f'多语言测量完成，共 {len(measured_keys)} 个 Sound')

    # 刷新单元格：keys 为空表示刷新全部
    def refresh_metric_cells(self, keys=None):
        for row_data in self.__rows:
            if keys is not None and row_data['key'] not in keys:
                continue
            for offset, language in enumerate(self.__languages):
                if language not in row_data['sources']:
                    continue
                loudness = row_data['loudness'].get(language)
                duration = row_data['duration'].get(language)
                loudness_item = NumberTableItem(self.format_loudness(loudness), loudness)
                duration_item = NumberTableItem(self.format_duration(duration), duration)
                if language in row_data.get('ambiguous', {}):
                    names = '、'.join(row_data['ambiguous'][language])
                    tip = f'{language} 下有多个 AudioSource（{names}），这里只统计第一个'
                    loudness_item.setToolTip(tip)
                    duration_item.setToolTip(tip)
                self.tblCompare.setItem(row_data['row'], COL_METRIC_START + offset * 2, loudness_item)
                self.tblCompare.setItem(row_data['row'], COL_METRIC_START + offset * 2 + 1, duration_item)
        self.refresh_severity()
        resize_table_and_window(self.tblCompare, self)

    # 按参考语言刷新响度 / 时长的 severity（参考语言那一列始终是 normal）
    def refresh_severity(self):
        reference = self.__reference_language
        for row_data in self.__rows:
            reference_loudness = row_data['loudness'].get(reference)
            reference_duration = row_data['duration'].get(reference)
            for offset, language in enumerate(self.__languages):
                if language not in row_data['sources']:
                    continue
                loudness_item = self.tblCompare.item(row_data['row'], COL_METRIC_START + offset * 2)
                duration_item = self.tblCompare.item(row_data['row'], COL_METRIC_START + offset * 2 + 1)
                self.__set_severity(loudness_item, self.loudness_severity(
                    row_data['loudness'].get(language), reference_loudness))
                self.__set_severity(duration_item, self.duration_severity(
                    row_data['duration'].get(language), reference_duration))

    # 把 severity 写进单元格背景（由 SeverityTableDelegate + material.css 渲染）
    @staticmethod
    def __set_severity(item, severity):
        if item is not None:
            item.setData(Qt.ItemDataRole.BackgroundRole, severity)

    # 响度偏差：超过宽容度 warning，超过两倍宽容度 danger；无信号不判
    def loudness_severity(self, loudness, reference_loudness):
        if loudness is None or reference_loudness is None:
            return CellSeverity.Normal
        if loudness <= audio_utils.MIN_LOUDNESS_DB or reference_loudness <= audio_utils.MIN_LOUDNESS_DB:
            return CellSeverity.Normal
        delta = abs(loudness - reference_loudness)
        if delta > 2 * self.__tolerance:
            return CellSeverity.Danger
        if delta > self.__tolerance:
            return CellSeverity.Warning
        return CellSeverity.Normal

    # 时长偏差（相对参考语言）：超过 20% warning，超过 50% danger
    @staticmethod
    def duration_severity(duration, reference_duration):
        if not duration or not reference_duration:
            return CellSeverity.Normal
        ratio = abs(duration - reference_duration) / reference_duration
        if ratio > DURATION_DANGER_RATIO:
            return CellSeverity.Danger
        if ratio > DURATION_WARNING_RATIO:
            return CellSeverity.Warning
        return CellSeverity.Normal

    # 响度显示文本（未测量 / 无信号 / 数值 + 单位）
    def format_loudness(self, loudness) -> str:
        if loudness is None:
            return ''
        if loudness <= audio_utils.MIN_LOUDNESS_DB:
            return '无信号'
        return f'{loudness:.1f} {self.__standard.unit}'

    # 时长显示文本（秒，只读）
    @staticmethod
    def format_duration(duration) -> str:
        if duration is None:
            return ''
        return f'{duration:.3f} s'

    # 单元格对应的对象（语言列对应该语言的 AudioSource，其它列对应该行的 Sound）
    def object_at_cell(self, row_data: dict, column: int):
        language, _metric = self.metric_at_column(column)
        if language is None:
            return row_data['sound']
        return row_data['sources'].get(language)

    # 统一响度：以参考语言为基准，把同一行其它语言的音频调成和参考语言一样响；
    # 同一个文件可能被多个 AudioSource 共用，按文件路径去重，避免重复加增益
    def unify_loudness(self):
        if self.is_busy():
            return
        reference = self.__reference_language
        if not reference:
            QMessageBox.warning(self, '统一响度', '请先选择参考语言。')
            return
        pending = {}
        skipped_count = 0
        no_reference_count = 0
        for row_data in self.get_selected_rows():
            reference_loudness = row_data['loudness'].get(reference)
            if reference_loudness is None or reference_loudness <= audio_utils.MIN_LOUDNESS_DB:
                no_reference_count += 1
                continue
            for language in self.__languages:
                if language == reference:
                    continue
                source = row_data['sources'].get(language)
                loudness = row_data['loudness'].get(language)
                if source is None or loudness is None or loudness <= audio_utils.MIN_LOUDNESS_DB:
                    continue
                if abs(reference_loudness - loudness) <= self.__tolerance:
                    skipped_count += 1
                    continue
                file_path = audio_source_utils.get_source_absolute_path(source)
                if not file_path or file_path in pending:
                    continue
                pending[file_path] = {'path': file_path, 'source': source, 'loudness': loudness,
                                      'target': reference_loudness}
        if skipped_count:
            Logger().info(f'{skipped_count} 个音频与参考语言已相差 {self.__tolerance} dB 以内，跳过')
        if no_reference_count:
            Logger().warning(f'{no_reference_count} 个 Sound 缺少参考语言 [{reference}] 的响度，已跳过')
        items = list(pending.values())
        if not items:
            message = f'其它语言已经和参考语言 [{reference}] 一致，不需要调整。'
            Logger().info(message)
            QMessageBox.information(self, '统一响度', message)
            return
        self.__adjust_results = [None] * len(items)
        batch_processor.create_async(
            items,
            self.adjust_item,
            '统一响度',
            on_finished=self.on_adjust_finished,
        )

    # 工作线程：按参考语言响度调整单个音频文件（裁剪区间保持不变）
    def adjust_item(self, index: int, item: dict):
        source = item['source']
        current = item['loudness']
        file_path = item['path']
        if current <= audio_utils.MIN_LOUDNESS_DB or not os.path.exists(file_path):
            self.__adjust_results[index] = {'item': item, 'status': '无信号'}
            return True
        with soundfile.SoundFile(file_path) as sound_file:
            data = sound_file.read(dtype='float32')
            samplerate = sound_file.samplerate
            subtype = sound_file.subtype
            total_frames = sound_file.frames
        start_frame, end_frame = audio_source_utils.get_trimmed_frame_range(
            source, total_frames, samplerate)
        # 削波保护只看实际播放的区间：被裁剪掉的部分不影响听感
        played = data[start_frame:end_frame]
        peak = float(numpy.max(numpy.abs(played))) if played.size else 0.0
        applied_gain = item['target'] - current
        limited = False
        if peak > 0 and applied_gain > 0:
            # 提升响度时限制增益，保证峰值不超过上限，避免削波
            limit_gain = 20 * math.log10(CLIP_LIMIT_PEAK / peak)
            if applied_gain > limit_gain:
                applied_gain = limit_gain
                limited = True
        factor = 10 ** (applied_gain / 20)
        numpy.clip(data * factor, -CLIP_LIMIT_PEAK, CLIP_LIMIT_PEAK, out=data)
        soundfile.write(file_path, data, samplerate, subtype=subtype)
        new_loudness, _duration = audio_source_utils.measure_trimmed_audio(source, self.__standard)
        self.__adjust_results[index] = {
            'item': item,
            'old_loudness': current,
            'new_loudness': new_loudness,
            'limited': limited,
        }
        return True

    # 主线程：重测整表并提示被限幅的音频
    def on_adjust_finished(self):
        self.sync_row_indexes()
        limited_entries = [result for result in self.__adjust_results
                           if result and result.get('limited') and result.get('new_loudness') is not None]
        adjusted_count = len([result for result in self.__adjust_results if result])
        Logger().info(
            f'已按参考语言 [{self.__reference_language}] 统一 {adjusted_count} 个音频，正在重新测量')
        self.analyze_loudness()
        if limited_entries:
            lines = [
                f"{os.path.basename(result['item']['path'])}："
                f"{result['old_loudness']:.1f} → {result['new_loudness']:.1f} {self.__standard.unit}"
                for result in limited_entries[:15]
            ]
            QMessageBox.warning(
                self,
                '统一响度',
                f'以下 {len(limited_entries)} 个音频按参考语言响度会产生削波，'
                '已调整为不削波的最大响度：\n\n' + '\n'.join(lines),
            )

    # 行右键菜单：复制单元格 / 通用对象动作（语言列对应该语言的 AudioSource）
    def show_context_menu(self, position):
        item = self.tblCompare.itemAt(position)
        if item is None:
            return
        row_data = self.row_data_at(item.row())
        if row_data is None:
            return
        target = self.object_at_cell(row_data, item.column())
        menu = QMenu(self)
        if item.text():
            menu.addAction('复制', lambda: clipboard.copy(item.text()))
        if target is not None:
            add_common_object_actions(menu, target, self)
        if not menu.actions():
            return
        menu.exec(self.tblCompare.viewport().mapToGlobal(position))
