import os
import logging
import soundfile

from libraries.utils import audio_utils
from libraries.utils.wwise import audio_source_utils, waapi_utils
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QDragEnterEvent
from PySide6.QtWidgets import QDialog, QFileDialog, QMenu, QTableWidgetItem

import globals.global_variables as gv
from libraries.wwise_object import WwiseObjectType
from ui.AudioSilenceTrimmer_ui import Ui_AudioSilenceTrimmer
from libraries.multi_thread import batch_processor
from windows.audio_preview_window import AudioPreviewWindow

Sound_Frame_Samples = 128


# 裁剪音频文件尾巴的工具
class AudioSilenceTrimWindow(QDialog, Ui_AudioSilenceTrimmer):

    def __init__(self, active_objects: list):
        super().__init__()
        self.setupUi(self)
        self.setup_triggers()
        self.sync_trim_options()
        self.__thresholdLinear = 0
        self.__currentRow = 0
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
        self.cbxTrimHead.toggled.connect(self.sync_trim_options)
        self.cbxTrimTail.toggled.connect(self.sync_trim_options)
        self.tblFileList.viewport().installEventFilter(self)
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
        self.tblFileList.setColumnHidden(2, not trim_head_checked)
        self.tblFileList.setColumnHidden(3, not trim_tail_checked)
        self.tblFileList.setColumnHidden(4, not trim_head_checked and not trim_tail_checked)

    # 更新淡入淡出时间和静音阈值
    def update_settings(self):
        self.__fadeInSeconds = self.spbFadeInDuration.value() / 1000
        self.__fadeOutSeconds = self.spbFadeOutDuration.value() / 1000
        self.__trimHeadThresholdSeconds = self.spbTrimHeadThreshold.value() / 1000
        self.__trimTailThresholdSeconds = self.spbTrimTailThreshold.value() / 1000
        self.__thresholdLinear = audio_utils.decibel_to_linear(self.spbCutThreshold.value())

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
            file_path = audio_source_utils.get_source_file_path(obj)
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
        menu = QMenu(self)
        preview_action = menu.addAction('预览')
        if menu.exec(self.tblFileList.viewport().mapToGlobal(position)) == preview_action:
            self.preview_file(self.tblFileList.itemAt(position).row())

    # 打开选中行的音频预览窗口
    def preview_file(self, row: int):
        if 0 <= row < len(self.__filePaths):
            AudioPreviewWindow(self.__filePaths[row], self).show()

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
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith(".wav"):
                    file_path = str(os.path.join(root, file))
                    self.add_file(file_path)
            self.tblFileList.repaint()

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
        self.tblFileList.setItem(row, 0, QTableWidgetItem(display_path))

    # 分析音尾时长
    def analyze_audio(self):
        self.__currentRow = 0
        self.update_settings()
        batch_processor.create_async(
            self.__filePaths,
            lambda index, path: self.analyze_file(path),
            '分析音频时长',
        )

    # 分析单个音频文件
    def analyze_file(self, file_path):
        sound_file = soundfile.SoundFile(file_path)
        audio_data = sound_file.read()
        # 计算音频长度
        duration = round(sound_file.frames / sound_file.samplerate * 1.0, 3)
        self.tblFileList.setItem(self.__currentRow, 1, QTableWidgetItem(str(duration)))
        # 只分析勾选了裁剪的方向
        trim_head_checked = self.cbxTrimHead.isChecked()
        trim_tail_checked = self.cbxTrimTail.isChecked()
        silence_duration_head = None
        silence_duration_tail = None
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
            status_item.setForeground(QColor(0, 0, 200))
        else:
            # 静音超过裁剪判定阈值（且长于保留的淡入淡出长度）才算可裁剪
            head_threshold = max(self.__trimHeadThresholdSeconds, self.__fadeInSeconds)
            tail_threshold = max(self.__trimTailThresholdSeconds, self.__fadeOutSeconds)
            if (trim_head_checked and silence_duration_head > head_threshold) or (trim_tail_checked and silence_duration_tail > tail_threshold):
                status_item = QTableWidgetItem('可裁剪')
                status_item.setForeground(QColor(200, 0, 0))
            else:
                status_item = QTableWidgetItem('无需裁剪')
        # 未勾选的方向不显示静音数值
        head_text = str(silence_duration_head) if silence_duration_head is not None else '-'
        tail_text = str(silence_duration_tail) if silence_duration_tail is not None else '-'
        self.tblFileList.setItem(self.__currentRow, 2, QTableWidgetItem(head_text))
        self.tblFileList.setItem(self.__currentRow, 3, QTableWidgetItem(tail_text))
        # 计算已分析静音占总时长的比例，限制最大为100%
        if silence_duration_head is not None or silence_duration_tail is not None:
            analyzed_duration = 0.0
            if silence_duration_head is not None:
                analyzed_duration += silence_duration_head
            if silence_duration_tail is not None:
                analyzed_duration += silence_duration_tail
            if duration > 0:
                ratio_text = f'{min(1.0, analyzed_duration / duration) * 100:.1f}%'
            else:
                ratio_text = '0.0%'
        else:
            ratio_text = '-'
        self.tblFileList.setItem(self.__currentRow, 4, QTableWidgetItem(ratio_text))
        sound_file.close()
        self.tblFileList.setItem(self.__currentRow, 5, status_item)
        self.__currentRow += 1

    # 开始裁剪
    def start_trimming(self):
        self.__currentRow = 0
        self.update_settings()
        batch_processor.create_async(
            self.__filePaths,
            lambda index, path: self.trim_file(path),
            '裁剪音频末尾',
        )

    # 裁剪单个音频文件回调
    def trim_file(self, file_path):
        if self.tblFileList.item(self.__currentRow, 5).text() == '完全静音':
            return
        # 未勾选方向的单元格为'-'，不参与裁剪
        head_text = self.tblFileList.item(self.__currentRow, 2).text()
        tail_text = self.tblFileList.item(self.__currentRow, 3).text()
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
        # 进行裁剪+淡入淡出
        if trim_head:
            audio_data = audio_utils.trim(audio_data, (silence_duration_head - self.__fadeInSeconds) * sample_rate, 0)
            audio_utils.fade(audio_data, int(self.__fadeInSeconds * sample_rate), 1)
            self.tblFileList.setItem(self.__currentRow, 2, QTableWidgetItem(str(self.__fadeInSeconds)))
        if trim_tail:
            audio_data = audio_utils.trim(audio_data, 0, (silence_duration_tail - self.__fadeOutSeconds) * sample_rate)
            audio_utils.fade(audio_data, int(self.__fadeOutSeconds * sample_rate), -1)
            self.tblFileList.setItem(self.__currentRow, 3, QTableWidgetItem(str(self.__fadeOutSeconds)))
        soundfile.write(file=write_path, data=audio_data, samplerate=sample_rate)
        # 更新列表显示
        status_item = QTableWidgetItem('已裁剪')
        status_item.setForeground(QColor(0, 200, 0))
        self.tblFileList.setItem(self.__currentRow, 5, status_item)
        self.__currentRow += 1

    def closeEvent(self, close_event):
        self.reset()
