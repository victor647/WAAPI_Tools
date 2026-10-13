"""GUI / MCP 共用的 Wwise 对象表：行模型、显示模式、填充与筛选逻辑。

具体批处理入口由子类实现 `_run_batch`：`wwise_object_table_gui` 使用 `create_async`，
`wwise_object_table_mcp` 使用 `create_sync`。
"""
import globals.global_variables as gv
from enum import Enum
from data import project_conventions
from PySide6.QtWidgets import QTableView
from PySide6.QtCore import Qt, Signal
from libraries.table_view.table_facade import TableFacade
from libraries.table_view.table_item_model import TableItemModel
from libraries.table_view.table_cell_data import TableCellData
from libraries.wwise_object import WwiseObject, WwiseObjectType
from libraries.utils.wwise import common_utils, soundbank_utils, waapi_utils, workunit_utils
from table.wwise_table_headers import *
from table.wwise_table_row_data import WwiseTableRowData
from libraries.utils.log_utils import Logger


# 导出单元格的值：路径列使用完整原始路径，布尔值转为是/否
def _export_cell_value(cell: TableCellData):
    if isinstance(cell.display_value, bool):
        return "是" if cell.display_value else "否"
    if cell.sort_value is not None:
        return cell.sort_value
    return cell.display_value


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
            obj = row_data.wwise_object
            Logger().debug(f"WAAPI - 表格勾选启用状态：{obj.type} [{obj.name}] 请求 {checked}")
            if not common_utils.set_object_inclusion(obj, checked):
                Logger().error(f"WAAPI - 无法设置启用状态：{obj.path} -> {checked}")
            # 以成功写入的请求值为准更新显示，避免回读「含父级的有效状态」导致刚写入的状态被覆盖
            row_data[ENABLE_COL] = checked
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
        # 极速模式(True)只填充基础属性与启用状态，完整模式才逐个对象读取备注、引用计数等属性
        self.light_mode: bool = False
        self.model.row_metadata_changed.connect(self._on_row_wwise_object_updated)
        self.wwise_transport_id: int = -1
        self._inclusion_cache: dict[str, bool] = {}
        # 集成视图「所属SoundBank」列的 Event -> Bank 对应关系，整表读取期间共用
        self._event_bank_map: dict | None = None
        # 整表读取时按页预取的列属性（{对象ID: {属性名: 值}}）与已预取过的分页起点
        self._properties_by_id: dict = {}
        self._prefetched_pages: set = set()

    def _run_batch(
        self,
        objects: list,
        processor,
        title: str,
        obj_name: str = "",
        on_finished=None,
        on_interrupted=None,
        exclusive: bool = True,
        progress_text_func=None,
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

    # 极速模式下隐藏本次不会读取的列（描述/引用计数以及设计、集成视图专属列），完整模式恢复显示
    def apply_column_visibility(self):
        if not self.table_view:
            return
        hidden_columns: set[int] = set()
        if self.light_mode:
            hidden_columns.update((DESCRIPTION_COL, REFERENCE_COUNT_COL))
            if self.display_mode == WwiseTableDisplayMode.Design:
                hidden_columns.update(range(VOLUME_COL, ORIGINAL_PATH_COL + 1))
            elif self.display_mode == WwiseTableDisplayMode.Integration:
                hidden_columns.update(range(ACTION_COL, VCS_AUTHOR_COL + 1))
        # 使用自动定义的 Bank 时不展示「所属SoundBank」列
        elif self.display_mode == WwiseTableDisplayMode.Integration and project_conventions.use_auto_defined_bank():
            hidden_columns.add(SOUNDBANK_COL)
        for column in range(self.model.columnCount()):
            self.table_view.setColumnHidden(column, column in hidden_columns)

    def refresh_table(self, refresh_data: bool = True):
        self._event_bank_map = None
        super().refresh_table(refresh_data)
        self.apply_column_visibility()

    # 集成视图需要时一次性算出 Event 对应的 Bank，后续行直接复用
    @property
    def event_bank_map(self) -> dict:
        if self._event_bank_map is None:
            self._event_bank_map = soundbank_utils.build_event_bank_map()
        return self._event_bank_map

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
        # 极速模式只读取基础信息与启用状态，不读取音频属性，因此不输出读取日志
        if not self.light_mode:
            Logger().info("开始读取音频对象信息...")
        self._inclusion_cache = {}
        self._event_bank_map = None
        self._prefetched_pages = set()
        self._properties_by_id = {}
        # 仍按对象逐个驱动批处理（进度条跟着对象数量走），列属性在读取每行时按「查询分页大小」惰性分批取回
        self._run_batch(
            gv.active_objects,
            self.add_row_data,
            "获取音频信息",
            "name",
            on_finished=self.on_table_filled,
            # 表格刷新是工具执行过程中也要能跑的只读批处理，不参与「同时只允许一个批处理」的限制
            exclusive=False,
        )

    def read_common_data(self, row_data: WwiseTableRowData, properties: dict = None):
        try:
            row_data.read_common_data(self._inclusion_cache, read_optional=not self.light_mode,
                                      properties=properties,
                                      property_values_by_id=self._properties_by_id)
        except Exception as e:
            Logger().error(f"读取行基础数据失败：{row_data.name} ({e})")

    # obj_types 为 None 表示不限类型；可传单个 WwiseObjectType 或一组
    def filter_by_type(self, obj_types: WwiseObjectType | set | None) -> int:
        if not self.table_view:
            return len(self.data)
        if obj_types is None:
            wanted = None
        elif isinstance(obj_types, WwiseObjectType):
            wanted = {obj_types}
        else:
            wanted = set(obj_types)
        found_count = 0
        for row in range(self.model.rowCount()):
            if not self.is_row_hidden(row):
                if wanted is not None and self.data[row].type not in wanted:
                    self.set_row_hidden(row, True)
                else:
                    found_count += 1
        return found_count

    # 只显示在用资源：AudioFileSource 行只保留父 Sound 的 ActiveSourceList 成员
    # （ActiveSourceList 在 WorkUnit 文件里，workunit_utils 内部按文件缓存，读不到时不隐藏，避免误杀）
    def filter_in_use_only(self, only_in_use: bool, workunit_path_by_source_id: dict = None) -> None:
        if not self.table_view or not only_in_use:
            return
        for row in range(self.model.rowCount()):
            if self.is_row_hidden(row):
                continue
            row_data = self.data[row]
            if row_data.type != WwiseObjectType.AudioSource:
                continue
            workunit_path = (workunit_path_by_source_id or {}).get(row_data.id)
            if not self.__is_source_in_use(row_data.wwise_object, workunit_path):
                self.set_row_hidden(row, True)

    # AudioFileSource 是否在其父 Sound 的 ActiveSourceList 中
    @staticmethod
    def __is_source_in_use(source: WwiseObject, workunit_path: str = None) -> bool:
        parent = waapi_utils.get_parent_object(source)
        if not parent or not parent.is_valid:
            return True
        active_ids = workunit_utils.get_active_source_ids_for_object(parent, workunit_path)
        if not active_ids:
            return True
        return source.id in active_ids

    def filter_inclusion_only(self, only_included: bool) -> None:
        if not self.table_view or not only_included:
            return
        for row in range(self.model.rowCount()):
            if self.is_row_hidden(row):
                continue
            if not common_utils.is_object_included(
                self.data[row].wwise_object,
                inclusion_cache=self._inclusion_cache,
                property_values_by_id=self._properties_by_id,
            ):
                self.set_row_hidden(row, True)

    # 当前显示模式下每行需要读取的列属性（按页一次取回）
    def page_property_names(self) -> list:
        names = ['notes', 'Inclusion']
        if self.display_mode == WwiseTableDisplayMode.Design:
            names += ['Volume', 'OutputBus', 'Attenuation', 'Conversion', 'MaxSoundPerInstance',
                      'originalFilePath']
        elif self.display_mode == WwiseTableDisplayMode.Integration:
            # 集成视图「作者」列需要对象所在的 WorkUnit 文件路径
            names += ['workUnit.filePath']
        return names

    # 预取 row 所在分页的列属性：只在分页首次被访问时发起一次 WAAPI 查询
    def prefetch_row_properties(self, row: int):
        names = ['Inclusion'] if self.light_mode else self.page_property_names()
        if not names:
            return
        objects = gv.active_objects
        start, end = waapi_utils.page_bounds(objects, row)
        if start in self._prefetched_pages:
            return
        self._prefetched_pages.add(start)
        page_objects = objects[start:end]
        properties_by_id = waapi_utils.get_objects_properties(page_objects, names)
        self._properties_by_id.update(properties_by_id)

    def add_row_data(self, row: int, data: WwiseObject, properties: dict = None):
        if not data:
            return
        self.prefetch_row_properties(row)
        if properties is None:
            properties = self._properties_by_id.get(data.id)
        row_data = WwiseTableRowData(row, len(self.header_list), data)
        self.read_common_data(row_data, properties)
        self.read_data_by_display_mode(row_data, properties)
        self.model.append_row(row_data)

    def read_data_by_display_mode(self, row_data: WwiseTableRowData, properties: dict = None):
        if self.light_mode:
            return
        try:
            if self.display_mode == WwiseTableDisplayMode.Design:
                row_data.read_design_info(properties)
            elif self.display_mode == WwiseTableDisplayMode.Integration:
                row_data.read_integration_info(self.event_bank_map, properties)
        except Exception as e:
            Logger().error(f"读取 {row_data.type} [{row_data.name}] 附加属性失败：{e}")

    # endregion ReadData

    # region Export
    # 按指定列导出当前可见行的数据（不含标题行，标题由调用方拼装）
    def build_export_rows(self, columns: list[int]) -> list[list]:
        rows = []
        for row_data in self.active_data:
            rows.append([_export_cell_value(row_data.cells[column]) for column in columns])
        return rows

    # 按单列导出当前可见行的数据（单属性导出为txt时使用）
    def build_export_column(self, column: int) -> list:
        return [_export_cell_value(row_data.cells[column]) for row_data in self.active_data]

    # endregion Export


def __getattr__(name: str):
    if name == "WwiseTableImpl":
        from table.wwise_object_table_gui import WwiseTableImpl

        return WwiseTableImpl
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
