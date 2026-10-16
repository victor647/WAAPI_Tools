import clipboard
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QHeaderView, QMenu, QMessageBox, QTableWidgetItem, QWidget

import globals.global_variables as gv
from libraries.multi_thread import batch_processor
from libraries.table_view.table_cell_data import CellSeverity
from libraries.table_view.table_severity_delegate import SeverityTableDelegate
from libraries.utils import user_config
from libraries.utils.log_utils import Logger
from libraries.utils.qt_utils import auto_adjust_window_width
from libraries.utils.wwise import (
    compression_utils,
    conversion_settings_utils,
    project_utils,
    waapi_utils,
)
from libraries.wwise_object import WwiseObject, WwiseObjectType
from table.wwise_table_context_menu import add_common_object_actions, connect_double_click_select
from table.wwise_table_row_data import WwiseTableRowData
from ui.AutoCompressionSettings_ui import Ui_AutoCompressionSettings
from windows.auto_compression_detail_window import AutoCompressionDetailWindow


WINDOW_SETTINGS_KEY = compression_utils.WINDOW_SETTINGS_KEY

COL_NAME = 0
COL_TYPE = 1
COL_PATH = 2
COL_SHORT_COUNT = 3
COL_MEDIUM_COUNT = 4
COL_LONG_COUNT = 5

# 详情列表里的档位显示名
CATEGORY_DISPLAY = {
    compression_utils.SHORT_CATEGORY: "短音效",
    compression_utils.MEDIUM_CATEGORY: "中音效",
    compression_utils.LONG_CATEGORY: "长音效",
    None: "未知（时长不可读）",
}
COUNT_COLUMNS = (COL_SHORT_COUNT, COL_MEDIUM_COUNT, COL_LONG_COUNT)
# 档位 -> 该档对应的「音效数」列（命中的列标绿）
CATEGORY_COLUMNS = {
    compression_utils.SHORT_CATEGORY: COL_SHORT_COUNT,
    compression_utils.MEDIUM_CATEGORY: COL_MEDIUM_COUNT,
    compression_utils.LONG_CATEGORY: COL_LONG_COUNT,
}

# 右侧「各档 Conversion 设置」小表格的列与行（档位放在行头）
COL_SETTING_SAMPLE_RATE = 0
COL_SETTING_FORMAT = 1
COL_SETTING_QUALITY = 2
COL_SETTING_FILE_COUNT = 3
SETTING_ROWS = (
    ("默认档", compression_utils.MEDIUM_CATEGORY),
    ("长音效", compression_utils.LONG_CATEGORY),
    ("短音效", compression_utils.SHORT_CATEGORY),
)
# 右侧小表格的紧凑行高（样式表会把默认行高撑大，这里固定住）
SETTING_ROW_HEIGHT = 24

# 名称模式结果表的列
COL_NAME_PLAN_NAME = 0
COL_NAME_PLAN_TYPE = 1
COL_NAME_PLAN_PATH = 2
COL_NAME_PLAN_KEYWORD = 3
COL_NAME_PLAN_CONVERSION = 4
# 关键词映射表的列
COL_KEYWORD = 0
COL_KEYWORD_CONVERSION = 1


