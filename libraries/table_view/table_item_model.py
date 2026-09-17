import globals.global_delegates as gd
from typing import Callable
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex
from PySide6.QtWidgets import QStyledItemDelegate, QApplication, QStyle, QWidget, QTableView
from libraries.table_view.table_cell_data import TableCellData, CellSeverity

INCLUSION_COL = 0

# 表格数据模型
class TableItemModel(QStandardItemModel):

    def __init__(self, parent=None):
        super(TableItemModel, self).__init__(parent)
        self._data = list()
        self._header = list[str]()

    @property
    def header(self) -> list[str]:
        return self._header

    # 设置标题
    @header.setter
    def header(self, header: list[str]) -> None:
        self.setHorizontalHeaderLabels(header)
        self._header = header

    @property
    def raw_data(self) -> list:
        return self._data

    def setData(self, index, value, role = ...):
        if role == Qt.ItemDataRole.CheckStateRole:
            checked = value == 2 or value == Qt.CheckState.Checked
            row = index.row()
            column = index.column()
            if not self._data[row].cells[column].is_enabled:
                return False
            self._data[row][column] = checked
            if gd.on_table_cell_checked:
                gd.on_table_cell_checked(row, column, checked)
        return super().setData(index, value, role)

    # 清除所有数据
    def clear_data(self) -> None:
        self._data.clear()

    # 添加一行
    def append_row(self, row_data) -> None:
        self.setRowCount(self.rowCount() + 1)
        self._data.append(row_data)

    # 单独刷新一格的显示
    def refresh_cell(self, row: int, column: int):
        row_data = self._data[row]
        self.set_cell_item(row, column, row_data.cells[column])
        index = self.createIndex(row, column)
        self.dataChanged.emit(index, index)

    # 单独刷新一行的显示
    def refresh_row(self, row_data):
        for column, cell_info in enumerate(row_data.cells):
            self.set_cell_item(row_data.row, column, cell_info)
        left = self.createIndex(row_data.row, 0)
        right = self.createIndex(row_data.row, self.columnCount() - 1)
        self.dataChanged.emit(left, right)

    # 单独刷新一列的显示
    def refresh_column(self, column: int):
        for row, row_data in enumerate(self._data):
            row_data = self._data[row]
            self.set_cell_item(row, column, row_data.cells[column])
        top = self.createIndex(0, column)
        bottom = self.createIndex(self.rowCount() - 1, column)
        self.dataChanged.emit(top, bottom)

    # 刷新全部表格显示
    def refresh_view(self):
        for row, row_data in enumerate(self._data):
            for column, cell_info in enumerate(row_data.cells):
                self.set_cell_item(row, column, cell_info)
        top_left = self.createIndex(0, 0)
        bottom_right = self.createIndex(self.rowCount() - 1, self.columnCount() - 1)
        self.dataChanged.emit(top_left, bottom_right)

    # 设置单元格内容
    def set_cell_item(self, row: int, column: int, cell_data: TableCellData):
        item = QStandardItem()
        # 空值
        if cell_data.display_value is None:
            item.setText("")
        # 布尔值以复选框形式显示
        elif isinstance(cell_data.display_value, bool):
            item.setCheckable(True)
            item.setCheckState(Qt.CheckState.Checked if cell_data.display_value else Qt.CheckState.Unchecked)
        # 数值保留两位小数
        elif isinstance(cell_data.display_value, float):
            item.setText(("%.2f" % cell_data.display_value).rstrip("0").rstrip("."))
            # 存储原始数值用于排序
            item.setData(cell_data.display_value, Qt.ItemDataRole.UserRole)
        # 整数类型（如quality）
        elif isinstance(cell_data.display_value, int):
            item.setText(str(cell_data.display_value))
            # 存储原始数值用于排序
            item.setData(cell_data.display_value, Qt.ItemDataRole.UserRole)
        # 其他类型直接显示原始数据
        else:
            item.setText(str(cell_data.display_value))
            # 如果有sort_value（用于格式化后的数值字符串），存储用于排序
            if cell_data.sort_value is not None:
                item.setData(cell_data.sort_value, Qt.ItemDataRole.UserRole)
                item.setData(cell_data.sort_value, Qt.ItemDataRole.ToolTipRole)

        # 设置重要程度
        item.setData(cell_data.severity, Qt.ItemDataRole.BackgroundRole)
        # 设置文本颜色
        if cell_data.text_color:
            item.setForeground(cell_data.text_color)
        if not cell_data.is_enabled:
            item.setEnabled(False)
            item.setForeground(Qt.GlobalColor.gray)
        self.setItem(row, column, item)

    # 全选（忽略隐藏的行）
    def check_all(self, checked: bool, table_view: QTableView):
        for row in range(self.rowCount()):
            if table_view.isRowHidden(row):
                continue
            self.check_row_inclusion(row, checked)

    # 单选
    def check_row_inclusion(self, row: int, checked: bool):
        item = self.item(row, INCLUSION_COL)
        check_state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        if item:
            item.setCheckState(check_state)
        self._data[row][INCLUSION_COL] = checked
        if gd.on_table_cell_checked:
            gd.on_table_cell_checked(row, INCLUSION_COL, checked)

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self._data)

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self._header)


