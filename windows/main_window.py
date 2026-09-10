from collections.abc import Callable
import threading

import clipboard
import webbrowser

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QTextCursor
from qt_material import build_stylesheet

import globals.global_variables as gv
from data import project_conventions
from data.action_help import ACTION_HELP
from globals.version import get_software_version
from globals.constants import DOCUMENTATION_URL
from libraries.multi_thread import batch_processor
from libraries.table_view.table_item_model import INCLUSION_COL
from libraries.utils.log_utils import Logger, set_log_theme
from libraries.waapi_client import WAAPIClient
from libraries.wwise_object import WwiseObject, WwiseObjectType
from table.wwise_object_table_gui import WwiseTableImpl
from table.wwise_object_table import WwiseTableDisplayMode
from table.wwise_table_headers import CHECK_BOX_COL, COMMON_HEADERS, ENABLE_COL, TABLE_DISPLAY_MODE_LABELS, PATH_COL
from windows.audio_silence_trim_window import AudioSilenceTrimWindow as AudioSilenceTrimWindow
from windows.advanced_filter_window import AdvancedFilterWindow as AdvancedFilterWindow
from windows.advanced_find_window import AdvancedFindWindow as AdvancedFindWindow
from windows.sync_trim_window import SyncTrimWindow as SyncTrimWindow
from windows.table_rename_window import TableRenamer as TableRenamer
from windows.template_replace_window import TemplateReplacer as TemplateReplacer
from windows.bank_assignment_window import BankAssignmentMatrix as BankAssignmentMatrix
from windows.project_validation_window import ProjectValidation as ProjectValidation
from windows.work_unit_import_window import WorkUnitImporter as WorkUnitImporter
from windows.project_settings_window import ProjectSettingsWindow as ProjectSettingsWindow
from windows.media_size_window import MediaSizeWindow as MediaSizeWindow
from windows.property_query_window import PropertyQueryWindow as PropertyQueryWindow
from waapi import CannotConnectToWaapiException
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QMenu, QTableWidgetItem
from ui.MainWindow_ui import Ui_MainWindow
from windows.export_object_list_window import ExportObjectListWindow as ExportObjectListWindow
from libraries.utils.wwise import common_utils, audio_source_utils, game_sync_utils, soundbank_utils, \
    localization_utils, project_utils, event_utils, container_utils, migration_utils, waapi_utils, mixing_utils
from libraries.utils import ai_utils, io_utils, path_utils, user_config


# AI 模型列表后台拉取线程：避免启动时在界面线程发 HTTP 请求
class AiModelListWorker(QThread):
    models_loaded = Signal(list)

    def __init__(self, connection: dict, api_key: str, parent=None):
        super().__init__(parent)
        self._connection = connection
        self._api_key = api_key

    def run(self):
        try:
            models = ai_utils.list_models(self._connection, self._api_key)
        except Exception:
            models = []
        self.models_loaded.emit(models)


# AI 对话工作线程：在后台请求 AI 代理并执行模型请求的工具调用，避免阻塞界面
class AiChatWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(str)
    failed_signal = Signal(str)
    stopped_signal = Signal(str)
    # 参数一：仍有效的对象列表；参数二：发送时可见对象的原始 id 列表
    objects_refreshed_signal = Signal(list, list)

    def __init__(self, prompt: str, objects: list, parent=None):
        super().__init__(parent)
        self._prompt = prompt
        self._objects = objects
        self._stop_event = threading.Event()

    def stop_requested(self):
        # 请求中止：agent loop 会在每轮/每次网络请求等待期间响应
        self._stop_event.set()

    def run(self):
        try:
            from libraries.ai_assistant import AIAgentStopped, run_assistant

            result = run_assistant(
                self._prompt,
                self._objects,
                on_log=self.log_signal.emit,
                should_stop=self._stop_event.is_set,
            )
            if result.mutated:
                refreshed = self._resolve_objects_after_ai()
                self.objects_refreshed_signal.emit(refreshed, [obj.id for obj in self._objects])
            self.finished_signal.emit(result.content)
        except AIAgentStopped:
            self.stopped_signal.emit("已按用户要求中止 AI 处理")
        except Exception as e:
            self.failed_signal.emit(str(e))

    # AI 修改过对象后，逐个重新解析可见对象的最新状态
    def _resolve_objects_after_ai(self):
        refreshed = []
        for obj in self._objects:
            updated = waapi_utils.get_full_info_from_obj_id(obj.id)
            if not updated.is_valid:
                # 原 id 已失效（删除或类型转换等），尝试按原路径找回
                updated = waapi_utils.find_object_by_path(obj.path)
            if updated and updated.is_valid:
                refreshed.append(updated)
        return refreshed


