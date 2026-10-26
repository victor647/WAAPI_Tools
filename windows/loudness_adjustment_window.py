from windows.base_analysis_dialog import BaseAnalysisDialog
import math
import os

import clipboard
import numpy
import soundfile
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QMenu,
    QMessageBox,
    QTableWidgetItem,
)

import globals.global_variables as gv
from libraries.multi_thread import batch_processor
from libraries.table_view.table_number_item import NumberTableItem
from libraries.table_view.table_cell_data import CellSeverity
from libraries.table_view.table_severity_delegate import SeverityTableDelegate
from libraries.utils import audio_utils, io_utils, path_utils, theme_utils, user_config
from libraries.utils.qt_utils import resize_table_and_window
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import audio_source_utils, mixing_utils, project_utils
from libraries.utils.wwise import waapi_utils
from libraries.wwise_object import WwiseObjectType
from table.wwise_table_context_menu import select_row_objects
from ui.LoudnessAdjustment_ui import Ui_LoudnessAdjustment
from windows.audio_preview_window import AudioPreviewWindow
from windows.loudness_detail_window import DetailChain, LoudnessDetailWindow

WINDOW_SETTINGS_KEY = 'loudness_adjustment'

# 不出现削波的音频峰值上限
CLIP_LIMIT_PEAK = 1.0

# 削波提示里最多列出的音频条数
LIMITED_LIST_LIMIT = 15

# 表格列
COL_CHECK = 0
COL_PATH = 1
COL_LOUDNESS = 2
COL_OBJECT_GAIN = 3
COL_BUS_GAIN = 4
COL_FINAL_LOUDNESS = 5
COL_STATUS = 6

# 响度标准下拉框的项顺序（与 ui/LoudnessAdjustment.ui 中的条目顺序一致）
LOUDNESS_STANDARDS = (audio_utils.LoudnessStandard.RMS, audio_utils.LoudnessStandard.LUFS)


