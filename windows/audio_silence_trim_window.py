import os
import logging
import clipboard
import soundfile

from libraries.utils import audio_utils, user_config
from libraries.utils.wwise import audio_source_utils, waapi_utils
from libraries.table_view.table_cell_data import CellSeverity
from libraries.table_view.table_severity_delegate import SeverityTableDelegate
from table.wwise_table_row_data import WwiseTableRowData
from libraries.utils.log_utils import Logger
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QDragEnterEvent
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QMenu,
    QMessageBox,
    QTableWidgetItem,
)

import globals.global_variables as gv
from libraries.wwise_object import WwiseObjectType
from ui.AudioSilenceTrimmer_ui import Ui_AudioSilenceTrimmer
from libraries.multi_thread import batch_processor
from windows.audio_preview_window import AudioPreviewMode, AudioPreviewWindow

Sound_Frame_Samples = 128

# 表格列
COL_CHECK = 0
COL_PATH = 1
COL_DURATION = 2
COL_HEAD = 3
COL_TAIL = 4
COL_RATIO = 5
COL_STATUS = 6


# 裁剪音频文件尾巴的工具
class AudioSilenceTrimWindow(QDialog, Ui_AudioSilenceTrimmer):

    def __init__(self, active_objects: list):
        super().__init__()
        self.setupUi(self)
        self.tblFileList.setColumnCount(7)
        self.tblFileList.setHorizontalHeaderLabels(
            ['选中', '音频文件路径', '总时长', '头部静音时长', '尾部静音时长', '静音占比', '处理状态']
        )
        self.setup_triggers()
        self.load_user_settings()
        self.sync_trim_options()
        self.__thresholdLinear = 0
        self.__fadeInSeconds = 0
        self.__fadeOutSeconds = 0
        self.__trimHeadThresholdSeconds = 0
        self.__trimTailThresholdSeconds = 0
        self.__filePaths = []
        self.__activeObjects = list(active_objects)
        self.__resolvedFilePaths = []
        # 等窗口出现后再异步读取主窗口对象背后的源文件，避免呼出前阻塞
        if len(self.__activeObjects) > 0:
            QTimer.singleShot(0, self.populate_from_main_window)
        self.tblFileList.resizeColumnsToContents()

    def setup_triggers(self):
        self.btnImportFiles.clicked.connect(self.import_files)
        self.btnImportFolder.clicked.connect(self.import_folder)
        self.btnAnalyzeAudio.clicked.connect(self.analyze_audio)
        self.btnStartTrimming.clicked.connect(self.start_trimming)
        self.cbxSelectAll.toggled.connect(self.toggle_select_all)
        self.cbxTrimHead.toggled.connect(self.sync_trim_options)
        self.cbxTrimTail.toggled.connect(self.sync_trim_options)
        self.tblFileList.viewport().installEventFilter(self)
        self.tblFileList.setItemDelegate(SeverityTableDelegate(self.tblFileList))
        self.tblFileList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tblFileList.customContextMenuRequested.connect(self.show_file_context_menu)

    # 根据裁剪选项置灰对应的淡入淡出控件并隐藏未裁剪方向的静音列
    def sync_trim_options(self):
        trim_head_checked = self.cbxTrimHead.isChecked()
        trim_tail_checked = self.cbxTrimTail.isChecked()
        self.lblFadeInDuration.setEnabled(trim_head_checked)
        self.spbFadeInDuration.setEnabled(trim_head_checked)
        self.lblTrimHeadThreshold.setEnabled(trim_head_checked)
        self.spbTrimHeadThreshold.setEnabled(trim_head_checked)
        self.lblFadeOutDuration.setEnabled(trim_tail_checked)
        self.spbFadeOutDuration.setEnabled(trim_tail_checked)
        self.lblTrimTailThreshold.setEnabled(trim_tail_checked)
        self.spbTrimTailThreshold.setEnabled(trim_tail_checked)
        self.tblFileList.setColumnHidden(COL_HEAD, not trim_head_checked)
        self.tblFileList.setColumnHidden(COL_TAIL, not trim_tail_checked)
        self.tblFileList.setColumnHidden(COL_RATIO, not trim_head_checked and not trim_tail_checked)

    # 更新淡入淡出时间和静音阈值
    def update_settings(self):
        self.__fadeInSeconds = self.spbFadeInDuration.value() / 1000
        self.__fadeOutSeconds = self.spbFadeOutDuration.value() / 1000
        self.__trimHeadThresholdSeconds = self.spbTrimHeadThreshold.value() / 1000
        self.__trimTailThresholdSeconds = self.spbTrimTailThreshold.value() / 1000
        self.__thresholdLinear = audio_utils.decibel_to_linear(self.spbCutThreshold.value())

    # 是否为「改为纯0」模式（不缩短时长，仅把识别的静音区域置为 0）
    def is_zero_mode(self) -> bool:
        return self.rbnModeZero.isChecked()

    # 读取本窗口持久化的参数（user_config.json 的 window_settings.audio_silence_trim）
    def load_user_settings(self):
        saved = user_config.get_window_settings('audio_silence_trim')
        if not saved:
            return
        self.spbCutThreshold.setValue(int(saved.get('cut_threshold_db', self.spbCutThreshold.value())))
        self.spbTrimHeadThreshold.setValue(int(saved.get('trim_head_threshold_ms', self.spbTrimHeadThreshold.value())))
        self.spbTrimTailThreshold.setValue(int(saved.get('trim_tail_threshold_ms', self.spbTrimTailThreshold.value())))
        self.spbFadeInDuration.setValue(int(saved.get('fade_in_ms', self.spbFadeInDuration.value())))
        self.spbFadeOutDuration.setValue(int(saved.get('fade_out_ms', self.spbFadeOutDuration.value())))
        self.cbxTrimHead.setChecked(bool(saved.get('trim_head', self.cbxTrimHead.isChecked())))
        self.cbxTrimTail.setChecked(bool(saved.get('trim_tail', self.cbxTrimTail.isChecked())))
        self.rbnModeZero.setChecked(bool(saved.get('zero_mode', False)))

    # 把本窗口参数写回 user_config.json
    def save_user_settings(self):
        user_config.set_window_settings('audio_silence_trim', {
            'cut_threshold_db': self.spbCutThreshold.value(),
            'trim_head_threshold_ms': self.spbTrimHeadThreshold.value(),
            'trim_tail_threshold_ms': self.spbTrimTailThreshold.value(),
            'fade_in_ms': self.spbFadeInDuration.value(),
            'fade_out_ms': self.spbFadeOutDuration.value(),
            'trim_head': self.cbxTrimHead.isChecked(),
            'trim_tail': self.cbxTrimTail.isChecked(),
            'zero_mode': self.rbnModeZero.isChecked(),
        })

    # 从外界拖动文件到窗口中
    def eventFilter(self, source, event):
        if event.type() == QDragEnterEvent:
            self.reset()
            for url in event.mimeData().urls():
                self.add_file(url.toLocalFile())
            return True
        return super().eventFilter(source, event)

    # 重置所有
    def reset(self):
        bp = gv.batch_processor
        if bp and hasattr(bp, "isRunning"):
            bp.stop()
            if bp.isRunning():
                bp.wait(3000)
        self.__filePaths = []
        self.tblFileList.setRowCount(0)

    # 后台解析主窗口对象背后的源文件，完成后才加入表格
    def populate_from_main_window(self):
        if gv.batch_processor and getattr(gv.batch_processor, 'isRunning', lambda: False)():
            return
        self.__resolvedFilePaths = []
        batch_processor.create_async(
            self.__activeObjects,
            self.resolve_object_source_files,
            '读取源文件',
            on_finished=self.on_source_files_resolved,
        )

    # 工作线程中解析单个对象（AudioSource 直接取源文件，其余递归子级）
    def resolve_object_source_files(self, index: int, obj):
        self.collect_source_paths(obj)
        return True

    # 递归收集源文件路径
    def collect_source_paths(self, obj):
        if obj.type == WwiseObjectType.AudioSource:
            file_path = audio_source_utils.get_source_absolute_path(obj)
            if file_path:
                self.__resolvedFilePaths.append(file_path)
            return
        for child in waapi_utils.get_child_objects(obj):
            self.collect_source_paths(child)

    # 主线程：把解析到的源文件加入列表
    def on_source_files_resolved(self):
        for file_path in self.__resolvedFilePaths:
            self.add_file(file_path)
        self.tblFileList.repaint()
        self.tblFileList.resizeColumnsToContents()

    # 表格行右键菜单：预览对应音频文件的波形
    def show_file_context_menu(self, position):
        if self.tblFileList.itemAt(position) is None:
            return
        row = self.tblFileList.itemAt(position).row()
        menu = QMenu(self)
        copy_action = menu.addAction('复制路径')
        preview_action = menu.addAction('预览')
        chosen = menu.exec(self.tblFileList.viewport().mapToGlobal(position))
        if chosen == copy_action and 0 <= row < len(self.__filePaths):
            clipboard.copy(self.__filePaths[row])
        elif chosen == preview_action:
            self.preview_file(row)

    # 打开选中行的音频预览窗口
    def preview_file(self, row: int):
        if 0 <= row < len(self.__filePaths):
            head_text = self.tblFileList.item(row, COL_HEAD).text() if self.tblFileList.item(row, COL_HEAD) else '-'
            tail_text = self.tblFileList.item(row, COL_TAIL).text() if self.tblFileList.item(row, COL_TAIL) else '-'

            def to_seconds(text: str):
                try:
                    return float(text)
                except ValueError:
                    return None

            AudioPreviewWindow(
                self.__filePaths[row],
                self,
                mode=AudioPreviewMode.SilenceTrim,
                head_silence_seconds=to_seconds(head_text),
                tail_silence_seconds=to_seconds(tail_text),
                fade_in_seconds=self.spbFadeInDuration.value() / 1000,
                fade_out_seconds=self.spbFadeOutDuration.value() / 1000,
            ).show()

    # 导入音频文件
    def import_files(self):
        self.reset()
        files = QFileDialog.getOpenFileNames(filter='WAV(*.wav)')
        file_count = len(files[0])
        if file_count == 0:
            return
        for file_path in files[0]:
            self.add_file(file_path)
        self.tblFileList.repaint()

    # 导入文件夹中所有音频文件
    def import_folder(self):
        self.reset()
        folder = QFileDialog.getExistingDirectory()
        wav_paths = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith(".wav"):
                    wav_paths.append(str(os.path.join(root, file)))
        if not wav_paths:
            return
        batch_processor.create_async(
            wav_paths,
            lambda index, file_path: self.add_file(file_path),
            '导入音频文件',
            on_finished=self.on_folder_import_finished,
        )

    # 文件夹导入完成后刷新显示
    def on_folder_import_finished(self):
        self.tblFileList.repaint()
        self.tblFileList.resizeColumnsToContents()
        Logger().info(f'文件夹导入完成，共 {len(self.__filePaths)} 个音频文件')

    # 添加单个文件回调
    def add_file(self, file_path: str):
        if not os.path.exists(file_path):
            logging.error(f'{file_path} does not exist!')
            return
        if not file_path.endswith('.wav'):
            return
        # 不要重复裁剪同一个文件
        if file_path in self.__filePaths:
            return
        row = self.tblFileList.rowCount()
        self.tblFileList.setRowCount(row + 1)
        self.__filePaths.append(file_path)
        display_path = audio_source_utils.to_originals_relative_path(file_path)
        check_item = QTableWidgetItem()
        check_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        check_item.setCheckState(Qt.CheckState.Checked)
        self.tblFileList.setItem(row, COL_CHECK, check_item)
        self.tblFileList.setItem(row, COL_PATH, QTableWidgetItem(WwiseTableRowData.get_path_text(display_path)))

    # 返回所有勾选行的 (行号, 文件路径)
    def get_selected_entries(self):
        entries = []
        for row in range(self.tblFileList.rowCount()):
            check_item = self.tblFileList.item(row, COL_CHECK)
            if row < len(self.__filePaths) and check_item is not None \
                    and check_item.checkState() == Qt.CheckState.Checked:
                entries.append((row, self.__filePaths[row]))
        return entries

    # 全选 checkbox：勾选则全部选中，取消则全部取消
    def toggle_select_all(self, checked: bool):
        for row in range(self.tblFileList.rowCount()):
            check_item = self.tblFileList.item(row, COL_CHECK)
            if check_item is not None:
                check_item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    # 分析选中文件的静音时长
    def analyze_audio(self):
        self.update_settings()
        entries = self.get_selected_entries()
        if not entries:
            Logger().warning('没有勾选任何文件，请先勾选需要分析的文件')
            return
        batch_processor.create_async(
            entries,
            lambda index, entry: self.analyze_file(entry[0], entry[1]),
            '分析音频时长',
            on_finished=self.on_analysis_finished,
        )

    # 分析完成后弹出预计节省时长汇总
    def on_analysis_finished(self):
        rows = self.get_selected_entries()
        total_seconds = 0.0
        saved_seconds = 0.0
        zeroed_seconds = 0.0
        for row, _ in rows:
            duration_text = self.tblFileList.item(row, COL_DURATION)
            status_item = self.tblFileList.item(row, COL_STATUS)
            if duration_text is None or status_item is None:
                continue
            try:
                duration = float(duration_text.text())
            except ValueError:
                continue
            total_seconds += duration
            if status_item.text() == '完全静音':
                continue

            def cell_seconds(column: int):
                item = self.tblFileList.item(row, column)
                try:
                    return float(item.text()) if item is not None else 0.0
                except ValueError:
                    return 0.0

            head = cell_seconds(COL_HEAD)
            tail = cell_seconds(COL_TAIL)
            if self.cbxTrimHead.isChecked() and head > max(self.__trimHeadThresholdSeconds, self.__fadeInSeconds):
                if self.is_zero_mode():
                    zeroed_seconds += head
                else:
                    saved_seconds += head - self.__fadeInSeconds
            if self.cbxTrimTail.isChecked() and tail > max(self.__trimTailThresholdSeconds, self.__fadeOutSeconds):
                if self.is_zero_mode():
                    zeroed_seconds += tail
                else:
                    saved_seconds += tail - self.__fadeOutSeconds

        if total_seconds <= 0:
            return
        if self.is_zero_mode():
            percent = zeroed_seconds / total_seconds * 100
            QMessageBox.information(
                self,
                '预计置0静音占比',
                f'按当前参数（改为纯0：音头={self.cbxTrimHead.isChecked()}，'
                f'音尾={self.cbxTrimTail.isChecked()}）处理：\n\n'
                f'将把 {zeroed_seconds:.2f}s 静音改为纯0（占文件总时长 {percent:.1f}%），'
                f'文件总时长 {total_seconds:.2f}s 不变。',
            )
            return
        percent = saved_seconds / total_seconds * 100
        QMessageBox.information(
            self,
            '预计节省时长',
            f'按当前参数（裁剪音头={self.cbxTrimHead.isChecked()}，裁剪音尾={self.cbxTrimTail.isChecked()}）裁剪：\n\n'
            f'文件总时长：{total_seconds:.2f}s\n'
            f'预计节省：{saved_seconds:.2f}s（{percent:.1f}%）',
        )

    # 分析单个音频文件
    def analyze_file(self, row: int, file_path: str):
        sound_file = soundfile.SoundFile(file_path)
        audio_data = sound_file.read()
        # 计算音频长度
        duration = round(sound_file.frames / sound_file.samplerate * 1.0, 3)
        self.tblFileList.setItem(row, COL_DURATION, QTableWidgetItem(str(duration)))
        # 只分析勾选了裁剪的方向
        trim_head_checked = self.cbxTrimHead.isChecked()
        trim_tail_checked = self.cbxTrimTail.isChecked()
        silence_duration_head = None
        silence_duration_tail = None
        head_trimmable = False
        tail_trimmable = False
        if trim_head_checked:
            # 计算头部静音长度
            silence_frames_head = audio_utils.get_silence_duration_frames(audio_data, Sound_Frame_Samples, self.__thresholdLinear, False)
            silence_duration_head = round(silence_frames_head * Sound_Frame_Samples / sound_file.samplerate * 1.0, 3)
        if trim_tail_checked:
            # 计算尾部静音长度
            silence_frames_tail = audio_utils.get_silence_duration_frames(audio_data, Sound_Frame_Samples, self.__thresholdLinear, True)
            silence_duration_tail = round(silence_frames_tail * Sound_Frame_Samples / sound_file.samplerate * 1.0, 3)
        if audio_utils.get_sound_frame_max_amp(audio_data) == 0:
            # 完全静音时勾选方向的静音就是整段音频
            if trim_head_checked:
                silence_duration_head = duration
            if trim_tail_checked:
                silence_duration_tail = duration
            status_item = QTableWidgetItem('完全静音')
        else:
            # 静音超过裁剪判定阈值（且长于保留的淡入淡出长度）才算可裁剪
            head_threshold = max(self.__trimHeadThresholdSeconds, self.__fadeInSeconds)
            tail_threshold = max(self.__trimTailThresholdSeconds, self.__fadeOutSeconds)
            head_trimmable = trim_head_checked and silence_duration_head is not None and silence_duration_head > head_threshold
            tail_trimmable = trim_tail_checked and silence_duration_tail is not None and silence_duration_tail > tail_threshold
            if head_trimmable or tail_trimmable:
                status_item = QTableWidgetItem('可裁剪')
                status_item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Warning)
            else:
                status_item = QTableWidgetItem('无需裁剪')
        # 未勾选的方向不显示静音数值
        head_text = str(silence_duration_head) if silence_duration_head is not None else '-'
        tail_text = str(silence_duration_tail) if silence_duration_tail is not None else '-'
        head_item = QTableWidgetItem(head_text)
        tail_item = QTableWidgetItem(tail_text)
        # 可裁剪的方向用 warning 背景标黄
        if head_trimmable:
            head_item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Warning)
        if tail_trimmable:
            tail_item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Warning)
        self.tblFileList.setItem(row, COL_HEAD, head_item)
        self.tblFileList.setItem(row, COL_TAIL, tail_item)
        # 计算已分析静音占总时长的比例，限制最大为100%
        ratio_percent = None
        if silence_duration_head is not None or silence_duration_tail is not None:
            analyzed_duration = 0.0
            if silence_duration_head is not None:
                analyzed_duration += silence_duration_head
            if silence_duration_tail is not None:
                analyzed_duration += silence_duration_tail
            if duration > 0:
                ratio_text = f'{min(1.0, analyzed_duration / duration) * 100:.1f}%'
                ratio_percent = min(100.0, analyzed_duration / duration * 100)
            else:
                ratio_text = '0.0%'
        else:
            ratio_text = '-'
        ratio_item = QTableWidgetItem(ratio_text)
        # 静音占比：>20% warning，>50% error
        if ratio_percent is not None:
            if ratio_percent > 50:
                ratio_item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Danger)
            elif ratio_percent > 20:
                ratio_item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Warning)
        self.tblFileList.setItem(row, COL_RATIO, ratio_item)
        sound_file.close()
        self.tblFileList.setItem(row, COL_STATUS, status_item)

    # 开始裁剪选中的文件
    def start_trimming(self):
        self.update_settings()
        entries = self.get_selected_entries()
        if not entries:
            Logger().warning('没有勾选任何文件，请先勾选需要裁剪的文件')
            return
        batch_processor.create_async(
            entries,
            lambda index, entry: self.trim_file(entry[0], entry[1]),
            '静音改为纯0' if self.is_zero_mode() else '裁剪音频末尾',
        )

    # 裁剪单个音频文件回调
    def trim_file(self, row: int, file_path: str):
        if self.tblFileList.item(row, COL_STATUS).text() == '完全静音':
            return
        # 未勾选方向的单元格为'-'，不参与裁剪
        head_text = self.tblFileList.item(row, COL_HEAD).text()
        tail_text = self.tblFileList.item(row, COL_TAIL).text()
        silence_duration_head = float(head_text) if head_text != '-' else 0.0
        silence_duration_tail = float(tail_text) if tail_text != '-' else 0.0
        # 只有超过裁剪判定阈值（且长于保留的淡入淡出长度）才裁剪
        trim_head = self.cbxTrimHead.isChecked() and silence_duration_head > max(self.__trimHeadThresholdSeconds, self.__fadeInSeconds)
        trim_tail = self.cbxTrimTail.isChecked() and silence_duration_tail > max(self.__trimTailThresholdSeconds, self.__fadeOutSeconds)
        sound_file = soundfile.SoundFile(file_path)
        audio_data = sound_file.read()
        sample_rate = sound_file.samplerate
        write_path = sound_file.name
        sound_file.close()
        if self.is_zero_mode():
            # 改为纯0：不缩短时长，把识别出的整段静音区域置为0，淡入淡出机制不变
            if trim_head:
                end_sample = int(round(silence_duration_head * sample_rate))
                audio_data[:end_sample] = 0
                audio_utils.fade(audio_data, int(self.__fadeInSeconds * sample_rate), 1)
            if trim_tail:
                start_sample = len(audio_data) - int(round(silence_duration_tail * sample_rate))
                audio_data[start_sample:] = 0
                audio_utils.fade(audio_data, int(self.__fadeOutSeconds * sample_rate), -1)
        else:
            # 进行裁剪+淡入淡出
            if trim_head:
                audio_data = audio_utils.trim(audio_data, (silence_duration_head - self.__fadeInSeconds) * sample_rate, 0)
                audio_utils.fade(audio_data, int(self.__fadeInSeconds * sample_rate), 1)
                self.tblFileList.setItem(row, COL_HEAD, QTableWidgetItem(str(self.__fadeInSeconds)))
            if trim_tail:
                audio_data = audio_utils.trim(audio_data, 0, (silence_duration_tail - self.__fadeOutSeconds) * sample_rate)
                audio_utils.fade(audio_data, int(self.__fadeOutSeconds * sample_rate), -1)
                self.tblFileList.setItem(row, COL_TAIL, QTableWidgetItem(str(self.__fadeOutSeconds)))
        soundfile.write(file=write_path, data=audio_data, samplerate=sample_rate)
        # 更新列表显示
        status_item = QTableWidgetItem('已置0' if self.is_zero_mode() else '已裁剪')
        status_item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Success)
        self.tblFileList.setItem(row, COL_STATUS, status_item)

    def closeEvent(self, close_event):
        self.save_user_settings()
        self.reset()
