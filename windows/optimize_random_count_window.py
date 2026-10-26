from windows.base_analysis_dialog import (
    AnalysisCheckDelegate,
    BaseAnalysisDialog,
    SELECTION_COL,
)
import clipboard
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QDialog, QHeaderView, QMenu, QMessageBox, QSpinBox, QStyledItemDelegate, QTableWidgetItem,
)

import globals.global_variables as gv
from data import project_conventions
from libraries.multi_thread import batch_processor
from libraries.table_view.table_cell_data import CellSeverity
from libraries.table_view.table_number_item import NumberTableItem
from libraries.table_view.table_path_item import create_path_item, full_path_from_item
from libraries.table_view.table_severity_delegate import SeverityTableDelegate
from libraries.utils import user_config
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import common_utils, compression_utils, project_utils, waapi_utils
from libraries.wwise_object import WwiseObjectType
from table.wwise_table_context_menu import add_common_object_actions, connect_double_click_select
from ui.OptimizeRandomCount_ui import Ui_OptimizeRandomCount

COL_NAME = 1
COL_PATH = 2
COL_TOTAL = 3
PLATFORM_COLUMN_START = 4

# 允许数量表：第一行勾选平台，第二行编辑允许数量
ALLOWED_SELECT_ROW = 0
ALLOWED_COUNT_ROW = 1

# 名称列固定宽度，避免长名称把路径和平台列挤出窗口
NAME_COLUMN_WIDTH = 220

# Wwise 的 RandomOrSequence 枚举：0 = Sequence，1 = Random
RANDOM_MODE = 1

# 可能包含 Random Container 子级的根对象类型；其它叶子类型不必做后代查询
CONTAINER_ROOT_TYPES = {
    WwiseObjectType.Folder,
    WwiseObjectType.WorkUnit,
    WwiseObjectType.ActorMixer,
    WwiseObjectType.PropertyContainer,
    WwiseObjectType.RandomContainer,
    WwiseObjectType.BlendContainer,
    WwiseObjectType.SwitchContainer,
}