class AutoCompressionSettingsWindow(QDialog, Ui_AutoCompressionSettings):

    _NO_PLAN_TOOLTIP = "没有可应用的节点：请先分析，或勾选「覆盖已有其它 Conversion 的节点」覆盖冲突节点。"

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setupUi(self)
        self.__targets: dict[str, WwiseObject] = {}
        # 主窗口表格行（规范化路径）的「选中」列勾选状态：未勾选的行连同子树都不分析
        self.__row_checked_by_path: dict[str, bool] = {}
        self.__target_type_counts = {"ActorMixer": 0, "Container": 0}
        self.__audio_sources: dict[str, WwiseObject] = {}
        self.__duration_by_source_id: dict = {}
        self.__plans: list[compression_utils.ConversionAssignmentPlan] = []
        self.__override_plans: list[compression_utils.ConversionAssignmentPlan] = []
        self.__conflict_plans: list[compression_utils.ConversionAssignmentPlan] = []
        # 需要在表格里列出并应用的全部节点：需要 Override 的节点 + 已有其它 Override 的冲突节点
        self.__table_plans: list[compression_utils.ConversionAssignmentPlan] = []
        self.__plans_by_target_id: dict[str, compression_utils.ConversionAssignmentPlan] = {}
        # 目标节点当前的 OverrideConversion / Conversion，按页批量读回
        self.__override_states: dict[str, dict] = {}
        self.__plan_batches: list[list[compression_utils.ConversionAssignmentPlan]] = []
        self.__failed_paths: list[str] = []
        self.__apply_total = 0
        self.__conversions_by_category: dict[str, WwiseObject] = {}
        self.__created_categories: set = set()
        self.__name_plans: list[compression_utils.NameConversionPlan] = []
        self.__name_plan_batches: list[list] = []
        self.__name_mapping: list = []
        self.__name_failed_paths: list[str] = []
        self.__name_apply_total = 0
        # 枚举阶段的模式：duration=按时长（同时收集音源与时长），name=按名称（只收集节点）
        self.__enumerate_mode = "duration"
        self.__processing_stage = ""
        self.__summary = {}
        self.__conversions_by_id: dict[str, WwiseObject] = {}
        # 名称模式：关键词 -> Conversion 映射表（Conversion 列用下拉选择）；表头要在读取设置前设好
        self.nameMap.set_headers(["关键词", "Conversion"])
        self.nameMap.set_fixed_row_count(6)
        # Conversion 列拉伸填满剩余宽度，下拉里能看全 Conversion 名字
        self.nameMap.set_column_stretch(COL_KEYWORD_CONVERSION)
        self.load_user_settings()
        self.setup_triggers()
        self.tblPlanResults.setItemDelegate(SeverityTableDelegate(self.tblPlanResults))
        # 档位直接作为行头，省掉一列；行高固定成紧凑高度，不被样式表撑开
        self.tblConversionSettings.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Fixed
        )
        self.tblConversionSettings.verticalHeader().setDefaultSectionSize(SETTING_ROW_HEIGHT)
        self.tblConversionSettings.verticalHeader().setMinimumSectionSize(SETTING_ROW_HEIGHT)
        self.tblNamePlanResults.setItemDelegate(SeverityTableDelegate(self.tblNamePlanResults))
        self.analysisRow.setAlignment(self.analysisPanel, Qt.AlignmentFlag.AlignTop)
        self.analysisRow.setAlignment(self.conversionPanel, Qt.AlignmentFlag.AlignTop)
        self._render_conversion_settings()
        self._update_control_state()
        # 窗口出现后再读工程里的 Conversion 列表与平台，避免呼出前阻塞
        QTimer.singleShot(0, self.load_conversions)
        QTimer.singleShot(0, self.load_platforms)
        QTimer.singleShot(0, self._fit_result_box_height)

    # 分析框只留两行文字的高度（样式表会给它加较大的内边距，等应用完样式再算）
    def _fit_result_box_height(self):
        self.pteResult.setFixedHeight(
            self.pteResult.fontMetrics().lineSpacing() * 2 + 2 * self.pteResult.frameWidth()
        )

    def setup_triggers(self):
        self.btnAnalyze.clicked.connect(self.start_analysis)
        self.btnApply.clicked.connect(self.apply_plans)
        self.cbbDefaultConversion.currentIndexChanged.connect(self._on_conversion_changed)
        self.spbShortThreshold.valueChanged.connect(self._on_threshold_changed)
        self.spbLongThreshold.valueChanged.connect(self._on_threshold_changed)
        self.cbxUseShort.toggled.connect(self._on_detection_toggled)
        self.cbxUseLong.toggled.connect(self._on_detection_toggled)
        self.cbxOverwriteConflicts.toggled.connect(self._on_overwrite_conflicts_toggled)
        self.cbxNameOverwriteConflicts.toggled.connect(self._on_overwrite_conflicts_toggled)
        self.cbbConversionPlatform.currentIndexChanged.connect(self._on_platform_changed)
        self.btnNameAnalyze.clicked.connect(self.start_name_analysis)
        self.btnNameApply.clicked.connect(self.apply_name_plans)
        self.tblPlanResults.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tblPlanResults.customContextMenuRequested.connect(self.show_context_menu)
        connect_double_click_select(self.tblPlanResults, self._targets_at_row)
        self.tblNamePlanResults.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tblNamePlanResults.customContextMenuRequested.connect(self.show_name_context_menu)
        connect_double_click_select(self.tblNamePlanResults, self._name_targets_at_row)

    @staticmethod
    def _get_scan_roots(objects: list[WwiseObject]) -> list[WwiseObject]:
        return compression_utils.scan_roots(objects)

    # 本次分析的目标：主窗口表格里勾选了「选中」列的可见对象（根去重）
    # 未勾选的对象连同其整棵子树都不参与分析；采集不到目标时给出提示并返回 None
    def _collect_scan_targets(self) -> list:
        checked_objects = gv.get_checked_table_objects()
        roots = self._get_scan_roots(checked_objects)
        if not roots:
            if gv.get_table_objects():
                message = (
                    "主窗口表格里没有勾选任何对象（表格最左侧的「选中」列）。\n"
                    "请先勾选要分析的对象。"
                )
            else:
                message = "表格中没有可识别的对象。"
            QMessageBox.warning(self, "自动转码设置", message)
            return None
        # 表格行的勾选状态：某对象取它自己或上层最近的表格行，那一行未勾选就整棵子树跳过
        row_checked_by_path = {
            compression_utils.normalized_path(obj.path): True
            for obj in checked_objects if obj.path
        }
        for path in gv.get_unchecked_table_paths():
            row_checked_by_path.setdefault(compression_utils.normalized_path(path), False)
        self.__row_checked_by_path = row_checked_by_path
        return roots

    def load_user_settings(self):
        saved = user_config.get_window_settings(WINDOW_SETTINGS_KEY)
        self.spbShortThreshold.setValue(float(saved.get("short_threshold", 0.5)))
        self.spbLongThreshold.setValue(float(saved.get("long_threshold", 5.0)))
        for checkbox, key, default in (
            (self.cbxUseShort, "use_short", True), (self.cbxUseLong, "use_long", True)
        ):
            checkbox.blockSignals(True)
            checkbox.setChecked(bool(saved.get(key, default)))
            checkbox.blockSignals(False)
        self._sync_threshold_enabled()
        overwrite_conflicts = bool(saved.get("overwrite_conflicts", True))
        # 两个模式各有一个勾选框（同一份设置），初值保持一致
        for checkbox in (self.cbxOverwriteConflicts, self.cbxNameOverwriteConflicts):
            checkbox.blockSignals(True)
            checkbox.setChecked(overwrite_conflicts)
            checkbox.blockSignals(False)
        keyword_map = saved.get("name_keyword_map") or []
        self.nameMap.set_data([
            (str(item.get("keyword", "")), str(item.get("conversion", "")))
            for item in keyword_map
            if isinstance(item, dict)
        ])

    def save_user_settings(self):
        user_config.set_window_settings(WINDOW_SETTINGS_KEY, {
            "default_conversion": self.cbbDefaultConversion.currentText(),
            "default_conversion_id": self.cbbDefaultConversion.currentData() or "",
            "short_threshold": self.spbShortThreshold.value(),
            "long_threshold": self.spbLongThreshold.value(),
            "use_short": self.cbxUseShort.isChecked(),
            "use_long": self.cbxUseLong.isChecked(),
            "overwrite_conflicts": self.cbxOverwriteConflicts.isChecked(),
            "name_keyword_map": [
                {"keyword": keyword, "conversion": conversion}
                for keyword, conversion in self.nameMap.rows()
            ],
        })

    # 窗口启动时读取工程的平台列表并选中 Wwise 当前平台，供右侧 Format / Quality 小表格使用
    def load_platforms(self):
        names = [
            str(item["name"]) for item in project_utils.get_platforms()
            if isinstance(item, dict) and item.get("name")
        ]
        current_name = project_utils.get_current_platform_name()
        self.cbbConversionPlatform.blockSignals(True)
        self.cbbConversionPlatform.clear()
        self.cbbConversionPlatform.addItems(names)
        index = self.cbbConversionPlatform.findText(current_name) if current_name else -1
        self.cbbConversionPlatform.setCurrentIndex(index if index >= 0 else (0 if names else -1))
        self.cbbConversionPlatform.blockSignals(False)
        self._render_conversion_settings()

    def _on_platform_changed(self, _index: int):
        self._render_conversion_settings()

    # 右侧小表格：三个档位的 Conversion 在当前平台下的 Format / Quality
    def _render_conversion_settings(self):
        platform = self.cbbConversionPlatform.currentText()
        setting_rows = self._setting_rows()
        conversions = {
            category: self.__conversions_by_category.get(category)
            for _label, category in setting_rows
        }
        settings = conversion_settings_utils.get_conversion_settings(
            [obj for obj in conversions.values() if obj], platform
        ) if platform else {}
        file_counts = compression_utils.count_files_by_conversion(
            self.__plans, list(self.__audio_sources.values()),
        )
        table = self.tblConversionSettings
        table.setRowCount(len(setting_rows))
        labels = [label for label, _category in setting_rows]
        table.setVerticalHeaderLabels(labels)
        # 行头宽度按最长档位名算，整表高度按行数收住，避免多余空白
        metrics = table.verticalHeader().fontMetrics()
        header_width = max(metrics.horizontalAdvance(label) for label in labels) + 16
        table.verticalHeader().setFixedWidth(header_width)
        table.setFixedHeight(
            table.horizontalHeader().sizeHint().height()
            + SETTING_ROW_HEIGHT * len(setting_rows)
            + 2 * table.frameWidth() + 2
        )
        for row, (_label, category) in enumerate(setting_rows):
            conversion = conversions.get(category)
            info = settings.get(conversion.id, {}) if conversion else {}
            # 本次新建的档位是默认档的副本，WorkUnit 还没落盘读不到，直接沿用默认档参数
            if not info and category in self.__created_categories:
                default_conversion = conversions.get(compression_utils.MEDIUM_CATEGORY)
                info = settings.get(default_conversion.id, {}) if default_conversion else {}
            # 表格里不显示 Conversion 名称，鼠标悬停时给出对象名与完整路径
            tooltip = f"{conversion.name}\n{conversion.path}" if conversion else "（未生成）"
            values = {
                COL_SETTING_SAMPLE_RATE: conversion_settings_utils.sample_rate_text(info.get("sample_rate")) or "-",
                COL_SETTING_FORMAT: info.get("format") or "-",
                COL_SETTING_QUALITY: info.get("quality") or "-",
                COL_SETTING_FILE_COUNT: str(file_counts.get(category, 0)),
            }
            for column, text in values.items():
                item = QTableWidgetItem(text)
                item.setToolTip(tooltip)
                table.setItem(row, column, item)
        # 列宽按内容自动，但不动窗口宽度（切换平台时表格变宽只应挤压分析框）
        auto_adjust_window_width(table, self, resize_columns=True, resize_window=False)
        # 面板宽度与表格内容完全一致，右边不留空档
        self.conversionPanel.setFixedWidth(
            header_width
            + sum(table.columnWidth(column) for column in range(table.columnCount()))
            + 2 * table.frameWidth() + 2
        )

    # 窗口启动时读取工程里的默认档候选 Conversion（排除名称含 Long / Short 的）
    def load_conversions(self):
        conversions = waapi_utils.find_all_objects_by_type(WwiseObjectType.Conversion)
        self.__conversions_by_id = {obj.id: obj for obj in conversions if obj.id}
        saved = user_config.get_window_settings(WINDOW_SETTINGS_KEY)
        self._fill_conversion_combo(
            self.cbbDefaultConversion,
            [
                obj for obj in conversions
                if "long" not in obj.name.lower() and "short" not in obj.name.lower()
            ],
            saved.get("default_conversion"), saved.get("default_conversion_id"),
        )
        # 名称模式的候选 Conversion：下拉里列出工程里的全部 Conversion
        self.nameMap.set_column_choices(
            COL_KEYWORD_CONVERSION,
            [obj.name for obj in sorted(conversions, key=lambda item: item.name)],
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

    # 长/短音效的判定可以各自开关：关掉的档位不参与分档，阈值输入框同步置灰
    def _on_detection_toggled(self, _checked: bool):
        self.save_user_settings()
        self._sync_threshold_enabled()
        self._render_conversion_settings()
        self._on_analysis_option_changed()

    def _sync_threshold_enabled(self):
        is_processing = bool(self.__processing_stage)
        self.spbShortThreshold.setEnabled(not is_processing and self.cbxUseShort.isChecked())
        self.spbLongThreshold.setEnabled(not is_processing and self.cbxUseLong.isChecked())

    # 长/短音效判定开关当前的状态：(区分短音效, 区分长音效)
    def _detection_flags(self) -> tuple:
        return self.cbxUseShort.isChecked(), self.cbxUseLong.isChecked()

    # 右侧小表格展示的行：默认档 + 已启用判定的档位
    def _setting_rows(self) -> tuple:
        use_short, use_long = self._detection_flags()
        enabled = compression_utils.enabled_categories(use_short, use_long)
        return tuple(
            (label, category) for label, category in SETTING_ROWS if category in enabled
        )

    def _on_analysis_option_changed(self, *_args):
        if self.__processing_stage or not self.__plans:
            return
        self._clear_analysis_results()
        self.pteResult.setPlainText("分析设置已修改，请重新分析后再应用。")

    # 两个模式的「是否覆盖冲突节点」共用一份设置，勾选其一即同步另一个
    def _on_overwrite_conflicts_toggled(self, checked: bool):
        for checkbox in (self.cbxOverwriteConflicts, self.cbxNameOverwriteConflicts):
            if checkbox.isChecked() != checked:
                checkbox.blockSignals(True)
                checkbox.setChecked(checked)
                checkbox.blockSignals(False)
        self.save_user_settings()
        self._update_control_state()

    # 冲突节点数写进勾选框文本，明细写进提示：分析结果框保持两行文字不变
    def _refresh_conflict_indicator(self):
        duration_conflicts = list(self.__conflict_plans)
        name_conflicts = [plan for plan in self.__name_plans if plan.conflict]
        self._update_conflict_checkbox(
            self.cbxOverwriteConflicts, duration_conflicts,
            "已有 Override 且不是本次方案指定的 Conversion 的节点（表格名称列标红）。"
            "勾选时按方案改写这些节点，不勾选时跳过它们、保留原有设置。",
        )
        self._update_conflict_checkbox(
            self.cbxNameOverwriteConflicts, name_conflicts,
            "当前 Conversion 不是映射表指定的那一个的节点（表格 Conversion 列标红）。"
            "勾选时按映射表改写这些节点，不勾选时跳过它们、保留原有设置。",
        )

    @staticmethod
    def _update_conflict_checkbox(checkbox, conflicts: list, hint: str):
        base_text = "覆盖已有其它 Conversion 的节点"
        checkbox.setText(
            f"{base_text}（{len(conflicts)}）" if conflicts else base_text
        )
        if not conflicts:
            checkbox.setToolTip(hint)
            return
        details = [
            f"{plan.target.name}：现有 {plan.existing_conversion_name or '（未知）'}"
            for plan in conflicts[:20]
        ]
        if len(conflicts) > 20:
            details.append(f"…共 {len(conflicts)} 个")
        checkbox.setToolTip("\n".join([hint, *details]))

    def _clear_analysis_results(self):
        self.__plans.clear()
        self.__override_plans.clear()
        self.__conflict_plans.clear()
        self.__table_plans.clear()
        self.__plans_by_target_id.clear()
        self.__override_states.clear()
        self.__plan_batches.clear()
        self.__failed_paths.clear()
        self.__apply_total = 0
        self.__summary = {}
        self.tblPlanResults.setSortingEnabled(False)
        self.tblPlanResults.clearContents()
        self.tblPlanResults.setRowCount(0)
        self.pteResult.clear()
        self._refresh_conflict_indicator()
        self._update_control_state()

    # 本次真正要写入的节点：未勾选「覆盖冲突节点」时跳过已有其它 Override 的节点
    def _plans_to_apply(self) -> list:
        overwrite_conflicts = self.cbxOverwriteConflicts.isChecked()
        return [
            plan for plan in self.__table_plans
            if overwrite_conflicts or not plan.conflict
        ]

    def _name_plans_to_apply(self) -> list:
        overwrite_conflicts = self.cbxNameOverwriteConflicts.isChecked()
        return [
            plan for plan in self.__name_plans
            if overwrite_conflicts or not plan.conflict
        ]

    def _update_control_state(self):
        is_processing = bool(self.__processing_stage)
        has_plans = bool(self.__table_plans)
        self.cbbDefaultConversion.setEnabled(not is_processing)
        self.cbxUseShort.setEnabled(not is_processing)
        self.cbxUseLong.setEnabled(not is_processing)
        self._sync_threshold_enabled()
        self.cbxOverwriteConflicts.setEnabled(not is_processing)
        self.cbxNameOverwriteConflicts.setEnabled(not is_processing)
        self.btnAnalyze.setEnabled(not is_processing)
        self.tblPlanResults.setEnabled(not is_processing and has_plans)
        # 分析出的 Override 节点必须整体应用（去掉上层会让下层继承关系错乱），因此不做部分勾选
        pending_plans = self._plans_to_apply()
        self.btnApply.setEnabled(not is_processing and bool(pending_plans))
        self.btnApply.setToolTip("" if is_processing or pending_plans else self._NO_PLAN_TOOLTIP)
        self.btnNameAnalyze.setEnabled(not is_processing)
        name_pending_plans = self._name_plans_to_apply()
        self.btnNameApply.setEnabled(not is_processing and bool(name_pending_plans))
        self.btnNameApply.setToolTip(
            "" if is_processing or name_pending_plans else self._NO_PLAN_TOOLTIP
        )

    def start_analysis(self):
        self._clear_analysis_results()
        default_conversion = self._selected_conversion(self.cbbDefaultConversion)
        if default_conversion is None:
            QMessageBox.warning(self, "自动转码设置", "请在工程中选择默认档使用的 Conversion 对象。")
            return
        short_threshold = self.spbShortThreshold.value()
        long_threshold = self.spbLongThreshold.value()
        use_short, use_long = self._detection_flags()
        if not use_short and not use_long:
            QMessageBox.warning(
                self, "自动转码设置", "请至少启用「短音效阈值」或「长音效阈值」中的一项。"
            )
            return
        if use_short and use_long and short_threshold >= long_threshold:
            QMessageBox.warning(self, "自动转码设置", "短音效阈值必须小于长音效阈值。")
            return
        # 每次分析都临时取主窗口当前对象，保证与表格同步
        table_objects = self._collect_scan_targets()
        if table_objects is None:
            return
        if batch_processor.is_busy():
            QMessageBox.warning(self, "自动转码设置", batch_processor.busy_message("分析"))
            return

        self.save_user_settings()
        # 长/短档 Conversion 按后缀查找，缺失时从默认档复制生成
        self.__conversions_by_category, self.__created_categories = (
            compression_utils.ensure_category_conversions(
                default_conversion, compression_utils.enabled_categories(use_short, use_long)
            )
        )
        self.__targets.clear()
        self.__target_type_counts = {"ActorMixer": 0, "Container": 0}
        self.__audio_sources.clear()
        self.__duration_by_source_id.clear()
        self.__plans.clear()
        self.__override_plans.clear()
        self.__conflict_plans.clear()
        self.__table_plans.clear()
        self.__plans_by_target_id.clear()
        self.__override_states.clear()
        self.__plan_batches.clear()
        self.__failed_paths.clear()
        self.__apply_total = 0
        self._refresh_conflict_indicator()
        self.__enumerate_mode = "duration"
        self.__processing_stage = "analyze"
        self._update_control_state()
        self.pteResult.setPlainText("正在枚举表格对象下的 ActorMixer、Container 与 AudioFileSource…")
        started = batch_processor.create_async(
            table_objects,
            self._enumerate_root_object,
            "自动转码设置：枚举对象",
            "name",
            on_finished=self._on_enumerate_finished,
            on_interrupted=self._on_scan_interrupted,
            progress_text_func=lambda _index, obj: obj.name,
        )
        if not started:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(self, "自动转码设置", batch_processor.busy_message("分析"))

    def _enumerate_root_object(self, _index: int, root: WwiseObject) -> bool:
        targets, audio_sources = compression_utils.discover_targets_and_sources(
            root, include_sources=self.__enumerate_mode != "name"
        )
        for obj in targets:
            if obj.id in self.__targets:
                continue
            # 主窗口里未勾选「选中」列的对象：它和它下面的整棵子树都不参与分析
            if compression_utils.is_excluded_by_rows(obj.path, self.__row_checked_by_path):
                continue
            self.__targets[obj.id] = obj
            object_type = (obj.wwise_dict or {}).get("type", "")
            if object_type == WwiseObjectType.ActorMixer.value:
                self.__target_type_counts["ActorMixer"] += 1
            else:
                self.__target_type_counts["Container"] += 1
        for obj in audio_sources:
            if compression_utils.is_excluded_by_rows(obj.path, self.__row_checked_by_path):
                continue
            self.__audio_sources[obj.id] = obj
        return True

    # 枚举完成后按「查询分页大小」分页读取播放时长：每页一次批量查询，进度条每页步进一次
    def _on_enumerate_finished(self):
        if not self.__targets:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(self, "自动转码设置", "表格对象下没有找到 ActorMixer。")
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
            "自动转码设置：读取播放时长",
            on_finished=self._start_override_state_read,
            on_interrupted=self._on_scan_interrupted,
            progress_text_func=lambda _index, page: f"{len(page)} 个音频源",
        )
        if not started:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(
                self, "自动转码设置", batch_processor.busy_message("读取播放时长")
            )

    def _read_duration_page(self, _index: int, page: list) -> bool:
        self.__duration_by_source_id.update(compression_utils.read_page_source_durations(page))
        return True

    # 时长读完后按「查询分页大小」分页读取目标节点现有的 OverrideConversion / Conversion，
    # 供冲突判定使用（每页一次批量查询，进度条每页步进一次）
    def _start_override_state_read(self):
        pages = list(waapi_utils.iter_object_pages(list(self.__targets.values())))
        if not pages:
            self._on_scan_finished()
            return
        self.pteResult.setPlainText(
            f"已枚举 {len(self.__targets)} 个目标节点，正在分页读取现有 Conversion…"
        )
        started = batch_processor.create_async(
            pages,
            self._read_override_state_page,
            "自动转码设置：读取现有 Conversion",
            on_finished=self._on_scan_finished,
            on_interrupted=self._on_scan_interrupted,
            progress_text_func=lambda _index, page: f"{len(page)} 个节点",
        )
        if not started:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(
                self, "自动转码设置", batch_processor.busy_message("读取现有 Conversion")
            )

    def _read_override_state_page(self, _index: int, page: list) -> bool:
        self.__override_states.update(compression_utils.read_page_override_states(page))
        return True

    def _on_scan_finished(self):
        if not self.__targets:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(self, "自动转码设置", "表格对象下没有找到 ActorMixer。")
            return

        use_short, use_long = self._detection_flags()
        self.__plans, self.__summary = compression_utils.build_conversion_plans(
            list(self.__targets.values()),
            list(self.__audio_sources.values()),
            self.__duration_by_source_id,
            self.spbShortThreshold.value(),
            self.spbLongThreshold.value(),
            self.__conversions_by_category,
            use_short=use_short,
            use_long=use_long,
        )
        if not self.__summary["valid_duration_count"]:
            self.__processing_stage = ""
            self._update_control_state()
            self.pteResult.setPlainText("未读取到有效的 AudioFileSource 播放时长。")
            QMessageBox.warning(self, "自动转码设置", "没有读取到有效的 AudioFileSource 播放时长，未修改 Conversion。")
            return

        self.__override_plans = [plan for plan in self.__plans if plan.override_enabled]
        self.__conflict_plans = compression_utils.mark_conversion_conflicts(
            self.__plans, self.__override_states, self.__conversions_by_category
        )
        # 表格列出需要 Override 的节点，以及已有其它 Override、会被方案改写的节点
        self.__table_plans = [
            plan for plan in self.__plans if plan.override_enabled or plan.conflict
        ]
        self.__plans_by_target_id = {
            plan.target.id: plan for plan in self.__table_plans
        }
        self._refresh_conflict_indicator()
        self._render_plan_results()
        self._render_conversion_settings()
        self.pteResult.setPlainText(self._analysis_text())
        self.__processing_stage = ""
        self._update_control_state()
        if not self.__table_plans:
            QMessageBox.information(self, "自动转码设置", "分析完成，没有需要设置 OverrideConversion 的节点。")
        elif self.__conflict_plans:
            QMessageBox.information(
                self, "自动转码设置",
                f"分析完成，其中 {len(self.__conflict_plans)} 个节点已有其它 Override"
                "（表格名称列标红，鼠标悬停可看差异）。",
            )

    # 占优阈值显示成 60:40 形式（取自本次分析使用的比例）
    def _dominance_text(self) -> str:
        ratio = self.__summary.get("dominance_ratio") or compression_utils.DEFAULT_DOMINANCE_RATIO
        majority = int(round(ratio * 100))
        return f"{majority}:{100 - majority}"

    # 分析结果文字：只列出本次启用档位的样本数（关掉的档位不显示，样本都算在默认档里）
    def _analysis_text(self) -> str:
        summary = self.__summary
        counts = []
        if summary.get("use_short"):
            counts.append(f"短 {summary['short_count']}")
        counts.append(f"中 {summary['medium_count']}")
        if summary.get("use_long"):
            counts.append(f"长 {summary['long_count']}")
        return (
            f"共包含音频文件：{len(self.__audio_sources)} 个（{'，'.join(counts)}，"
            f"分析节点：{len(self.__plans)} 个（ActorMixer {self.__target_type_counts['ActorMixer']}，"
            f"Container {self.__target_type_counts['Container']}）；需要 Override 的节点 {len(self.__override_plans)} 个。"
        )

    # 某档使用的 Conversion 名称（缺失时显示占位文本）
    def __conversion_name(self, category: str) -> str:
        conversion = self.__conversions_by_category.get(category)
        return conversion.name if conversion else "（未生成）"

    def _render_plan_results(self):
        # 未启用的档位不参与判定，对应列直接隐藏
        use_short, use_long = self._detection_flags()
        self.tblPlanResults.setColumnHidden(COL_SHORT_COUNT, not use_short)
        self.tblPlanResults.setColumnHidden(COL_LONG_COUNT, not use_long)
        self.tblPlanResults.setSortingEnabled(False)
        self.tblPlanResults.setRowCount(len(self.__table_plans))
        for row, plan in enumerate(self.__table_plans):
            name_item = QTableWidgetItem(plan.target.name)
            name_item.setData(Qt.ItemDataRole.UserRole, plan.target.id)
            # 已有其它 Override 的节点：名称列标红，鼠标悬停看到具体差异
            if plan.conflict:
                name_item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Danger)
                name_item.setToolTip(self._conflict_tooltip(plan))
            self.tblPlanResults.setItem(row, COL_NAME, name_item)
            self.tblPlanResults.setItem(row, COL_TYPE, QTableWidgetItem(plan.target.type.name))
            path_item = QTableWidgetItem(WwiseTableRowData.get_path_text(plan.target.path))
            path_item.setData(Qt.ItemDataRole.UserRole, plan.target.path or "")
            self.tblPlanResults.setItem(row, COL_PATH, path_item)
            severity_by_column = self._count_severities(plan)
            for column, category in (
                (COL_SHORT_COUNT, compression_utils.SHORT_CATEGORY),
                (COL_MEDIUM_COUNT, compression_utils.MEDIUM_CATEGORY),
                (COL_LONG_COUNT, compression_utils.LONG_CATEGORY),
            ):
                count_item = QTableWidgetItem()
                count_item.setData(
                    Qt.ItemDataRole.DisplayRole, plan.counts_by_category.get(category, 0)
                )
                severity = severity_by_column.get(column)
                if severity is not None:
                    count_item.setData(Qt.ItemDataRole.BackgroundRole, severity)
                self.tblPlanResults.setItem(row, column, count_item)
        self.tblPlanResults.setSortingEnabled(True)
        # 列宽按内容自动（不撑宽窗口），剩余宽度给「路径」列，避免右侧留白
        auto_adjust_window_width(
            self.tblPlanResults, self, resize_columns=True, resize_window=False
        )
        self.tblPlanResults.horizontalHeader().setSectionResizeMode(
            COL_PATH, QHeaderView.ResizeMode.Stretch
        )

    # 冲突节点的差异说明：现有 Conversion 是什么、应用后会变成什么
    @staticmethod
    def _conflict_tooltip(plan: compression_utils.ConversionAssignmentPlan) -> str:
        existing = plan.existing_conversion_name or "（未知）"
        if plan.override_enabled:
            return f"已有其它 Override：{existing}，不在本次方案内；应用后改为 {plan.conversion.name}"
        return f"已有其它 Override：{existing}，但方案判定该节点应继承上层；应用后清除 Override"

    # 三列「音效数」的标色：命中档位标绿；最底层节点里夹着另一种极端时长时，把那一列标黄提醒
    def _count_severities(self, plan: compression_utils.ConversionAssignmentPlan) -> dict:
        severities = {}
        active_column = CATEGORY_COLUMNS.get(plan.effective_category)
        if active_column is not None:
            severities[active_column] = CellSeverity.Success
        if plan.has_child_target:
            return severities
        counts = plan.counts_by_category
        short_count = counts.get(compression_utils.SHORT_CATEGORY, 0)
        long_count = counts.get(compression_utils.LONG_CATEGORY, 0)
        if plan.effective_category == compression_utils.SHORT_CATEGORY and long_count:
            severities[COL_LONG_COUNT] = CellSeverity.Warning
        elif plan.effective_category == compression_utils.LONG_CATEGORY and short_count:
            severities[COL_SHORT_COUNT] = CellSeverity.Warning
        elif plan.effective_category == compression_utils.MEDIUM_CATEGORY:
            # 中档命中时，两头的极端时长都不该出现，非 0 就提醒
            if short_count:
                severities[COL_SHORT_COUNT] = CellSeverity.Warning
            if long_count:
                severities[COL_LONG_COUNT] = CellSeverity.Warning
        return severities

    # 某一行对应的待应用方案（按对象 id 反查，排序后依然有效）
    def _plan_at_row(self, row: int) -> compression_utils.ConversionAssignmentPlan:
        item = self.tblPlanResults.item(row, COL_NAME)
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
        if index.column() in COUNT_COLUMNS:
            menu.addAction('详情', lambda: self.show_plan_details(plan))
        add_common_object_actions(menu, plan.target, self)
        menu.exec(self.tblPlanResults.viewport().mapToGlobal(position))

    # 右键「详情」：列出该节点包含的每个音频文件的时长与分档判定
    def show_plan_details(self, plan: compression_utils.ConversionAssignmentPlan):
        short_threshold = self.__summary.get("short_threshold", self.spbShortThreshold.value())
        long_threshold = self.__summary.get("long_threshold", self.spbLongThreshold.value())
        rows = compression_utils.describe_target_sources(
            plan.target, list(self.__audio_sources.values()), self.__duration_by_source_id,
            short_threshold, long_threshold,
            use_short=self.__summary.get("use_short", True),
            use_long=self.__summary.get("use_long", True),
        )
        entries = [
            {
                "source": source,
                "duration": duration,
                "category_text": CATEGORY_DISPLAY.get(category, CATEGORY_DISPLAY[None]),
            }
            for source, duration, category in rows
        ]
        AutoCompressionDetailWindow(entries, f"音效详情 - {plan.target.name}", self).exec()

    # 复制对象的完整路径（表格里显示的是缩写形式）
    @staticmethod
    def copy_object_path(node: WwiseObject):
        clipboard.copy(node.path)
        Logger().info(f"已复制到剪贴板：{node.path}")

    def apply_plans(self):
        plans = self._plans_to_apply()
        if not plans:
            QMessageBox.information(
                self, "自动转码设置",
                "没有需要应用的节点：请先分析，或勾选「覆盖已有其它 Conversion 的节点」。",
            )
            return
        if batch_processor.is_busy():
            QMessageBox.warning(
                self, "自动转码设置", batch_processor.busy_message("应用 Conversion")
            )
            return

        page_size = max(1, user_config.get_tool_page_size())
        self.__plan_batches = [
            plans[index:index + page_size]
            for index in range(0, len(plans), page_size)
        ]
        self.__apply_total = len(plans)
        self.__failed_paths.clear()
        self.__processing_stage = "apply"
        self._update_control_state()
        started = batch_processor.create_async(
            self.__plan_batches,
            self._apply_plan_batch,
            "自动转码设置：应用 Conversion",
            on_finished=self._on_apply_finished,
            on_interrupted=self._on_apply_interrupted,
            progress_text_func=lambda _index, plans: f"{len(plans)} 个目标对象",
            undo_group="自动转码设置",
        )
        if not started:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(
                self, "自动转码设置", batch_processor.busy_message("应用 Conversion")
            )

    def _apply_plan_batch(self, _index: int, plans: list[compression_utils.ConversionAssignmentPlan]) -> bool:
        self.__failed_paths.extend(compression_utils.apply_conversion_plans(plans))
        return True

    def _on_apply_finished(self):
        self.__processing_stage = ""
        self._update_control_state()
        failed_count = len(set(self.__failed_paths))
        applied_count = self.__apply_total - failed_count
        skipped_count = len(self.__table_plans) - self.__apply_total
        result = f"已应用节点：{self.__apply_total} 个（成功 {applied_count}，失败 {failed_count}"
        result += f"，跳过冲突节点 {skipped_count} 个）。" if skipped_count else "）。"
        self.pteResult.setPlainText(result)
        Logger().info(result)
        if failed_count:
            QMessageBox.warning(
                self,
                "自动转码设置",
                f"{failed_count} 个目标对象设置失败，详情见日志。",
            )

    def _on_scan_interrupted(self):
        self.__processing_stage = ""
        self._update_control_state()
        QMessageBox.warning(self, "自动转码设置", "对象扫描被中断，未修改 Conversion。")

    def _on_apply_interrupted(self):
        self.__processing_stage = ""
        self._update_control_state()
        QMessageBox.warning(self, "自动转码设置", "Conversion 应用被中断，部分 ActorMixer 可能已修改。")

    # region 按名称模式
    # 读取映射表并解析成 (关键词, WwiseObject)；配置有问题时弹窗并返回 None
    def _read_name_mapping(self) -> list:
        rows = self.nameMap.rows()
        if not rows:
            QMessageBox.warning(self, "自动转码设置", "请先配置「关键词 → Conversion」映射。")
            return None
        by_name = {
            obj.name: obj
            for obj in waapi_utils.find_all_objects_by_type(WwiseObjectType.Conversion)
        }
        mapping = []
        for keyword, conversion_name in rows:
            if not keyword:
                QMessageBox.warning(self, "自动转码设置", "关键词不能为空。")
                return None
            conversion = by_name.get(conversion_name)
            if conversion is None:
                QMessageBox.warning(self, "自动转码设置", f"找不到 Conversion 对象：{conversion_name}")
                return None
            mapping.append((keyword, conversion))
        return mapping

    # 名称模式分析：枚举表格对象下的节点，按名称是否包含关键词来匹配
    def start_name_analysis(self):
        mapping = self._read_name_mapping()
        if mapping is None:
            return
        table_objects = self._collect_scan_targets()
        if table_objects is None:
            return
        if batch_processor.is_busy():
            QMessageBox.warning(self, "自动转码设置", batch_processor.busy_message("分析"))
            return

        self.__name_mapping = mapping
        self.__name_plans.clear()
        self.__name_plan_batches.clear()
        self.__name_failed_paths.clear()
        self.__targets.clear()
        self.__override_states.clear()
        self.__name_apply_total = 0
        self._refresh_conflict_indicator()
        self.__enumerate_mode = "name"
        self.__processing_stage = "name-analyze"
        self._update_control_state()
        self.lblNameStatus.setText("正在枚举对象…")
        started = batch_processor.create_async(
            table_objects,
            self._enumerate_root_object,
            "自动转码设置：枚举对象",
            "name",
            on_finished=self._on_name_enumerate_finished,
            on_interrupted=self._on_name_interrupted,
            progress_text_func=lambda _index, obj: obj.name,
        )
        if not started:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(self, "自动转码设置", batch_processor.busy_message("分析"))

    def _on_name_enumerate_finished(self):
        if not self.__targets:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(self, "自动转码设置", "表格对象下没有找到可配置的节点。")
            return
        pages = list(waapi_utils.iter_object_pages(list(self.__targets.values())))
        if not pages:
            self._on_name_state_finished()
            return
        self.lblNameStatus.setText(
            f"已枚举 {len(self.__targets)} 个节点，正在分页读取现有 Conversion…"
        )
        started = batch_processor.create_async(
            pages,
            self._read_override_state_page,
            "自动转码设置：读取现有 Conversion",
            on_finished=self._on_name_state_finished,
            on_interrupted=self._on_name_interrupted,
            progress_text_func=lambda _index, page: f"{len(page)} 个节点",
        )
        if not started:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(
                self, "自动转码设置", batch_processor.busy_message("读取现有 Conversion")
            )

    def _on_name_state_finished(self):
        self.__processing_stage = ""
        self.__name_plans = compression_utils.build_name_conversion_plans(
            list(self.__targets.values()), self.__name_mapping
        )
        compression_utils.mark_conversion_conflicts(self.__name_plans, self.__override_states)
        self._render_name_plan_results()
        self._refresh_conflict_indicator()
        self._update_control_state()

    def _render_name_plan_results(self):
        table = self.tblNamePlanResults
        table.setSortingEnabled(False)
        table.setRowCount(len(self.__name_plans))
        for row, plan in enumerate(self.__name_plans):
            name_item = QTableWidgetItem(plan.target.name)
            name_item.setData(Qt.ItemDataRole.UserRole, plan.target.id)
            table.setItem(row, COL_NAME_PLAN_NAME, name_item)
            table.setItem(row, COL_NAME_PLAN_TYPE, QTableWidgetItem(plan.target.type.name))
            path_item = QTableWidgetItem(WwiseTableRowData.get_path_text(plan.target.path))
            path_item.setData(Qt.ItemDataRole.UserRole, plan.target.id)
            table.setItem(row, COL_NAME_PLAN_PATH, path_item)
            table.setItem(row, COL_NAME_PLAN_KEYWORD, QTableWidgetItem(plan.keyword))
            conversion_item = QTableWidgetItem(plan.conversion.name)
            # 现有 Conversion 与映射表不一致的节点：Conversion 列标红，悬停看差异
            if plan.conflict:
                conversion_item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Danger)
                conversion_item.setToolTip(
                    f"已有其它 Override：{plan.existing_conversion_name or '（未知）'}；"
                    f"应用后改为 {plan.conversion.name}"
                )
            table.setItem(row, COL_NAME_PLAN_CONVERSION, conversion_item)
        table.setSortingEnabled(True)
        # 列宽按内容自动（不撑宽窗口），剩余宽度给「路径」列
        auto_adjust_window_width(table, self, resize_columns=True, resize_window=False)
        table.horizontalHeader().setSectionResizeMode(
            COL_NAME_PLAN_PATH, QHeaderView.ResizeMode.Stretch
        )
        self.lblNameStatus.setText(
            f"匹配到 {len(self.__name_plans)} 个节点。"
            if self.__name_plans else "没有节点名包含配置的关键词。"
        )

    def _name_plan_at_row(self, row: int):
        item = self.tblNamePlanResults.item(row, COL_NAME_PLAN_NAME)
        if item is None:
            return None
        target_id = item.data(Qt.ItemDataRole.UserRole)
        return next((plan for plan in self.__name_plans if plan.target.id == target_id), None)

    def _name_targets_at_row(self, row: int) -> list:
        plan = self._name_plan_at_row(row)
        return [plan.target] if plan is not None else []

    # 名称模式结果表的右键菜单：复制路径 + 通用对象动作
    def show_name_context_menu(self, position):
        index = self.tblNamePlanResults.indexAt(position)
        if not index.isValid():
            return
        plan = self._name_plan_at_row(index.row())
        if plan is None:
            return
        menu = QMenu(self)
        if index.column() == COL_NAME_PLAN_PATH:
            menu.addAction('复制', lambda: self.copy_object_path(plan.target))
        add_common_object_actions(menu, plan.target, self)
        menu.exec(self.tblNamePlanResults.viewport().mapToGlobal(position))

    def apply_name_plans(self):
        plans = self._name_plans_to_apply()
        if not plans:
            QMessageBox.information(
                self, "自动转码设置",
                "没有需要应用的节点：请先分析，或勾选「覆盖已有其它 Conversion 的节点」。",
            )
            return
        if batch_processor.is_busy():
            QMessageBox.warning(
                self, "自动转码设置", batch_processor.busy_message("应用 Conversion")
            )
            return

        page_size = max(1, user_config.get_tool_page_size())
        self.__name_plan_batches = [
            plans[index:index + page_size]
            for index in range(0, len(plans), page_size)
        ]
        self.__name_apply_total = len(plans)
        self.__name_failed_paths.clear()
        self.__processing_stage = "name-apply"
        self._update_control_state()
        started = batch_processor.create_async(
            self.__name_plan_batches,
            self._apply_name_plan_batch,
            "自动转码设置：按名称应用 Conversion",
            on_finished=self._on_name_apply_finished,
            on_interrupted=self._on_name_interrupted,
            progress_text_func=lambda _index, plans_batch: f"{len(plans_batch)} 个节点",
            undo_group="自动转码设置",
        )
        if not started:
            self.__processing_stage = ""
            self._update_control_state()
            QMessageBox.warning(
                self, "自动转码设置", batch_processor.busy_message("应用 Conversion")
            )

    def _apply_name_plan_batch(self, _index: int, plans: list) -> bool:
        self.__name_failed_paths.extend(compression_utils.apply_name_conversion_plans(plans))
        return True

    def _on_name_apply_finished(self):
        self.__processing_stage = ""
        self._update_control_state()
        failed_count = len(set(self.__name_failed_paths))
        applied_count = self.__name_apply_total - failed_count
        skipped_count = len(self.__name_plans) - self.__name_apply_total
        text = f"已应用节点：{self.__name_apply_total} 个（成功 {applied_count}，失败 {failed_count}"
        text += f"，跳过冲突节点 {skipped_count} 个）。" if skipped_count else "）。"
        self.lblNameStatus.setText(text)
        Logger().info(text)
        if failed_count:
            QMessageBox.warning(
                self, "自动转码设置", f"{failed_count} 个目标对象设置失败，详情见日志。"
            )

    def _on_name_interrupted(self):
        self.__processing_stage = ""
        self._update_control_state()
        QMessageBox.warning(self, "自动转码设置", "名称模式任务被中断，部分对象可能已修改。")

    def closeEvent(self, event):
        if self.__processing_stage:
            event.ignore()
            return
        self.save_user_settings()
        super().closeEvent(event)
