from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget


# 响度表显示范围与刻度（dBFS）
METER_MAX_DB = 0.0
METER_MIN_DB = -60.0
METER_TICKS = (0, -12, -24, -36, -48, -60)

BAR_LEFT = 6
BAR_WIDTH = 14
COLUMN_WIDTH = 26
TICK_WIDTH = 26
VALUE_HEIGHT = 18
LABEL_HEIGHT = 14
MIN_WIDTH = 76

# 常见声道数的通道短名，其它按序号显示
CHANNEL_LABELS = {
    1: ('M',),
    2: ('L', 'R'),
    4: ('L', 'R', 'Ls', 'Rs'),
    6: ('L', 'R', 'C', 'LFE', 'Ls', 'Rs'),
}


# 实时响度表：每个声道一根竖直电平条 + 当前响度数值
class LoudnessMeterWidget(QWidget):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.__levels = [METER_MIN_DB]
        self.setMinimumWidth(MIN_WIDTH)

    # 更新各声道响度（dBFS），列表长度即声道数
    def set_levels(self, levels):
        if not levels:
            return
        channel_count_changed = len(levels) != len(self.__levels)
        self.__levels = [max(METER_MIN_DB, min(METER_MAX_DB, level)) for level in levels]
        if channel_count_changed:
            self.updateGeometry()
        self.update()

    # 单值更新（单声道）
    def set_level(self, level_db: float):
        self.set_levels([level_db])

    # 复位到下限
    def reset(self):
        self.set_levels([METER_MIN_DB] * len(self.__levels))

    def sizeHint(self):
        return QSize(self.__panel_width(), 180)

    def minimumSizeHint(self):
        return QSize(self.__panel_width(), 120)

    # 按声道数计算面板宽度
    def __panel_width(self):
        return max(MIN_WIDTH, BAR_LEFT + len(self.__levels) * COLUMN_WIDTH + TICK_WIDTH + 6)

    # 通道短名
    def __channel_labels(self):
        count = len(self.__levels)
        return CHANNEL_LABELS.get(count, tuple(str(index + 1) for index in range(count)))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#14181f"))
        count = len(self.__levels)
        width = self.width()
        height = self.height()
        bar_top = VALUE_HEIGHT + 4
        bar_height = height - bar_top - LABEL_HEIGHT - 6
        if count == 0 or bar_height <= 0:
            return
        labels = self.__channel_labels()
        tick_left = BAR_LEFT + count * COLUMN_WIDTH

        # 数值行：每声道一个当前响度，右侧标注单位
        font = painter.font()
        if font.pointSizeF() > 0:
            font.setPointSizeF(max(6.0, font.pointSizeF() - 2))
            painter.setFont(font)
        painter.setPen(QColor("#c9d3df"))
        for index, level in enumerate(self.__levels):
            column_left = BAR_LEFT + index * COLUMN_WIDTH
            value_text = '--' if level <= METER_MIN_DB else f'{level:.1f}'
            painter.drawText(column_left, 0, COLUMN_WIDTH, VALUE_HEIGHT, Qt.AlignmentFlag.AlignCenter, value_text)
        painter.setPen(QColor("#8a93a1"))
        painter.drawText(tick_left + 5, 0, TICK_WIDTH - 5, VALUE_HEIGHT, Qt.AlignmentFlag.AlignCenter, 'dBFS')

        # dBFS 刻度
        for db_value in METER_TICKS:
            line_y = bar_top + int((METER_MAX_DB - db_value) / (METER_MAX_DB - METER_MIN_DB) * bar_height)
            painter.drawLine(tick_left, line_y, tick_left + 3, line_y)
            painter.drawText(tick_left + 5, line_y - 6, TICK_WIDTH - 5, 12,
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(db_value))

        # 各声道电平条：底槽 + 绿→黄→红渐变 + 边框 + 通道名
        for index, level in enumerate(self.__levels):
            bar_left = BAR_LEFT + index * COLUMN_WIDTH + (COLUMN_WIDTH - BAR_WIDTH) // 2
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#20262f"))
            painter.drawRect(bar_left, bar_top, BAR_WIDTH, bar_height)
            level_y = bar_top + int((METER_MAX_DB - level) / (METER_MAX_DB - METER_MIN_DB) * bar_height)
            gradient = QLinearGradient(0, bar_top + bar_height, 0, bar_top)
            gradient.setColorAt(0.0, QColor("#4fc3a1"))
            gradient.setColorAt(0.7, QColor("#ffc107"))
            gradient.setColorAt(1.0, QColor("#ff5252"))
            painter.setBrush(gradient)
            painter.drawRect(bar_left, level_y, BAR_WIDTH, bar_top + bar_height - level_y)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QColor("#2a313c"))
            painter.drawRect(bar_left, bar_top, BAR_WIDTH, bar_height)
            painter.setPen(QColor("#8a93a1"))
            painter.drawText(bar_left - (COLUMN_WIDTH - BAR_WIDTH) // 2, bar_top + bar_height + 2,
                             COLUMN_WIDTH, LABEL_HEIGHT, Qt.AlignmentFlag.AlignCenter, labels[index])