# 响度调整工具：统一表格中所有音频的响度
class LoudnessAdjustmentWindow(BaseAnalysisDialog, Ui_LoudnessAdjustment):

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # 输入对象在 populate_sources 里从主窗口临时获取，保证与表格同步
        self.__active_objects: list = []
        # 表格每行的数据：{'key', 'row', 'path', 'wwise_objects', 'loudness', 'original_loudness',
        #                 'object_gain', 'bus_gain', 'gain_details', 'adjusted', 'limited'}
        self.__entries = []
        self.__scanned_paths = []
        self.__analysis_items = []
        self.__analysis_results = []
        self.__adjust_results = []
        self.__gain_cache = mixing_utils.GainOffsetCache()
        self.__standard = audio_utils.LoudnessStandard.RMS
        self.__loading_settings = False
        self.setup_triggers()
        self.tblAudioList.setItemDelegate(SeverityTableDelegate(self.tblAudioList))
        self.load_user_settings()
        self.__sync_gain_columns()
        # 等窗口出现后再异步读取对象背后的源文件，避免呼出前阻塞
        QTimer.singleShot(0, self.populate_sources)

    def setup_triggers(self):
        self.btnImportFiles.clicked.connect(self.import_files)
        self.btnImportFolder.clicked.connect(self.import_folder)
        self.btnExportList.clicked.connect(self.export_list)
        self.btnImportList.clicked.connect(self.import_list)
        self.btnAnalyzeSample.clicked.connect(self.analyze_sample_loudness)
        self.btnAnalyzeObject.clicked.connect(self.analyze_object_adjustment)
        self.btnAnalyzeAll.clicked.connect(self.analyze_all)
        self.btnUnifyLoudness.clicked.connect(self.unify_loudness)
        self.cbxSelectAll.toggled.connect(self.toggle_select_all)
        self.cbbLoudnessStandard.currentIndexChanged.connect(self.on_loudness_standard_changed)
        self.spbTargetLoudness.valueChanged.connect(self.save_user_settings)
        self.spbTolerance.valueChanged.connect(self.save_user_settings)
        # 目标响度 / 宽容度变化后重新判定状态列
        self.spbTargetLoudness.valueChanged.connect(self.refresh_status_column)
        self.spbTolerance.valueChanged.connect(self.refresh_status_column)
        self.tblAudioList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tblAudioList.customContextMenuRequested.connect(self.show_entry_context_menu)
        self.tblAudioList.itemDoubleClicked.connect(self.on_row_double_clicked)
        # 表格支持按列排序：排序会移动行，排序后要重新对齐条目记录的行号
        self.tblAudioList.setSortingEnabled(True)
        self.tblAudioList.horizontalHeader().sortIndicatorChanged.connect(self.sync_entry_rows)

    # 排序后表格行会变，按 COL_CHECK 里存的条目 key 重新刷新每个条目的行号
    def sync_entry_rows(self, *_args):
        entry_by_key = {entry['key']: entry for entry in self.__entries}
        for row in range(self.tblAudioList.rowCount()):
            key_item = self.tblAudioList.item(row, COL_CHECK)
            key = key_item.data(Qt.ItemDataRole.UserRole) if key_item is not None else None
            entry = entry_by_key.get(key)
            if entry is not None:
                entry['row'] = row

    # 某一行的条目（按 COL_CHECK 里存的 key 取，排序后行号会变）
    def get_entry_at_row(self, row: int):
        item = self.tblAudioList.item(row, COL_CHECK)
        key = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return self.get_entry_by_key(key)

    # 按 key 取条目（批处理结果回填时用，避免依赖会随排序变化的行号）
    def get_entry_by_key(self, key):
        return next((entry for entry in self.__entries if entry['key'] == key), None)

    # 双击：音量调整两列等同右键「详细」，其它列在 Wwise 中选中对应对象
    def on_row_double_clicked(self, item: QTableWidgetItem):
        entry = self.get_entry_at_row(item.row())
        if entry is None:
            return
        if item.column() in (COL_OBJECT_GAIN, COL_BUS_GAIN):
            chain = DetailChain.Object if item.column() == COL_OBJECT_GAIN else DetailChain.Bus
            self.show_entry_detail(entry, chain)
            return
        select_row_objects(entry['wwise_objects'])

    # 表格行右键菜单：路径列给复制 / 预览，音量调整列给详细
    def show_entry_context_menu(self, position):
        item = self.tblAudioList.itemAt(position)
        if item is None:
            return
        row = item.row()
        entry = self.get_entry_at_row(row)
        if entry is None:
            return
        menu = QMenu(self)
        copy_action = preview_action = detail_action = None
        if item.text():
            copy_value = entry['path'] if item.column() == COL_PATH else item.text()
            copy_action = menu.addAction('复制')
        if item.column() == COL_PATH:
            preview_action = menu.addAction('预览')
        if item.column() in (COL_OBJECT_GAIN, COL_BUS_GAIN):
            detail_action = menu.addAction('详细')
        if not menu.actions():
            return
        chosen = menu.exec(self.tblAudioList.viewport().mapToGlobal(position))
        if copy_action is not None and chosen == copy_action:
            clipboard.copy(copy_value)
        elif preview_action is not None and chosen == preview_action:
            self.preview_entry(entry)
        elif detail_action is not None and chosen == detail_action:
            # 在对象列点详细只看对象链路，在总线列点详细只看总线链路
            chain = DetailChain.Object if item.column() == COL_OBJECT_GAIN else DetailChain.Bus
            self.show_entry_detail(entry, chain)

    # 打开该行音频的波形预览窗口
    def preview_entry(self, entry: dict):
        AudioPreviewWindow(entry['path'], self).show()

    # 打开该行的音量调整明细窗口（逐级列出指定链路上每个属性的调整值）
    def show_entry_detail(self, entry: dict, chain: DetailChain):
        if not entry['wwise_objects']:
            Logger().warning(f'{os.path.basename(entry["path"])} 不是来自 Wwise 对象，没有音量调整明细')
            return
        detail = LoudnessDetailWindow(entry['path'], entry['wwise_objects'], entry['loudness'], chain,
                                      self.__standard.unit)
        detail.exec()
        # 在明细里改过对象的属性时，重算所有引用这些对象的行
        self.refresh_objects(detail.modified_objects())

    # 重算所有引用了指定对象的行（对象/总线音量调整 + 最终响度 + 状态）
    def refresh_objects(self, objects: list):
        if not objects or self.is_busy():
            return
        modified_ids = {obj.id for obj in objects}
        # 属性刚被改过，必须重新读一遍，不能复用旧缓存
        cache = mixing_utils.GainOffsetCache()
        # 改动可能落在对象的上级或总线上，按整条链路判断是否受影响
        targets = [
            entry for entry in self.__entries
            if any(modified_ids & cache.get_chain_ids(obj) for obj in entry['wwise_objects'])
        ]
        if not targets:
            return
        self.__analysis_items = targets
        self.__analysis_results = [{} for _ in targets]
        self.__gain_cache = cache
        Logger().info(f'音量调整已改动，重新计算 {len(targets)} 个音频的调整值')
        batch_processor.create_async(
            targets,
            self.analyze_object,
            '刷新音量调整',
            on_finished=self.on_refresh_finished,
            on_interrupted=self.on_refresh_finished,
        )

    # 主线程：把重算结果写回表格
    def on_refresh_finished(self):
        self.sync_entry_rows()
        for index, entry in enumerate(self.__analysis_items):
            gains = self.__analysis_results[index].get('gains')
            if not gains:
                continue
            self.__fill_gain_cells(entry, gains)
            self.__update_loudness_cells(entry)
        self.refresh_status_column()
        resize_table_and_window(self.tblAudioList, self)

    # 读取持久化的目标响度与宽容度
    def load_user_settings(self):
        self.__loading_settings = True
        saved = user_config.get_window_settings(WINDOW_SETTINGS_KEY)
        target = saved.get('target_loudness_db', self.spbTargetLoudness.value())
        self.spbTargetLoudness.setValue(float(target))
        tolerance = saved.get('tolerance_db', self.spbTolerance.value())
        self.spbTolerance.setValue(float(tolerance))
        standard = str(saved.get('loudness_standard', audio_utils.LoudnessStandard.RMS.value))
        index = next((i for i, item in enumerate(LOUDNESS_STANDARDS) if item.value == standard), 0)
        self.cbbLoudnessStandard.setCurrentIndex(index)
        self.__sync_loudness_standard()
        self.__loading_settings = False

    # 保存目标响度、宽容度与响度标准
    def save_user_settings(self, *_args):
        user_config.set_window_settings(WINDOW_SETTINGS_KEY, {
            'target_loudness_db': self.spbTargetLoudness.value(),
            'tolerance_db': self.spbTolerance.value(),
            'loudness_standard': self.__loudness_standard().value,
        })

    # 当前选择的响度标准
    def __loudness_standard(self) -> audio_utils.LoudnessStandard:
        index = self.cbbLoudnessStandard.currentIndex()
        if not 0 <= index < len(LOUDNESS_STANDARDS):
            return audio_utils.LoudnessStandard.RMS
        return LOUDNESS_STANDARDS[index]

    # 响度标准变化：刷新单位显示、保存设置，并自动重新分析已测过响度的音频
    def on_loudness_standard_changed(self, _index: int):
        if self.__loading_settings:
            return
        self.__sync_loudness_standard()
        self.save_user_settings()
        standard_name = self.__standard.name
        targets = [entry for entry in self.__entries if entry['loudness'] is not None]
        if not targets:
            Logger().info(f'响度标准已切换为 {standard_name}')
            return
        Logger().info(f'响度标准已切换为 {standard_name}，正在重新分析 {len(targets)} 个音频的原始样本')
        self._run_analysis(self.analyze_sample, '分析原始样本', do_sample=True, do_object=False,
                           entries=targets)

    # 目标响度后缀跟随响度标准（RMS 用 dBFS、LUFS 用 LUFS）
    def __sync_loudness_standard(self):
        self.__standard = self.__loudness_standard()
        self.spbTargetLoudness.setSuffix(f' {self.__standard.unit}')

    # 是否已有批处理在运行（避免并发批处理覆盖 gv.batch_processor）
    @staticmethod
    def is_busy() -> bool:
        return batch_processor.is_busy()

    # 从主窗口对象解析源文件并加入表格（不做任何分析，音量调整由「分析对象调整」负责）
    def populate_sources(self):
        if self.is_busy():
            return
        # 只取主窗口「选中」列已勾选对象下的 AudioSource
        self.__active_objects = self.collect_analysis_targets(WwiseObjectType.AudioSource)
        if not self.__active_objects:
            Logger().warning('勾选对象下没有可用于「响度调整」的 AudioSource')
            return
        self.__scanned_paths = [None] * len(self.__active_objects)
        self.__prefetched_pages: set = set()
        self.__paths_by_id: dict = {}
        batch_processor.create_async(
            self.__active_objects,
            self.resolve_source_path,
            '读取源文件',
            'name',
            on_finished=self.on_sources_resolved,
        )

    # 工作线程：解析单个 Wwise 对象背后的源文件路径；路径按所在分页惰性预取
    def resolve_source_path(self, index: int, obj):
        self.__prefetch_source_paths(index)
        file_path = self.__paths_by_id.get(obj.id, {}).get('originalFilePath')
        if not file_path or not os.path.exists(file_path):
            Logger().warning(f'找不到源文件：{obj.name}')
            return True
        self.__scanned_paths[index] = (file_path, obj)
        return True

    # 预取 index 所在分页里所有对象的源文件路径
    def __prefetch_source_paths(self, index: int):
        start, end = waapi_utils.page_bounds(self.__active_objects, index)
        if start in self.__prefetched_pages:
            return
        self.__prefetched_pages.add(start)
        self.__paths_by_id.update(
            waapi_utils.get_objects_properties(self.__active_objects[start:end], ['originalFilePath']))

    # 主线程：把解析出的源文件加入表格，并记住对应的 Wwise 对象供后续分析使用
    def on_sources_resolved(self):
        resolved = [result for result in self.__scanned_paths if result]
        if not resolved:
            Logger().warning('没有找到任何源文件')
            QMessageBox.warning(
                self,
                '响度调整',
                f'{len(self.__active_objects)} 个 AudioSource 都没有解析出可用的源文件：\n'
                '对象的原始 wav 可能没有导入、已被移动，或工程路径读取失败。\n\n'
                '可以先在主窗口双击进 Wwise 确认这些对象的源文件状态，'
                '或者用「导入文件 / 导入文件夹」直接处理磁盘上的音频。',
            )
            return
        # 同一个音频文件可能被多个 Wwise 对象引用，这里按路径汇总成列表
        objects = {}
        for file_path, obj in resolved:
            objects.setdefault(os.path.normcase(os.path.abspath(file_path)), []).append(obj)
        added = self.append_files([file_path for file_path, _obj in resolved], objects)
        Logger().info(f'读取源文件完成，新增 {len(added)} 个音频文件')

    # 导入音频文件
    def import_files(self):
        if self.is_busy():
            return
        selected = QFileDialog.getOpenFileNames(self, '选择音频文件', '', 'WAV(*.wav)')
        if not selected[0]:
            return
        added = self.append_files(selected[0])
        Logger().info(f'导入完成，新增 {len(added)} 个音频文件')

    # 导出列表：有 Wwise 对象的按工程相对路径（originalRelativeFilePath）导出，
    # 手工导入、没有 Wwise 对象的音频才用绝对路径
    def export_list(self):
        if not self.__entries:
            Logger().warning('表格中没有可导出的音频')
            return
        lines = []
        for entry in self.__entries:
            relative_path = audio_source_utils.to_originals_relative_path(entry['path']) \
                if entry['wwise_objects'] else entry['path']
            # 相对路径转换失败（不在 Originals 下）时退回绝对路径
            lines.append(relative_path if not os.path.isabs(relative_path) else entry['path'])
        io_utils.export_to_txt(lines, 'WAAPI_Tools_AudioList')
        Logger().info(f'已导出 {len(lines)} 条音频路径')

    # 导入列表：相对路径按工程 Originals 目录还原，并尽量找回引用该文件的 Wwise 对象
    def import_list(self):
        if self.is_busy():
            return
        lines = io_utils.import_from_txt()
        if not lines:
            return
        originals_folder = project_utils.get_originals_folder()
        paths = []
        objects = {}
        missing = []
        for line in lines:
            text = str(line).strip()
            if not text:
                continue
            absolute_path = text if os.path.isabs(text) else os.path.join(originals_folder, text)
            if not os.path.exists(absolute_path):
                missing.append(text)
                continue
            paths.append(absolute_path)
            if not os.path.isabs(text):
                # 相对路径来自工程：顺便把引用该文件的 AudioSource 挂上，音量调整列才能用
                sources = waapi_utils.find_audio_sources_by_original_path(text)
                if sources:
                    objects[os.path.normcase(os.path.abspath(absolute_path))] = sources
        added = self.append_files(paths, objects)
        Logger().info(f'导入列表完成，新增 {len(added)} 个音频文件'
                      + (f'，{len(missing)} 条路径不存在已跳过' if missing else ''))
        if missing:
            Logger().warning('以下路径在磁盘上不存在：\n' + '\n'.join(missing[:10]))

    # 导入文件夹里的所有音频文件（异步 + 进度条）
    def import_folder(self):
        if self.is_busy():
            return
        folder = QFileDialog.getExistingDirectory(self, '选择音频文件夹')
        if not folder:
            return
        wav_paths = []
        for root, _dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith('.wav'):
                    wav_paths.append(os.path.join(root, file))
        if not wav_paths:
            Logger().warning('文件夹中没有找到 wav 文件')
            return
        self.__scanned_paths = [None] * len(wav_paths)
        batch_processor.create_async(
            wav_paths,
            self.collect_folder_file,
            '导入音频文件',
            on_finished=self.on_folder_import_finished,
        )

    # 工作线程：校验文件夹中扫描到的音频文件
    def collect_folder_file(self, index: int, file_path: str):
        if os.path.exists(file_path):
            self.__scanned_paths[index] = file_path
        return True

    # 主线程：把文件夹中扫到的文件加入表格
    def on_folder_import_finished(self):
        file_paths = [path for path in self.__scanned_paths if path]
        added = self.append_files(file_paths)
        Logger().info(f'文件夹导入完成，新增 {len(added)} 个音频文件')

    # 主线程：按绝对路径去重后追加表格行，返回实际新增的文件路径；
    # objects 为 {normcase 绝对路径: [引用该文件的 Wwise 对象]}，手工导入的音频文件没有该信息
    def append_files(self, file_paths: list, objects: dict = None) -> list:
        objects = objects or {}
        known_keys = {entry['key'] for entry in self.__entries}
        added_paths = []
        for file_path in file_paths:
            absolute_path = os.path.abspath(file_path)
            key = os.path.normcase(absolute_path)
            if key in known_keys or not os.path.exists(absolute_path):
                continue
            wwise_objects = list(objects.get(key) or [])
            known_keys.add(key)
            row = len(self.__entries)
            self.tblAudioList.insertRow(row)
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            # 新行跟随「全选」状态（默认勾选）
            check_item.setCheckState(
                Qt.CheckState.Checked if self.cbxSelectAll.isChecked() else Qt.CheckState.Unchecked
            )
            # 存一份条目 key：排序后据此把行号重新对回条目
            check_item.setData(Qt.ItemDataRole.UserRole, key)
            self.tblAudioList.setItem(row, COL_CHECK, check_item)
            display_path = path_utils.get_display_path(
                audio_source_utils.to_originals_relative_path(absolute_path)
            )
            path_item = QTableWidgetItem(display_path)
            # 文件对应的 Wwise 对象路径：可能被多个对象引用，鼠标悬停即可看到
            if wwise_objects:
                path_item.setToolTip('引用对象：\n' + '\n'.join(obj.path for obj in wwise_objects))
            self.tblAudioList.setItem(row, COL_PATH, path_item)
            self.tblAudioList.setItem(row, COL_LOUDNESS, QTableWidgetItem(''))
            self.tblAudioList.setItem(row, COL_OBJECT_GAIN, QTableWidgetItem(''))
            self.tblAudioList.setItem(row, COL_BUS_GAIN, QTableWidgetItem(''))
            self.tblAudioList.setItem(row, COL_FINAL_LOUDNESS, QTableWidgetItem(''))
            self.tblAudioList.setItem(row, COL_STATUS, QTableWidgetItem(''))
            self.__entries.append({
                'key': key,
                'row': row,
                'path': absolute_path,
                'wwise_objects': wwise_objects,
                'loudness': None,
                'original_loudness': None,
                'object_gain': None,
                'bus_gain': None,
                'gain_details': [],
                'adjusted': False,
                'limited': False,
            })
            added_paths.append(absolute_path)
        # 排序开启时插入行后行序可能变化，统一重新对齐一次
        self.sync_entry_rows()
        self.__sync_gain_columns()
        resize_table_and_window(self.tblAudioList, self)
        return added_paths

    # 表格里没有任何来自 Wwise 的音频时（导入文件/文件夹模式），隐藏 Wwise 调整相关的列
    def __sync_gain_columns(self):
        has_wwise_source = any(entry['wwise_objects'] for entry in self.__entries)
        for column in (COL_OBJECT_GAIN, COL_BUS_GAIN, COL_FINAL_LOUDNESS):
            self.tblAudioList.setColumnHidden(column, not has_wwise_source)

    # 返回所有勾选行的数据（按 key 映射，排序后依然正确）
    def get_selected_entries(self) -> list:
        entries = []
        for row in range(self.tblAudioList.rowCount()):
            check_item = self.tblAudioList.item(row, COL_CHECK)
            if check_item is None or check_item.checkState() != Qt.CheckState.Checked:
                continue
            entry = self.get_entry_at_row(row)
            if entry is not None:
                entries.append(entry)
        return entries

    # 全选 checkbox：勾选则全部选中，取消则全部取消
    def toggle_select_all(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.tblAudioList.rowCount()):
            check_item = self.tblAudioList.item(row, COL_CHECK)
            if check_item is not None:
                check_item.setCheckState(state)

    # 分析勾选音频的原始样本响度（响度列）
    def analyze_sample_loudness(self):
        self._run_analysis(self.analyze_sample, '分析原始样本', do_sample=True, do_object=False)

    # 分析勾选音频所在对象与总线的音量调整（对象音量调整 / 总线音量调整列）
    def analyze_object_adjustment(self):
        self._run_analysis(self.analyze_object, '分析对象调整', do_sample=False, do_object=True)

    # 一键分析：原始样本 + 对象调整
    def analyze_all(self):
        self._run_analysis(self.analyze_all_in_one, '分析响度', do_sample=True, do_object=True)

    # 启动一次异步分析；entries 为空时取勾选行（切换响度标准时会直接传入已分析过的行）
    def _run_analysis(self, processor, title: str, do_sample: bool, do_object: bool, entries: list = None):
        if self.is_busy():
            return
        if entries is None:
            entries = self.get_selected_entries()
            if not entries:
                Logger().warning('没有勾选任何音频，请先勾选需要分析的音频')
                return
        if not entries:
            return
        if do_object:
            # 每次对象分析都用新缓存，避免读到旧的工程数据
            self.__gain_cache = mixing_utils.GainOffsetCache()
        self.__analysis_items = entries
        self.__analysis_results = [{} for _ in entries]
        for entry in entries:
            if do_sample:
                self.tblAudioList.setItem(entry['row'], COL_LOUDNESS, QTableWidgetItem('分析中…'))
                self.tblAudioList.setItem(entry['row'], COL_FINAL_LOUDNESS, QTableWidgetItem(''))
            if do_object:
                self.tblAudioList.setItem(entry['row'], COL_OBJECT_GAIN, QTableWidgetItem('分析中…'))
                self.tblAudioList.setItem(entry['row'], COL_BUS_GAIN, QTableWidgetItem('分析中…'))
        batch_processor.create_async(
            entries,
            processor,
            title,
            on_finished=self.on_analysis_finished,
            # 中途异常时也走一次收尾，避免单元格停在「分析中…」
            on_interrupted=self.on_analysis_finished,
        )

    # 工作线程：测量单个音频文件的响度
    def analyze_sample(self, index: int, entry: dict):
        self.__analysis_results[index]['loudness'] = audio_utils.calculate_loudness_by_standard(
            entry['path'], self.__standard
        )
        return True

    # 工作线程：累加每个引用对象链路与总线链路的音量调整；没有对应 Wwise 对象时跳过
    def analyze_object(self, index: int, entry: dict):
        if not entry['wwise_objects']:
            return True
        details = []
        for obj in entry['wwise_objects']:
            object_gain, bus_gain = mixing_utils.get_gain_offsets(obj, self.__gain_cache)
            details.append((obj, object_gain, bus_gain))
        self.__analysis_results[index]['gains'] = details
        return True

    # 工作线程：同时做样本响度与对象调整
    def analyze_all_in_one(self, index: int, entry: dict):
        self.analyze_sample(index, entry)
        self.analyze_object(index, entry)
        return True

    # 主线程：把分析结果填入表格
    def on_analysis_finished(self):
        # 排序开启时行序可能已变，先按 key 重新对齐行号
        self.sync_entry_rows()
        analyzed_count = 0
        failed_count = 0
        missing_object_count = 0
        for index, entry in enumerate(self.__analysis_items):
            result = self.__analysis_results[index]
            loudness = result.get('loudness')
            if loudness is not None:
                entry['loudness'] = loudness
                # 原始响度作为状态列差值的基准，调整后不再变化
                entry['original_loudness'] = loudness
                # 重新分析后状态回到「需提高 / 无需处理 / 需降低」判定
                entry['adjusted'] = False
                entry['limited'] = False
                analyzed_count += 1
            elif self.tblAudioList.item(entry['row'], COL_LOUDNESS).text() == '分析中…':
                failed_count += 1
                self.tblAudioList.setItem(entry['row'], COL_LOUDNESS, QTableWidgetItem('分析失败'))
            gains = result.get('gains')
            if gains:
                self.__fill_gain_cells(entry, gains)
            elif self.tblAudioList.item(entry['row'], COL_OBJECT_GAIN).text() == '分析中…':
                if entry['wwise_objects']:
                    failed_count += 1
                else:
                    missing_object_count += 1
                self.tblAudioList.setItem(entry['row'], COL_OBJECT_GAIN, QTableWidgetItem(''))
                self.tblAudioList.setItem(entry['row'], COL_BUS_GAIN, QTableWidgetItem(''))
            self.__update_loudness_cells(entry)
        if failed_count:
            Logger().warning(f'{failed_count} 个音频分析失败')
        if missing_object_count:
            Logger().warning(f'{missing_object_count} 个音频没有对应的 Wwise 对象，未计算音量调整')
        self.refresh_status_column()
        resize_table_and_window(self.tblAudioList, self)
        Logger().info(f'分析完成，共 {len(self.__analysis_items)} 个音频，其中 {analyzed_count} 个测量到响度')

    # 主线程：把每个引用对象的调整值汇总到两列；取值不一致时显示引用对象数量
    def __fill_gain_cells(self, entry: dict, gains: list):
        entry['gain_details'] = gains
        object_gain, object_tip = self.__summarize_gain(gains, 1)
        bus_gain, bus_tip = self.__summarize_gain(gains, 2)
        entry['object_gain'] = object_gain
        entry['bus_gain'] = bus_gain
        count = len(gains)
        object_item = NumberTableItem(
            self.__format_gain(object_gain) if object_gain is not None else f'{count} 个对象',
            object_gain,
        )
        bus_item = NumberTableItem(
            self.__format_gain(bus_gain) if bus_gain is not None else f'{count} 个对象',
            bus_gain,
        )
        # 增益用主题的 success 色、减益用 danger 色
        for item, value in ((object_item, object_gain), (bus_item, bus_gain)):
            color = theme_utils.get_gain_text_color(value)
            if color:
                item.setForeground(color)
        object_item.setToolTip(object_tip)
        bus_item.setToolTip(bus_tip)
        self.tblAudioList.setItem(entry['row'], COL_OBJECT_GAIN, object_item)
        self.tblAudioList.setItem(entry['row'], COL_BUS_GAIN, bus_item)

    # 汇总某一列（对象 1 / 总线 2）在不同引用对象上的取值：一致才算得出公共值，否则返回 None
    @staticmethod
    def __summarize_gain(gains: list, offset_index: int) -> tuple:
        lines = []
        values = set()
        for obj, object_gain, bus_gain in gains:
            value = round((object_gain, bus_gain)[offset_index - 1], 1)
            values.add(value)
            lines.append(f'{obj.path}：{value:+.1f} dB')
        return (values.pop() if len(values) == 1 else None), '\n'.join(lines)

    # 把响度格式化为显示文本（单位跟随当前响度标准）
    def __format_loudness(self, loudness: float) -> str:
        if loudness <= audio_utils.MIN_LOUDNESS_DB:
            return '无信号'
        return f'{loudness:.1f} {self.__standard.unit}'

    # 把调整前后的响度差值格式化为「已提高 3.2dB」/「已降低 6dB」
    @staticmethod
    def __format_loudness_delta(original: float, adjusted: float) -> str:
        delta = adjusted - original
        if abs(delta) < 0.05:
            return '无变化'
        direction = '已提高' if delta > 0 else '已降低'
        return f'{direction}{abs(delta):.1f}'.rstrip('0').rstrip('.') + 'dB'

    # 把音量偏移格式化为「+3.0 dB」/「0 dB」；没有该信息时留空
    @staticmethod
    def __format_gain(offset) -> str:
        if offset is None:
            return ''
        if abs(offset) < 0.05:
            return '0 dB'
        return f'{offset:+.1f} dB'

    # 刷新某一行的响度与最终响度：最终响度 = 实测响度 + 对象链路偏移 + 总线链路偏移
    def __update_loudness_cells(self, entry: dict):
        # 还没测到响度时保留原有文本（可能是「分析中…」或「分析失败」）
        if entry['loudness'] is not None:
            self.tblAudioList.setItem(entry['row'], COL_LOUDNESS, NumberTableItem(
                self.__format_loudness(entry['loudness']), entry['loudness']
            ))
        self.tblAudioList.setItem(entry['row'], COL_FINAL_LOUDNESS, NumberTableItem(
            self.__format_final_loudness(entry), self.__final_loudness(entry)
        ))

    # 该行已知的链路增益合计（对象 + 总线）；未做对象调整分析或取值不唯一时返回 None
    @staticmethod
    def __gain_total(entry: dict):
        if entry['loudness'] is None or entry['object_gain'] is None or entry['bus_gain'] is None:
            return None
        return entry['object_gain'] + entry['bus_gain']

    # 最终响度的数值：实测响度 + 对象链路偏移 + 总线链路偏移；任一项缺失时返回 None
    def __final_loudness(self, entry: dict):
        gain_total = self.__gain_total(entry)
        if gain_total is None:
            return None
        return entry['loudness'] + gain_total

    # 状态判定用的响度：分析过对象调整就用最终响度，否则退回实测响度
    # （只调文件响度、不看 Wwise 调整时，也要能给出状态）
    def __status_loudness(self, entry: dict):
        final_loudness = self.__final_loudness(entry)
        return entry['loudness'] if final_loudness is None else final_loudness

    # 最终响度：只有拿到实测响度与两条链路的偏移（来自 Wwise 对象）时才有意义
    def __format_final_loudness(self, entry: dict) -> str:
        if entry['loudness'] is not None and entry['loudness'] <= audio_utils.MIN_LOUDNESS_DB:
            return '无信号'
        final_loudness = self.__final_loudness(entry)
        if final_loudness is None:
            return ''
        return f'{final_loudness:.1f} {self.__standard.unit}'

    # 按目标响度与宽容度渲染状态列：未处理时用最终响度比对，标记需提高 / 无需处理 / 需降低
    def refresh_status_column(self, *_args):
        target = self.spbTargetLoudness.value()
        tolerance = self.spbTolerance.value()
        for entry in self.__entries:
            self.tblAudioList.setItem(entry['row'], COL_STATUS, self.__status_cell(entry, target, tolerance))

    # 生成单个条目对应的状态单元格
    def __status_cell(self, entry: dict, target: float, tolerance: float) -> QTableWidgetItem:
        item = QTableWidgetItem()
        loudness = entry['loudness']
        if loudness is None:
            return item
        if loudness <= audio_utils.MIN_LOUDNESS_DB:
            item.setText('完全静音')
            item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Ignored)
            return item
        if entry['adjusted']:
            item.setText(self.__format_loudness_delta(entry['original_loudness'], loudness))
            severity = CellSeverity.Warning if entry['limited'] else CellSeverity.Success
            item.setData(Qt.ItemDataRole.BackgroundRole, severity)
            return item
        # 状态用「最终响度」判定：对象与总线上的音量调整会一起影响听感；
        # 未做对象调整分析时按实测响度判断，便于只调整文件响度的用法
        status_loudness = self.__status_loudness(entry)
        if status_loudness is None:
            return item
        delta = target - status_loudness
        if abs(delta) <= tolerance:
            item.setText('无需处理')
            item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Success)
        elif delta > 0:
            item.setText('需提高')
            item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Warning)
        else:
            item.setText('需降低')
            item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Warning)
        return item

    # 统一响度：按目标响度与当前响度的差值调整勾选的音频（宽容度内的音频不处理）
    def unify_loudness(self):
        if self.is_busy():
            return
        target = self.spbTargetLoudness.value()
        tolerance = self.spbTolerance.value()
        selected = self.get_selected_entries()
        if not selected:
            QMessageBox.warning(self, '尚未选择', '没有勾选任何音频，请先勾选需要处理的音频。')
            return
        unanalyzed_count = len([entry for entry in selected if entry['loudness'] is None])
        if unanalyzed_count:
            message = (f'勾选的 {len(selected)} 个音频中有 {unanalyzed_count} 个还没有响度分析结果。\n'
                       '请先点击「分析原始样本」或「一键分析」，分析完成后再统一响度。')
            Logger().warning(message.replace('\n', ' '))
            QMessageBox.warning(self, '尚未分析', message)
            return
        items = []
        skipped_count = 0
        for entry in selected:
            gain_total = self.__gain_total(entry)
            # 目标响度是「最终响度」口径：分析过对象调整时把链路增益算进去，
            # 没分析过（或取值不唯一）时只看文件本身，保证状态列与这里判定一致
            effective_loudness = entry['loudness'] if gain_total is None \
                else entry['loudness'] + gain_total
            if entry['loudness'] > audio_utils.MIN_LOUDNESS_DB \
                    and abs(target - effective_loudness) <= tolerance:
                skipped_count += 1
                continue
            items.append({
                'key': entry['key'],
                'row': entry['row'],
                'path': entry['path'],
                'loudness': entry['loudness'],
                'gain_total': gain_total or 0.0,
                'target': target,
            })
        if skipped_count:
            Logger().info(f'{skipped_count} 个音频已在目标响度 ±{tolerance} dB 范围内，不做处理')
        if not items:
            Logger().warning('没有需要调整的音频，请先勾选并分析响度')
            self.refresh_status_column()
            return
        self.__adjust_results = [None] * len(items)
        batch_processor.create_async(
            items,
            self.adjust_entry,
            '统一响度',
            on_finished=self.on_adjust_finished,
        )

    # 工作线程：按目标响度调整单个音频文件
    def adjust_entry(self, index: int, entry: dict):
        file_path = entry['path']
        current = entry['loudness']
        target = entry['target']
        # 目标是最终响度，链路增益由 Wwise 侧负责，文件只需要补到「目标 - 链路增益」
        file_target = target - entry.get('gain_total', 0.0)
        if current <= audio_utils.MIN_LOUDNESS_DB:
            # 完全静音的音频没有可调整的信号
            self.__adjust_results[index] = {'entry': entry, 'status': '完全静音'}
            return True
        with soundfile.SoundFile(file_path) as sound_file:
            data = sound_file.read(dtype='float32')
            samplerate = sound_file.samplerate
            subtype = sound_file.subtype
        peak = float(numpy.max(numpy.abs(data))) if data.size else 0.0
        applied_gain = file_target - current
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
        new_loudness = audio_utils.calculate_loudness_by_standard(file_path, self.__standard)
        self.__adjust_results[index] = {
            'entry': entry,
            'old_loudness': current,
            'new_loudness': new_loudness,
            'limited': limited,
            'target': target,
        }
        return True

    # 主线程：更新表格并提示被限制的音频
    def on_adjust_finished(self):
        self.sync_entry_rows()
        limited_entries = []
        adjusted_count = 0
        for result in self.__adjust_results:
            if result is None:
                continue
            entry = self.get_entry_by_key(result['entry'].get('key'))
            if entry is None:
                continue
            new_loudness = result.get('new_loudness')
            if new_loudness is None:
                continue
            entry['loudness'] = new_loudness
            entry['adjusted'] = True
            entry['limited'] = result['limited']
            self.__update_loudness_cells(entry)
            adjusted_count += 1
            if result['limited']:
                limited_entries.append(result)
        self.refresh_status_column()
        resize_table_and_window(self.tblAudioList, self)
        Logger().info(f'响度调整完成，共处理 {adjusted_count} 个音频')
        if limited_entries:
            self.__show_limited_message(limited_entries)

    # 提示因削波被限制增益的音频
    def __show_limited_message(self, limited_entries: list):
        lines = []
        for result in limited_entries[:LIMITED_LIST_LIMIT]:
            entry = result['entry']
            lines.append(
                f"{os.path.basename(entry['path'])}：{result['old_loudness']:.1f} → "
                f"{result['new_loudness']:.1f} dBFS（目标 {result['target']:.0f} dBFS）"
            )
        if len(limited_entries) > LIMITED_LIST_LIMIT:
            lines.append(f'…等共 {len(limited_entries)} 个音频')
        QMessageBox.warning(
            self,
            '响度调整',
            f'以下 {len(limited_entries)} 个音频按目标响度会产生削波，已调整为不削波的最大响度：\n\n'
            + '\n'.join(lines),
        )

    def closeEvent(self, event):
        self.save_user_settings()
        super().closeEvent(event)
