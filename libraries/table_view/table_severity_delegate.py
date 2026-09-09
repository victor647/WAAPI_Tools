from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QTableWidget

from libraries.table_view.table_cell_data import CellSeverity
from libraries.table_view.table_item_model import TableStandardModelCell


# 供普通 QTableWidget 使用的统一 severity 渲染 delegate
# 单元格把 CellSeverity 存进 BackgroundRole，由 TableStandardModelCell +
# material.css 的 [urgent=...] QSS 决定实际颜色（与主窗口对象表一致）
class SeverityTableDelegate(QStyledItemDelegate):

    def __init__(self, parent: QTableWidget = None):
        super().__init__(parent)
        self.__cell = TableStandardModelCell(parent)

    def paint(self, painter, option, index):
        table = self.parent()
        item = table.item(index.row(), index.column()) if isinstance(table, QTableWidget) else None
        if item is not None and isinstance(item.data(Qt.ItemDataRole.BackgroundRole), CellSeverity):
            self.__cell.format_from_item(item)
        else:
            self.__cell.setProperty("urgent", "normal")
        self.initStyleOption(option, index)
        style = QApplication.style()
        style.unpolish(self.__cell)
        style.polish(self.__cell)
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, option, painter, self.__cell)
