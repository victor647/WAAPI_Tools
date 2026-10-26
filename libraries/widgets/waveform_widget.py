import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter
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
        # 淡入/淡出标记：(start_ms, end_ms, 'in'/'out')
        self.__fade_markers_ms = []
        # 保留的有效区间：(start_ms, end_ms)；区间外绘制白色遮罩
        self.__active_region_ms = None
        # 纵向缩放系数：1.0 表示满幅（1.0 振幅贴到上下边界）
        self.__zoom = 1.0
        # 显示模式：'wave' 波形 / 'spectrum' 频谱热力图
        self.__display_mode = 'wave'
        # 频谱模式下的横向缩放倍数（分屏滚动显示）
        self.__x_zoom = 1.0
        self.__spectrogram_db = None
        self.__spectrogram_image = None
        self.__spectrogram_image_size = (0, 0)
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
        self.__spectrogram_db = None
        self.__spectrogram_image = None
        self.__spectrogram_image_size = (0, 0)
        self.update()

    # 切换显示模式
    def set_display_mode(self, mode: str):
        if mode not in ('wave', 'spectrum'):
            return
        self.__display_mode = mode
        self.__spectrogram_image = None
        self.__spectrogram_image_size = (0, 0)
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

    # 设置淡入/淡出斜线标记（表示裁剪后保留的淡变效果）
    def set_fade_markers(self, markers: list):
        self.__fade_markers_ms = [tuple(marker) for marker in markers]
        self.update()

    # 设置有效区间；None 表示不遮罩
    def set_active_region(self, start_ms: int = None, end_ms: int = None):
        if start_ms is None or end_ms is None:
            self.__active_region_ms = None
        else:
            self.__active_region_ms = (max(0, int(start_ms)), max(0, int(end_ms)))
        self.update()

    # 放大：波形纵向、频谱横向分屏
    def zoom_in(self):
        if self.__display_mode == 'spectrum':
            self.__x_zoom = min(64.0, self.__x_zoom * 1.5)
        else:
            self.__zoom = min(64.0, self.__zoom * 1.5)
        self.__spectrogram_image = None
        self.update()

    # 缩小：下限都是默认的原始缩放（波形到 0dB 边界 / 频谱到全时长）
    def zoom_out(self):
        if self.__display_mode == 'spectrum':
            self.__x_zoom = max(1.0, self.__x_zoom / 1.5)
        else:
            self.__zoom = max(1.0, self.__zoom / 1.5)
        self.__spectrogram_image = None
        self.update()

    # 绘图区域几何信息
    def _plot_rect(self):
        return PLOT_LEFT, PLOT_TOP, self.width() - PLOT_LEFT - PLOT_RIGHT, self.height() - PLOT_TOP - PLOT_BOTTOM

    # 当前可见的时间范围（毫秒）：频谱横向放大时按“整屏滚动”分块——
    # 红线在屏内从左向右走，走到右边界后整屏前进一块、红线回到最左
    def _visible_ms_range(self):
        duration_ms = self.__duration_ms
        if duration_ms <= 0 or self.__display_mode != 'spectrum' or self.__x_zoom <= 1.0:
            return 0, duration_ms
        slice_ms = max(1, int(duration_ms / self.__x_zoom))
        position = self.__position_ms
        # 整屏对齐：红线在当前屏内从左走到右，越界后换下一屏回到最左
        start = (position // slice_ms) * slice_ms
        end = min(duration_ms, start + slice_ms)
        if end <= start:
            end = min(duration_ms, start + 1)
        return start, end

    # 毫秒 → 横坐标（考虑横向缩放）
    def _ms_to_x(self, ms: int):
        left, top, plot_width, plot_height = self._plot_rect()
        if plot_width <= 0:
            return PLOT_LEFT
        start_ms, end_ms = self._visible_ms_range()
        if end_ms <= start_ms:
            return PLOT_LEFT
        fraction = (ms - start_ms) / (end_ms - start_ms)
        return int(PLOT_LEFT + max(0.0, min(1.0, fraction)) * plot_width)

    # 横坐标 → 毫秒
    def _x_to_ms(self, x: int):
        left, top, plot_width, plot_height = self._plot_rect()
        if plot_width <= 0 or self.__duration_ms <= 0:
            return None
        start_ms, end_ms = self._visible_ms_range()
        fraction = (x - PLOT_LEFT) / plot_width
        return int(start_ms + max(0.0, min(1.0, fraction)) * (end_ms - start_ms))

    # 把绘图区内的横坐标换算成播放时间（毫秒），越界返回 None
    def _time_from_x(self, x: int):
        left, top, plot_width, plot_height = self._plot_rect()
        if plot_width <= 0 or plot_height <= 0 or self.__duration_ms <= 0:
            return None
        if x < left or x > left + plot_width:
            return None
        return self._x_to_ms(x)

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
                line_x = self._ms_to_x(current_ms)
                if not PLOT_LEFT <= line_x <= PLOT_LEFT + plot_width:
                    current_ms += step_ms
                    continue
                painter.drawLine(line_x, PLOT_TOP, line_x, PLOT_TOP + plot_height)
                painter.setPen(text_color)
                painter.drawText(line_x - 25, PLOT_TOP + plot_height + 6, 50, 16, Qt.AlignmentFlag.AlignHCenter, f"{current_ms}ms")
                painter.setPen(grid_color)
                current_ms += step_ms
        else:
            time_step = self._nice_time_step(duration)
            time_seconds = 0.0
            while time_seconds <= duration + 1e-9:
                line_x = self._ms_to_x(int(time_seconds * 1000))
                if not PLOT_LEFT <= line_x <= PLOT_LEFT + plot_width:
                    time_seconds += time_step
                    continue
                painter.drawLine(line_x, PLOT_TOP, line_x, PLOT_TOP + plot_height)
                painter.setPen(text_color)
                painter.drawText(line_x - 25, PLOT_TOP + plot_height + 6, 50, 16, Qt.AlignmentFlag.AlignHCenter, f"{time_seconds:g}s")
                painter.setPen(grid_color)
                time_seconds += time_step

        center_y = PLOT_TOP + plot_height / 2
        half_height = plot_height / 2 - 4
        if self.__display_mode == 'spectrum':
            self._paint_spectrogram(painter, plot_width, plot_height)
        else:
            # 波形：纵轴 0 线居中上下对称，刻度按绝对满幅标度 0/-6/-12/-18 dBFS
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
                painter.drawText(0, lower_y + 2, PLOT_LEFT - 4, 14, Qt.AlignmentFlag.AlignRight, f"{db_value}dB")
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

        # 标注统一裁剪在绘图区内
        painter.setClipRect(PLOT_LEFT, PLOT_TOP, plot_width, plot_height)
        # 静音区域：半透明黄色标出
        if self.__silence_regions_ms and self.__duration_ms > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 193, 7, 90))
            for start_ms, end_ms in self.__silence_regions_ms:
                start_ms = max(0, min(int(start_ms), self.__duration_ms))
                end_ms = max(start_ms, min(int(end_ms), self.__duration_ms))
                x1 = self._ms_to_x(start_ms)
                x2 = self._ms_to_x(end_ms)
                painter.drawRect(x1, PLOT_TOP, x2 - x1, plot_height)

        # 淡入/淡出斜线：表示裁剪后保留的淡变效果
        if self.__fade_markers_ms and self.__duration_ms > 0:
            pen = QColor("#7fd6ff")
            pen.setAlpha(230)
            painter.setPen(pen)
            for start_ms, end_ms, fade_type in self.__fade_markers_ms:
                start_ms = max(0, min(int(start_ms), self.__duration_ms))
                end_ms = max(start_ms, min(int(end_ms), self.__duration_ms))
                if end_ms <= start_ms:
                    continue
                x1 = self._ms_to_x(start_ms)
                x2 = self._ms_to_x(end_ms)
                full_y = int(center_y - (half_height - 4))
                if fade_type == 'in':
                    painter.drawLine(x1, int(center_y), x2, full_y)
                else:
                    painter.drawLine(x1, full_y, x2, int(center_y))

        # 有效区间之外覆盖 50% 白色遮罩
        if self.__active_region_ms and self.__duration_ms > 0:
            start_ms, end_ms = self.__active_region_ms
            start_ms = max(0, min(start_ms, self.__duration_ms))
            end_ms = max(start_ms, min(end_ms, self.__duration_ms))
            mask_pen = painter.pen()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 128))
            x1 = self._ms_to_x(start_ms)
            x2 = self._ms_to_x(end_ms)
            if x1 > PLOT_LEFT:
                painter.drawRect(PLOT_LEFT, PLOT_TOP, x1 - PLOT_LEFT, plot_height)
            if x2 < PLOT_LEFT + plot_width:
                painter.drawRect(x2, PLOT_TOP, PLOT_LEFT + plot_width - x2, plot_height)
            painter.setPen(mask_pen)

        # 红色播放头
        if self.__duration_ms > 0:
            playhead_x = self._ms_to_x(self.__position_ms)
            painter.setPen(QColor("#ff5252"))
            painter.drawLine(playhead_x, PLOT_TOP, playhead_x, PLOT_TOP + plot_height)

    # 频谱模式：按当前绘图区尺寸生成一张热力图（带缓存）。
    # 每个像素列都在对应时间点上独立做一帧 FFT，保证横轴时间与波形/播放头完全一致。
    def _spectrogram_image(self, plot_width: int, plot_height: int):
        if plot_width <= 0 or plot_height <= 0:
            return None
        start_ms, end_ms = self._visible_ms_range()
        # 播放/拖动时按 200ms 分桶，避免逐毫秒重建整张热力图
        bucket = 200
        start_ms = (start_ms // bucket) * bucket
        end_ms = (end_ms // bucket) * bucket
        if end_ms <= start_ms:
            end_ms = min(self.__duration_ms, start_ms + bucket)
        cache_key = (plot_width, plot_height, start_ms, end_ms)
        if self.__spectrogram_image is not None and self.__spectrogram_image_size == cache_key:
            return self.__spectrogram_image
        sample_count = self.__mono.size if self.__mono is not None else 0
        if sample_count == 0:
            return None
        if self.__duration_ms <= 0:
            return None
        n_fft = 1024
        while n_fft > sample_count and n_fft > 64:
            n_fft //= 2
        window = np.hanning(n_fft).astype(np.float32)
        # 每一像素列映射到当前可见时间范围的对应采样点，与播放头共用同一时间轴
        start_sample = int(start_ms / self.__duration_ms * sample_count)
        end_sample = int(end_ms / self.__duration_ms * sample_count)
        start_sample = max(0, min(start_sample, sample_count - n_fft))
        end_sample = max(start_sample + 1, min(end_sample, sample_count))
        step = (end_sample - start_sample) / max(1, plot_width - 1)
        columns = []
        for column in range(plot_width):
            start = min(int(start_sample + column * step), sample_count - n_fft)
            spectrum = np.abs(np.fft.rfft(self.__mono[start:start + n_fft] * window))
            columns.append(spectrum)
        magnitude = np.stack(columns)  # (宽, 频率)
        values_db = 20 * np.log10(magnitude + 1e-9)
        freqs = magnitude.shape[1]
        # 频率从下往上增大：底部第 0 行对应低频，顶部对应 Nyquist
        freq_index = np.clip(freqs - 1 - (np.arange(plot_height) * freqs) // plot_height, 0, freqs - 1)
        sampled = values_db[:, freq_index]  # (宽, 高)
        values = sampled.T
        db_min = float(np.percentile(values, 1))
        db_max = float(np.percentile(values, 99))
        if db_max <= db_min:
            db_max = db_min + 1.0
        level = np.clip((values - db_min) / (db_max - db_min), 0.0, 1.0)

        # Adobe Audition 风格的暖色热力图
        positions = [0.0, 0.2, 0.45, 0.7, 1.0]
        reds = [12, 30, 80, 255, 255]
        greens = [16, 70, 220, 240, 90]
        blues = [48, 230, 120, 70, 40]
        red = np.interp(level, positions, reds)
        green = np.interp(level, positions, greens)
        blue = np.interp(level, positions, blues)
        bgra = np.zeros((plot_height, plot_width, 4), dtype=np.uint8)
        bgra[:, :, 0] = blue
        bgra[:, :, 1] = green
        bgra[:, :, 2] = red
        bgra[:, :, 3] = 255
        image = QImage(bgra.data, plot_width, plot_height, bgra.strides[0], QImage.Format.Format_RGB32)
        self.__spectrogram_image = image.copy()
        self.__spectrogram_image_size = cache_key
        return self.__spectrogram_image

    # 频谱模式：把热力图铺满绘图区并画边框
    def _paint_spectrogram(self, painter, plot_width: int, plot_height: int):
        image = self._spectrogram_image(plot_width, plot_height)
        if image is not None:
            painter.drawImage(PLOT_LEFT, PLOT_TOP, image)
        painter.setPen(QColor("#2a313c"))
        painter.drawRect(PLOT_LEFT, PLOT_TOP, plot_width, plot_height)
        # 频谱纵轴：Hz（0 → Nyquist 从下往上）
        nyquist = self.__sample_rate / 2
        if nyquist <= 0:
            return
        grid_color = QColor("#2a313c")
        text_color = QColor("#8a93a1")
        painter.setPen(grid_color)
        for step in range(5):
            freq = nyquist * step / 4
            line_y = int(PLOT_TOP + plot_height * (1 - step / 4))
            painter.drawLine(PLOT_LEFT, line_y, PLOT_LEFT + plot_width, line_y)
            label = f'{int(freq)}'
            painter.setPen(text_color)
            painter.drawText(0, line_y - 7, PLOT_LEFT - 4, 14, Qt.AlignmentFlag.AlignRight, label)
            painter.setPen(grid_color)

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
