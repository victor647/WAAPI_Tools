from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QTableWidget

from libraries.table_view.table_item_model import TableStandardModelCell


# 供普通 QTableWidget 使用的统一 severity 渲染 delegate
# 单元格把 CellSeverity 存进 BackgroundRole，由 TableStandardModelCell +
# material.css 的 [urgent=...] QSS 决定实际颜色（与主窗口对象表一致）
class SeverityTableDelegate(QStyledItemDelegate):

    def __init__(self, parent: QTableWidget = None):
        super().__init__(parent)
        self.__cell = TableStandardModelCell(parent)

    def paint(self, painter, option, index):
        try:
            table = self.parent()
            if isinstance(table, QTableWidget):
                item = table.item(index.row(), index.column())
                severity = (
                    item.data(Qt.ItemDataRole.BackgroundRole)
                    if item is not None else None
                )
            else:
                severity = index.data(Qt.ItemDataRole.BackgroundRole)
            self.__cell.format_from_severity(severity)
            self.initStyleOption(option, index)
            style = QApplication.style()
            style.unpolish(self.__cell)
            style.polish(self.__cell)
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, option, painter, self.__cell)
        except KeyboardInterrupt:
            # IDE 停止调试时 SIGINT 可能落在绘制回调内；静默忽略，
            # 避免异常穿过 C++ 边界打印 “Error calling Python override ...”（正常关闭不受影响）
            return
