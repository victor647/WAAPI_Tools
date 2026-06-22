"""GUI / MCP 共用的 Wwise 对象表：行模型、显示模式、填充与筛选逻辑。

具体批处理入口由子类实现 `_run_batch`：`wwise_object_table_gui` 使用 `create_async`，
`wwise_object_table_mcp` 使用 `create_sync`。
"""
import globals.global_variables as gv
from enum import Enum
from PySide6.QtWidgets import QTableView
from PySide6.QtCore import Qt, Signal
from libraries.table_view.table_facade import TableFacade
from libraries.table_view.table_item_model import TableItemModel
from libraries.table_view.table_cell_data import TableCellData
from libraries.wwise_object import WwiseObject, WwiseObjectType
from libraries.utils.wwise import common_utils, waapi_utils
from table.wwise_table_headers import *
from table.wwise_table_row_data import WwiseTableRowData
from libraries.utils.log_utils import Logger


# 与 Wwise 表格配合：「启用」列勾选时写入工程并回读有效状态（含父级链路）
class WwiseObjectTableModel(TableItemModel):
    inclusion_updated = Signal(int)
    row_metadata_changed = Signal(int)

    def set_cell_item(self, row: int, column: int, cell_data: TableCellData):
        super().set_cell_item(row, column, cell_data)
        item = self.item(row, column)
        if not item:
            return
        flags = item.flags()
        flags &= ~Qt.ItemFlag.ItemIsEditable
        if column in (NAME_COL, DESCRIPTION_COL):
            flags |= Qt.ItemFlag.ItemIsEditable
        item.setFlags(flags)

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.EditRole and index.column() == NAME_COL:
            row = index.row()
            new_name = ("" if value is None else str(value)).strip()
            row_data = self._data[row]
            if not new_name:
                row_data.read_common_data()
                self.refresh_cell(row, NAME_COL)
                return True
            if new_name == row_data.name:
                return True
            if waapi_utils.rename_object(row_data.wwise_object, new_name):
                updated = waapi_utils.get_full_info_from_obj_id(row_data.wwise_object.id)
                if updated and updated.is_valid:
                    row_data.replace_wwise_object(updated)
                row_data.read_common_data()
                self.row_metadata_changed.emit(row)
            else:
                Logger().error(
                    f"WAAPI - 无法重命名：{row_data.wwise_object.type} [{row_data.wwise_object.path}]"
                )
                row_data.read_common_data()
                self.refresh_cell(row, NAME_COL)
            return True
        if role == Qt.ItemDataRole.EditRole and index.column() == DESCRIPTION_COL:
            row = index.row()
            text = "" if value is None else str(value)
            row_data = self._data[row]
            if waapi_utils.set_object_notes(row_data.wwise_object, text):
                row_data[DESCRIPTION_COL] = text
            else:
                Logger().error(
                    f"WAAPI - 无法写入备注：{row_data.wwise_object.type} [{row_data.wwise_object.path}]"
                )
                row_data[DESCRIPTION_COL] = row_data.notes
            self.refresh_cell(row, DESCRIPTION_COL)
            return True
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == ENABLE_COL:
            row = index.row()
            row_data = self._data[row]
            if not row_data.cells[ENABLE_COL].is_enabled:
                return False
            checked = value == Qt.CheckState.Checked or value == 2
            common_utils.set_object_inclusion(row_data.wwise_object, checked)
            actual = common_utils.is_object_included(row_data.wwise_object)
            row_data[ENABLE_COL] = actual
            self.refresh_cell(row, ENABLE_COL)
            self.inclusion_updated.emit(row)
            return True
        return super().setData(index, value, role)


class WwiseTableDisplayMode(Enum):
    General = 0
    Design = 1
    Integration = 2


class WwiseObjectTable(TableFacade):
    def __init__(self, table_view: QTableView | None = None):
        super().__init__(table_view, item_model_class=WwiseObjectTableModel)
        self.display_mode: WwiseTableDisplayMode = WwiseTableDisplayMode.General
        self.model.row_metadata_changed.connect(self._on_row_wwise_object_updated)
        self.wwise_transport_id: int = -1
        self._inclusion_cache: dict[str, bool] = {}

    def _run_batch(
        self,
        objects: list,
        processor,
        title: str,
        obj_name: str = "",
        on_finished=None,
        on_interrupted=None,
    ):
        raise NotImplementedError

    def _on_row_wwise_object_updated(self, row: int):
        row_data = self.data[row]
        self.read_data_by_display_mode(row_data)
        self.model.refresh_row(row_data)

    # region Display
    def set_display_mode(self, mode: int):
        self.display_mode = WwiseTableDisplayMode(mode)
        self.refresh_table(False)

    def get_common_headers(self):
        return COMMON_HEADERS.copy()

    def get_headers_by_display_mode(self) -> list[str]:
        if self.display_mode == WwiseTableDisplayMode.Design:
            return DESIGN_HEADERS
        elif self.display_mode == WwiseTableDisplayMode.Integration:
            return INTEGRATION_HEADERS
        return []

    # endregion Display

    # region ReadData
    def fill_table_data(self):
        Logger().info("开始读取音频配置信息...")
        self._inclusion_cache = {}
        self._run_batch(
            gv.active_objects,
            self.add_row_data,
            "获取音频信息",
            "name",
            on_finished=self.on_table_filled,
        )

    def read_common_data(self, row_data: WwiseTableRowData):
        row_data.read_common_data(self._inclusion_cache)

    def filter_by_type(self, obj_type: WwiseObjectType | None) -> int:
        if not self.table_view:
            return len(self.data)
        found_count = 0
        for row in range(self.model.rowCount()):
            if not self.table_view.isRowHidden(row):
                if obj_type is not None and self.data[row].type != obj_type:
                    self.table_view.setRowHidden(row, True)
                else:
                    found_count += 1
        return found_count

    def filter_inclusion_only(self, only_included: bool) -> None:
        if not self.table_view or not only_included:
            return
        for row in range(self.model.rowCount()):
            if self.table_view.isRowHidden(row):
                continue
            if not common_utils.is_object_included(
                self.data[row].wwise_object,
                inclusion_cache=self._inclusion_cache,
            ):
                self.table_view.setRowHidden(row, True)

    def add_row_data(self, row: int, data: WwiseObject):
        if not data:
            return
        row_data = WwiseTableRowData(row, len(self.header_list), data)
        row_data.read_common_data(self._inclusion_cache)
        self.read_data_by_display_mode(row_data)
        self.model.append_row(row_data)

    def read_data_by_display_mode(self, row_data: WwiseTableRowData):
        if self.display_mode == WwiseTableDisplayMode.Design:
            row_data.read_design_info()
        elif self.display_mode == WwiseTableDisplayMode.Integration:
            row_data.read_integration_info()

    # endregion ReadData


def __getattr__(name: str):
    if name == "WwiseTableImpl":
        from table.wwise_object_table_gui import WwiseTableImpl

        return WwiseTableImpl
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
