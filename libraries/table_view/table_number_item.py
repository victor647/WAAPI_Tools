from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem


# 数值单元格：排序时按数值大小比较（默认按显示文本排会把 -9 排到 -12 前面）。
# 数值存放在 UserRole；没有数值（空、「分析中…」、「无信号」之外的文本等）时退回文本比较。
class NumberTableItem(QTableWidgetItem):

    def __init__(self, text: str = "", value=None):
        super().__init__(text)
        if isinstance(value, (int, float)):
            self.setData(Qt.ItemDataRole.UserRole, float(value))

    def __lt__(self, other):
        mine = self.data(Qt.ItemDataRole.UserRole)
        theirs = other.data(Qt.ItemDataRole.UserRole)
        if isinstance(mine, (int, float)) and isinstance(theirs, (int, float)):
            return mine < theirs
        return super().__lt__(other)
