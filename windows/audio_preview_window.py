import os
from enum import Enum

import soundfile
from PySide6.QtCore import QLoggingCategory, Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QDialog, QWidget

from libraries.utils.wwise import audio_source_utils
from ui.AudioPreview_ui import Ui_AudioPreview

# 关闭 QtMultimedia ffmpeg 后端的媒体信息输出，避免打开文件时在控制台打印红色日志
os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.*=false")


# 预览窗口模式
class AudioPreviewMode(Enum):
    Standard = "standard"
    SilenceTrim = "silence_trim"


# 音频预览窗口：显示波形，支持播放/暂停/停止与拖动进度
class AudioPreviewWindow(QDialog, Ui_AudioPreview):

    def __init__(
        self,
        file_path: str,
        parent: QWidget = None,
        mode: AudioPreviewMode = AudioPreviewMode.Standard,
        head_silence_seconds: float = None,
        tail_silence_seconds: float = None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.__file_path = file_path
        self.__mode = mode
        self.__head_silence_seconds = head_silence_seconds
        self.__tail_silence_seconds = tail_silence_seconds
        self.__media_player = QMediaPlayer(self)
        self.__audio_output = QAudioOutput(self)
        self.__media_player.setAudioOutput(self.__audio_output)
        self.__audio_output.setVolume(1.0)
        self.setup_triggers()
        self.__setup_player()
        self.__load_audio()

    # 绑定按钮信号槽
    def setup_triggers(self):
        self.btnPlay.clicked.connect(self.toggle_play_pause)
        self.btnStop.clicked.connect(self.stop_audio)
        self.btnOpenFolder.clicked.connect(self.open_containing_folder)
        self.btnZoomOut.clicked.connect(self.waveform.zoom_out)
        self.btnZoomIn.clicked.connect(self.waveform.zoom_in)

    def __setup_player(self):
        QLoggingCategory.setFilterRules("qt.multimedia.*=false")
        self.waveform.seek_callback = self.__media_player.setPosition
        self.__media_player.positionChanged.connect(self.waveform.set_position)
        self.__media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.__media_player.mediaStatusChanged.connect(self._on_media_status_changed)

    # 读取音频并生成波形
    def __load_audio(self):
        display_path = audio_source_utils.to_originals_relative_path(self.__file_path)
        if not os.path.exists(self.__file_path):
            self.lblInfo.setText(f"文件不存在：{display_path}")
            self.lblInfo.setToolTip(display_path)
            self.btnPlay.setEnabled(False)
            self.btnStop.setEnabled(False)
            return
        sound_file = soundfile.SoundFile(self.__file_path)
        audio_data = sound_file.read()
        sample_rate = sound_file.samplerate
        duration = sound_file.frames / sample_rate if sample_rate else 0
        sound_file.close()
        self.waveform.set_audio(audio_data, sample_rate)
        self.waveform.set_duration(int(duration * 1000))
        self.__apply_silence_regions(duration)
        elided_path = self.fontMetrics().elidedText(display_path, Qt.TextElideMode.ElideMiddle, 420)
        self.lblInfo.setText(f"{elided_path}    时长 {duration:.2f}s")
        self.lblInfo.setToolTip(display_path)
        self.__media_player.setSource(QUrl.fromLocalFile(self.__file_path))

    # SilenceTrim 模式下把头部/尾部静音时长转成波形上的黄色区域
    def __apply_silence_regions(self, duration: float):
        if self.__mode != AudioPreviewMode.SilenceTrim:
            return
        duration_ms = int(duration * 1000)
        regions = []
        if self.__head_silence_seconds:
            regions.append((0, int(min(duration, self.__head_silence_seconds) * 1000)))
        if self.__tail_silence_seconds:
            tail_start = int(max(0.0, duration - self.__tail_silence_seconds) * 1000)
            regions.append((tail_start, duration_ms))
        self.waveform.set_silence_regions(regions)

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

    # 打开文件所在文件夹
    def open_containing_folder(self):
        folder = os.path.dirname(self.__file_path)
        if os.path.isdir(folder):
            if hasattr(os, "startfile"):
                os.startfile(folder)

    def closeEvent(self, event):
        self.__media_player.stop()
        super().closeEvent(event)
