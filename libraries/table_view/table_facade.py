from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QTableView, QAbstractItemView, QHeaderView
from libraries.table_view.table_cell_data import CellSeverity
from libraries.table_view.table_item_model import TableItemModel, AudioTableSortProxyModel, AudioTableItemDelegate, \
    INCLUSION_COL
from typing import Callable, Type
from libraries.table_view.table_row_data import TableRowData
from libraries.utils.log_utils import Logger


# TableView 装饰类；table_view 为 None 时仅保留 model / proxy，供无界面（如 MCP）批处理使用
class TableFacade(object):
    def __init__(
        self,
        table_view: QTableView | None = None,
        item_model_class: Type[TableItemModel] | None = None,
        headers: list[str] | None = None,
        sorting_enabled: bool = True,
        pinned_bottom_count: int = 0,
        pinned_bottom_checker: Callable[[QModelIndex], bool] | None = None,
    ):
        self.table_view = table_view
        self.sorting_enabled = sorting_enabled
        self.pinned_bottom_count = pinned_bottom_count
        self.pinned_bottom_checker = pinned_bottom_checker
        self.custom_headers = list(headers) if headers is not None else None
        model_cls = item_model_class or TableItemModel
        parent = table_view.parent() if table_view else None
        self.model = model_cls(parent)
        self.proxy_model = AudioTableSortProxyModel(parent)
        self.proxy_model.pinned_bottom_count = pinned_bottom_count
        self.proxy_model.pinned_bottom_checker = pinned_bottom_checker
        self.proxy_model.setSourceModel(self.model)
        self.item_delegate: AudioTableItemDelegate | None = None
        if table_view:
            self.table_view.setModel(self.proxy_model)
            self.item_delegate = AudioTableItemDelegate(self.table_view)
            self.table_view.setItemDelegate(self.item_delegate)
        self.header_list = []
        if self.custom_headers is not None:
            self.refresh_headers()
        if table_view:
            self.init_table_view()

    @property
    def column_num(self) -> int:
        return self.model.columnCount()

    # 所有源数据
    @property
    def data(self) -> list:
        return self.model.raw_data

    # 不包含隐藏列的源数据
    @property
    def active_data(self):
        active_data = []
        for row in range(self.model.rowCount()):
            if self.is_row_hidden(row):
                continue
            active_data.append(self.data[row])
        return active_data

    # 从视图索引获取源数据行索引
    def get_source_row(self, index: QModelIndex) -> int:
        source_index = self.proxy_model.mapToSource(index)
        return source_index.row()

    # 源模型行在当前视图中的隐藏状态（兼容排序/过滤后的视图行映射）
    def is_row_hidden(self, source_row: int) -> bool:
        if not self.table_view:
            return False
        if self.proxy_model:
            proxy_index = self.proxy_model.mapFromSource(self.model.index(source_row, 0))
            if not proxy_index.isValid():
                return True
            return self.table_view.isRowHidden(proxy_index.row())
        return self.table_view.isRowHidden(source_row)

    # 按源模型行设置视图行的显隐状态
    def set_row_hidden(self, source_row: int, hidden: bool) -> None:
        if not self.table_view:
            return
        if self.proxy_model:
            proxy_index = self.proxy_model.mapFromSource(self.model.index(source_row, 0))
            if proxy_index.isValid():
                self.table_view.setRowHidden(proxy_index.row(), hidden)
        else:
            self.table_view.setRowHidden(source_row, hidden)

    # 初始化表格设置
    def init_table_view(self):
        if not self.table_view:
            return
        self.table_view.verticalHeader().setHidden(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        self.set_sorting_enabled(self.sorting_enabled)

    # 启用或禁用表格排序
    def set_sorting_enabled(self, enabled: bool):
        self.sorting_enabled = enabled
        if self.table_view:
            self.table_view.setSortingEnabled(enabled)
            header = self.table_view.horizontalHeader()
            if header:
                header.setSortIndicatorShown(enabled)

    # 刷新整个表格
    def refresh_table(self, refresh_data=True):
        Logger().info("正在刷新表格内容...")
        if self.table_view and self.sorting_enabled:
            self.table_view.setSortingEnabled(False)
        self.refresh_headers()
        if refresh_data:
            self.model.clear_data()
            self.fill_table_data()
        else:
            if hasattr(self, "_inclusion_cache"):
                self._inclusion_cache = {}
            for row_data in self.data:
                row_data.reset_cells(len(self.header_list))
                self.read_common_data(row_data)
                self.read_data_by_display_mode(row_data)
            self.on_table_filled()

    # 设置表格标题页
    def refresh_headers(self):
        self.header_list = self.get_common_headers()
        self.model.layoutAboutToBeChanged.emit()
        self.header_list.extend(self.get_headers_by_display_mode())
        self.model.header = self.header_list
        self.model.layoutChanged.emit()

    # 获取所有显示模式通用的标题行
    def get_common_headers(self) -> list[str]:
        if self.custom_headers is not None:
            return self.custom_headers.copy()
        return []

    # 根据当前显示模式获取列信息
    def get_headers_by_display_mode(self) -> list[str]:
        return []

    # 数据行辅助创建与追加
    def create_row(self) -> TableRowData:
        col_count = len(self.header_list) or self.column_num or (len(self.custom_headers) if self.custom_headers else 0)
        return TableRowData(self.model.rowCount(), col_count)

    def append_row(self, row_data: TableRowData) -> None:
        self.model.append_row(row_data)

    def append_row_values(
        self,
        display_values: list,
        raw_values: list | None = None,
        severities: list | None = None,
    ) -> TableRowData:
        row_data = self.create_row()
        for col, disp in enumerate(display_values):
            raw = raw_values[col] if (raw_values and col < len(raw_values)) else None
            row_data.set_cell_value(col, disp, raw)
            if severities and col < len(severities) and severities[col] is not None:
                row_data.set_cell_severity(col, severities[col])
        self.append_row(row_data)
        return row_data

    def clear(self) -> None:
        self.model.clear_data()

    # 自动根据 DisplayRole 文本设定列宽并自适应扩展窗口宽度
    def auto_set_column_width(self):
        if not self.table_view:
            return
        from libraries.utils.qt_utils import auto_adjust_window_width
        auto_adjust_window_width(self.table_view, resize_columns=True)

    # 右键菜单
    def show_context_menu(self, position):
        pass

    # 填充表格内容
    def fill_table_data(self):
        pass

    # 表格内容填充完毕
    def on_table_filled(self):
        row_count = self.model.rowCount()
        Logger().info("表格读取完成")
        Logger().status(f"共{row_count}条")
        if self.table_view and self.item_delegate:
            self.item_delegate.reset_all_widgets(row_count * len(self.model.header))
        self.model.refresh_view()
        self.model.layoutAboutToBeChanged.emit()
        self.model.layoutChanged.emit()
        if self.table_view:
            if self.sorting_enabled:
                self.table_view.setSortingEnabled(True)
            self.auto_set_column_width()

    # 筛选表格中勾选和显示的行
    def get_active_rows(self, checked: bool = True, visible: bool = True) -> list:
        active_rows = []
        for row_data in self.data:
            if checked and not row_data[INCLUSION_COL]:
                continue
            if visible and self.is_row_hidden(row_data.row):
                continue
            active_rows.append(row_data)
        return active_rows

    # 操作完成后更新单元格显示
    def update_cell_display(self, row_data: TableRowData, column: int, value, severity: CellSeverity = None):
        row_data[column] = value
        if severity is None:
            severity = CellSeverity.Success
        row_data.set_cell_severity(column, severity)
        self.model.refresh_cell(row_data.row, column)

    def read_common_data(self, row_data):
        pass

    def read_data_by_display_mode(self, row_data):
        pass

    # 根据所选关键词筛选（case_sensitive 为 True 时区分大小写）
    @staticmethod
    def _filter_segment_matches(properties: list[str], word: str, exact_match: bool) -> bool:
        if not exact_match:
            return any(word in p for p in properties)
        for prop in properties:
            if prop == word:
                return True
            path_nodes = prop.replace("\\", "/").split("/")
            if any(node == word for node in path_nodes):
                return True
        return False

    def filter_results(self, keyword: str, case_sensitive: bool = False) -> int:
        if not self.table_view:
            return len(self.data)

        total_count = self.model.rowCount()
        if total_count == 0:
            return 0
        found_count = 0
        if not keyword:
            for row in range(self.model.rowCount()):
                self.table_view.setRowHidden(row, False)
                found_count += 1
            return found_count

        segments = [s.strip() for s in keyword.split(";")]
        for row in range(self.model.rowCount()):
            properties = self.data[row].get_searched_properties()
            props = [str(p) for p in properties] if case_sensitive else [str(p).lower() for p in properties]

            can_show = True
            for seg in segments:
                if not seg:
                    continue
                exclude = seg.startswith("-")
                if exclude:
                    seg = seg[1:].strip()
                exact_match = seg.startswith("=")
                if exact_match:
                    seg = seg[1:].strip()
                if not seg:
                    continue
                w = seg if case_sensitive else seg.lower()
                if exclude:
                    if self._filter_segment_matches(props, w, exact_match):
                        can_show = False
                        break
                else:
                    if not self._filter_segment_matches(props, w, exact_match):
                        can_show = False
                        continue
            if can_show:
                found_count += 1
            self.set_row_hidden(row, not can_show)
        return found_count