class MainWindow(QMainWindow, Ui_MainWindow):
    # 主窗口：对象列表以 globals.active_objects 为源，表格由 WwiseTableImpl 驱动

    # 兼容子窗口对 main_window.activeObjects 的读写（与 gv.active_objects 同步）
    @property
    def activeObjects(self):
        return gv.active_objects

    @activeObjects.setter
    def activeObjects(self, value):
        gv.active_objects = list(value) if value is not None else []

    # 初始化主窗口、表格与对象列表历史栈
    def __init__(self, style_sheet):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle(f"WAAPI 工具集 {get_software_version()}")
        self.style_sheet = style_sheet
        self.table = WwiseTableImpl(self.tblWwiseObjects)
        self._object_history: list[tuple] = []
        self._history_index: int = -1
        self._restoring_history: bool = False
        self.__eventFilterBase = None
        self.__languageFilterBase = None
        self._full_mode_origin: list[WwiseObject] | None = None
        self._full_mode_entry_ids: tuple | None = None
        self._ai_worker = None
        self._ai_model_worker = None
        # 恢复上次保存的高级筛选复选框设置，使视图筛选在启动后立即生效
        advanced_settings = user_config.get_advanced_filter_settings()
        self.cbxCaseSensitive.setChecked(advanced_settings["case_sensitive"])
        self.cbxOnlyIncludedEnabled.setChecked(advanced_settings["only_included"])
        # 恢复高级查找设置（递归查找 / 保留原始层级）
        advanced_find_settings = user_config.get_advanced_find_settings()
        self.cbxRecursiveFind.setChecked(advanced_find_settings["recursive_find"])
        self.cbxKeepSelf.setChecked(advanced_find_settings["keep_self"])
        # 恢复「按属性」下拉框上次选择
        main_window_settings = user_config.get_window_settings('main_window')
        saved_property = main_window_settings.get('find_property')
        if saved_property:
            index = self.cbbFindProperty.findText(saved_property)
            if index >= 0:
                self.cbbFindProperty.setCurrentIndex(index)
        self.setup_triggers()
        self._setup_action_help()
        self._setup_ai_assistant()
        self.check_wwise_connection()
        self.update_convention_action_states()
        self._update_history_buttons()

    # 给菜单项写入使用说明：悬停显示气泡（tooltip），同时状态栏显示（statusTip）
    def _setup_action_help(self):
        for menu in self.menubar.findChildren(QMenu):
            menu.setToolTipsVisible(True)
        for menu in self.menubar.findChildren(QMenu):
            for action in menu.actions():
                if action.isSeparator():
                    continue
                text = ACTION_HELP.get(action.objectName())
                if not text:
                    continue
                action.setToolTip(text)
                action.setStatusTip(" ".join(text.split()))

    # 绑定底部 AI 助手输入栏的信号槽
    def _setup_ai_assistant(self):
        # 状态圆点：初始为未确认（红），模型列表拉取成功后转绿
        self._set_ai_proxy_dot(False)
        self.cbbAiModel.clear()
        saved_model = user_config.get_ai_model()
        if saved_model:
            self.cbbAiModel.addItem(saved_model)
            self.cbbAiModel.setCurrentText(saved_model)
        # 后台拉取代理支持的模型列表（失败时仍可手动输入）
        connection = ai_utils.resolve_connection(
            user_config.get_ai_mode(),
            user_config.get_ai_proxy_url(),
            user_config.get_ai_provider(),
            user_config.get_ai_base_url(),
        )
        self._ai_model_worker = AiModelListWorker(
            connection, user_config.get_ai_api_key(), self
        )
        self._ai_model_worker.models_loaded.connect(self._on_ai_models_loaded)
        self._ai_model_worker.start()

    # 把下拉框中当前模型写回 user_config.json（下次启动沿用）
    def _persist_ai_model(self):
        model = self.cbbAiModel.currentText().strip()
        if model and model != user_config.get_ai_model():
            user_config.save_ai_model(model)

    # AI 助手 label 右侧的连接状态圆点：绿=代理可达，红=未连接/拉取失败
    def _set_ai_proxy_dot(self, connected: bool):
        color = "#2ECC71" if connected else "#E74C3C"
        self.lblAiModelStatus.setToolTip(
            "AI 代理服务器已连接" if connected else "未连接到 AI 代理服务器"
        )
        self.lblAiModelStatus.setStyleSheet(
            f"background-color: {color}; border-radius: 6px;"
        )

    # 模型列表就绪后填充下拉框并尽量保持上次选择
    def _on_ai_models_loaded(self, models: list):
        if not models:
            self._set_ai_proxy_dot(False)
            Logger().warning("无法从 AI 代理获取模型列表，请直接在模型下拉框中输入模型名")
            return
        self._set_ai_proxy_dot(True)
        saved_model = user_config.get_ai_model()
        self.cbbAiModel.blockSignals(True)
        self.cbbAiModel.clear()
        self.cbbAiModel.addItems(models)
        if saved_model and saved_model in models:
            self.cbbAiModel.setCurrentText(saved_model)
        elif saved_model:
            # 已保存的模型不在当前列表，保留该值供手动重选
            self.cbbAiModel.addItem(saved_model)
            self.cbbAiModel.setCurrentText(saved_model)
        else:
            self.cbbAiModel.setCurrentIndex(0)
        self.cbbAiModel.blockSignals(False)
        Logger().info(
            f"AI 模型列表已加载（共 {len(models)} 个），当前：{self.cbbAiModel.currentText()}"
        )

    # 发送/处理期间禁用发送按钮，避免重复触发
    def _set_ai_busy(self, busy: bool):
        self.btnAiSend.setEnabled(not busy)
        self.btnAiStop.setEnabled(busy)
        self.ledAiPrompt.setPlaceholderText(
            "AI 正在处理中，请稍候…" if busy
            else "输入指令让 AI 处理表格中的对象，例如：把列表里所有 Sound 改为全小写命名（Enter 发送）"
        )

    # 点击「停止」：请求后台 agent loop 尽快中止
    def _on_ai_stop(self):
        if not self._ai_worker or not self._ai_worker.isRunning():
            return
        Logger().info("正在中止 AI 处理…")
        self._ai_worker.stop_requested()

    # 读取输入并启动后台 AI 对话线程
    def _on_ai_send(self):
        if self._ai_worker and self._ai_worker.isRunning():
            Logger().warning("AI 正在处理中，请等待当前任务完成")
            return
        prompt = self.ledAiPrompt.text().strip()
        if not prompt:
            return
        objects = self.get_visible_objects()
        if not objects:
            Logger().warning("表格中没有可处理的对象，请先在 Wwise 中选中对象或点击「获取Wwise选中对象」")
            return
        model = self.cbbAiModel.currentText().strip()
        if not model:
            Logger().warning("请先选择或输入 AI 模型（输入框左侧的下拉框）")
            return
        self._persist_ai_model()
        Logger().query(f"AI 指令：{prompt}（共 {len(objects)} 个对象）")
        self.ledAiPrompt.clear()
        self._set_ai_busy(True)
        worker = AiChatWorker(prompt, objects, self)
        worker.log_signal.connect(self._on_ai_log)
        worker.objects_refreshed_signal.connect(self._on_ai_objects_refreshed)
        worker.finished_signal.connect(self._on_ai_finished)
        worker.failed_signal.connect(self._on_ai_failed)
        worker.stopped_signal.connect(self._on_ai_stopped)
        self._ai_worker = worker
        worker.start()

    def _on_ai_log(self, text: str):
        Logger().info(f"[AI] {text}")

    def _on_ai_finished(self, content: str):
        self._set_ai_busy(False)
        self._set_ai_proxy_dot(True)
        if content:
            from libraries.ai_assistant import clean_display_content

            Logger().query(f"AI：{clean_display_content(content)}")

    def _on_ai_failed(self, error: str):
        self._set_ai_busy(False)
        self._set_ai_proxy_dot(False)
        Logger().error(f"AI 处理失败：{error}")

    def _on_ai_stopped(self, text: str):
        self._set_ai_busy(False)
        Logger().warning(text)

    # AI 修改过对象后重建 gv.active_objects 并刷新表格
    def _on_ai_objects_refreshed(self, refreshed_objects: list, processed_ids: list[str]):
        replacement = {obj.id: obj for obj in refreshed_objects}
        processed = set(processed_ids)
        rebuilt = []
        dropped = 0
        for obj in gv.active_objects:
            if obj.id in replacement:
                rebuilt.append(replacement[obj.id])
            elif obj.id not in processed:
                # 隐藏行未交给 AI 处理，保持原样
                rebuilt.append(obj)
            else:
                # 交给 AI 处理后已无法解析（被删除或类型转换），从列表移除
                dropped += 1
        gv.active_objects = rebuilt
        if dropped:
            Logger().info(f"AI 处理后有 {dropped} 个对象已不存在（被删除或转换），已从表格移除")
        else:
            Logger().info("AI 已修改对象，正在刷新表格…")
        self.show_obj_list()

    # 初始化表格视图模式下拉框（选项与列定义见 wwise_table_headers / WwiseTableDisplayMode）
    def _setup_table_display_mode_combo(self):
        self.cbbTableDisplayMode.clear()
        self.cbbTableDisplayMode.addItems(list(TABLE_DISPLAY_MODE_LABELS))
        self.cbbTableDisplayMode.blockSignals(True)
        self.cbbTableDisplayMode.setCurrentIndex(self.table.display_mode.value)
        self.cbbTableDisplayMode.blockSignals(False)
        self.cbbTableDisplayMode.currentIndexChanged.connect(self.on_table_display_mode_changed)

    # 类型下拉框的可选项：全部类型 + 动态取自 WwiseObjectType 的所有值（筛选与高级查找共用）
    def get_filter_type_options(self) -> list[str]:
        return ['全部类型'] + [member.value for member in sorted(WwiseObjectType, key=lambda item: item.value)]

    # 类型筛选下拉框：全部类型 + 动态取自 WwiseObjectType 的所有值
    def _setup_type_filter_combo(self):
        self.cbbFilterType.blockSignals(True)
        self.cbbFilterType.clear()
        self.cbbFilterType.addItems(self.get_filter_type_options())
        self.cbbFilterType.blockSignals(False)

    # 绑定「极速模式」开关：默认勾选，只加载基础属性与启用状态
    def _setup_turbo_mode_checkbox(self):
        self.table.light_mode = self.cbxTurboMode.isChecked()
        self.cbxTurboMode.toggled.connect(self._on_turbo_mode_toggled)

    # 打开工程规范设置窗口
    def open_project_settings_window(self):
        settings_window = ProjectSettingsWindow(
            on_ai_saved=self._reload_ai_model_from_settings,
            on_theme_applied=self.apply_app_theme,
        )
        settings_window.exec()
        self.update_convention_action_states()

    # 按工程规范开关刷新菜单项可用状态
    def update_convention_action_states(self):
        # 使用类型缩写依赖缩写规范；自动设置颜色依赖颜色规范；自动添加备注依赖互为备注开关
        self.actUseAcronym.setEnabled(project_conventions.is_acronym_enabled())
        self.actAutoSetColor.setEnabled(project_conventions.is_color_enabled())
        self.actAutoAddNotes.setEnabled(project_conventions.use_event_ref_notes())

    # 应用 qt_material 主题：重建样式表并立即刷新到整个应用
    def apply_app_theme(self, theme: str):
        set_log_theme(theme)
        stylesheet = build_stylesheet(theme=theme, template=path_utils.get_resource_path("material.css"))
        self.style_sheet = stylesheet
        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet)
        self.set_widget_style(self.lblWwiseConnection, self.lblWwiseConnection.property("class") or "warning")

    # 设置窗口保存 AI 模型后，同步主窗口下拉框为配置值
    def _reload_ai_model_from_settings(self):
        model = user_config.get_ai_model()
        if not model:
            return
        if self.cbbAiModel.findText(model) < 0:
            self.cbbAiModel.addItem(model)
        self.cbbAiModel.setCurrentText(model)

    # 打开帮助文档：链接统一维护在 user_config.json 的 Documentation，未配置时回退内置常量
    def open_help_documentation(self):
        url = (
            user_config.get_documentation_url()
            or DOCUMENTATION_URL
        )
        if not url:
            Logger().warning("未配置帮助文档链接，请在 user_config.json 的 Documentation 字段中填写")
            return
        webbrowser.open(url)

    # 极速模式勾选切换：勾选时快速查找完整列表；取消勾选进入完整模式，对当前可见对象读取全部属性
    def _on_turbo_mode_toggled(self, checked: bool):
        if self._restoring_history:
            return
        if checked:
            # 若完整模式下没有切换过对象列表，则恢复进入完整模式前的完整列表以便继续查找
            if (self._full_mode_entry_ids is not None
                    and self._object_id_sequence(gv.active_objects) == self._full_mode_entry_ids):
                gv.active_objects = self._full_mode_origin
            self._full_mode_origin = None
            self._full_mode_entry_ids = None
        else:
            self._full_mode_origin = self._clone_object_list(gv.active_objects)
            # 完整模式只针对查找后剩余的可见对象
            visible = self.get_visible_objects()
            self._full_mode_entry_ids = self._object_id_sequence(visible)
            gv.active_objects = visible
        self.table.light_mode = checked
        self.show_obj_list()

    @staticmethod
    def _object_id_sequence(objs: list) -> tuple:
        return tuple(obj.id for obj in objs)

    # 切换表格显示模式并重新应用筛选
    def on_table_display_mode_changed(self, index: int):
        if index < 0:
            return
        # 极速模式仅服务于通用视图：切到设计/集成视图时自动关闭极速模式
        if index != WwiseTableDisplayMode.General.value and self.cbxTurboMode.isChecked():
            self.cbxTurboMode.blockSignals(True)
            self.cbxTurboMode.setChecked(False)
            self.cbxTurboMode.blockSignals(False)
            self.table.light_mode = False
        self.table.set_display_mode(index)
        self.apply_table_filter()

    # 切换对象类型筛选时立即刷新表格（与「应用筛选」一致，并记入对象列表历史）
    def _on_filter_type_changed(self, index: int):
        if index < 0 or self._restoring_history:
            return
        self.apply_table_filter(record_history=True)

    # 点击「筛选」按钮后应用关键字筛选并记入历史
    def apply_keyword_filter(self):
        if self._restoring_history:
            return
        self.apply_table_filter(record_history=True)

    # 区分大小写变更时重新筛选并记入历史
    def _on_case_sensitive_changed(self, _checked: bool):
        if self._restoring_history:
            return
        self.apply_table_filter(record_history=True)

    # 「仅显示启用对象」变更时重新筛选并记入历史
    def _on_only_included_toggled(self, _checked: bool):
        if self._restoring_history:
            return
        self.apply_table_filter(record_history=True)

    # 「启用」列写入 Wwise 后，若正在按启用筛选则刷新行可见性
    def _on_wwise_inclusion_cell_changed(self, _row: int):
        if self.cbxOnlyIncludedEnabled.isChecked():
            self.apply_table_filter(record_history=False)

    # 绑定菜单、工具栏与按钮的信号槽
    def setup_triggers(self):
        self._setup_table_display_mode_combo()
        self._setup_type_filter_combo()
        self._setup_turbo_mode_checkbox()
        # 日志绑定
        Logger().set_log_window_stream(self.add_log)
        Logger().set_status_bar_stream(lambda text: self.statusbar.showMessage(text))
        # 所有按键
        self.actReconnectWwise.triggered.connect(self.check_wwise_connection)
        self.btnGetSelectedObjects.clicked.connect(self.get_selected_objects)
        self.btnSelectInWwise.clicked.connect(self.select_table_objects_in_wwise)
        self.btnClearTable.clicked.connect(self.clear_object_list)
        self.cbxTableSelectAll.toggled.connect(self.select_all_rows)
        self.btnMultiEditor.clicked.connect(self.open_in_multi_editor)
        self.btnBatchRename.clicked.connect(self.open_in_batch_rename)
        self.btnFindParent.clicked.connect(self.find_parent)
        self.btnFindChildren.clicked.connect(self.find_children)
        self.btnFindReferences.clicked.connect(self.find_references)
        self.btnAdvancedFind.clicked.connect(self.open_advanced_find_window)
        self.btnFindProperty.clicked.connect(self.find_by_property)
        self.cbbFindProperty.currentTextChanged.connect(self._on_find_property_changed)
        self.cbxCaseSensitive.toggled.connect(self._on_case_sensitive_changed)
        self.cbxOnlyIncludedEnabled.toggled.connect(self._on_only_included_toggled)
        self.cbbFilterType.currentIndexChanged.connect(self._on_filter_type_changed)
        self.btnApplyFilter.clicked.connect(self.apply_keyword_filter)
        self.btnAdvancedFilter.clicked.connect(self.open_advanced_filter_window)
        self.btnObjectHistoryBack.clicked.connect(self.object_history_back)
        self.btnObjectHistoryForward.clicked.connect(self.object_history_forward)
        # 文件菜单
        self.actImportObjectList.triggered.connect(self.import_object_list)
        self.actExportObjectList.triggered.connect(self.export_object_list)
        self.actProjectSettings.triggered.connect(self.open_project_settings_window)
        # 编辑菜单
        self.actUndo.triggered.connect(waapi_utils.undo)
        self.actRedo.triggered.connect(waapi_utils.redo)

        self.setup_batch_processor(self.actDeleteObjects, lambda index, obj: waapi_utils.delete_object(obj), expand=False)
        # 通用菜单（改变类型为仅表格类型列右键）
        self.setup_batch_processor(self.actCreateWorkUnit, lambda index, obj: common_utils.create_parent(obj, WwiseObjectType.WorkUnit), expand=False)
        self.setup_batch_processor(self.actCreateActorMixer, lambda index, obj: common_utils.create_parent(obj, WwiseObjectType.ActorMixer), expand=False)
        self.setup_batch_processor(self.actCreateVirtualFolder, lambda index, obj: common_utils.create_parent(obj, WwiseObjectType.Folder), expand=False)
        self.setup_batch_processor(self.actCreateBlendContainer, lambda index, obj: common_utils.create_parent(obj, WwiseObjectType.BlendContainer), expand=False)
        self.setup_batch_processor(self.actCreateRandomSequenceContainer, lambda index, obj: common_utils.create_parent(obj, WwiseObjectType.RandomContainer), expand=False)
        self.setup_batch_processor(self.actCreateSwitchContainer, lambda index, obj: common_utils.create_parent(obj, WwiseObjectType.SwitchContainer), expand=False)

        self.setup_batch_processor(self.actMoveToSelection, lambda index, obj: common_utils.move_to_selection(obj), expand=False)
        self.setup_batch_processor(self.actCopyFromSelection, lambda index, obj: common_utils.copy_from_selection(obj), expand=False)

        self.setup_batch_processor(self.actChangeToLowerCase, lambda index, obj: common_utils.rename_to_lower_case(obj))
        self.setup_batch_processor(self.actChangeToTitleCase, lambda index, obj: common_utils.rename_to_title_case(obj))
        self.setup_batch_processor(self.actChangeToUpperCase, lambda index, obj: common_utils.rename_to_upper_case(obj))
        self.setup_batch_processor(self.actRenameToShort, lambda index, obj: common_utils.rename_to_short_name(obj))
        self.setup_batch_processor(self.actRenameToFull, lambda index, obj: common_utils.rename_to_full_name(obj))
        self.setup_batch_processor(self.actRemovePrefix, lambda index, obj: common_utils.remove_name_prefix(obj))
        self.setup_batch_processor(self.actRemoveSuffix, lambda index, obj: common_utils.remove_name_suffix(obj))
        self.setup_batch_processor(self.actUseAcronym, lambda index, obj: common_utils.rename_with_acronym(obj))
        self.setup_batch_processor(self.actAutoSetColor, lambda index, obj: common_utils.update_object_colors(obj))
        self.setup_batch_processor(self.actAutoAddNotes, lambda index, obj: common_utils.update_reference_notes(obj))
        self.setup_batch_processor(self.actSplitUnderScore, lambda index, obj: common_utils.split_underscore_to_folder(obj))

        self.actReplaceByTemplate.triggered.connect(self.open_template_replace_window)
        self.actRenameByDataTable.triggered.connect(self.open_table_rename_window)
        # 源文件菜单
        self.actTrimAudioSilence.triggered.connect(self.open_audio_silence_trimmer_window)
        self.actSyncTrim.triggered.connect(self.open_sync_trim_window)
        self.setup_batch_processor(self.actApplyEditsToOriginal, lambda index, obj: audio_source_utils.apply_source_edits(obj), WwiseObjectType.AudioSource)
        self.setup_batch_processor(self.actResetSourceEdits, lambda index, obj: audio_source_utils.reset_source_editor(obj), WwiseObjectType.AudioSource)
        self.setup_batch_processor(self.actRenameOriginalToWwise, lambda index, obj: audio_source_utils.rename_original_to_wwise(obj), WwiseObjectType.Sound)
        self.setup_batch_processor(self.actAutoImport, lambda index, obj: audio_source_utils.auto_import_by_path(obj), WwiseObjectType.Sound)
        self.setup_batch_processor(self.actTidyOriginalFolders, lambda index, obj: audio_source_utils.tidy_original_folders(obj), WwiseObjectType.Sound)
        self.actDeleteUnusedAKDFiles.triggered.connect(audio_source_utils.delete_unused_akd_files)
        # 本地化菜单
        self.setup_batch_processor(self.actLocalizeLanguages, lambda index, obj: localization_utils.localize_languages(obj), WwiseObjectType.Sound)
        self.setup_batch_processor(self.actFillSilenceForRefLanguage, lambda index, obj: localization_utils.import_silence_for_ref_language(obj), WwiseObjectType.Sound)
        self.setup_batch_processor(self.actFillSilenceForAllLanguages, lambda index, obj: localization_utils.import_silence_for_all_languages(obj), WwiseObjectType.Sound)
        self.actFilterByLanguage.triggered.connect(self.filter_by_active_language)
        # 混音菜单
        self.setup_batch_processor(self.actDownMixFader, lambda index, obj: mixing_utils.down_mix_fader(obj))
        self.setup_batch_processor(self.actVolumeToGain, lambda index, obj: mixing_utils.volume_to_gain(obj))
        self.setup_batch_processor(self.actEnableEffectRender, lambda index, obj: mixing_utils.set_effect_slot_property(obj, 'Render', True))
        self.setup_batch_processor(self.actDisableEffectRender, lambda index, obj: mixing_utils.set_effect_slot_property(obj, 'Render', False))
        self.setup_batch_processor(self.actEnableEffectBypass, lambda index, obj: mixing_utils.set_effect_slot_property(obj, 'Bypass', True))
        self.setup_batch_processor(self.actDisableEffectBypass, lambda index, obj: mixing_utils.set_effect_slot_property(obj, 'Bypass', False))
        # Container菜单
        self.setup_batch_processor(self.actBreakContainer, lambda index, obj: container_utils.break_container(obj), expand=False)
        self.setup_batch_processor(self.actReplaceParent, lambda index, obj: container_utils.replace_parent(obj), expand=False)
        self.setup_batch_processor(self.actAssignSwitchMappings, lambda index, obj: container_utils.auto_assign_switch_mappings(obj), WwiseObjectType.SwitchContainer)
        self.setup_batch_processor(self.actRemoveSwitchMappings, lambda index, obj: waapi_utils.remove_switch_mappings(obj), WwiseObjectType.SwitchContainer)
        self.setup_batch_processor(self.actAssignToGenericPath, lambda index, obj: container_utils.assign_to_generic_path(obj), WwiseObjectType.SwitchContainer)
        self.setup_batch_processor(self.actSplitTo1P3P, lambda index, obj: container_utils.split_by_net_role(obj, False, True), expand=False)
        self.setup_batch_processor(self.actSplitTo1P2P3P, lambda index, obj: container_utils.split_by_net_role(obj, True, True), expand=False)
        self.setup_batch_processor(self.actSplitTo1P2P, lambda index, obj: container_utils.split_by_net_role(obj, True, False), expand=False)
        self.setup_batch_processor(self.actGroupAsRandom, lambda index, obj: container_utils.group_as_random(obj), WwiseObjectType.Sound)
        self.setup_batch_processor(self.actRenameRandomChildren, lambda index, obj: container_utils.rename_random_children(obj), WwiseObjectType.RandomContainer)
        # Event菜单
        self.setup_batch_processor(self.actCreatePlayEvent, lambda index, obj: event_utils.create_play_event(obj), (
            WwiseObjectType.Sound, WwiseObjectType.RandomContainer, WwiseObjectType.BlendContainer,
            WwiseObjectType.SwitchContainer, WwiseObjectType.MusicPlaylistContainer,
            WwiseObjectType.MusicSwitchContainer, WwiseObjectType.MusicSegment,
        ))
        self.setup_batch_processor(self.actRenameEventByTarget, lambda index, obj: event_utils.rename_event_by_target(obj), WwiseObjectType.Event)
        self.actExportAllEvents.triggered.connect(event_utils.export_all_events)
        # SoundBank菜单
        self.setup_batch_processor(self.actCreateSoundBank, lambda index, obj: soundbank_utils.create_bank_for_object(obj), expand=False)
        self.setup_batch_processor(self.actClearInclusions, lambda index, obj: waapi_utils.clear_bank_inclusions(obj), WwiseObjectType.SoundBank)
        self.setup_batch_processor(self.actIncludeMediaOnly, lambda index, obj: soundbank_utils.set_inclusion_type(obj, ['media']), WwiseObjectType.SoundBank)
        self.setup_batch_processor(self.actIncludeEventsAndStructures, lambda index, obj: soundbank_utils.set_inclusion_type(obj, ['events', 'structures']), WwiseObjectType.SoundBank)
        self.setup_batch_processor(self.actIncludeAll, lambda index, obj: soundbank_utils.set_inclusion_type(obj, ['events', 'structures', 'media']), WwiseObjectType.SoundBank)
        self.actAddToSelectedBank.triggered.connect(self.add_to_selected_bank)

        self.actBankAssignmentMatrix.triggered.connect(self.open_bank_assignment_matrix_window)
        self.actGenerateEventBankMap.triggered.connect(soundbank_utils.generate_event_bank_map)
        # 统计菜单
        self.actCalculateMediaSize.triggered.connect(self.calculate_media_size)
        self.actPropertyQuery.triggered.connect(self.open_property_query_window)
        # GameSync菜单
        self.actCopyRtpcFromSelection.triggered.connect(self.copy_rtpc_from_selection)
        # 导入菜单
        self.actImportWorkUnit.triggered.connect(self.import_from_work_unit)
        self.actImportFMODEvent.triggered.connect(migration_utils.import_fmod_events)
        self.actImportFMODPreset.triggered.connect(migration_utils.import_fmod_presets)
        # 其他菜单
        self.actHelpDoc.triggered.connect(self.open_help_documentation)
        self.actProjectValidation.triggered.connect(self.open_project_validation_window)        

        self.table.model.inclusion_updated.connect(self._on_wwise_inclusion_cell_changed)
        # AI 助手输入栏
        self.btnAiSend.clicked.connect(self._on_ai_send)
        self.btnAiStop.clicked.connect(self._on_ai_stop)
        self.ledAiPrompt.returnPressed.connect(self._on_ai_send)
        # 用户选择/输入模型后立即持久化到 user_config.json，避免每次启动回到第一个
        self.cbbAiModel.activated.connect(lambda _index: self._persist_ai_model())
        line_edit = self.cbbAiModel.lineEdit()
        if line_edit is not None:
            line_edit.editingFinished.connect(self._persist_ai_model)

    # 连接批处理器到操作（processor 签名为 (index, obj)，与 batch_processor.create_async 一致）
    def setup_batch_processor(self, action, obj_func: Callable, target_types=None, expand: bool = None):
        def proc(index, obj):
            obj_func(index, obj)
            return True

        action.triggered.connect(
            lambda: batch_processor.create_async(
                self.collect_tool_targets(target_types, expand),
                proc,
                action.text(),
                "name",
            )
        )

    # 重置筛选
    def reset_filter(self, apply_filter: bool = True):
        self._restoring_history = True
        try:
            self.ledFilterKeyword.setText("")
            self.cbbFilterType.setCurrentIndex(0)
            self.cbxCaseSensitive.setChecked(False)
            self.cbxOnlyIncludedEnabled.setChecked(False)
        finally:
            self._restoring_history = False
        if apply_filter:
            self.apply_table_filter()

    # 设置按钮的颜色
    def set_widget_style(self, widget, style: str):
        widget.setProperty("class", style)
        widget.setStyleSheet(self.style_sheet)

    # 检查WAAPI连接状态
    def check_wwise_connection(self):
        project_utils.wwise_version = 0
        try:
            Logger().debug("正在尝试连接Wwise...")
            client = WAAPIClient()
            if client.is_connected():
                client.client.subscribe('ak.wwise.core.project.postClosed', lambda: self.on_wwise_connection_changed(False))
                project_path = project_utils.get_project_path()
                if project_path:
                    version = project_utils.get_project_version()
                    self.lblWwiseConnection.setText(f'已连接到Wwise{version}')
                    if version and version < 2021:
                        Logger().warning(f'Wwise {version} 低于本工具最低支持版本 2021，部分功能可能不可用')
                    Logger().debug(f"Wwise已成功连接到{project_path}")
                else:
                    Logger().error(f"Wwise未连接，请打开Wwise工程后重试")
                project_conventions.init()
        except CannotConnectToWaapiException:
            Logger().warning("无法连接到Wwise，请确认Wwise工程已打开！")
            self.on_wwise_connection_changed(False)

    # 当Wwise连接状态改变时更新
    def on_wwise_connection_changed(self, connected: bool):
        self.lblWwiseConnection.setText("Wwise工程已连接" if connected else "Wwise工程未连接")
        self.set_widget_style(self.lblWwiseConnection, "success" if connected else "warning")
        if not connected:
            waapi_utils.close_client()

    # 获取Wwise中选中的对象
    def get_selected_objects(self):
        self.__eventFilterBase = None
        self.__languageFilterBase = None
        gv.active_objects = waapi_utils.get_selected_objects()
        # 获取新选中对象只负责载入并展示，不执行任何筛选
        self.reset_filter(False)
        self.table.refresh_table(True)
        self._object_history_reset_with_current()

    # 由 Wwise 右键菜单（--from-wwise）启动时：读取 Wwise 当前选中的对象载入列表
    def load_current_wwise_selection(self):
        try:
            if not WAAPIClient().is_connected():
                Logger().warning("无法连接到Wwise，请确认Wwise工程已打开且已启用Authoring API")
                return
        except CannotConnectToWaapiException:
            Logger().warning("无法连接到Wwise，请确认Wwise工程已打开且已启用Authoring API")
            return
        self.get_selected_objects()

    # 接收 Wwise 右键菜单（Open in WAAPI Tools）传入的对象 GUID 并载入列表
    def load_external_objects(self, object_ids: list[str]):
        if not object_ids:
            return
        try:
            if not WAAPIClient().is_connected():
                Logger().warning("无法连接到Wwise，请确认Wwise工程已打开且已启用Authoring API")
                return
        except CannotConnectToWaapiException:
            Logger().warning("无法连接到Wwise，请确认Wwise工程已打开且已启用Authoring API")
            return
        objects = []
        for raw_id in object_ids:
            obj = waapi_utils.get_full_info_from_obj_id(str(raw_id).strip())
            if obj.is_valid:
                objects.append(obj)
            else:
                Logger().debug(f"无法解析Wwise对象ID，已跳过：{raw_id}")
        if not objects:
            Logger().warning("Wwise右键传入的对象均无法在工程中解析，请确认已打开正确的Wwise工程")
            return
        gv.active_objects = objects
        self.reset_filter(False)
        self.table.refresh_table(True)
        self.apply_table_filter()
        self._object_history_reset_with_current()
        Logger().info(f"已从Wwise右键菜单载入 {len(objects)} 个对象")

    # 拷贝 WwiseObject 列表（字典级拷贝）
    @staticmethod
    def _clone_object_list(objs: list[WwiseObject]) -> list[WwiseObject]:
        return [WwiseObject(dict(o.wwise_dict) if o.wwise_dict else {}) for o in objs]

    # 采集当前活动对象与筛选控件状态为快照
    def _capture_object_list_snapshot(self) -> tuple:
        return (
            self._clone_object_list(gv.active_objects),
            self.ledFilterKeyword.text(),
            self.cbbFilterType.currentText(),
            self.cbxCaseSensitive.isChecked(),
            self.cbxOnlyIncludedEnabled.isChecked(),
        )

    # 比较两快照是否等价（对象 id 序列与筛选条件）
    @staticmethod
    def _snapshots_equal(a: tuple, b: tuple) -> bool:
        oa, kwa, ta, ca, oi_a = a
        ob, kwb, tb, cb, oi_b = b
        if kwa != kwb or ta != tb or ca != cb or oi_a != oi_b:
            return False
        if len(oa) != len(ob):
            return False
        return tuple(x.id for x in oa) == tuple(x.id for x in ob)

    # 清空前进分支并以当前界面状态作为唯一历史项（获取选中时调用）
    def _object_history_reset_with_current(self):
        self._object_history = [self._capture_object_list_snapshot()]
        self._history_index = 0
        self._update_history_buttons()

    # 当前与上一状态不同时追加快照，并丢弃原“前进”栈
    def _history_append_current_if_changed(self):
        snap = self._capture_object_list_snapshot()
        if self._object_history and self._snapshots_equal(snap, self._object_history[self._history_index]):
            return
        self._object_history = self._object_history[: self._history_index + 1]
        self._object_history.append(snap)
        self._history_index = len(self._object_history) - 1
        self._update_history_buttons()

    # 将界面恢复到指定快照（活动对象 + 筛选 + 刷新表格）
    def _restore_object_list_snapshot(self, snap: tuple):
        self.__eventFilterBase = None
        self.__languageFilterBase = None
        objs, kw, ft, cs, oi = snap
        self._restoring_history = True
        try:
            gv.active_objects = self._clone_object_list(objs)
            self.ledFilterKeyword.setText(kw)
            self.cbbFilterType.setCurrentText(ft)
            self.cbxCaseSensitive.setChecked(cs)
            self.cbxOnlyIncludedEnabled.setChecked(oi)
            self.table.refresh_table(True)
            self.apply_table_filter()
        finally:
            self._restoring_history = False
        self._update_history_buttons()

    # 按历史游标启用或禁用后退、前进按钮
    def _update_history_buttons(self):
        n = len(self._object_history)
        self.btnObjectHistoryBack.setEnabled(self._history_index > 0)
        self.btnObjectHistoryForward.setEnabled(n > 0 and self._history_index < n - 1)

    # 后退到上一对象列表快照
    def object_history_back(self):
        if self._history_index <= 0:
            return
        self._history_index -= 1
        self._restore_object_list_snapshot(self._object_history[self._history_index])

    # 前进到下一对象列表快照
    def object_history_forward(self):
        if self._history_index >= len(self._object_history) - 1:
            return
        self._history_index += 1
        self._restore_object_list_snapshot(self._object_history[self._history_index])

    # 按当前 gv.active_objects 重建表格并应用筛选（旧代码中的 show_obj_list；仍被子窗口调用）
    def show_obj_list(self):
        self.table.refresh_table(True)
        self.apply_table_filter()

    # 清空操作对象列表
    def clear_object_list(self):
        self.__eventFilterBase = None
        self.__languageFilterBase = None
        gv.active_objects = []
        self.table.refresh_table(True)

    # 筛选表格内容
    def apply_table_filter(self, record_history: bool = False):
        total_count = self.table.model.rowCount()
        # 表格尚未载入数据（异步填充中）时无需筛选，避免误报 0/0
        if total_count == 0:
            return
        self.table.filter_results(self.ledFilterKeyword.text(), self.cbxCaseSensitive.isChecked())
        type_text = self.cbbFilterType.currentText()
        if not type_text or type_text == "全部类型":
            self.table.filter_by_type(None)
        else:
            self.table.filter_by_type(WwiseObjectType(type_text))
        self.table.filter_inclusion_only(self.cbxOnlyIncludedEnabled.isChecked())
        # 关键词/类型/启用等筛选全部执行完后，一次性输出筛选结果
        shown_count = sum(
            1
            for row in range(total_count)
            if not self.tblWwiseObjects.isRowHidden(row)
        )
        Logger().query(f"筛选完成，显示{shown_count}/{total_count}条")
        self.calculate_checked_rows()
        if record_history and not self._restoring_history:
            self._history_append_current_if_changed()

    # 统计有多少行选中
    def calculate_checked_rows(self):
        checked = 0
        total = 0
        for row_info in self.table.data:
            if self.tblWwiseObjects.isRowHidden(row_info.row):
                continue
            total += 1
            if row_info[INCLUSION_COL]:
                checked += 1
        Logger().status(f"已选中({checked}/{total})")

    # 全选/取消全选当前可见行的「选中」列
    def select_all_rows(self, checked: bool):
        proxy = self.tblWwiseObjects.model()
        for row in range(proxy.rowCount()):
            if self.tblWwiseObjects.isRowHidden(row):
                continue
            source_row = proxy.mapToSource(proxy.index(row, INCLUSION_COL)).row()
            self.table.model.check_row_inclusion(source_row, checked)
        self.table.model.refresh_column(INCLUSION_COL)
        self.calculate_checked_rows()

    # 获取当前筛选后仍可见的 Wwise 对象
    def get_visible_objects(self) -> list[WwiseObject]:
        return [row_data.wwise_object for row_data in self.table.active_data]

    # 获取目标类型对象：按「自动获取子对象」设置决定只取可见行还是先展开子级再筛选
    def get_tool_target_objects(self, target_types) -> list[WwiseObject]:
        return self.collect_tool_targets(target_types)

    # 统一的工具执行前对象采集：按「工具执行前自动获取子对象」决定是否展开子级，
    # 可按目标类型筛选（target_types 为 None 表示不筛类型），并遵循高级筛选的语言设置
    def collect_tool_targets(self, target_types=None, expand: bool = None) -> list[WwiseObject]:
        if target_types is not None and isinstance(target_types, WwiseObjectType):
            target_types = {target_types}
        elif target_types is not None:
            target_types = set(target_types)
        if expand is None:
            expand = user_config.get_tool_auto_fetch_children()
        # 高级筛选中开启「按当前语言筛选」时，只收集当前语言的音频源
        language_filter_active = (
            user_config.get_advanced_filter_settings().get("language_filter") == "active"
        )
        active_language = (
            localization_utils.get_current_language() if language_filter_active else None
        )
        visible_objects = self.get_visible_objects()
        collected: list[WwiseObject] = []
        seen_ids: set[str] = set()

        def add_object(obj: WwiseObject):
            if target_types is not None and obj.type not in target_types:
                return
            if obj.id not in seen_ids:
                if (
                    language_filter_active
                    and obj.type in (WwiseObjectType.Sound, WwiseObjectType.AudioSource)
                    and localization_utils.get_sound_language(obj) != active_language
                ):
                    return
                seen_ids.add(obj.id)
                collected.append(obj)

        if not expand:
            for obj in visible_objects:
                add_object(obj)
            return collected
        for obj in visible_objects:
            add_object(obj)
            if target_types is None:
                # 不筛类型：只能拉全部后代
                for child in waapi_utils.get_child_objects(obj, True):
                    add_object(child)
            else:
                # 有目标类型：用按类型查询后代的接口（单次 WAQL，比全量分页更快）
                for child in waapi_utils.get_descendants_of_type(obj, target_types):
                    add_object(child)
        return collected

    # 查找父级对象
    def find_parent(self):
        ancestor_mode = self.cbxRecursiveFind.isChecked()
        visible_objects = self.get_visible_objects()
        found_objects = list(visible_objects) if self.cbxKeepSelf.isChecked() else []
        for obj in visible_objects:
            if ancestor_mode:
                for ancestor in waapi_utils.get_ancestor_objects(obj):
                    found_objects.append(ancestor)
            else:
                found_objects.append(waapi_utils.get_parent_object(obj))
        gv.active_objects = found_objects
        self.table.refresh_table(True)
        self.apply_table_filter()
        self._history_append_current_if_changed()

    # 查找子级对象
    def find_children(self):
        visible_objects = self.get_visible_objects()
        all_children = list(visible_objects) if self.cbxKeepSelf.isChecked() else []
        for obj in visible_objects:
            for child in waapi_utils.get_child_objects(obj, self.cbxRecursiveFind.isChecked()):
                all_children.append(child)
        gv.active_objects = all_children
        self.table.refresh_table(True)
        self.apply_table_filter()
        self._history_append_current_if_changed()

    # 查找指定类型的子对象（高级查找窗口调用；遵循「递归查找」与「保留原始层级」设置）
    def find_children_by_type(self, type_text: str):
        target_type = None if not type_text or type_text == '全部类型' else WwiseObjectType(type_text)
        visible_objects = self.get_visible_objects()
        if not visible_objects:
            Logger().warning('表格中没有可查找的对象')
            return
        recursive = self.cbxRecursiveFind.isChecked()
        found_objects = list(visible_objects) if self.cbxKeepSelf.isChecked() else []
        seen_ids = {obj.id for obj in found_objects}
        for obj in visible_objects:
            # 递归 + 指定类型时用按类型查后代的接口（单次 WAQL，比全量分页更快）
            if target_type is not None and recursive:
                children = waapi_utils.get_descendants_of_type(obj, target_type)
            else:
                children = waapi_utils.get_child_objects(obj, recursive)
            for child in children:
                if target_type is not None and child.type != target_type:
                    continue
                if child.id in seen_ids:
                    continue
                seen_ids.add(child.id)
                found_objects.append(child)
        if not found_objects:
            Logger().warning('没有查找到符合条件的子对象')
            return
        gv.active_objects = found_objects
        self.table.refresh_table(True)
        self.apply_table_filter()
        self._history_append_current_if_changed()
        Logger().info(f'共查找到 {len(found_objects)} 个对象')

    # 查找引用当前表格对象的所有对象，逐一查询并去重后加入表格
    def find_references(self):
        visible_objects = self.get_visible_objects()
        found_objects = list(visible_objects) if self.cbxKeepSelf.isChecked() else []
        seen_ids = {obj.id for obj in found_objects}
        for obj in visible_objects:
            if obj.type == WwiseObjectType.AudioSource:
                references = self._get_audio_source_references(obj)
            else:
                references = waapi_utils.get_object_references(obj)
            for reference in references:
                if reference.id not in seen_ids:
                    seen_ids.add(reference.id)
                    found_objects.append(reference)
        gv.active_objects = found_objects
        self.table.refresh_table(True)
        self.apply_table_filter()
        self._history_append_current_if_changed()

    # 打开高级查找窗口
    def open_advanced_find_window(self):
        AdvancedFindWindow(self).exec()

    # 按属性查找：对表格内每个对象读取指定属性，属性返回对象引用的对象作为新的表格内容
    def find_by_property(self):
        property_name = self.cbbFindProperty.currentText().strip()
        if not property_name:
            Logger().warning('请输入要查找的属性名称')
            return
        objects = self.get_visible_objects()
        if not objects:
            Logger().warning('表格中没有可查找的对象')
            return
        found_objects: list[WwiseObject] = []
        seen_ids: set[str] = set()

        def process(index, obj):
            target = waapi_utils.get_referenced_object(obj, property_name)
            if target and target.is_valid and target.id not in seen_ids:
                seen_ids.add(target.id)
                found_objects.append(target)
            return True

        def finished():
            if not found_objects:
                Logger().warning(f'没有对象在属性「{property_name}」上返回有效对象')
                return
            gv.active_objects = found_objects
            self.show_obj_list()
            self._history_append_current_if_changed()
            Logger().info(f'属性「{property_name}」查找到 {len(found_objects)} 个对象')

        batch_processor.create_async(
            objects, process, f'查找属性 {property_name}', 'name', on_finished=finished
        )

    # 「按属性」下拉框选择变化时写入 user_config（主窗口设置节点）
    def _on_find_property_changed(self, text: str):
        settings = dict(user_config.get_window_settings('main_window'))
        settings['find_property'] = text
        user_config.set_window_settings('main_window', settings)

    # AudioFileSource 无法用 referencesTo 反查，改为按 originalRelativeFilePath 反查同源文件对象
    # 结果始终包含自身，保证未勾选「保留原始层级」时也能把当前对象搜出来
    def _get_audio_source_references(self, source: WwiseObject) -> list[WwiseObject]:
        relative_path = waapi_utils.get_object_property(source, 'originalRelativeFilePath')
        if not relative_path:
            return []
        return waapi_utils.find_audio_sources_by_original_path(relative_path)

    # 按工程当前参考语言筛选对象
    def filter_by_active_language(self):
        if self.__languageFilterBase is None:
            self.__languageFilterBase = list(self.get_visible_objects())
        active_language = localization_utils.get_current_language()
        gv.active_objects = [
            obj
            for obj in self.get_visible_objects()
            if localization_utils.get_sound_language(obj) == active_language
        ]
        self.show_obj_list()

    # 重置「语言」筛选：恢复为筛选前的列表
    def reset_active_language_filter(self):
        if self.__languageFilterBase is not None:
            gv.active_objects = self.__languageFilterBase
        else:
            gv.active_objects = [row.wwise_object for row in self.table.data]
        self.__languageFilterBase = None
        self.show_obj_list()

    # 按是否被 Event 引用筛选对象
    def filter_by_event_reference(self, with_ref: bool):
        if self.__eventFilterBase is None:
            self.__eventFilterBase = list(self.get_visible_objects())
        gv.active_objects = [
            obj
            for obj in self.__eventFilterBase
            if (with_ref and event_utils.has_event_reference(obj))
            or (not with_ref and not event_utils.has_event_reference(obj))
        ]
        self.show_obj_list()

    # 重置「Event 引用」筛选：恢复为当前表格中的全部行
    def reset_event_reference_filter(self):
        if self.__eventFilterBase is not None:
            gv.active_objects = self.__eventFilterBase
        else:
            gv.active_objects = [row.wwise_object for row in self.table.data]
        self.__eventFilterBase = None
        self.show_obj_list()

    # 打开高级筛选窗口
    def open_advanced_filter_window(self):
        AdvancedFilterWindow(self).exec()

    # 复制对象的路径
    def copy_object_path(self, item: QTableWidgetItem):
        if item.column() != PATH_COL:
            item = self.tblWwiseObjects.item(item.row(), PATH_COL)
        clipboard.copy(self._path_text(item))

    # 在Wwise中选中列表中双击的对象
    def show_object_in_wwise(self, item: QTableWidgetItem):
        if item.column() != PATH_COL:
            item = self.tblWwiseObjects.item(item.row(), PATH_COL)
        obj = waapi_utils.find_object_by_path(self._path_text(item))
        if obj:
            waapi_utils.select_objects_in_wwise([obj])

    # 路径列可能显示简写，优先取 UserRole 中的完整路径
    @staticmethod
    def _path_text(item) -> str:
        if item is None:
            return ''
        return item.data(Qt.ItemDataRole.UserRole) or item.text()

    # 在Wwise中同时选中表格里的所有对象
    def select_table_objects_in_wwise(self):
        objects = [row.wwise_object for row in self.table.data]
        if not objects:
            Logger().warning("表格为空，暂无可选中的对象")
            return
        if waapi_utils.select_objects_in_wwise(objects):
            Logger().info(f"已在Wwise中选中表格内的 {len(objects)} 个对象")

    # 导出对象列表
    def export_object_list(self):
        headers = self.table.header_list
        # 「选中」「启用」为表格操作列，不参与导出
        export_headers = [
            header
            for column, header in enumerate(headers)
            if column not in (CHECK_BOX_COL, ENABLE_COL)
        ]
        export_window = ExportObjectListWindow(export_headers)
        if export_window.exec() != QDialog.DialogCode.Accepted:
            return
        selected_headers = export_window.get_selected_headers()
        if not selected_headers:
            Logger().warning("未选择任何导出属性，已取消导出")
            return
        selected_columns = [headers.index(header) for header in selected_headers]
        # 只勾选一列时导出为txt，且不含表头
        if len(selected_columns) == 1:
            io_utils.export_to_txt(
                self.table.build_export_column(selected_columns[0]), 'WAAPI_Tools_Objects'
            )
            return
        rows = [selected_headers]
        rows.extend(self.table.build_export_rows(selected_columns))
        io_utils.export_to_csv(rows, 'WAAPI_Tools_Objects')

    # 导入对象列表
    def import_object_list(self):
        csv_data = io_utils.import_from_csv()
        if not csv_data:
            return
        headers = [str(header).strip() for header in csv_data[0]]
        path_header = COMMON_HEADERS[PATH_COL]
        if path_header not in headers:
            Logger().warning(f"导入失败：CSV中未包含「{path_header}」列，仅支持包含该列的CSV文件")
            return
        path_column = headers.index(path_header)
        paths = []
        for row in csv_data[1:]:
            if len(row) <= path_column:
                continue
            path = str(row[path_column]).strip()
            if path and path not in paths:
                paths.append(path)
        if not paths:
            Logger().warning("导入失败：CSV中没有可导入的路径数据")
            return
        objects = []
        missing_count = 0
        for path in paths:
            obj = waapi_utils.find_object_by_path(path)
            if obj and obj.is_valid:
                objects.append(obj)
            else:
                missing_count += 1
        if not objects:
            Logger().error("导入失败：CSV中的路径在Wwise工程中均未找到")
            return
        gv.active_objects = objects
        self.show_obj_list()
        suffix = f"，{missing_count}个路径未找到" if missing_count else ""
        Logger().info(f"导入完成，共导入{len(objects)}个对象{suffix}")

    # 导入Work Unit
    @staticmethod
    def import_from_work_unit():
        import_window = WorkUnitImporter()
        import_window.show()
        import_window.exec()

    # 打开Wwise的多项编辑器
    def open_in_multi_editor(self):
        waapi_utils.execute_ui_command(self.get_visible_objects(), 'ShowMultiEditor')
        waapi_utils.bring_wwise_to_foreground()

    # 打开Wwise的批量重命名工具
    def open_in_batch_rename(self):
        waapi_utils.execute_ui_command(self.get_visible_objects(), 'ShowBatchRename')
        waapi_utils.bring_wwise_to_foreground()

    # 打开模板批量替换窗口
    def open_template_replace_window(self):
        replace_window = TemplateReplacer(self)
        replace_window.show()
        replace_window.exec()

    # 打开读表重命名窗口
    def open_table_rename_window(self):
        rename_window = TableRenamer(self)
        rename_window.show()
        rename_window.exec()

    # 打开音频末尾静音裁剪窗口
    def open_audio_silence_trimmer_window(self):
        target_objects = self.get_tool_target_objects(WwiseObjectType.AudioSource)
        trim_window = AudioSilenceTrimWindow(target_objects)
        trim_window.show()
        trim_window.exec()

    # 打开同步裁剪窗口，列出主窗口表格中的所有 AudioSource 及其裁剪信息
    def open_sync_trim_window(self):
        sources = [
            row.wwise_object
            for row in self.table.data
            if row.wwise_object.type == WwiseObjectType.AudioSource
        ]
        if not sources:
            Logger().warning('当前表格中没有 AudioSource 对象')
            return
        trim_window = SyncTrimWindow(sources)
        trim_window.show()
        trim_window.exec()

    # 打开媒体资源大小统计窗口（按每个对象逐项展示）
    def calculate_media_size(self):
        objects = [row_data.wwise_object for row_data in self.table.active_data]
        if not objects:
            Logger().warning('表格中没有可统计的对象')
            return
        media_window = MediaSizeWindow(objects)
        media_window.show()
        media_window.exec()

    # 打开属性查询窗口，对表格可见对象批量读取指定属性
    def open_property_query_window(self):
        objects = self.collect_tool_targets()
        if not objects:
            Logger().warning('表格中没有可查询的对象')
            return
        query_window = PropertyQueryWindow(objects)
        query_window.show()
        query_window.exec()

    # 添加列表对象到选中的Bank中
    def add_to_selected_bank(self):
        banks = waapi_utils.get_selected_objects()
        if len(banks) == 0 or banks[0].type != WwiseObjectType.SoundBank:
            return
        soundbank_utils.add_objects_to_bank(banks[0], self.get_visible_objects(), ['media'])

    # 打开Bank的列表分配窗口
    def open_bank_assignment_matrix_window(self):
        matrix_window = BankAssignmentMatrix(self)
        matrix_window.show()
        matrix_window.exec()

    # 替换对象上的RTPC
    def copy_rtpc_from_selection(self):
        selection = waapi_utils.get_selected_objects()
        if len(selection) < 1:
            return False
        game_sync_utils.copy_rtpc(selection[0], self.get_visible_objects())

    # 打开工程检查窗口
    def open_project_validation_window(self):
        validate_window = ProjectValidation(self)
        validate_window.show()
        validate_window.exec()

    # 添加日志，确保自动定位到最新
    def add_log(self, line):
        cursor = self.txeOutputLogs.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.txeOutputLogs.append(line)
        self.txeOutputLogs.setTextCursor(cursor)
        self.txeOutputLogs.ensureCursorVisible()


    # 窗口关闭事件处理
    def closeEvent(self, event):
        Logger().info("正在关闭应用程序...")
        # 等待 AI 对话线程结束（最多 3 秒）
        if self._ai_worker and self._ai_worker.isRunning():
            self._ai_worker.stop_requested()
            self._ai_worker.wait(3000)
        if self._ai_model_worker and self._ai_model_worker.isRunning():
            self._ai_model_worker.wait(2000)
        # 停止所有正在运行的批处理线程
        if gv.batch_processor and hasattr(gv.batch_processor, "isRunning"):
            gv.batch_processor.stop()
            if gv.batch_processor.isRunning():
                gv.batch_processor.wait(3000)  # 等待最多3秒
        # 关闭进度条窗口
        if gv.progress_bar:
            gv.progress_bar.close()
        # 关闭WAAPI连接
        try:
            waapi_utils.close_client()
        except Exception as e:
            Logger().error(f"关闭WAAPI连接时出错: {e}")
        Logger().debug("应用程序已关闭")
        event.accept()
