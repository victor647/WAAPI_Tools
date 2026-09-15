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
from libraries.table_view.table_cell_data import CellSeverity
from libraries.table_view.table_severity_delegate import SeverityTableDelegate
from libraries.utils import audio_utils, user_config
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import audio_source_utils
from ui.LoudnessAdjustment_ui import Ui_LoudnessAdjustment
from windows.audio_preview_window import AudioPreviewWindow

WINDOW_SETTINGS_KEY = 'loudness_adjustment'

# 不出现削波的音频峰值上限
CLIP_LIMIT_PEAK = 1.0

# 削波提示里最多列出的音频条数
LIMITED_LIST_LIMIT = 15

# 表格列
COL_CHECK = 0
COL_PATH = 1
COL_LOUDNESS = 2
COL_STATUS = 3


# 响度调整工具：统一表格中所有音频的响度
class LoudnessAdjustmentWindow(QDialog, Ui_LoudnessAdjustment):

    def __init__(self, active_objects: list):
        super().__init__()
        self.setupUi(self)
        self.__active_objects = list(active_objects)
        # 表格每行的数据：{'key', 'row', 'path', 'loudness', 'original_loudness', 'adjusted', 'limited'}
        self.__entries = []
        self.__scanned_paths = []
        self.__analyzed = []
        self.__analyzing_keys = set()
        self.__adjust_results = []
        self.setup_triggers()
        self.tblAudioList.setItemDelegate(SeverityTableDelegate(self.tblAudioList))
        self.load_user_settings()
        # 等窗口出现后再异步读取对象背后的源文件，避免呼出前阻塞
        if self.__active_objects:
            QTimer.singleShot(0, self.populate_sources)

    def setup_triggers(self):
        self.btnImportFiles.clicked.connect(self.import_files)
        self.btnImportFolder.clicked.connect(self.import_folder)
        self.btnAnalyzeLoudness.clicked.connect(self.analyze_loudness)
        self.btnUnifyLoudness.clicked.connect(self.unify_loudness)
        self.cbxSelectAll.toggled.connect(self.toggle_select_all)
        self.spbTargetLoudness.valueChanged.connect(self.save_user_settings)
        self.spbTolerance.valueChanged.connect(self.save_user_settings)
        # 目标响度 / 宽容度变化后重新判定状态列
        self.spbTargetLoudness.valueChanged.connect(self.refresh_status_column)
        self.spbTolerance.valueChanged.connect(self.refresh_status_column)
        self.tblAudioList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tblAudioList.customContextMenuRequested.connect(self.show_entry_context_menu)

    # 表格行右键菜单：复制路径 / 预览音频
    def show_entry_context_menu(self, position):
        item = self.tblAudioList.itemAt(position)
        if item is None or not 0 <= item.row() < len(self.__entries):
            return
        row = item.row()
        menu = QMenu(self)
        copy_action = menu.addAction('复制')
        preview_action = menu.addAction('预览')
        chosen = menu.exec(self.tblAudioList.viewport().mapToGlobal(position))
        if chosen == copy_action:
            clipboard.copy(self.__entries[row]['path'])
        elif chosen == preview_action:
            self.preview_entry(row)

    # 打开该行音频的波形预览窗口
    def preview_entry(self, row: int):
        if 0 <= row < len(self.__entries):
            AudioPreviewWindow(self.__entries[row]['path'], self).show()

    # 读取持久化的目标响度与宽容度
    def load_user_settings(self):
        saved = user_config.get_window_settings(WINDOW_SETTINGS_KEY)
        target = saved.get('target_loudness_db', self.spbTargetLoudness.value())
        self.spbTargetLoudness.setValue(float(target))
        tolerance = saved.get('tolerance_db', self.spbTolerance.value())
        self.spbTolerance.setValue(float(tolerance))

    # 保存目标响度与宽容度
    def save_user_settings(self, *_args):
        user_config.set_window_settings(WINDOW_SETTINGS_KEY, {
            'target_loudness_db': self.spbTargetLoudness.value(),
            'tolerance_db': self.spbTolerance.value(),
        })

    # 是否已有批处理在运行（避免并发批处理覆盖 gv.batch_processor）
    @staticmethod
    def is_busy() -> bool:
        processor = gv.batch_processor
        return bool(processor) and getattr(processor, 'isRunning', lambda: False)()

    # 从主窗口对象解析源文件并加入表格（不自动分析响度）
    def populate_sources(self):
        if self.is_busy():
            return
        self.__analyzed = [None] * len(self.__active_objects)
        batch_processor.create_async(
            self.__active_objects,
            self.resolve_source_path,
            '读取源文件',
            'name',
            on_finished=self.on_sources_resolved,
        )

    # 工作线程：解析单个 Wwise 对象背后的源文件路径
    def resolve_source_path(self, index: int, obj):
        file_path = audio_source_utils.get_source_absolute_path(obj)
        if not file_path or not os.path.exists(file_path):
            Logger().warning(f'找不到源文件：{obj.name}')
            return True
        self.__analyzed[index] = file_path
        return True

    # 主线程：把解析出的源文件加入表格
    def on_sources_resolved(self):
        file_paths = [path for path in self.__analyzed if path]
        if not file_paths:
            Logger().warning('没有找到任何源文件')
            return
        added = self.append_files(file_paths)
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

    # 主线程：按绝对路径去重后追加表格行，返回实际新增的文件路径
    def append_files(self, file_paths: list) -> list:
        known_keys = {entry['key'] for entry in self.__entries}
        added_paths = []
        for file_path in file_paths:
            absolute_path = os.path.abspath(file_path)
            key = os.path.normcase(absolute_path)
            if key in known_keys or not os.path.exists(absolute_path):
                continue
            known_keys.add(key)
            row = len(self.__entries)
            self.tblAudioList.insertRow(row)
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            check_item.setCheckState(Qt.CheckState.Checked)
            self.tblAudioList.setItem(row, COL_CHECK, check_item)
            self.tblAudioList.setItem(row, COL_PATH, QTableWidgetItem(
                audio_source_utils.to_originals_relative_path(absolute_path)
            ))
            self.tblAudioList.setItem(row, COL_LOUDNESS, QTableWidgetItem(''))
            self.tblAudioList.setItem(row, COL_STATUS, QTableWidgetItem(''))
            self.__entries.append({
                'key': key,
                'row': row,
                'path': absolute_path,
                'loudness': None,
                'original_loudness': None,
                'adjusted': False,
                'limited': False,
            })
            added_paths.append(absolute_path)
        self.tblAudioList.resizeColumnsToContents()
        return added_paths

    # 返回所有勾选行的数据
    def get_selected_entries(self) -> list:
        entries = []
        for row in range(self.tblAudioList.rowCount()):
            check_item = self.tblAudioList.item(row, COL_CHECK)
            if row < len(self.__entries) and check_item is not None \
                    and check_item.checkState() == Qt.CheckState.Checked:
                entries.append(self.__entries[row])
        return entries

    # 全选 checkbox：勾选则全部选中，取消则全部取消
    def toggle_select_all(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.tblAudioList.rowCount()):
            check_item = self.tblAudioList.item(row, COL_CHECK)
            if check_item is not None:
                check_item.setCheckState(state)

    # 分析勾选音频的响度
    def analyze_loudness(self):
        if self.is_busy():
            return
        entries = self.get_selected_entries()
        if not entries:
            Logger().warning('没有勾选任何音频，请先勾选需要分析的音频')
            return
        self.__analyzed = [None] * len(entries)
        self.__analyzing_keys = {entry['key'] for entry in entries}
        for entry in entries:
            self.tblAudioList.setItem(entry['row'], COL_LOUDNESS, QTableWidgetItem('分析中…'))
        batch_processor.create_async(
            [entry['path'] for entry in entries],
            self.analyze_file,
            '分析音频响度',
            on_finished=self.on_files_analyzed,
        )

    # 工作线程：分析单个音频文件的响度
    def analyze_file(self, index: int, file_path: str):
        loudness = audio_utils.calculate_loudness(
            file_path, threshold_db=audio_utils.LOUDNESS_SILENCE_THRESHOLD_DB
        )
        self.__analyzed[index] = (file_path, loudness)
        return True

    # 主线程：把分析结果填入表格
    def on_files_analyzed(self):
        entry_by_key = {entry['key']: entry for entry in self.__entries}
        analyzed_keys = set()
        for result in self.__analyzed:
            if result is None:
                continue
            file_path, loudness = result
            key = os.path.normcase(file_path)
            entry = entry_by_key.get(key)
            if entry is None:
                continue
            analyzed_keys.add(key)
            entry['loudness'] = loudness
            # 原始响度作为状态列差值的基准，调整后不再变化
            entry['original_loudness'] = loudness
            # 重新分析后状态回到「需提高 / 无需处理 / 需降低」判定
            entry['adjusted'] = False
            entry['limited'] = False
            self.tblAudioList.setItem(entry['row'], COL_LOUDNESS, QTableWidgetItem(
                self.__format_loudness(loudness)
            ))
        # 分析失败的音频不留「分析中…」状态
        for key in self.__analyzing_keys - analyzed_keys:
            entry = entry_by_key.get(key)
            if entry is not None:
                self.tblAudioList.setItem(entry['row'], COL_LOUDNESS, QTableWidgetItem('分析失败'))
        self.refresh_status_column()
        self.tblAudioList.resizeColumnsToContents()
        Logger().info(f'响度分析完成，共 {len(analyzed_keys)} 个音频')

    # 把响度格式化为显示文本
    @staticmethod
    def __format_loudness(loudness: float) -> str:
        if loudness <= audio_utils.MIN_LOUDNESS_DB:
            return '无信号'
        return f'{loudness:.1f} dBFS'

    # 把调整前后的响度差值格式化为「已提高 3.2dB」/「已降低 6dB」
    @staticmethod
    def __format_loudness_delta(original: float, adjusted: float) -> str:
        delta = adjusted - original
        if abs(delta) < 0.05:
            return '无变化'
        direction = '已提高' if delta > 0 else '已降低'
        return f'{direction}{abs(delta):.1f}'.rstrip('0').rstrip('.') + 'dB'

    # 按目标响度与宽容度渲染状态列：未处理时标记需提高 / 无需处理 / 需降低
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
        delta = target - loudness
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
        unanalyzed_count = len([entry for entry in selected if entry['loudness'] is None])
        if unanalyzed_count:
            Logger().warning(f'有 {unanalyzed_count} 个勾选的音频尚未分析响度，已跳过')
        items = []
        skipped_count = 0
        for entry in selected:
            if entry['loudness'] is None:
                continue
            if entry['loudness'] > audio_utils.MIN_LOUDNESS_DB \
                    and abs(target - entry['loudness']) <= tolerance:
                # 已在目标响度的宽容度范围内，不做处理
                skipped_count += 1
                continue
            items.append({
                'row': entry['row'],
                'path': entry['path'],
                'loudness': entry['loudness'],
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
        if current <= audio_utils.MIN_LOUDNESS_DB:
            # 完全静音的音频没有可调整的信号
            self.__adjust_results[index] = {'entry': entry, 'status': '完全静音'}
            return True
        with soundfile.SoundFile(file_path) as sound_file:
            data = sound_file.read(dtype='float32')
            samplerate = sound_file.samplerate
            subtype = sound_file.subtype
        peak = float(numpy.max(numpy.abs(data))) if data.size else 0.0
        applied_gain = target - current
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
        new_loudness = audio_utils.calculate_loudness(
            file_path, threshold_db=audio_utils.LOUDNESS_SILENCE_THRESHOLD_DB
        )
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
        limited_entries = []
        adjusted_count = 0
        for result in self.__adjust_results:
            if result is None:
                continue
            entry = self.__entries[result['entry']['row']]
            new_loudness = result.get('new_loudness')
            if new_loudness is None:
                continue
            entry['loudness'] = new_loudness
            entry['adjusted'] = True
            entry['limited'] = result['limited']
            self.tblAudioList.setItem(entry['row'], COL_LOUDNESS, QTableWidgetItem(
                self.__format_loudness(new_loudness)
            ))
            adjusted_count += 1
            if result['limited']:
                limited_entries.append(result)
        self.refresh_status_column()
        self.tblAudioList.resizeColumnsToContents()
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
