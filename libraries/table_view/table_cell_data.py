from enum import Enum

# 单元格的重要程度
class CellSeverity(Enum):
    Normal = 0
    Warning = 1
    Danger = 2
    Success = 3
    Ignored = 4

# 单元格数据封装
class TableCellData(object):

    def __init__(self):
        self.display_value = ""
        self.severity = CellSeverity.Normal
        self.text_color = None  # Optional QColor for text color
        self.sort_value = None  # Raw numeric value for sorting (used when value is formatted string)
        self.is_enabled = True