# 允许数量单元格的编辑器：双击/回车后显示整数 SpinBox
class AllowedCountDelegate(QStyledItemDelegate):

    def createEditor(self, parent, option, index):
        editor = QSpinBox(parent)
        editor.setRange(0, 9999)
        editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return editor

    def setEditorData(self, editor, index):
        try:
            editor.setValue(int(index.data(Qt.ItemDataRole.EditRole)))
        except (TypeError, ValueError):
            editor.setValue(0)

    def setModelData(self, editor, model, index):
        editor.interpretText()
        model.setData(index, str(editor.value()), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


# 优化随机数量：按平台统计 Random Container 下启用的子对象，并把每个容器限制在指定数量
class OptimizeRandomCountWindow(BaseAnalysisDialog, Ui_OptimizeRandomCount):

    # Wwise 切平台命令从 WAAPI 工作线程发出，转到 GUI 线程再更新界面
    platform_command_received = Signal(str)

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # 每行对应一个 Random Container；分析结果按行号存放，工作线程只写自己的下标
        self.__entries: list = []
        self.__analysis_results: list = []
        self.__optimize_results: list = []
        self.__containers: list = []
        self.__random_containers: list = []
        self.__roots: list = []
        self.__root_containers: list = []
        self.__row_checked_by_path: dict = {}
        self.__container_children: dict = {}
        self.__container_skipped: dict = {}
        self.__all_children: list = []
        self.__platform_counts: dict = {}
        self.__skipped_sequence = 0
        self.__skipped_unknown = 0
        self.__platforms: list[str] = []
        self.__platform_names_by_id: dict[str, str] = {}
        self.__current_platform = ''
        # 批处理期间使用的参数在主线程捕获，工作线程不直接读界面控件
        self.__running_default_allowed = 0
        self.__running_allowed_by_platform: dict = {}
        self.__running_platforms: list = []
        self.__running_all_platforms = True
        self.__selected_platforms: set[str] = set()
        self.__selection_initialized = False
        self.__platform_subscription = None
        self.__pending_platform_refresh = False
        self.__event_platform_name = ''
        self.__updating_allowed_counts = False
        self.cbxOnlyOverLimit.setChecked(user_config.get_optimize_random_only_over_limit())
        self.cbxShowMultiGroup.setChecked(user_config.get_optimize_random_show_multi_group())
        self.tblRandomContainers.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.analysis_table = self.setup_analysis_table(
            self.tblRandomContainers, ['名称', '路径', '总样本数量']
        )
        self.tblAllowedCounts.setStyleSheet(
            "QTableWidget { border: none; background: transparent; }"
            "QTableWidget::item { border: none; background: transparent; }"
            "QHeaderView::section { border: none; padding: 0px 4px; }"
            "QTableCornerButton::section { border: none; }"
        )
        self.tblAllowedCounts.setItemDelegate(AllowedCountDelegate(self.tblAllowedCounts))
        self.tblAllowedCounts.setItemDelegateForRow(
            ALLOWED_SELECT_ROW, AnalysisCheckDelegate(self.tblAllowedCounts)
        )
        self.tblAllowedCounts.viewport().setAutoFillBackground(False)
        self.tblAllowedCounts.viewport().setStyleSheet("background: transparent; border: none;")
        self.tblAllowedCounts.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tblAllowedCounts.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        transparent = QColor(0, 0, 0, 0)
        palette = self.tblAllowedCounts.palette()
        palette.setColor(QPalette.ColorRole.Base, transparent)
        palette.setColor(QPalette.ColorRole.Window, transparent)
        palette.setColor(QPalette.ColorRole.AlternateBase, transparent)
        self.tblAllowedCounts.setPalette(palette)
        self.tblAllowedCounts.viewport().setPalette(palette)
        self.tblRandomContainers.setItemDelegate(SeverityTableDelegate(self.tblRandomContainers))
        self.setup_triggers()
        self.load_platforms()
        self.load_allowed_counts()
        self.subscribe_platform_changes()

    def setup_triggers(self):
        self.btnAnalyze.clicked.connect(self.analyze)
        self.btnOptimizeSelected.clicked.connect(self.optimize_selected_platforms)
        self.btnOptimizeAll.clicked.connect(self.optimize_all_platforms)
        self.cbxOnlyOverLimit.toggled.connect(self.on_only_over_limit_toggled)
        self.cbxShowMultiGroup.toggled.connect(self.on_show_multi_group_toggled)
        self.cbxSelectAllPlatforms.toggled.connect(self.on_select_all_platforms_toggled)
        self.tblAllowedCounts.itemChanged.connect(self.on_allowed_count_item_changed)
        self.platform_command_received.connect(self.on_platform_command)
        self.tblRandomContainers.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tblRandomContainers.customContextMenuRequested.connect(self.show_context_menu)
        connect_double_click_select(self.tblRandomContainers, self.objects_at_row)

    def closeEvent(self, event):
        self.unsubscribe_platform_changes()
        super().closeEvent(event)

    # 允许数量表：每个平台一列，第一行勾选平台，第二行编辑数量
    def load_allowed_counts(self):
        settings = user_config.get_optimize_random_count_settings()
        default_allowed = settings["allowed_count"]
        allowed_by_platform = settings["allowed_by_platform"]
        platform_set = set(self.__platforms)
        if not self.__selection_initialized:
            if self.__platforms:
                saved = settings["selected_platforms"]
                if saved is None:
                    selected = {self.__current_platform} & platform_set
                else:
                    selected = {name for name in saved if name in platform_set}
                    if not selected and saved and self.__current_platform in platform_set:
                        selected = {self.__current_platform}
                self.__selected_platforms = selected
                self.__selection_initialized = True
        else:
            self.__selected_platforms &= platform_set
        table = self.tblAllowedCounts
        self.__updating_allowed_counts = True
        table.blockSignals(True)
        table.clearContents()
        table.setColumnCount(len(self.__platforms))
        table.setHorizontalHeaderLabels(list(self.__platforms))
        table.setRowCount(2 if self.__platforms else 0)
        for column, platform in enumerate(self.__platforms):
            select_item = QTableWidgetItem()
            select_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            select_item.setCheckState(
                Qt.CheckState.Checked
                if platform in self.__selected_platforms
                else Qt.CheckState.Unchecked
            )
            select_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            select_item.setToolTip(f'勾选后「优化所选平台」会处理 {platform}')
            table.setItem(ALLOWED_SELECT_ROW, column, select_item)
            item = QTableWidgetItem(str(allowed_by_platform.get(platform, default_allowed)))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(ALLOWED_COUNT_ROW, column, item)
        if self.__platforms:
            vertical_header = table.verticalHeader()
            vertical_header.setVisible(True)
            vertical_header.setFixedWidth(44)
            vertical_header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setVerticalHeaderLabels(['选择', '限制'])
            table.horizontalHeader().setFixedHeight(24)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            vertical_header.setDefaultSectionSize(24)
            table.setRowHeight(ALLOWED_SELECT_ROW, 24)
            table.setRowHeight(ALLOWED_COUNT_ROW, 24)
        else:
            table.verticalHeader().setVisible(False)
        self.cbxSelectAllPlatforms.setEnabled(bool(self.__platforms))
        self.cbxSelectAllPlatforms.setChecked(
            bool(self.__platforms)
            and len(self.__selected_platforms) == len(self.__platforms)
        )
        table.blockSignals(False)
        self.__updating_allowed_counts = False
        self.refresh_severity()
        self.apply_row_filter()

    def on_allowed_count_item_changed(self, item: QTableWidgetItem):
        if self.__updating_allowed_counts:
            return
        column = item.column()
        if not 0 <= column < len(self.__platforms):
            return
        platform = self.__platforms[column]
        if item.row() == ALLOWED_SELECT_ROW:
            self.on_platform_selection_changed(platform, item)
            return
        if item.row() != ALLOWED_COUNT_ROW:
            return
        previous = user_config.get_optimize_random_allowed_count(platform)
        try:
            value = max(0, min(9999, int(item.text().strip())))
        except (TypeError, ValueError):
            value = previous
            Logger().warning(f'平台「{platform}」的允许数量不是整数，已还原为 {value}')
        self.__updating_allowed_counts = True
        item.setText(str(value))
        self.__updating_allowed_counts = False
        user_config.set_optimize_random_allowed_count(platform, value)
        self.refresh_severity()
        self.apply_row_filter()

    def on_platform_selection_changed(self, platform: str, item: QTableWidgetItem):
        if item.checkState() == Qt.CheckState.Checked:
            self.__selected_platforms.add(platform)
        else:
            self.__selected_platforms.discard(platform)
        user_config.set_optimize_random_selected_platforms(
            [name for name in self.__platforms if name in self.__selected_platforms]
        )
        self.__updating_allowed_counts = True
        self.cbxSelectAllPlatforms.setChecked(
            bool(self.__platforms)
            and len(self.__selected_platforms) == len(self.__platforms)
        )
        self.__updating_allowed_counts = False

    def selected_platforms(self) -> list:
        return [name for name in self.__platforms if name in self.__selected_platforms]

    # 「全选平台」：勾选时选中所有平台，取消时清空选择
    def on_select_all_platforms_toggled(self, checked: bool):
        if self.__updating_allowed_counts:
            return
        self.__selected_platforms = set(self.__platforms) if checked else set()
        table = self.tblAllowedCounts
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.__updating_allowed_counts = True
        for column in range(len(self.__platforms)):
            item = table.item(ALLOWED_SELECT_ROW, column)
            if item is not None:
                item.setCheckState(state)
        self.__updating_allowed_counts = False
        user_config.set_optimize_random_selected_platforms(
            [name for name in self.__platforms if name in self.__selected_platforms]
        )

    # 读取工程平台列表与当前平台，并同步表头
    def load_platforms(self):
        try:
            if not waapi_utils.is_connected():
                platforms, current_platform = [], ''
            else:
                platforms = project_utils.get_platforms()
                current_platform = project_utils.get_current_platform_name()
        except Exception:
            Logger().exception('读取工程平台失败')
            platforms, current_platform = [], ''
        self.__platforms = [
            str(item['name']) for item in platforms
            if isinstance(item, dict) and item.get('name')
        ]
        self.__platform_names_by_id = {
            str(item['id']).strip('{}').lower(): str(item['name'])
            for item in platforms
            if isinstance(item, dict) and item.get('id') and item.get('name')
        }
        self.__current_platform = current_platform
        self.render_platform_headers()

    # 按当前平台重绘标签与表头
    def render_platform_headers(self):
        headers = ['名称', '路径', '总样本数量'] + [
            f'{platform}（当前）' if platform == self.__current_platform else platform
            for platform in self.__platforms
        ]
        self.analysis_table.setup(headers)
        header = self.tblRandomContainers.horizontalHeader()
        header.setSectionResizeMode(SELECTION_COL, QHeaderView.ResizeMode.Fixed)
        self.tblRandomContainers.setColumnWidth(SELECTION_COL, 36)
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Interactive)
        self.tblRandomContainers.setColumnWidth(COL_NAME, NAME_COLUMN_WIDTH)
        header.setSectionResizeMode(COL_PATH, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_TOTAL, QHeaderView.ResizeMode.ResizeToContents)
        for column in range(PLATFORM_COLUMN_START, self.tblRandomContainers.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)

    # 订阅 Wwise UI 命令；收到切平台命令后立即刷新当前平台与该平台允许数量
    def subscribe_platform_changes(self):
        if self.__platform_subscription is not None:
            return
        try:
            self.__platform_subscription = waapi_utils.subscribe_topic(
                'ak.wwise.ui.commands.executed', self.on_wwise_ui_command
            )
        except Exception:
            Logger().exception('订阅 Wwise 平台切换事件失败')
            self.__platform_subscription = None
        if self.__platform_subscription is not None:
            Logger().debug('已订阅 Wwise 平台切换事件')
        else:
            Logger().debug('未能订阅 Wwise 平台切换事件，将在分析/优化时重新读取平台')

    def unsubscribe_platform_changes(self):
        if self.__platform_subscription is None:
            return
        waapi_utils.unsubscribe_topic(self.__platform_subscription)
        self.__platform_subscription = None

    # WAAPI 回调在工作线程触发，只发信号回 GUI 线程
    def on_wwise_ui_command(self, payload=None, *args, **_kwargs):
        if isinstance(payload, (list, tuple)) and payload and isinstance(payload[0], dict):
            payload = payload[0]
        if not isinstance(payload, dict):
            payload = next((arg for arg in args if isinstance(arg, dict)), None)
        if not isinstance(payload, dict):
            nested = _kwargs.get('payload')
            payload = nested if isinstance(nested, dict) else None
        if not isinstance(payload, dict) and ('command' in _kwargs or 'platforms' in _kwargs):
            payload = _kwargs
        if not isinstance(payload, dict):
            return
        command = str(payload.get('command') or '')
        platforms = payload.get('platforms') or []
        if isinstance(platforms, (str, dict)):
            platforms = [platforms]
        Logger().trace(f'Wwise UI 命令：{command} platforms={platforms}', console=False, detail=True)
        lowered = command.lower()
        if 'switch' in lowered and 'platform' in lowered:
            Logger().info(f'收到 Wwise 平台切换命令：{command}')
            for platform_id in platforms:
                if isinstance(platform_id, dict):
                    platform_id = platform_id.get('id') or ''
                value = str(platform_id).strip('{}')
                name = self.__platform_names_by_id.get(value.lower(), '')
                if not name and value in self.__platforms:
                    name = value
                if name:
                    self.__event_platform_name = name
                    break
            self.platform_command_received.emit(command)

    def on_platform_command(self, _command: str):
        # 批处理期间不改 __platforms，等批量结束后再刷新
        if self.is_busy():
            self.__pending_platform_refresh = True
            return
        # 事件带有平台 ID 时可直接按它刷新；否则稍等 currentPlatformId 落定
        if self.__event_platform_name:
            preferred = self.__event_platform_name
            self.__event_platform_name = ''
            self.refresh_platform_state(preferred)
            return
        QTimer.singleShot(100, self.refresh_platform_after_command)

    def refresh_platform_after_command(self):
        if self.is_busy():
            self.__pending_platform_refresh = True
            return
        preferred = self.__event_platform_name
        self.__event_platform_name = ''
        self.refresh_platform_state(preferred)

    def refresh_platform_state(self, preferred_platform: str = ''):
        previous = self.__current_platform
        self.load_platforms()
        # currentPlatformId 尚未更新时，用事件里的平台 ID 兜底
        if (
            preferred_platform
            and preferred_platform in self.__platforms
            and self.__current_platform == previous
        ):
            self.__current_platform = preferred_platform
            self.render_platform_headers()
        self.load_allowed_counts()
        self.__pending_platform_refresh = False
        if self.__current_platform and self.__current_platform != previous:
            Logger().info(f'当前平台已切换为 {self.__current_platform}')

    @staticmethod
    def is_busy() -> bool:
        return batch_processor.is_busy()

    @staticmethod
    def chunk_items(items: list, size: int) -> list:
        size = max(1, int(size))
        return [items[index:index + size] for index in range(0, len(items), size)]

    # 采集主窗口对象下所有 Random 模式的 Random Container，并逐行统计各平台启用的子对象数量
    def analyze(self):
        if self.is_busy():
            Logger().warning('已有任务正在运行，请等它结束后再分析')
            return
        self.load_platforms()
        self.load_allowed_counts()
        if not self.__platforms:
            Logger().warning('未读取到工程平台，无法分析随机容器')
            return
        checked_objects, row_checked_by_path = self.analysis_scope()
        if not checked_objects:
            self.__clear_analysis_state()
            if gv.get_table_objects():
                message = self.no_checked_objects_message()
            else:
                message = '表格中没有可用于「优化随机数量」的对象'
            Logger().warning(message)
            QMessageBox.warning(self, '未选择对象', message)
            return
        roots = compression_utils.scan_roots(checked_objects)
        self.__clear_analysis_state()
        self.__row_checked_by_path = row_checked_by_path
        self.__roots = roots
        self.__root_containers = [[] for _ in roots]
        started = batch_processor.create_async(
            roots,
            self.collect_targets_from_root,
            '查找 Random Container',
            'name',
            on_finished=self.on_targets_collected,
        )
        if not started:
            Logger().warning('无法启动分析任务')

    def __clear_analysis_state(self):
        self.__roots = []
        self.__root_containers = []
        self.__containers = []
        self.__random_containers = []
        self.__row_checked_by_path = {}
        self.__container_children = {}
        self.__container_skipped = {}
        self.__all_children = []
        self.__platform_counts = {}
        self.__skipped_sequence = 0
        self.__skipped_unknown = 0
        self.__entries = []
        self.__analysis_results = []
        self.__optimize_results = []
        self.tblRandomContainers.setRowCount(0)

    # 阶段 1：单个根对象下查找所有 Random Container（工作线程）
    def collect_targets_from_root(self, index: int, root):
        found = []
        try:
            if root.type == WwiseObjectType.RandomContainer:
                found.append(root)
            if root.type in CONTAINER_ROOT_TYPES:
                found.extend(waapi_utils.get_descendants_of_type(
                    root, WwiseObjectType.RandomContainer
                ))
        except Exception:
            Logger().exception(f'查找 Random Container 失败：{root.path}')
        unique = {}
        for obj in found:
            unique.setdefault(obj.id, obj)
        self.__root_containers[index] = list(unique.values())
        return True

    def on_targets_collected(self):
        unique = {}
        for items in self.__root_containers:
            for obj in items:
                unique.setdefault(obj.id, obj)
        self.__containers = [
            obj for obj in unique.values()
            if not self.is_excluded_by_scope(
                obj.path, self.__row_checked_by_path
            )
        ]
        if not self.__containers:
            Logger().warning('没有找到可用于「优化随机数量」的 Random Container')
            return
        Logger().debug(f'找到 {len(self.__containers)} 个随机容器，正在筛选模式')
        self.start_next_batch(self.start_mode_filter)

    # 上一阶段线程结束后再启动下一阶段，避免 batch_processor 认为仍在运行
    def start_next_batch(self, starter, attempt: int = 0):
        if self.is_busy():
            if attempt < 50:
                QTimer.singleShot(50, lambda: self.start_next_batch(starter, attempt + 1))
            else:
                Logger().warning('上一阶段批处理未结束，分析中止')
            return
        starter()

    # 阶段 2：批量筛选 Random 模式
    def start_mode_filter(self):
        batches = self.chunk_items(self.__containers, user_config.get_tool_page_size())
        self.__random_containers = []
        self.__skipped_sequence = 0
        self.__skipped_unknown = 0
        batch_processor.create_async(
            batches, self.filter_random_containers, '筛选 Random 模式',
            progress_text_func=lambda index, batch: (
                f'第 {index + 1}/{len(batches)} 批（{len(batch)} 个容器）'
            ),
            on_finished=self.on_modes_filtered,
        )

    def filter_random_containers(self, _index: int, batch: list):
        try:
            modes = waapi_utils.get_objects_properties(batch, ['RandomOrSequence'])
            for container in batch:
                is_random = self.is_random_mode(
                    modes.get(container.id, {}).get('RandomOrSequence')
                )
                if is_random is True:
                    self.__random_containers.append(container)
                elif is_random is False:
                    self.__skipped_sequence += 1
                else:
                    self.__skipped_unknown += 1
        except Exception:
            Logger().exception('筛选 Random 模式失败')
        return True

    def on_modes_filtered(self):
        if not self.__random_containers:
            Logger().warning('没有找到 Random 模式的 Random Container（Sequence 模式已跳过）')
            return
        summary = f'找到 {len(self.__random_containers)} 个 Random Container'
        if self.__skipped_sequence:
            summary += f'，跳过 {self.__skipped_sequence} 个 Sequence 容器'
        if self.__skipped_unknown:
            summary += f'，{self.__skipped_unknown} 个容器未能读取模式'
        Logger().info(summary)
        self.start_next_batch(self.start_collect_children)

    # 阶段 3：一次性批量读取所有容器的直接子对象
    def start_collect_children(self):
        page_size = max(1, user_config.get_tool_page_size())
        batches = self.chunk_items(self.__random_containers, max(50, page_size // 2))
        self.__container_children = {}
        self.__container_skipped = {}
        batch_processor.create_async(
            batches, self.collect_children_batch, '读取 Random Container 子对象',
            progress_text_func=lambda index, batch: (
                f'第 {index + 1}/{len(batches)} 批（{len(batch)} 个容器）'
            ),
            on_finished=self.on_children_collected,
        )

    def collect_children_batch(self, _index: int, batch: list):
        try:
            children_objects = waapi_utils.get_children_of_objects(
                batch, return_fields=['parent']
            )
            grouped = {}
            for child in children_objects:
                parent = (child.wwise_dict or {}).get('parent') or {}
                parent_id = parent.get('id') if isinstance(parent, dict) else ''
                if parent_id:
                    grouped.setdefault(parent_id, []).append(child)
            for container in batch:
                sorted_children, skipped_names = self.sorted_settable_children(
                    grouped.get(container.id, [])
                )
                self.__container_children[container.id] = sorted_children
                self.__container_skipped[container.id] = skipped_names
        except Exception:
            Logger().exception('读取 Random Container 子对象失败')
            for container in batch:
                self.__container_children.setdefault(container.id, [])
                self.__container_skipped.setdefault(container.id, [])
        return True

    def on_children_collected(self):
        all_children_by_id = {}
        for children in self.__container_children.values():
            for child in children:
                all_children_by_id.setdefault(child.id, child)
        self.__all_children = list(all_children_by_id.values())
        Logger().info(f'读取到 {len(self.__all_children)} 个 Random Container 子对象')
        self.start_next_batch(self.start_platform_counts)

    # 阶段 4：每个平台只做一批 Inclusion 查询（内部按分页大小自动分批）
    def start_platform_counts(self):
        self.__platform_counts = {
            platform: {container.id: 0 for container in self.__random_containers}
            for platform in self.__platforms
        }
        if not self.__all_children:
            self.on_platform_counts_collected()
            return
        child_batches = self.chunk_items(
            self.__all_children, user_config.get_tool_page_size()
        )
        work_items = [
            (platform, batch)
            for platform in self.__platforms
            for batch in child_batches
        ]
        batch_processor.create_async(
            work_items, self.count_platform_batch, '统计各平台启用数量',
            progress_text_func=lambda index, item: (
                f'{item[0]} 第 {(index % len(child_batches)) + 1}/{len(child_batches)} 批'
            ),
            on_finished=self.on_platform_counts_collected,
        )

    def count_platform_batch(self, _index: int, item: tuple):
        platform, batch = item
        try:
            properties = waapi_utils.get_objects_properties(
                batch, ['Inclusion'], platform=platform
            )
            counts = self.__platform_counts.setdefault(platform, {})
            for child in batch:
                parent = (child.wwise_dict or {}).get('parent') or {}
                parent_id = parent.get('id') if isinstance(parent, dict) else ''
                if not parent_id or parent_id not in counts:
                    continue
                if (properties.get(child.id) or {}).get('Inclusion'):
                    counts[parent_id] += 1
        except Exception:
            Logger().exception(f'统计平台 {platform} 启用数量失败')
        return True

    # 收集随机容器内所有合法子对象去掉数字后缀后的基础名称
    @staticmethod
    def collect_child_base_names(children: list) -> list:
        base_names = []
        for child in children:
            base_name = project_conventions.get_random_container_base_name(child.name)
            if base_name and base_name not in base_names:
                base_names.append(base_name)
        return base_names

    def on_platform_counts_collected(self):
        self.__entries = [
            {'container': container, 'row': row, 'counts': {}}
            for row, container in enumerate(self.__random_containers)
        ]
        self.__analysis_results = []
        for container in self.__random_containers:
            children = self.__container_children.get(container.id, [])
            self.__analysis_results.append({
                'container': container,
                'children_count': len(children),
                'counts': {
                    platform: self.__platform_counts.get(platform, {}).get(container.id, 0)
                    for platform in self.__platforms
                },
                'skipped_child_names': self.__container_skipped.get(container.id, []),
                'child_base_names': self.collect_child_base_names(children),
            })
        self.fill_placeholder_rows()
        self.on_analysis_finished()

    # 只把 Random 模式纳入统计；兼容数值与字符串两种返回
    @staticmethod
    def is_random_mode(value):
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ('random', '1', 'true'):
                return True
            if normalized in ('sequence', '0', 'false'):
                return False
            return None
        try:
            return int(value) == RANDOM_MODE
        except (TypeError, ValueError):
            return None

    # 先把行占位出来，让分析过程中就能看到容器列表
    def fill_placeholder_rows(self):
        self.analysis_table.ensure_rows(len(self.__entries))
        for row, entry in enumerate(self.__entries):
            container = entry['container']
            name_item = QTableWidgetItem(container.name)
            name_item.setToolTip(f'{container.name}\n{container.path}')
            self.tblRandomContainers.setItem(row, COL_NAME, name_item)
            path_item = create_path_item(container.path)
            self.tblRandomContainers.setItem(row, COL_PATH, path_item)
            self.tblRandomContainers.setItem(row, COL_TOTAL, QTableWidgetItem('分析中…'))
            entry['row'] = row
            for column in range(PLATFORM_COLUMN_START, PLATFORM_COLUMN_START + len(self.__platforms)):
                self.tblRandomContainers.setItem(row, column, QTableWidgetItem('分析中…'))

    # 只保留符合 Random Container 命名规范的子对象，并按后缀数字升序排列
    @staticmethod
    def sorted_settable_children(children: list):
        pattern = project_conventions.get_random_container_child_pattern()
        candidates = []
        skipped_names = []
        for index, child in enumerate(children):
            if not common_utils.can_set_object_inclusion(child):
                continue
            if not pattern:
                candidates.append(((0, index), child))
                continue
            sort_key = project_conventions.get_random_container_child_sort_key(child.name)
            if sort_key is None:
                skipped_names.append(child.name)
                continue
            candidates.append((sort_key, child))
        candidates.sort(key=lambda item: item[0])
        return [child for _, child in candidates], skipped_names

    def on_analysis_finished(self):
        analyzed = 0
        skipped_total = 0
        for row, result in enumerate(self.__analysis_results):
            if not result:
                self.tblRandomContainers.setItem(row, COL_TOTAL, QTableWidgetItem('-'))
                for column in range(PLATFORM_COLUMN_START, PLATFORM_COLUMN_START + len(self.__platforms)):
                    self.tblRandomContainers.setItem(row, column, QTableWidgetItem('-'))
                continue
            analyzed += 1
            entry = self.__entries[row]
            entry['counts'] = dict(result.get('counts') or {})
            entry['children_count'] = result.get('children_count', 0)
            entry['skipped_child_names'] = list(result.get('skipped_child_names') or [])
            entry['child_base_names'] = list(result.get('child_base_names') or [])
            entry['multi_group'] = len(entry['child_base_names']) > 1
            skipped_total += len(entry['skipped_child_names'])
            total_item = NumberTableItem(str(entry['children_count']), entry['children_count'])
            total_tip = '符合 Random 命名规范的子对象总数（含未启用）'
            if entry['multi_group']:
                total_item.setData(
                    Qt.ItemDataRole.BackgroundRole, CellSeverity.Danger
                )
                total_tip += (
                    '\n包含多种名称前缀：'
                    + '、'.join(entry['child_base_names'])
                    + '，请检查是否为多播对象。'
                )
            elif entry['children_count'] <= 1:
                total_item.setData(
                    Qt.ItemDataRole.BackgroundRole, CellSeverity.Warning
                )
                total_tip += f'\n子对象数量为 {entry["children_count"]}，请检查容器内容。'
            total_item.setToolTip(total_tip)
            self.tblRandomContainers.setItem(row, COL_TOTAL, total_item)
            name_item = self.tblRandomContainers.item(row, COL_NAME)
            if name_item is not None:
                tooltip = f'{entry["container"].name}\n{entry["container"].path}'
                if entry['skipped_child_names']:
                    tooltip += (
                        f'\n\n有 {len(entry["skipped_child_names"])} 个子对象'
                        '不符合 Random 命名规范，已忽略。'
                    )
                    name_item.setData(
                        Qt.ItemDataRole.BackgroundRole, CellSeverity.Warning
                    )
                name_item.setToolTip(tooltip)
            for column, platform in enumerate(self.__platforms, start=PLATFORM_COLUMN_START):
                count = entry['counts'].get(platform)
                item = NumberTableItem(
                    str(count) if count is not None else '-',
                    count,
                )
                self.tblRandomContainers.setItem(row, column, item)
        self.refresh_severity()
        self.apply_row_filter()
        summary = f'分析完成：{analyzed} 个 Random Container'
        if skipped_total:
            summary += f'；已忽略 {skipped_total} 个命名不规范子对象'
        Logger().info(summary)
        if self.__pending_platform_refresh:
            preferred = self.__event_platform_name
            self.__event_platform_name = ''
            self.refresh_platform_state(preferred)

    # 数量超过允许值的单元格标红，方便一眼看出需要优化的容器
    def refresh_severity(self, *_args):
        settings = user_config.get_optimize_random_count_settings()
        default_allowed = settings["allowed_count"]
        allowed_by_platform = settings["allowed_by_platform"]
        for row, entry in enumerate(self.__entries):
            counts = entry.get('counts') or {}
            for column, platform in enumerate(self.__platforms, start=PLATFORM_COLUMN_START):
                allowed = allowed_by_platform.get(platform, default_allowed)
                item = self.tblRandomContainers.item(row, column)
                if item is None:
                    continue
                count = counts.get(platform)
                if count is None:
                    item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Normal)
                    item.setToolTip('')
                    continue
                item.setData(
                    Qt.ItemDataRole.BackgroundRole,
                    CellSeverity.Danger if count > allowed else CellSeverity.Normal,
                )
                item.setToolTip(f'{platform}：启用 {count} 个，允许 {allowed} 个')

    # 组合过滤：仅显示超标对象，以及是否显示多种名称前缀的多播对象
    def apply_row_filter(self, *_args):
        only_over_limit = self.cbxOnlyOverLimit.isChecked()
        show_multi_group = self.cbxShowMultiGroup.isChecked()
        settings = user_config.get_optimize_random_count_settings()
        default_allowed = settings["allowed_count"]
        allowed_by_platform = settings["allowed_by_platform"]
        visible_count = 0
        for row, entry in enumerate(self.__entries):
            counts = entry.get('counts') or {}
            # 尚未分析出结果的占位行暂时保留，避免勾选过滤时表格全空
            if not counts:
                self.tblRandomContainers.setRowHidden(row, False)
                visible_count += 1
                continue
            over_limit = False
            for platform in self.__platforms:
                count = counts.get(platform)
                if count is None:
                    continue
                if count > allowed_by_platform.get(platform, default_allowed):
                    over_limit = True
                    break
            hidden = (
                (only_over_limit and not over_limit)
                or (not show_multi_group and entry.get('multi_group'))
            )
            self.tblRandomContainers.setRowHidden(row, hidden)
            if not hidden:
                visible_count += 1
        return visible_count

    def on_only_over_limit_toggled(self, checked: bool):
        user_config.set_optimize_random_only_over_limit(checked)
        self.refresh_severity()
        visible_count = self.apply_row_filter()
        if checked and self.__entries and visible_count == 0:
            Logger().info('当前没有超标对象')

    def on_show_multi_group_toggled(self, checked: bool):
        user_config.set_optimize_random_show_multi_group(checked)
        self.apply_row_filter()

    def optimize_selected_platforms(self):
        self.start_optimize(selected_only=True)

    def optimize_all_platforms(self):
        self.start_optimize(selected_only=False)

    # 执行优化：所选平台只处理勾选平台；全部平台忽略勾选状态处理所有平台
    def start_optimize(self, selected_only: bool):
        if self.is_busy():
            Logger().warning('已有任务正在运行，请等它结束后再优化')
            return
        self.load_platforms()
        self.load_allowed_counts()
        if not self.__platforms:
            Logger().warning('未读取到工程平台，无法优化随机容器')
            return
        if selected_only:
            platforms = self.selected_platforms()
            if not platforms:
                message = '请先在「随机数限制」表格中勾选至少一个需要优化的平台。'
                Logger().warning(message)
                QMessageBox.warning(self, '未选择平台', message)
                return
        else:
            platforms = list(self.__platforms)
        # 优化依赖分析结果（各平台启用数量）；没有分析或分析被中断时先提示，避免按空数据执行
        if not self.__entries or any(not entry.get('counts') for entry in self.__entries):
            message = ('还没有分析结果。请先点击「分析」，等分析完成后再优化。'
                       if not self.__entries else
                       '部分 Random Container 还没有分析结果（分析可能被中断），请重新点击「分析」后再优化。')
            Logger().warning(message)
            QMessageBox.warning(self, '尚未分析', message)
            return
        selected_rows = self.analysis_table.selected_rows(visible_only=True)
        if not selected_rows:
            message = '没有勾选需要优化的随机容器，请先在结果表「选中」列勾选。'
            Logger().warning(message)
            QMessageBox.warning(self, '未选择对象', message)
            return
        settings = user_config.get_optimize_random_count_settings()
        self.__running_default_allowed = settings["allowed_count"]
        allowed_by_platform = {}
        for column, platform in enumerate(self.__platforms):
            item = self.tblAllowedCounts.item(ALLOWED_COUNT_ROW, column)
            try:
                allowed_by_platform[platform] = max(0, min(9999, int(item.text().strip())))
            except (AttributeError, TypeError, ValueError):
                allowed_by_platform[platform] = settings["allowed_by_platform"].get(
                    platform, self.__running_default_allowed
                )
        self.__running_platforms = list(platforms)
        # 只有本次覆盖全部平台时，才能把超出所有平台上限的尾部对象全局关闭
        self.__running_all_platforms = set(platforms) == set(self.__platforms)
        self.__running_allowed_by_platform = {
            platform: allowed_by_platform.get(platform, self.__running_default_allowed)
            for platform in platforms
        }
        self.__optimize_results = [{} for _ in self.__entries]
        platform_detail = '，'.join(
            f'{platform}={self.__running_allowed_by_platform[platform]}'
            for platform in platforms
        )
        title = '优化所选平台' if selected_only else '优化全部平台'
        work_items = [
            (row, self.__entries[row]['container'])
            for row in selected_rows
        ]
        Logger().info(
            f'开始优化随机容器：{len(platforms)} 个平台（{platform_detail}），'
            f'共 {len(work_items)} 个容器'
        )
        batch_processor.create_async(
            work_items,
            self.optimize_container,
            title,
            progress_text_func=lambda index, item: item[1].name,
            on_finished=self.on_optimize_finished,
            undo_group=title,
        )

    # 工作线程：单个容器在每个平台按顺序启用前 N 个，其余解除该平台链接后停用
    def optimize_container(self, index: int, item):
        row, container = item
        try:
            children = self.__container_children.get(container.id)
            if children is None:
                children, skipped_names = self.sorted_settable_children(
                    waapi_utils.get_child_objects(container)
                )
            else:
                children = list(children)
                skipped_names = self.__container_skipped.get(container.id, [])
            changed = 0
            failed = 0
            counts = {}
            # 全平台模式下，超出所有平台允许数量的尾部对象在任何平台都不该启用。
            # 已 unlink 的平台会保留自己的值，需要先 link 回来，全局关闭才能生效。
            global_disable_from = len(children)
            if self.__running_all_platforms:
                global_disable_from = max(
                    self.__running_allowed_by_platform.get(
                        platform, self.__running_default_allowed
                    )
                    for platform in self.__running_platforms
                )
            properties_by_platform = {
                platform: (
                    waapi_utils.get_objects_properties(
                        children, ['Inclusion'], platform=platform
                    ) if children else {}
                )
                for platform in self.__running_platforms
            }
            for order, child in enumerate(children):
                if order >= global_disable_from:
                    included_platforms = [
                        platform for platform in self.__running_platforms
                        if bool(
                            (properties_by_platform[platform].get(child.id) or {}).get('Inclusion')
                        )
                    ]
                    if not included_platforms:
                        continue
                    global_platforms = 0
                    for platform in included_platforms:
                        linked = common_utils.is_object_property_linked(
                            child, 'Inclusion', platform
                        )
                        if linked is not True and not common_utils.link_object_property(
                            child, 'Inclusion', platform
                        ):
                            # 链接失败时退化为只关闭该平台，避免影响其它平台
                            if common_utils.set_object_inclusion_for_platform(child, False, platform):
                                changed += 1
                            else:
                                failed += 1
                            continue
                        global_platforms += 1
                    if global_platforms:
                        if common_utils.set_object_inclusion(child, False):
                            changed += global_platforms
                        else:
                            failed += global_platforms
                    continue
                for platform in self.__running_platforms:
                    allowed = self.__running_allowed_by_platform.get(
                        platform, self.__running_default_allowed
                    )
                    included = bool(
                        (properties_by_platform[platform].get(child.id) or {}).get('Inclusion')
                    )
                    target = order < allowed
                    if included == target:
                        continue
                    if common_utils.set_object_inclusion_for_platform(child, target, platform):
                        changed += 1
                    else:
                        failed += 1
            for platform in self.__running_platforms:
                final_properties = waapi_utils.get_objects_properties(
                    children, ['Inclusion'], platform=platform
                ) if children else {}
                counts[platform] = sum(
                    1 for child in children
                    if (final_properties.get(child.id) or {}).get('Inclusion')
                )
            self.__optimize_results[row] = {
                'container': container,
                'changed': changed,
                'failed': failed,
                'counts': counts,
                'children_count': len(children),
                'skipped_count': len(skipped_names),
            }
            return True
        except Exception:
            Logger().exception(f'优化随机容器失败：{container.path}')
            self.__optimize_results[row] = {'container': container, 'error': True}
            return False

    def on_optimize_finished(self):
        changed_total = 0
        failed_total = 0
        skipped_total = 0
        for row, result in enumerate(self.__optimize_results):
            if not result:
                continue
            changed_total += result.get('changed', 0)
            failed_total += result.get('failed', 0)
            skipped_total += result.get('skipped_count', 0)
            if result.get('error'):
                continue
            counts = result.get('counts') or {}
            self.__entries[row].setdefault('counts', {}).update(counts)
            for column, platform in enumerate(self.__platforms, start=PLATFORM_COLUMN_START):
                count = counts.get(platform)
                if count is not None:
                    self.tblRandomContainers.setItem(
                        row, column, NumberTableItem(str(count), count)
                    )
        self.refresh_severity()
        self.apply_row_filter()
        platform_label = (
            self.__running_platforms[0]
            if len(self.__running_platforms) == 1
            else f'{len(self.__running_platforms)} 个平台'
        )
        Logger().info(
            f'随机容器优化完成：{platform_label}，修改 {changed_total} 处平台状态'
            + (f'，失败 {failed_total} 个' if failed_total else '')
            + (f'，忽略 {skipped_total} 个命名不规范子对象' if skipped_total else '')
        )
        if self.__pending_platform_refresh:
            preferred = self.__event_platform_name
            self.__event_platform_name = ''
            self.refresh_platform_state(preferred)

    def objects_at_row(self, row: int) -> list:
        if 0 <= row < len(self.__entries):
            return [self.__entries[row]['container']]
        return []

    # 任意列的右键菜单都作用于该行的随机容器，通用项与其它表格保持一致
    def show_context_menu(self, position):
        item = self.tblRandomContainers.itemAt(position)
        if item is None:
            return
        row = item.row()
        if not 0 <= row < len(self.__entries):
            return
        menu = QMenu(self)
        add_common_object_actions(
            menu, self.__entries[row]['container'], self,
        )
        # 复制动作按列取单元格内容：名称列复制名称，路径列复制路径
        if item.text():
            menu.addSeparator()
            copy_value = (
                full_path_from_item(item) if item.column() == COL_PATH else item.text()
            )
            menu.addAction('复制', lambda: clipboard.copy(copy_value))
        menu.exec(self.tblRandomContainers.viewport().mapToGlobal(position))
