from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem

from libraries.utils import path_utils


# 统一的 Wwise 路径单元格：显示缩写路径，Tooltip / UserRole 保留完整路径
def create_path_item(path: str) -> QTableWidgetItem:
    full_path = path or ""
    item = QTableWidgetItem(path_utils.get_display_path(full_path))
    item.setToolTip(full_path)
    item.setData(Qt.ItemDataRole.UserRole, full_path)
    return item


# 取路径单元格的完整路径；旧单元格没有 UserRole 时退回 Tooltip
def full_path_from_item(item: QTableWidgetItem) -> str:
    if item is None:
        return ""
    value = item.data(Qt.ItemDataRole.UserRole)
    if value:
        return str(value)
    return item.toolTip() or item.text()
