from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


# 多列键值映射编辑表（带添加/删除按钮）
class MapEdit(QWidget):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.__column_count = 0
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

    # 设置表头（列数）并清空旧数据
    def set_headers(self, headers: list[str]):
        self.__column_count = len(headers)
        self.__table.setColumnCount(self.__column_count)
        self.__table.setHorizontalHeaderLabels(headers)

    def set_data(self, rows: list[tuple]):
        self.__table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                self.__table.setItem(row, column, QTableWidgetItem(str(value)))

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
