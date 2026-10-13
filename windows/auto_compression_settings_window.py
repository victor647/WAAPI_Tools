import time

import clipboard
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QHeaderView, QMenu, QMessageBox, QTableWidgetItem, QWidget

import globals.global_variables as gv
from libraries.multi_thread import batch_processor
from libraries.utils import user_config
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import audio_source_utils, compression_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType
from table.wwise_table_context_menu import add_common_object_actions, connect_double_click_select
from table.wwise_table_row_data import WwiseTableRowData
from ui.AutoCompressionSettings_ui import Ui_AutoCompressionSettings


WINDOW_SETTINGS_KEY = "auto_compression_settings"
CONTAINER_TYPE_VALUES = tuple(dict.fromkeys(
    object_type.value for object_type in WwiseObjectType if object_type.value.endswith("Container")
))
TARGET_DISCOVERY_TYPE_VALUES = (
    WwiseObjectType.ActorMixer.value,
    *CONTAINER_TYPE_VALUES,
)

COL_ENABLED = 0
COL_NAME = 1
COL_TYPE = 2
COL_PATH = 3
COL_LONG_COUNT = 4
COL_SHORT_COUNT = 5
COL_CONVERSION = 6


class AutoCompressionSettingsWindow(QDialog, Ui_AutoCompressionSettings):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setupUi(self)
        self.__targets: dict[str, WwiseObject] = {}
        self.__target_type_counts = {"ActorMixer": 0, "Container": 0}
        self.__audio_sources: dict[str, WwiseObject] = {}
        self.__duration_by_source_id: dict = {}
        self.__plans: list[compression_utils.ConversionAssignmentPlan] = []
        self.__override_plans: list[compression_utils.ConversionAssignmentPlan] = []
        self.__plans_by_target_id: dict[str, compression_utils.ConversionAssignmentPlan] = {}
        self.__selected_plans: list[compression_utils.ConversionAssignmentPlan] = []
        self.__plan_batches: list[list[compression_utils.ConversionAssignmentPlan]] = []
        self.__failed_paths: list[str] = []
        self.__long_conversion: WwiseObject = None
        self.__short_conversion: WwiseObject = None
        self.__processing_stage = ""
        self.__summary = {}
        self.__analysis_started_at = 0.0
        self.__analysis_seconds = 0.0
        self.__conversion_load_seconds = 0.0
        self.__conversions_by_id: dict[str, WwiseObject] = {}
        self.__scan_started_at = 0.0
        self.__scan_seconds = 0.0
        self.__planning_seconds = 0.0
        self.__apply_started_at = 0.0
        self.load_user_settings()
        self.setup_triggers()
        self.tblPlanResults.setColumnWidth(COL_ENABLED, 48)
        self.tblPlanResults.setColumnWidth(COL_NAME, 160)
        self.tblPlanResults.setColumnWidth(COL_TYPE, 110)
        self.tblPlanResults.setColumnWidth(COL_LONG_COUNT, 85)
        self.tblPlanResults.setColumnWidth(COL_SHORT_COUNT, 85)
        self.tblPlanResults.setColumnWidth(COL_CONVERSION, 180)
        self.tblPlanResults.horizontalHeader().setSectionResizeMode(
            COL_PATH, QHeaderView.ResizeMode.Stretch
        )
        self._update_control_state()
        # 窗口出现后再读工程里的 Conversion 列表，避免呼出前阻塞
        QTimer.singleShot(0, self.load_conversions)

    def setup_triggers(self):
        self.btnAnalyze.clicked.connect(self.start_analysis)
        self.btnApplySelected.clicked.connect(self.apply_selected_plans)
        self.cbxSelectAll.toggled.connect(self.toggle_select_all)
        self.cbbLongConversion.currentIndexChanged.connect(self._on_conversion_changed)
        self.cbbShortConversion.currentIndexChanged.connect(self._on_conversion_changed)
        self.spbDurationThreshold.valueChanged.connect(self._on_threshold_changed)
        self.tblPlanResults.itemChanged.connect(self._update_apply_button_state)
        self.tblPlanResults.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tblPlanResults.customContextMenuRequested.connect(self.show_context_menu)
        connect_double_click_select(self.tblPlanResults, self._targets_at_row)

    @staticmethod
    def _get_scan_roots(objects: list[WwiseObject]) -> list[WwiseObject]:
        unique_objects = {obj.id: obj for obj in objects if obj and obj.id}
        roots = list(unique_objects.values())
        root_paths = [obj.path.rstrip("\\") for obj in roots if obj.path]
        return [
            obj for obj in roots
            if not obj.path or not any(
                path != obj.path.rstrip("\\") and obj.path.startswith(path + "\\")
                for path in root_paths
            )
        ]

    def load_user_settings(self):
        saved = user_config.get_window_settings(WINDOW_SETTINGS_KEY)
        self.spbDurationThreshold.setValue(float(saved.get("duration_threshold", 0.5)))

    def save_user_settings(self):
        user_config.set_window_settings(WINDOW_SETTINGS_KEY, {
            "long_conversion": self.cbbLongConversion.currentText(),
            "long_conversion_id": self.cbbLongConversion.currentData() or "",
            "short_conversion": self.cbbShortConversion.currentText(),
            "short_conversion_id": self.cbbShortConversion.currentData() or "",
            "duration_threshold": self.spbDurationThreshold.value(),
        })

    # 窗口启动时读取工程里所有 Conversion，按名称里是否含 Long / Short 分成两组填进下拉框
    def load_conversions(self):
        started_at = time.perf_counter()
        conversions = waapi_utils.find_all_objects_by_type(WwiseObjectType.Conversion)
        self.__conversion_load_seconds = time.perf_counter() - started_at
        self.__conversions_by_id = {obj.id: obj for obj in conversions if obj.id}
        saved = user_config.get_window_settings(WINDOW_SETTINGS_KEY)
        self._fill_conversion_combo(
            self.cbbLongConversion,
            [obj for obj in conversions if "long" in obj.name.lower()],
            saved.get("long_conversion"), saved.get("long_conversion_id"),
        )
        self._fill_conversion_combo(
            self.cbbShortConversion,
            [obj for obj in conversions if "short" in obj.name.lower()],
            saved.get("short_conversion"), saved.get("short_conversion_id"),
        )
        self._update_control_state()

    # 填充下拉框：优先按上次保存的 id 选中，其次按名称，都没有就选第一项
    @staticmethod
    def _fill_conversion_combo(combo, objects, saved_name, saved_id):
        combo.blockSignals(True)
        combo.clear()
        for obj in sorted(objects, key=lambda item: item.name):
            combo.addItem(obj.name, obj.id)
            combo.setItemData(combo.count() - 1, obj.path, Qt.ItemDataRole.ToolTipRole)
        index = combo.findData(saved_id) if saved_id else -1
        if index < 0 and saved_name:
            index = combo.findText(saved_name)
        combo.setCurrentIndex(index if index >= 0 else (0 if combo.count() else -1))
        combo.blockSignals(False)

    def _on_conversion_changed(self, _index: int):
        self.save_user_settings()
        self._on_analysis_option_changed()

    # 下拉框当前选中的 Conversion 对象（没选到返回 None）
    def _selected_conversion(self, combo) -> WwiseObject:
        return self.__conversions_by_id.get(combo.currentData())

    def _on_threshold_changed(self, _value: float):
        self.save_user_settings()
        self._on_analysis_option_changed()

    def _on_analysis_option_changed(self, *_args):
        if self.__processing_stage or not self.__plans:
            return
        self._clear_analysis_results()
        self.pteResult.setPlainText("分析设置已修改，请重新分析后再应用。")

    def _clear_analysis_results(self):
        self.__plans.clear()
        self.__override_plans.clear()
        self.__plans_by_target_id.clear()
        self.__selected_plans.clear()
        self.__plan_batches.clear()
        self.__failed_paths.clear()
        self.__summary = {}
        self.tblPlanResults.setSortingEnabled(False)
        self.tblPlanResults.clearContents()
        self.tblPlanResults.setRowCount(0)
        self.pteResult.clear()
        self.cbxSelectAll.setChecked(True)
        self._update_control_state()

    def _has_checked_rows(self) -> bool:
        return any(
            (item := self.tblPlanResults.item(row, COL_ENABLED)) is not None
            and item.checkState() == Qt.CheckState.Checked
            for row in range(self.tblPlanResults.rowCount())
        )

    def _update_apply_button_state(self, _item=None):
        self.btnApplySelected.setEnabled(
            not self.__processing_stage and self._has_checked_rows()
        )

    def _update_control_state(self):
        is_processing = bool(self.__processing_stage)
        has_plans = bool(self.__override_plans)
        self.cbbLongConversion.setEnabled(not is_processing)
        self.cbbShortConversion.setEnabled(not is_processing)
        self.spbDurationThreshold.setEnabled(not is_processing)
        self.btnAnalyze.setEnabled(not is_processing)
        self.tblPlanResults.setEnabled(not is_processing and has_plans)
        self.cbxSelectAll.setEnabled(not is_processing and has_plans)
        self._update_apply_button_state()

    def start_analysis(self):
        self._clear_analysis_results()
        long_conversion = self._selected_conversion(self.cbbLongConversion)
        short_conversion = self._selected_conversion(self.cbbShortConversion)
        if long_conversion is None or short_conversion is None:
            QMessageBox.warning(self, "自动压缩设置", "请在工程中选择长音效和短音效使用的 Conversion 对象。")
            return
        if long_conversion.id == short_conversion.id:
            QMessageBox.warning(self, "自动压缩设置", "长音效与短音效不能使用同一个 Conversion 对象。")
            return
        # 每次分析都临时取主窗口当前对象，保证与表格同步
        table_objects = self._get_scan_roots(gv.get_table_objects())
        if not table_objects:
            QMessageBox.warning(self, "自动压缩设置", "表格中没有可识别的对象。")
            return
        if batch_processor.is_busy():
            QMessageBox.warning(self, "自动压缩设置", batch_processor.busy_message("分析"))
            return

        self.__analysis_started_at = time.perf_counter()

        self.save_user_settings()
        self.__long_conversion = long_conversion
        self.__short_conversion = short_conversion
        self.__targets.clear()
        self.__target_type_counts = {"ActorMixer": 0, "Container": 0}
        self.__audio_sources.clear()
        self.__duration_by_source_id.clear()
        self.__plans.clear()
        self.__override_plans.clear()
        self.__plans_by_target_id.clear()
        self.__selected_plans.clear()
        self.__plan_batches.clear()
        self.__failed_paths.clear()
        self.__processing_stage = "analyze"
        self._update_control_state()
        self.pteResult.setPlainText("正在枚举表格对象下的 ActorMixer、Container 与 AudioFileSource…")
        self.__scan_started_at = time.perf_counter()
        started = batch_processor.create_async(
            table_objects,
            self._enumerate_root_object,
            "自动压缩设置：枚举对象",
            "name",
            on_finished=self._on_enumerate_finished,
            on_interrupted=self._on_scan_interrupted,
            progress_text_func=lambda _index, obj: obj.name,
        )
        if not started:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(self, "自动压缩设置", batch_processor.busy_message("分析"))

    def _enumerate_root_object(self, _index: int, root: WwiseObject) -> bool:
        root_type = (root.wwise_dict or {}).get("type", "")
        target_nodes = [root] if root_type == WwiseObjectType.ActorMixer.value or root_type.endswith(
            "Container"
        ) else []
        target_nodes.extend(waapi_utils.get_descendants_of_type(root, TARGET_DISCOVERY_TYPE_VALUES))
        audio_sources = [root] if root_type == WwiseObjectType.AudioSource.value else []
        audio_sources.extend(waapi_utils.get_descendants_of_type(root, WwiseObjectType.AudioSource))
        actor_mixer_paths = {
            obj.path.rstrip("\\")
            for obj in target_nodes
            if (obj.wwise_dict or {}).get("type") == WwiseObjectType.ActorMixer.value and obj.path
        }
        for obj in target_nodes:
            object_type = (obj.wwise_dict or {}).get("type", "")
            if object_type == WwiseObjectType.ActorMixer.value:
                if obj.id not in self.__targets:
                    self.__targets[obj.id] = obj
                    self.__target_type_counts["ActorMixer"] += 1
            elif (
                isinstance(object_type, str)
                and object_type.endswith("Container")
                and obj.has_property("Conversion")
                and obj.has_property("OverrideConversion")
            ):
                if any(obj.path.startswith(path + "\\") for path in actor_mixer_paths):
                    if obj.id not in self.__targets:
                        self.__targets[obj.id] = obj
                        self.__target_type_counts["Container"] += 1
        for obj in audio_sources:
            if (obj.wwise_dict or {}).get("type") == WwiseObjectType.AudioSource.value:
                self.__audio_sources[obj.id] = obj
        return True

    # 枚举完成后按「查询分页大小」分页读取播放时长：每页一次批量查询，进度条每页步进一次
    def _on_enumerate_finished(self):
        if not self.__targets:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(self, "自动压缩设置", "表格对象下没有找到 ActorMixer。")
            return
        source_pages = list(waapi_utils.iter_object_pages(list(self.__audio_sources.values())))
        if not source_pages:
            self._on_scan_finished()
            return
        self.pteResult.setPlainText(
            f"已枚举 {len(self.__audio_sources)} 个 AudioFileSource，正在分页读取播放时长…"
        )
        started = batch_processor.create_async(
            source_pages,
            self._read_duration_page,
            "自动压缩设置：读取播放时长",
            on_finished=self._on_scan_finished,
            on_interrupted=self._on_scan_interrupted,
            progress_text_func=lambda _index, page: f"{len(page)} 个音频源",
        )
        if not started:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(
                self, "自动压缩设置", batch_processor.busy_message("读取播放时长")
            )

    def _read_duration_page(self, _index: int, page: list) -> bool:
        self.__duration_by_source_id.update(waapi_utils.get_objects_properties(
            page, [audio_source_utils.AUDIO_SOURCE_PLAYBACK_DURATION_PROPERTY]
        ))
        return True

    def _on_scan_finished(self):
        self.__scan_seconds = time.perf_counter() - self.__scan_started_at
        if not self.__targets:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(self, "自动压缩设置", "表格对象下没有找到 ActorMixer。")
            return

        planning_started_at = time.perf_counter()
        self.__plans, self.__summary = compression_utils.build_conversion_plans(
            list(self.__targets.values()),
            list(self.__audio_sources.values()),
            self.__duration_by_source_id,
            self.spbDurationThreshold.value(),
            self.__long_conversion,
            self.__short_conversion,
        )
        self.__planning_seconds = time.perf_counter() - planning_started_at
        if not self.__summary["valid_duration_count"]:
            self.__processing_stage = ""
            self.__analysis_seconds = time.perf_counter() - self.__analysis_started_at
            self._update_control_state()
            self.pteResult.setPlainText(
                f"未读取到有效的 AudioFileSource 播放时长。\n"
                f"分析耗时 {self.__analysis_seconds:.2f}s"
            )
            QMessageBox.warning(self, "自动压缩设置", "没有读取到有效的 AudioFileSource 播放时长，未修改 Conversion。")
            return

        self.__override_plans = [plan for plan in self.__plans if plan.override_enabled]
        self.__plans_by_target_id = {
            plan.target.id: plan for plan in self.__override_plans
        }
        self._render_plan_results()
        self.__analysis_seconds = time.perf_counter() - self.__analysis_started_at
        default_conversion = (
            self.__long_conversion
            if self.__summary["default_category"] == compression_utils.LONG_CATEGORY
            else self.__short_conversion
        )
        self.pteResult.setPlainText(
            f"音频文件：{len(self.__audio_sources)} 个（长 {self.__summary['long_count']}，"
            f"短 {self.__summary['short_count']}，时长不可读 {self.__summary['unclassified_count']}）\n"
            f"默认 Conversion：{default_conversion.name}（按根节点多数结果推导）\n"
            f"分析节点：{len(self.__plans)} 个（ActorMixer {self.__target_type_counts['ActorMixer']}，"
            f"Container {self.__target_type_counts['Container']}）；需要 Override 的节点 "
            f"{len(self.__override_plans)} 个\n"
            f"分析耗时 {self.__analysis_seconds:.2f}s（扫描 {self.__scan_seconds:.2f}s，"
            f"判定 {self.__planning_seconds:.2f}s；Conversion 列表加载 "
            f"{self.__conversion_load_seconds:.2f}s）。候选项默认全部勾选，请确认后应用。"
        )
        self.__processing_stage = ""
        self._update_control_state()
        if not self.__override_plans:
            QMessageBox.information(self, "自动压缩设置", "分析完成，没有需要设置 OverrideConversion 的节点。")

    def _render_plan_results(self):
        check_state = Qt.CheckState.Checked if self.cbxSelectAll.isChecked() else Qt.CheckState.Unchecked
        self.tblPlanResults.blockSignals(True)
        self.tblPlanResults.setSortingEnabled(False)
        self.tblPlanResults.setRowCount(len(self.__override_plans))
        for row, plan in enumerate(self.__override_plans):
            enabled_item = QTableWidgetItem()
            enabled_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            enabled_item.setCheckState(check_state)
            enabled_item.setData(Qt.ItemDataRole.UserRole, plan.target.id)
            self.tblPlanResults.setItem(row, COL_ENABLED, enabled_item)

            name_item = QTableWidgetItem(plan.target.name)
            name_item.setData(Qt.ItemDataRole.UserRole, plan.target.id)
            self.tblPlanResults.setItem(row, COL_NAME, name_item)
            self.tblPlanResults.setItem(row, COL_TYPE, QTableWidgetItem(plan.target.type.name))
            path_item = QTableWidgetItem(WwiseTableRowData.get_path_text(plan.target.path))
            path_item.setData(Qt.ItemDataRole.UserRole, plan.target.path or "")
            self.tblPlanResults.setItem(row, COL_PATH, path_item)
            long_count_item = QTableWidgetItem()
            long_count_item.setData(Qt.ItemDataRole.DisplayRole, plan.long_source_count)
            self.tblPlanResults.setItem(row, COL_LONG_COUNT, long_count_item)
            short_count_item = QTableWidgetItem()
            short_count_item.setData(Qt.ItemDataRole.DisplayRole, plan.short_source_count)
            self.tblPlanResults.setItem(row, COL_SHORT_COUNT, short_count_item)
            self.tblPlanResults.setItem(
                row, COL_CONVERSION, QTableWidgetItem(plan.conversion.name)
            )
        self.tblPlanResults.blockSignals(False)
        self.tblPlanResults.setSortingEnabled(True)
        self._update_apply_button_state()

    # 全选 checkbox：勾选则全部选中，取消则全部取消
    def toggle_select_all(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.tblPlanResults.rowCount()):
            item = self.tblPlanResults.item(row, COL_ENABLED)
            if item is not None:
                item.setCheckState(state)

    # 某一行对应的待应用方案（按对象 id 反查，排序后依然有效）
    def _plan_at_row(self, row: int) -> compression_utils.ConversionAssignmentPlan:
        item = self.tblPlanResults.item(row, COL_ENABLED)
        if item is None:
            return None
        return self.__plans_by_target_id.get(item.data(Qt.ItemDataRole.UserRole))

    def _targets_at_row(self, row: int) -> list:
        plan = self._plan_at_row(row)
        return [plan.target] if plan is not None else []

    # 行右键菜单：路径列可复制完整路径，行上提供通用对象动作（在Wwise中选中）
    def show_context_menu(self, position):
        index = self.tblPlanResults.indexAt(position)
        if not index.isValid():
            return
        plan = self._plan_at_row(index.row())
        if plan is None:
            return
        menu = QMenu(self)
        if index.column() == COL_PATH:
            menu.addAction('复制', lambda: self.copy_object_path(plan.target))
        add_common_object_actions(menu, plan.target, self)
        menu.exec(self.tblPlanResults.viewport().mapToGlobal(position))

    # 复制对象的完整路径（表格里显示的是缩写形式）
    @staticmethod
    def copy_object_path(node: WwiseObject):
        clipboard.copy(node.path)
        Logger().info(f"已复制到剪贴板：{node.path}")

    def _get_checked_plans(self) -> list[compression_utils.ConversionAssignmentPlan]:
        plans = []
        for row in range(self.tblPlanResults.rowCount()):
            item = self.tblPlanResults.item(row, COL_ENABLED)
            if item is None or item.checkState() != Qt.CheckState.Checked:
                continue
            target_id = item.data(Qt.ItemDataRole.UserRole)
            plan = self.__plans_by_target_id.get(target_id)
            if plan is not None:
                plans.append(plan)
        return plans

    def apply_selected_plans(self):
        selected_plans = self._get_checked_plans()
        if not selected_plans:
            QMessageBox.information(self, "自动压缩设置", "请先勾选要应用的节点。")
            return
        if batch_processor.is_busy():
            QMessageBox.warning(
                self, "自动压缩设置", batch_processor.busy_message("应用 Conversion")
            )
            return

        self.__selected_plans = selected_plans
        page_size = max(1, user_config.get_tool_page_size())
        self.__plan_batches = [
            selected_plans[index:index + page_size]
            for index in range(0, len(selected_plans), page_size)
        ]
        self.__failed_paths.clear()
        self.__apply_started_at = time.perf_counter()
        self.__processing_stage = "apply"
        self._update_control_state()
        started = batch_processor.create_async(
            self.__plan_batches,
            self._apply_plan_batch,
            "自动压缩设置：应用 Conversion",
            on_finished=self._on_apply_finished,
            on_interrupted=self._on_apply_interrupted,
            progress_text_func=lambda _index, plans: f"{len(plans)} 个目标对象",
            undo_group="自动压缩设置",
        )
        if not started:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(
                self, "自动压缩设置", batch_processor.busy_message("应用 Conversion")
            )

    def _apply_plan_batch(self, _index: int, plans: list[compression_utils.ConversionAssignmentPlan]) -> bool:
        self.__failed_paths.extend(compression_utils.apply_conversion_plans(plans))
        return True

    def _on_apply_finished(self):
        self.__processing_stage = ""
        self._update_control_state()
        failed_count = len(set(self.__failed_paths))
        applied_count = len(self.__selected_plans) - failed_count
        apply_seconds = time.perf_counter() - self.__apply_started_at
        total_seconds = self.__analysis_seconds + apply_seconds
        default_conversion = (
            self.__long_conversion
            if self.__summary["default_category"] == compression_utils.LONG_CATEGORY
            else self.__short_conversion
        )
        result = (
            f"识别完成：长音效 {self.__summary['long_count']} 个，短音效 {self.__summary['short_count']} 个。\n"
            f"默认 Conversion：{default_conversion.name}。\n"
            f"应用勾选节点：{len(self.__selected_plans)} 个；{applied_count} 个成功，"
            f"{failed_count} 个失败。\n"
            f"耗时（不含人工确认时间）：总计 {total_seconds:.2f}s（分析 "
            f"{self.__analysis_seconds:.2f}s：Conversion 列表加载 {self.__conversion_load_seconds:.2f}s，"
            f"扫描 {self.__scan_seconds:.2f}s，判定 {self.__planning_seconds:.2f}s；"
            f"应用 {apply_seconds:.2f}s）。"
        )
        self.pteResult.setPlainText(result)
        Logger().info(result.replace("\n", "；"))
        if failed_count:
            QMessageBox.warning(
                self,
                "自动压缩设置",
                f"{failed_count} 个目标对象设置失败，详情见日志。",
            )

    def _on_scan_interrupted(self):
        self.__processing_stage = ""
        self._update_control_state()
        QMessageBox.warning(self, "自动压缩设置", "对象扫描被中断，未修改 Conversion。")

    def _on_apply_interrupted(self):
        self.__processing_stage = ""
        self._update_control_state()
        QMessageBox.warning(self, "自动压缩设置", "Conversion 应用被中断，部分 ActorMixer 可能已修改。")

    def closeEvent(self, event):
        if self.__processing_stage:
            event.ignore()
            return
        self.save_user_settings()
        super().closeEvent(event)
