import os
import logging
import clipboard
import soundfile

from libraries.utils import audio_utils, user_config
from libraries.utils.qt_utils import resize_table_and_window
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

    # 静音处理方式：裁剪源文件 / 静音改为纯0 / 只改 Wwise 里的 Trim 值
    MODE_TRIM = 'trim'
    MODE_ZERO = 'zero'
    MODE_WWISE = 'wwise'

    def __init__(self):
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
        # 输入对象在 populate_from_main_window 里从主窗口临时获取，保证与表格同步
        self.__activeObjects: list = []
        self.__resolvedFilePaths = []
        # 工作线程算出的处理结果，由主线程写回表格（{行号: {'status', 'severity', 'head', 'tail'}}）
        self.__trim_results = {}
        # 等窗口出现后再异步读取主窗口对象背后的源文件，避免呼出前阻塞
        QTimer.singleShot(0, self.populate_from_main_window)
        resize_table_and_window(self.tblFileList, self)

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
        self.tblFileList.itemDoubleClicked.connect(self.select_source_in_wwise)

    # 双击行（路径列）按源文件反查对象并在 Wwise 中选中
    def select_source_in_wwise(self, item: QTableWidgetItem):
        row = item.row()
        if not 0 <= row < len(self.__filePaths):
            return
        relative_path = audio_source_utils.to_originals_relative_path(self.__filePaths[row])
        sources = waapi_utils.find_audio_sources_by_original_path(relative_path)
        if not sources:
            Logger().warning(f'未在工程中找到使用源文件 [{relative_path}] 的对象')
            return
        waapi_utils.select_objects_in_wwise(sources)

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

    # 当前静音处理方式
    def current_mode(self) -> str:
        if self.rbnModeZero.isChecked():
            return self.MODE_ZERO
        if self.rbnModeWwise.isChecked():
            return self.MODE_WWISE
        return self.MODE_TRIM

    # 是否为「改为纯0」模式（不缩短时长，仅把识别的静音区域置为 0）
    def is_zero_mode(self) -> bool:
        return self.current_mode() == self.MODE_ZERO

    # 是否为「Wwise 内部裁剪」模式（不动源文件，只改 AudioFileSource 的 TrimBegin / TrimEnd）
    def is_wwise_mode(self) -> bool:
        return self.current_mode() == self.MODE_WWISE

    # 切换模式单选按钮
    def set_mode(self, mode: str) -> None:
        self.rbnModeTrim.setChecked(mode == self.MODE_TRIM)
        self.rbnModeZero.setChecked(mode == self.MODE_ZERO)
        self.rbnModeWwise.setChecked(mode == self.MODE_WWISE)

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
        # 旧配置里只有 zero_mode 布尔值，读不到 mode 时按它兼容
        mode = str(saved.get('mode', '') or '')
        if mode not in (self.MODE_TRIM, self.MODE_ZERO, self.MODE_WWISE):
            mode = self.MODE_ZERO if saved.get('zero_mode') else self.MODE_TRIM
        self.set_mode(mode)

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
            'mode': self.current_mode(),
            # 兼容旧版本：只认 zero_mode 时仍然能读回「改为纯0」
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
        # 临时取主窗口当前 AudioSource，保证与表格同步
        self.__activeObjects = gv.get_tool_targets(WwiseObjectType.AudioSource)
        if not self.__activeObjects:
            Logger().warning('表格中没有可用于「静音裁剪」的 AudioSource')
            return
        self.__resolvedFilePaths = []
        self.__prefetched_pages: set = set()
        self.__sources_by_object: dict = {}
        self.__paths_by_id: dict = {}
        batch_processor.create_async(
            self.__activeObjects,
            self.resolve_object_source_files,
            '读取源文件',
            on_finished=self.on_source_files_resolved,
        )

    # 工作线程中解析单个对象（AudioSource 直接取源文件，其余递归子级）
    # 源文件路径按「查询分页大小」所在的页惰性预取，进度仍按输入对象逐个推进
    def resolve_object_source_files(self, index: int, obj):
        self.__prefetch_source_paths(index)
        for source in self.__sources_of(obj):
            file_path = self.__paths_by_id.get(source.id, {}).get('originalFilePath')
            if file_path:
                self.__resolvedFilePaths.append(file_path)
        return True

    # 预取 index 所在分页里所有 AudioSource 的源文件路径
    def __prefetch_source_paths(self, index: int):
        start, end = waapi_utils.page_bounds(self.__activeObjects, index)
        if start in self.__prefetched_pages:
            return
        self.__prefetched_pages.add(start)
        sources = [source for obj in self.__activeObjects[start:end] for source in self.__sources_of(obj)]
        self.__paths_by_id.update(waapi_utils.get_objects_properties(sources, ['originalFilePath']))

    # 单个对象展开出的 AudioSource（同一次批处理里复用，避免重复递归查询子对象）
    def __sources_of(self, obj) -> list:
        sources = self.__sources_by_object.get(obj.id)
        if sources is None:
            sources = []
            self.collect_source_objects(obj, sources)
            self.__sources_by_object[obj.id] = sources
        return sources

    # 递归收集对象下的全部 AudioSource（AudioSource 直接收集，其余递归子级）
    def collect_source_objects(self, obj, collected: list):
        if obj.type == WwiseObjectType.AudioSource:
            collected.append(obj)
            return
        for child in waapi_utils.get_child_objects(obj):
            self.collect_source_objects(child, collected)

    # 主线程：把解析到的源文件加入列表
    def on_source_files_resolved(self):
        for file_path in self.__resolvedFilePaths:
            self.add_file(file_path)
        self.tblFileList.repaint()
        resize_table_and_window(self.tblFileList, self)
        if self.tblFileList.rowCount() == 0:
            # 表格还是空的说明源文件都没解析出来，给出提示避免用户以为是卡住了
            Logger().warning('没有解析到可裁剪的源文件')
            QMessageBox.warning(
                self,
                '静音裁剪',
                f'{len(self.__activeObjects)} 个对象下都没有解析出可用的源文件：\n'
                '对象的原始 wav 可能没有导入、已被移动，或工程路径读取失败。\n\n'
                '可以先在主窗口双击进 Wwise 确认这些对象的源文件状态，'
                '或者用「导入文件 / 导入文件夹」直接处理磁盘上的音频。',
            )

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
        resize_table_and_window(self.tblFileList, self)
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
        if self.is_wwise_mode():
            percent = saved_seconds / total_seconds * 100
            QMessageBox.information(
                self,
                '预计缩短的播放时长',
                f'按当前参数（Wwise 内部裁剪：音头={self.cbxTrimHead.isChecked()}，'
                f'音尾={self.cbxTrimTail.isChecked()}）处理：\n\n'
                f'文件总时长：{total_seconds:.2f}s（源文件不变）\n'
                f'Wwise 中的播放时长将缩短：{saved_seconds:.2f}s（{percent:.1f}%）',
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
        self.__trim_results = {}
        title = {
            self.MODE_ZERO: '静音改为纯0',
            self.MODE_WWISE: '在 Wwise 中裁剪静音',
        }.get(self.current_mode(), '裁剪音频末尾')
        batch_processor.create_async(
            entries,
            lambda index, entry: self.trim_file(entry[0], entry[1]),
            title,
            # 结果在主线程写回表格（工作线程不碰 UI）
            on_item_processed=self.on_trim_item_processed,
        )

    # 主线程：把工作线程算出的裁剪结果写进表格
    def on_trim_item_processed(self, payload):
        _index, entry = payload
        row = entry[0]
        result = self.__trim_results.pop(row, None)
        if not result:
            return
        for column, key in ((COL_HEAD, 'head'), (COL_TAIL, 'tail')):
            if result.get(key) is not None:
                self.tblFileList.setItem(row, column, QTableWidgetItem(result[key]))
        status_item = QTableWidgetItem(result['status'])
        if result.get('severity') is not None:
            status_item.setData(Qt.ItemDataRole.BackgroundRole, result['severity'])
        self.tblFileList.setItem(row, COL_STATUS, status_item)

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
        if self.is_wwise_mode():
            # Wwise 内部裁剪：不读也不写源文件，只改引用该文件的 AudioFileSource
            self.apply_wwise_trim(row, file_path, silence_duration_head, silence_duration_tail, trim_head, trim_tail)
            return
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
                self.__trim_results[row] = {'status': '已裁剪', 'severity': CellSeverity.Success,
                                            'head': str(self.__fadeInSeconds)}
            if trim_tail:
                audio_data = audio_utils.trim(audio_data, 0, (silence_duration_tail - self.__fadeOutSeconds) * sample_rate)
                audio_utils.fade(audio_data, int(self.__fadeOutSeconds * sample_rate), -1)
                self.__trim_results.setdefault(row, {'status': '已裁剪', 'severity': CellSeverity.Success})['tail'] = \
                    str(self.__fadeOutSeconds)
        soundfile.write(file=write_path, data=audio_data, samplerate=sample_rate)
        # 更新列表显示
        result = self.__trim_results.setdefault(row, {'status': '已裁剪', 'severity': CellSeverity.Success})
        if self.is_zero_mode():
            result['status'] = '已置0'

    # Wwise 内部裁剪：把识别出的静音改写成 AudioFileSource 的 TrimBegin / TrimEnd（秒，从两端算起），
    # 淡入淡出时长照常保留在裁剪区间内；源文件完全不动
    def apply_wwise_trim(self, row: int, file_path: str, head_seconds: float, tail_seconds: float,
                         trim_head: bool, trim_tail: bool):
        relative_path = audio_source_utils.to_originals_relative_path(file_path)
        sources = waapi_utils.find_audio_sources_by_original_path(relative_path) if relative_path else []
        if not sources:
            Logger().warning(f'[{os.path.basename(file_path)}] 工程里没有引用该文件的 AudioFileSource，跳过')
            self.__trim_results[row] = {'status': '无Wwise对象', 'severity': CellSeverity.Warning}
            return
        trim_begin = head_seconds - self.__fadeInSeconds if trim_head else None
        trim_end = tail_seconds - self.__fadeOutSeconds if trim_tail else None
        updated_count = 0
        failed_count = 0
        for source in sources:
            old_info = audio_source_utils.get_source_edit_info(source) or (None, None, None, None, None, None)
            if audio_source_utils.set_source_trim_range(source, trim_begin, trim_end):
                updated_count += 1
                Logger().debug(f'[{source.name}] Wwise 裁剪区间：TrimBegin {old_info[0]} -> {trim_begin}，'
                               f'TrimEnd {old_info[1]} -> {trim_end}')
            else:
                failed_count += 1
                Logger().error(f'[{source.name}] 设置裁剪区间失败：TrimBegin={trim_begin} TrimEnd={trim_end}')
        Logger().info(f'[{os.path.basename(file_path)}] 已在 Wwise 中设置裁剪区间：'
                      f'TrimBegin={trim_begin} TrimEnd={trim_end}（{updated_count} 个 AudioFileSource）')
        if failed_count:
            self.__trim_results[row] = {'status': f'部分失败({failed_count})', 'severity': CellSeverity.Danger}
        else:
            self.__trim_results[row] = {'status': '已在Wwise裁剪', 'severity': CellSeverity.Success}

    def closeEvent(self, close_event):
        self.save_user_settings()
        self.reset()
