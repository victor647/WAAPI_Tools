import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


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
        # 需要标黄的区域（毫秒区间列表）
        self.__silence_regions_ms = []
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

    # 设置要标黄的静音区域（毫秒区间列表）
    def set_silence_regions(self, regions_ms: list):
        self.__silence_regions_ms = [tuple(region) for region in regions_ms]
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

        # 静音区域：半透明黄色标出
        if self.__silence_regions_ms and self.__duration_ms > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 193, 7, 90))
            for start_ms, end_ms in self.__silence_regions_ms:
                start_ms = max(0, min(int(start_ms), self.__duration_ms))
                end_ms = max(start_ms, min(int(end_ms), self.__duration_ms))
                x1 = PLOT_LEFT + int(start_ms / self.__duration_ms * plot_width)
                x2 = PLOT_LEFT + int(end_ms / self.__duration_ms * plot_width)
                painter.drawRect(x1, PLOT_TOP, x2 - x1, plot_height)

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
