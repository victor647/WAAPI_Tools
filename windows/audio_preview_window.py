import os

import numpy as np
import soundfile
from PySide6.QtCore import QLoggingCategory, Qt, QUrl
from PySide6.QtGui import QColor, QPainter
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from libraries.utils.wwise import audio_source_utils

# 关闭 QtMultimedia ffmpeg 后端的媒体信息输出，避免打开文件时在控制台打印红色日志
os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.*=false")


PLOT_LEFT = 48
PLOT_RIGHT = 10
PLOT_TOP = 10
PLOT_BOTTOM = 26


# 波形显示控件：绘制带时间/dBFS 坐标轴的波形与红色播放头，支持拖动播放头定位
class WaveformWidget(QWidget):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.__mono = None
        self.__sample_rate = 0
        self.__duration_ms = 0
        self.__position_ms = 0
        # 纵向缩放系数：1.0 表示满幅（1.0 振幅贴到上下边界）
        self.__zoom = 1.0
        # 拖动播放头时的回调（参数为毫秒）
        self.seek_callback = None
        self.setMinimumHeight(180)
        self.setMouseTracking(True)

    # 载入音频数据并重绘（保存带符号单声道用于对称波形）
    def set_audio(self, audio_data, sample_rate: int):
        data = audio_data.astype(np.float32)
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        self.__mono = data
        self.__sample_rate = sample_rate
        self.update()

    # 设置总时长（毫秒）
    def set_duration(self, duration_ms: int):
        self.__duration_ms = max(0, duration_ms)
        self.update()

    # 更新播放头位置（毫秒）
    def set_position(self, position_ms: int):
        self.__position_ms = max(0, position_ms)
        self.update()

    # 纵向放大
    def zoom_in(self):
        self.__zoom = min(64.0, self.__zoom * 1.5)
        self.update()

    # 纵向缩小
    def zoom_out(self):
        self.__zoom = max(0.0625, self.__zoom / 1.5)
        self.update()

    # 绘图区域几何信息
    def _plot_rect(self):
        return PLOT_LEFT, PLOT_TOP, self.width() - PLOT_LEFT - PLOT_RIGHT, self.height() - PLOT_TOP - PLOT_BOTTOM

    # 把绘图区内的横坐标换算成播放时间（毫秒），越界返回 None
    def _time_from_x(self, x: int):
        left, top, plot_width, plot_height = self._plot_rect()
        if plot_width <= 0 or plot_height <= 0 or self.__duration_ms <= 0:
            return None
        if x < left or x > left + plot_width:
            return None
        return int((x - left) / plot_width * self.__duration_ms)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.seek_callback:
            position_ms = self._time_from_x(int(event.position().x()))
            if position_ms is not None:
                self.set_position(position_ms)
                self.seek_callback(position_ms)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        x = int(event.position().x())
        left, top, plot_width, plot_height = self._plot_rect()
        if plot_width > 0 and plot_height > 0 and left <= x <= left + plot_width:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.unsetCursor()
        if event.buttons() & Qt.MouseButton.LeftButton and self.seek_callback:
            position_ms = self._time_from_x(x)
            if position_ms is not None:
                self.set_position(position_ms)
                self.seek_callback(position_ms)
        super().mouseMoveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#14181f"))
        width = self.width()
        height = self.height()
        if self.__mono is None or self.__mono.size == 0:
            painter.setPen(QColor("#8a93a1"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "无波形数据")
            return
        plot_width = width - PLOT_LEFT - PLOT_RIGHT
        plot_height = height - PLOT_TOP - PLOT_BOTTOM
        if plot_width <= 0 or plot_height <= 0:
            return
        duration = self.__mono.size / self.__sample_rate if self.__sample_rate else 0

        grid_color = QColor("#2a313c")
        text_color = QColor("#8a93a1")
        painter.setFont(self.font())

        # 横轴：时间刻度（总时长小于 1 秒时用毫秒）
        duration_ms = duration * 1000
        painter.setPen(grid_color)
        if duration_ms < 1000:
            step_ms = int(self._nice_time_step(duration_ms))
            current_ms = 0
            while current_ms <= duration_ms + 1e-6:
                line_x = PLOT_LEFT + int(current_ms / duration_ms * plot_width) if duration_ms else PLOT_LEFT
                painter.drawLine(line_x, PLOT_TOP, line_x, PLOT_TOP + plot_height)
                painter.setPen(text_color)
                painter.drawText(line_x - 25, PLOT_TOP + plot_height + 6, 50, 16, Qt.AlignmentFlag.AlignHCenter, f"{current_ms}ms")
                painter.setPen(grid_color)
                current_ms += step_ms
        else:
            time_step = self._nice_time_step(duration)
            time_seconds = 0.0
            while time_seconds <= duration + 1e-9:
                line_x = PLOT_LEFT + int(time_seconds / duration * plot_width) if duration else PLOT_LEFT
                painter.drawLine(line_x, PLOT_TOP, line_x, PLOT_TOP + plot_height)
                painter.setPen(text_color)
                painter.drawText(line_x - 25, PLOT_TOP + plot_height + 6, 50, 16, Qt.AlignmentFlag.AlignHCenter, f"{time_seconds:g}s")
                painter.setPen(grid_color)
                time_seconds += time_step

        # 纵轴：0 线居中上下对称；刻度按绝对满幅标度 0/-6/-12/-18 dBFS
        center_y = PLOT_TOP + plot_height / 2
        half_height = plot_height / 2 - 4
        amp_scale = self.__zoom * half_height
        painter.setPen(QColor("#3d4653"))
        painter.drawLine(PLOT_LEFT, int(center_y), PLOT_LEFT + plot_width, int(center_y))
        painter.setPen(grid_color)
        for db_value in (0, -6, -12, -18):
            ratio = 10 ** (db_value / 20)
            offset = ratio * amp_scale
            upper_y = int(center_y - offset)
            lower_y = int(center_y + offset)
            painter.drawLine(PLOT_LEFT, upper_y, PLOT_LEFT + plot_width, upper_y)
            painter.drawLine(PLOT_LEFT, lower_y, PLOT_LEFT + plot_width, lower_y)
            painter.setPen(text_color)
            painter.drawText(0, upper_y - 7, PLOT_LEFT - 4, 14, Qt.AlignmentFlag.AlignRight, f"{db_value}dB")
            painter.setPen(grid_color)
        painter.drawRect(PLOT_LEFT, PLOT_TOP, plot_width, plot_height)

        # 波形（逐像素列最小/最大振幅，按恒定满幅标度绘制）
        painter.setClipRect(PLOT_LEFT, PLOT_TOP, plot_width, plot_height)
        step = self.__mono.size / plot_width
        painter.setPen(QColor("#4fc3a1"))
        for column in range(plot_width):
            start = int(column * step)
            end = max(start + 1, int((column + 1) * step))
            segment = self.__mono[start:end]
            top_y = int(center_y - float(np.max(segment)) * amp_scale)
            bottom_y = int(center_y - float(np.min(segment)) * amp_scale)
            painter.drawLine(PLOT_LEFT + column, top_y, PLOT_LEFT + column, bottom_y)

        # 红色播放头
        if self.__duration_ms > 0:
            playhead_x = PLOT_LEFT + int(self.__position_ms / self.__duration_ms * plot_width)
            painter.setPen(QColor("#ff5252"))
            painter.drawLine(playhead_x, PLOT_TOP, playhead_x, PLOT_TOP + plot_height)

    # 选择合适的时间刻度间隔
    @staticmethod
    def _nice_time_step(duration: float) -> float:
        if duration <= 0:
            return 1.0
        raw = duration / 7
        magnitude = 10 ** np.floor(np.log10(raw))
        for factor in (1, 2, 5, 10):
            candidate = factor * magnitude
            if candidate >= raw:
                return candidate
        return 10 * magnitude


# 音频预览窗口：显示波形，支持播放/暂停/停止与拖动进度
class AudioPreviewWindow(QDialog):

    def __init__(self, file_path: str, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("音频预览")
        self.setMinimumSize(760, 280)
        self.__file_path = file_path
        self.__waveform = WaveformWidget(self)
        self.__lblInfo = QLabel(self)
        self.__btnPlay = QPushButton("播放", self)
        self.__btnStop = QPushButton("停止", self)
        self.__btnOpenFolder = QPushButton("打开文件夹", self)
        self.__btnZoomOut = QPushButton("缩小", self)
        self.__btnZoomIn = QPushButton("放大", self)
        self.__chkLoop = QCheckBox("循环", self)
        self.__media_player = QMediaPlayer(self)
        self.__audio_output = QAudioOutput(self)
        self.__media_player.setAudioOutput(self.__audio_output)
        self.__audio_output.setVolume(1.0)
        self.__build_ui()
        self.__setup_player()
        self.__load_audio()

    def __build_ui(self):
        button_row = QHBoxLayout()
        button_row.addWidget(self.__lblInfo)
        button_row.addStretch()
        button_row.addWidget(self.__chkLoop)
        button_row.addWidget(self.__btnPlay)
        button_row.addWidget(self.__btnStop)
        button_row.addWidget(self.__btnOpenFolder)
        button_row.addWidget(self.__btnZoomOut)
        button_row.addWidget(self.__btnZoomIn)
        layout = QVBoxLayout(self)
        layout.addLayout(button_row)
        layout.addWidget(self.__waveform, 1)
        self.__btnPlay.clicked.connect(self.toggle_play_pause)
        self.__btnStop.clicked.connect(self.stop_audio)
        self.__btnOpenFolder.clicked.connect(self.open_containing_folder)
        self.__btnZoomOut.clicked.connect(self.__waveform.zoom_out)
        self.__btnZoomIn.clicked.connect(self.__waveform.zoom_in)

    def __setup_player(self):
        QLoggingCategory.setFilterRules("qt.multimedia.*=false")
        self.__waveform.seek_callback = self.__media_player.setPosition
        self.__media_player.positionChanged.connect(self.__waveform.set_position)
        self.__media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.__media_player.mediaStatusChanged.connect(self._on_media_status_changed)

    # 读取音频并生成波形
    def __load_audio(self):
        display_path = audio_source_utils.to_originals_relative_path(self.__file_path)
        if not os.path.exists(self.__file_path):
            self.__lblInfo.setText(f"文件不存在：{display_path}")
            self.__lblInfo.setToolTip(display_path)
            self.__btnPlay.setEnabled(False)
            self.__btnStop.setEnabled(False)
            return
        sound_file = soundfile.SoundFile(self.__file_path)
        audio_data = sound_file.read()
        sample_rate = sound_file.samplerate
        duration = sound_file.frames / sample_rate if sample_rate else 0
        sound_file.close()
        self.__waveform.set_audio(audio_data, sample_rate)
        self.__waveform.set_duration(int(duration * 1000))
        elided_path = self.fontMetrics().elidedText(display_path, Qt.TextElideMode.ElideMiddle, 420)
        self.__lblInfo.setText(f"{elided_path}    时长 {duration:.2f}s")
        self.__lblInfo.setToolTip(display_path)
        self.__media_player.setSource(QUrl.fromLocalFile(self.__file_path))

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
        self.__waveform.set_position(0)

    # 播放状态改变时切换按钮文案
    def _on_playback_state_changed(self, state):
        self.__btnPlay.setText("暂停" if state == QMediaPlayer.PlaybackState.PlayingState else "播放")

    # 播放结束时：循环则重头播放，否则回到开头
    def _on_media_status_changed(self, status):
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        if self.__chkLoop.isChecked():
            self.__media_player.play()
        else:
            self.__media_player.stop()
            self.__media_player.setPosition(0)
            self.__waveform.set_position(0)

    # 打开文件所在文件夹
    def open_containing_folder(self):
        folder = os.path.dirname(self.__file_path)
        if os.path.isdir(folder):
            if hasattr(os, "startfile"):
                os.startfile(folder)

    def closeEvent(self, event):
        self.__media_player.stop()
        super().closeEvent(event)