# 自定义排序代理模型，支持按数值排序而不是文本排序
class AudioTableSortProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pinned_bottom_count: int = 0
        self.pinned_bottom_checker: Callable[[QModelIndex], bool] | None = None

    def is_pinned_bottom(self, index: QModelIndex) -> bool:
        if not index.isValid():
            return False
        if self.pinned_bottom_checker and self.pinned_bottom_checker(index):
            return True
        if self.pinned_bottom_count > 0:
            source_model = self.sourceModel()
            if source_model:
                if index.row() >= source_model.rowCount() - self.pinned_bottom_count:
                    return True
        return False

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        left_pinned = self.is_pinned_bottom(left)
        right_pinned = self.is_pinned_bottom(right)
        if left_pinned and right_pinned:
            is_asc = (self.sortOrder() == Qt.SortOrder.AscendingOrder)
            return (left.row() < right.row()) if is_asc else (left.row() > right.row())
        if left_pinned != right_pinned:
            is_asc = (self.sortOrder() == Qt.SortOrder.AscendingOrder)
            return not is_asc if left_pinned else is_asc

        # 重写比较方法，优先使用 UserRole 中的数值进行排序
        # 获取UserRole中的数值（如果存在）
        left_value = left.data(Qt.ItemDataRole.UserRole)
        right_value = right.data(Qt.ItemDataRole.UserRole)
        
        # 如果两个值都是数值，使用数值比较
        if left_value is not None and right_value is not None:
            try:
                left_num = float(left_value)
                right_num = float(right_value)
                return left_num < right_num
            except (ValueError, TypeError):
                return str(left_value) < str(right_value)
        
        # 如果只有一个值是数值，数值优先
        if left_value is not None:
            try:
                float(left_value)
                return True  # 数值排在前面
            except (ValueError, TypeError):
                pass
        
        if right_value is not None:
            try:
                float(right_value)
                return False  # 数值排在前面
            except (ValueError, TypeError):
                pass
        
        # 如果都没有数值，使用默认的文本排序
        left_text = left.data(Qt.ItemDataRole.DisplayRole) or ""
        right_text = right.data(Qt.ItemDataRole.DisplayRole) or ""
        return left_text < right_text

# 表格的显示组件
class TableStandardModelCell(QWidget):
    def __init__(self, parent=None):
        super(TableStandardModelCell, self).__init__(parent)

    # 根据重要性设置不同颜色
    def format_from_item(self, item):
        severity = item.data(Qt.ItemDataRole.BackgroundRole)
        if severity == CellSeverity.Normal or severity == CellSeverity.Ignored:
            self.setProperty("urgent", "normal")
        elif severity == CellSeverity.Warning:
            self.setProperty("urgent", "warning")
        elif severity == CellSeverity.Danger:
            self.setProperty("urgent", "danger")
        elif severity == CellSeverity.Success:
            self.setProperty("urgent", "success")

# 为表格创建Item
class AudioTableItemDelegate(QStyledItemDelegate):

    def __init__(self, parent=None):
        super(AudioTableItemDelegate, self).__init__(parent)
        self.cell_widgets: list[TableStandardModelCell] = []

    # 重置所有的单元格
    def reset_all_widgets(self, num: int):
        self.cell_widgets.clear()
        self.cell_widgets = [TableStandardModelCell() for _ in range(num)]

    def paint(self, painter, option, index):
        model = index.model()
        widget_index = model.columnCount() * index.row() + index.column()
        if widget_index >= len(self.cell_widgets):
            return
        cell_widget = self.cell_widgets[widget_index]
        # 如果是代理模型，需要映射到源模型
        if isinstance(model, QSortFilterProxyModel):
            source_index = model.mapToSource(index)
            source_model = source_index.model()
            if isinstance(source_model, QStandardItemModel):
                item = source_model.itemFromIndex(source_index)
                cell_widget.format_from_item(item)
        elif isinstance(model, QStandardItemModel):
            item = model.itemFromIndex(index)
            cell_widget.format_from_item(item)
        self.initStyleOption(option, index)
        style = QApplication.style()
        style.unpolish(cell_widget)
        style.polish(cell_widget)
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, option, painter, cell_widget)
