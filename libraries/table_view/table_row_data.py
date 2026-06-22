from PySide6.QtCore import Qt
from libraries.table_view.table_cell_data import TableCellData, CellSeverity

# 表格中每行的数据
class TableRowData(object):

    def __init__(self, row: int, max_column: int):
        self.row = row
        # 每一列的单元格数据
        self.cells: list[TableCellData] = []
        self.reset_cells(max_column)

    def __getitem__(self, idx: int):
        return self.cells[idx].display_value

    def __setitem__(self, idx: int, value):
        self.cells[idx].display_value = value

    # 重置所有单元格数据
    def reset_cells(self, max_column: int):
        self.cells = [TableCellData() for _ in range(max_column)]

    # 设置单元格的重要程度
    def set_cell_severity(self, col: int, severity: CellSeverity):
        # 忽略的单元格显示灰色
        if severity == CellSeverity.Ignored:
            self.cells[col].text_color = Qt.GlobalColor.gray
        self.cells[col].severity = severity

    # 设置单元格的值（显示值和原始数值）
    def set_cell_value(self, col: int, display_value, raw_value=None):
        self.cells[col].display_value = display_value
        if raw_value is not None:
            self.cells[col].sort_value = raw_value
        elif isinstance(display_value, (int, float)):
            # 如果display_value本身就是数值类型，自动用作raw_value
            self.cells[col].sort_value = display_value

    # 筛选时决定需要筛选的条目（子类覆盖）
    def get_searched_properties(self) -> list[str]:
        return []