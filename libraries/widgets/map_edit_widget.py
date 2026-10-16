from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


# 下拉框编辑器：让某一列的单元格从固定选项里选
class ComboColumnDelegate(QStyledItemDelegate):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.__choices: list[str] = []

    def set_choices(self, choices: list):
        self.__choices = [str(choice) for choice in choices]

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.__choices)
        return editor

    def setEditorData(self, editor, index):
        position = editor.findText(str(index.data() or ""))
        editor.setCurrentIndex(position if position >= 0 else 0)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText())


# 多列键值映射编辑表（带添加/删除按钮）
class MapEdit(QWidget):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.__column_count = 0
        self.__first_column_readonly = False
        self.__readonly_columns: set[int] = set()
        self.__combo_delegates: dict = {}
        self.__table = QTableWidget(0, 0, self)
        self.__btnAdd = QPushButton("添加", self)
        self.__btnRemove = QPushButton("删除选中", self)
        self.__btnAdd.clicked.connect(self.add_row)
        self.__btnRemove.clicked.connect(self.remove_selected)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.__btnAdd)
        button_row.addWidget(self.__btnRemove)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.__table)
        layout.addLayout(button_row)

    # 固定行数：隐藏添加/删除按钮，只允许编辑单元格内容
    def set_fixed_rows(self, fixed: bool):
        self.__btnAdd.setVisible(not fixed)
        self.__btnRemove.setVisible(not fixed)

    # 固定高度：刚好容纳指定行数（含表头），超出的行靠滚动查看
    def set_fixed_row_count(self, rows: int):
        table = self.__table
        header_height = table.horizontalHeader().sizeHint().height()
        row_height = table.verticalHeader().defaultSectionSize()
        self.setFixedHeight(header_height + row_height * rows + table.frameWidth() * 2)

    # 首列只读（用于角色/类型等作为键的列）
    def set_first_column_readonly(self, readonly: bool):
        self.__first_column_readonly = readonly
        for row in range(self.__table.rowCount()):
            self.__apply_first_column_flags(row)
        self.__apply_header_state(0)

    # 指定列只读（如关闭缩写规范后禁用「缩写」列）
    def set_column_readonly(self, column: int, readonly: bool):
        if readonly:
            self.__readonly_columns.add(column)
        else:
            self.__readonly_columns.discard(column)
        for row in range(self.__table.rowCount()):
            self.__apply_cell_state(row, column)
        self.__apply_header_state(column)

    # 指定列改用下拉框编辑（choices 为可选值，切换选项后自动刷新后续选择）
    def set_column_choices(self, column: int, choices: list):
        delegate = self.__combo_delegates.get(column)
        if delegate is None:
            delegate = ComboColumnDelegate(self.__table)
            self.__combo_delegates[column] = delegate
            self.__table.setItemDelegateForColumn(column, delegate)
        delegate.set_choices(choices)

    # 指定列拉伸填满剩余宽度（其余列保持默认宽度）
    def set_column_stretch(self, column: int):
        self.__table.horizontalHeader().setSectionResizeMode(
            column, QHeaderView.ResizeMode.Stretch
        )

    # 只读列同时把文字/表头置灰，提示不可编辑
    def __apply_cell_state(self, row: int, column: int):
        item = self.__table.item(row, column)
        if item is None:
            return
        flags = item.flags()
        is_readonly = column in self.__readonly_columns or (column == 0 and self.__first_column_readonly)
        if is_readonly:
            flags &= ~Qt.ItemFlag.ItemIsEditable
        else:
            flags |= Qt.ItemFlag.ItemIsEditable
        item.setFlags(flags)
        if is_readonly:
            item.setForeground(QBrush(Qt.GlobalColor.gray))
        else:
            item.setData(Qt.ItemDataRole.ForegroundRole, None)

    def __apply_header_state(self, column: int):
        is_readonly = column in self.__readonly_columns or (column == 0 and self.__first_column_readonly)
        self.__table.model().setHeaderData(
            column, Qt.Orientation.Horizontal,
            QBrush(Qt.GlobalColor.gray) if is_readonly else None,
            Qt.ItemDataRole.ForegroundRole,
        )

    def __apply_first_column_flags(self, row: int):
        self.__apply_cell_state(row, 0)

    # 设置表头（列数）并清空旧数据
    def set_headers(self, headers: list[str]):
        self.__column_count = len(headers)
        self.__table.setColumnCount(self.__column_count)
        self.__table.setHorizontalHeaderLabels(headers)
        self.__apply_header_state(0)
        for column in self.__readonly_columns:
            self.__apply_header_state(column)

    def set_data(self, rows: list[tuple]):
        self.__table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                self.__table.setItem(row, column, QTableWidgetItem(str(value)))
            self.__apply_first_column_flags(row)
            for column in self.__readonly_columns:
                self.__apply_cell_state(row, column)

    def rows(self) -> list[tuple]:
        result = []
        for row in range(self.__table.rowCount()):
            values = []
            for column in range(self.__column_count):
                item = self.__table.item(row, column)
                values.append(item.text().strip() if item else "")
            if any(values):
                result.append(tuple(values))
        return result

    def add_row(self):
        self.__table.insertRow(self.__table.rowCount())

    def remove_selected(self):
        for index in sorted({item.row() for item in self.__table.selectedItems()}, reverse=True):
            self.__table.removeRow(index)
