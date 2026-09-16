import os
from enum import Enum

import soundfile
from PySide6.QtCore import QLoggingCategory, Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QDialog, QWidget

from libraries.utils import path_utils, user_config
from libraries.utils import audio_utils
from libraries.utils.wwise import audio_source_utils
from ui.AudioPreview_ui import Ui_AudioPreview

# 关闭 QtMultimedia ffmpeg 后端的媒体信息输出，避免打开文件时在控制台打印红色日志
os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.*=false")

# 实时响度表的统计窗口（毫秒）
METER_WINDOW_MS = 400


# 预览窗口模式
class AudioPreviewMode(Enum):
    Standard = "standard"
    SilenceTrim = "silence_trim"


# 把文件字节数格式化为可读大小
def format_file_size(num_bytes: int) -> str:
    if num_bytes < 1024 * 1024:
        return f'{num_bytes / 1024:.1f} KB'
    return f'{num_bytes / (1024 * 1024):.2f} MB'


# 音频预览窗口：显示波形，支持播放/暂停/停止与拖动进度
class AudioPreviewWindow(QDialog, Ui_AudioPreview):

    def __init__(
        self,
        file_path: str,
        parent: QWidget = None,
        mode: AudioPreviewMode = AudioPreviewMode.Standard,
        head_silence_seconds: float = None,
        tail_silence_seconds: float = None,
        fade_in_seconds: float = None,
        fade_out_seconds: float = None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.__file_path = file_path
        self.__mode = mode
        self.__head_silence_seconds = head_silence_seconds
        self.__tail_silence_seconds = tail_silence_seconds
        self.__fade_in_seconds = fade_in_seconds
        self.__fade_out_seconds = fade_out_seconds
        self.__audio_data = None
        self.__sample_rate = 0
        self.__media_player = QMediaPlayer(self)
        self.__audio_output = QAudioOutput(self)
        self.__media_player.setAudioOutput(self.__audio_output)
        self.__audio_output.setVolume(1.0)
        self.setup_triggers()
        self.__load_display_mode()
        self.__setup_player()
        self.__load_audio()

    # 绑定按钮信号槽
    def setup_triggers(self):
        self.btnPlay.clicked.connect(self.toggle_play_pause)
        self.btnStop.clicked.connect(self.stop_audio)
        self.btnOpenFolder.clicked.connect(self.open_containing_folder)
        self.btnZoomOut.clicked.connect(self.waveform.zoom_out)
        self.btnZoomIn.clicked.connect(self.waveform.zoom_in)
        self.cbbDisplayMode.currentIndexChanged.connect(self._on_display_mode_changed)

    # 读取并应用持久化的显示模式
    def __load_display_mode(self):
        saved = user_config.get_window_settings('audio_preview')
        mode = saved.get('display_mode', 'wave')
        index = 1 if mode == 'spectrum' else 0
        self.cbbDisplayMode.blockSignals(True)
        self.cbbDisplayMode.setCurrentIndex(index)
        self.cbbDisplayMode.blockSignals(False)
        self.waveform.set_display_mode('spectrum' if index == 1 else 'wave')

    # 显示模式切换：更新波形控件并保存
    def _on_display_mode_changed(self, index: int):
        mode = 'spectrum' if index == 1 else 'wave'
        self.waveform.set_display_mode(mode)
        saved = user_config.get_window_settings('audio_preview')
        saved['display_mode'] = mode
        user_config.set_window_settings('audio_preview', saved)

    def __setup_player(self):
        QLoggingCategory.setFilterRules("qt.multimedia.*=false")
        self.waveform.seek_callback = self.__media_player.setPosition
        self.__media_player.positionChanged.connect(self.waveform.set_position)
        self.__media_player.positionChanged.connect(self.__update_loudness_meter)
        self.__media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.__media_player.mediaStatusChanged.connect(self._on_media_status_changed)

    # 读取音频并生成波形
    def __load_audio(self):
        display_path = path_utils.get_display_path(
            audio_source_utils.to_originals_relative_path(self.__file_path)
        )
        if not os.path.exists(self.__file_path):
            self.lblInfo.setText(f"文件不存在：{display_path}")
            self.lblInfo.setToolTip(display_path)
            self.btnPlay.setEnabled(False)
            self.btnStop.setEnabled(False)
            return
        sound_file = soundfile.SoundFile(self.__file_path)
        audio_data = sound_file.read()
        sample_rate = sound_file.samplerate
        channels = getattr(sound_file, 'channels', 1)
        duration = sound_file.frames / sample_rate if sample_rate else 0
        sound_file.close()
        self.waveform.set_audio(audio_data, sample_rate)
        self.waveform.set_duration(int(duration * 1000))
        self.__audio_data = audio_data
        self.__sample_rate = sample_rate
        # 先按声道数初始化电平表，未播放时显示为下限
        self.loudnessMeter.set_levels([audio_utils.MIN_LOUDNESS_DB] * max(1, channels))
        self.__apply_silence_markers(duration)
        file_size = format_file_size(os.path.getsize(self.__file_path))
        loudness_db = audio_utils.calculate_loudness(
            self.__file_path, threshold_db=audio_utils.LOUDNESS_SILENCE_THRESHOLD_DB
        )
        loudness_text = '无信号' if loudness_db <= audio_utils.MIN_LOUDNESS_DB else f'{loudness_db:.1f} dBFS'
        details_text = (f'时长 {duration:.2f}s   |   大小 {file_size}'
                        f'   |   {channels} 声道   |   采样率 {int(sample_rate)} Hz'
                        f'   |   平均响度 {loudness_text}')
        self.lblInfo.setText(self.fontMetrics().elidedText(display_path, Qt.TextElideMode.ElideMiddle, 700))
        self.lblInfo.setToolTip(display_path)
        self.lblFileDetails.setText(details_text)
        self.lblFileDetails.setToolTip(details_text)
        self.__media_player.setSource(QUrl.fromLocalFile(self.__file_path))

    # 按播放位置取当前位置往前一小段音频，分声道计算并显示实时响度
    def __update_loudness_meter(self, position_ms: int):
        if self.__audio_data is None or self.__sample_rate <= 0:
            return
        end_sample = min(int(position_ms / 1000 * self.__sample_rate), len(self.__audio_data))
        if end_sample <= 0:
            self.loudnessMeter.reset()
            return
        start_sample = max(0, end_sample - int(METER_WINDOW_MS / 1000 * self.__sample_rate))
        chunk = self.__audio_data[start_sample:end_sample]
        if chunk.size == 0:
            return
        if chunk.ndim == 1:
            channels = [chunk]
        else:
            channels = [chunk[:, index] for index in range(chunk.shape[1])]
        self.loudnessMeter.set_levels([audio_utils.calculate_loudness_from_data(channel) for channel in channels])

    # SilenceTrim 模式下把头部/尾部静音转成黄色区域，把保留淡入淡出画成斜线
    def __apply_silence_markers(self, duration: float):
        if self.__mode != AudioPreviewMode.SilenceTrim:
            return
        duration_ms = int(duration * 1000)
        regions = []
        fade_markers = []
        if self.__head_silence_seconds:
            head_ms = int(min(duration, self.__head_silence_seconds) * 1000)
            regions.append((0, head_ms))
            # 淡入位于头静音的末尾、声音开始前：从 head - fadeIn 到 head
            if self.__fade_in_seconds:
                fade_start = max(0, head_ms - int(self.__fade_in_seconds * 1000))
                fade_markers.append((fade_start, head_ms, 'in'))
        if self.__tail_silence_seconds:
            tail_start = int(max(0.0, duration - self.__tail_silence_seconds) * 1000)
            regions.append((tail_start, duration_ms))
            # 淡出位于尾静音的开头、声音结束之后：从 tail_start 到 tail_start + fadeOut
            if self.__fade_out_seconds:
                fade_end = min(duration_ms, tail_start + int(self.__fade_out_seconds * 1000))
                fade_markers.append((tail_start, fade_end, 'out'))
        self.waveform.set_silence_regions(regions)
        self.waveform.set_fade_markers(fade_markers)

    # 播放/暂停切换
    def toggle_play_pause(self):
        if self.__media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.__media_player.pause()
        else:
            self.__media_player.play()

    # 停止并把进度拉回开头
    def stop_audio(self):
        self.__media_player.stop()
        self.__media_player.setPosition(0)
        self.waveform.set_position(0)
        self.loudnessMeter.reset()

    # 播放状态改变时切换按钮文案
    def _on_playback_state_changed(self, state):
        self.btnPlay.setText("暂停" if state == QMediaPlayer.PlaybackState.PlayingState else "播放")

    # 播放结束时：循环则重头播放，否则回到开头
    def _on_media_status_changed(self, status):
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        if self.chkLoop.isChecked():
            self.__media_player.play()
        else:
            self.__media_player.stop()
            self.__media_player.setPosition(0)
            self.waveform.set_position(0)
            self.loudnessMeter.reset()

    # 打开文件所在文件夹
    def open_containing_folder(self):
        folder = os.path.dirname(self.__file_path)
        if os.path.isdir(folder):
            if hasattr(os, "startfile"):
                os.startfile(folder)

    def closeEvent(self, event):
        self.__media_player.stop()
        super().closeEvent(event)
