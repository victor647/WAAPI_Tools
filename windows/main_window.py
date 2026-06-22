from collections.abc import Callable

import clipboard
import webbrowser

from PySide6.QtGui import QTextCursor

import globals.global_variables as gv
from data import project_conventions
from globals.constants import *
from libraries.multi_thread import batch_processor
from libraries.table_view.table_item_model import INCLUSION_COL
from libraries.utils.log_utils import Logger
from libraries.utils.p4_utils import P4Client
from libraries.waapi_client import WAAPIClient
from libraries.wwise_object import WwiseObject, WwiseObjectType
from table.wwise_object_table_gui import WwiseTableImpl
from table.wwise_table_headers import TABLE_DISPLAY_MODE_LABELS, PATH_COL
from windows.audio_silence_trim_window import AudioSilenceTrimWindow as AudioSilenceTrimWindow
from windows.table_rename_window import TableRenamer as TableRenamer
from windows.template_replace_window import TemplateReplacer as TemplateReplacer
from windows.bank_assignment_window import BankAssignmentMatrix as BankAssignmentMatrix
from windows.project_validation_window import ProjectValidation as ProjectValidation
from windows.unity_asset_manager_window import UnityAssetManager as UnityAssetManager
from windows.work_unit_import_window import WorkUnitImporter as WorkUnitImporter
from waapi import CannotConnectToWaapiException
from PySide6.QtWidgets import QMainWindow, QStyle, QTableWidgetItem, QToolButton
from ui.MainWindow_ui import Ui_MainWindow
from libraries.utils.wwise import common_utils, audio_source_utils, game_sync_utils, soundbank_utils, \
    localization_utils, project_utils, event_utils, container_utils, migration_utils, waapi_utils, mixing_utils
from libraries.utils import io_utils


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
        self.setWindowTitle(f"WAAPI 工具集 {SOFTWARE_VERSION}")
        self.style_sheet = style_sheet
        self.table = WwiseTableImpl(self.tblWwiseObjects)
        self._object_history: list[tuple] = []
        self._history_index: int = -1
        self._restoring_history: bool = False
        self._setup_filter_help_button()
        self.setup_triggers()
        self.check_wwise_connection()
        self._update_history_buttons()

    # 初始化表格视图模式下拉框（选项与列定义见 wwise_table_headers / WwiseTableDisplayMode）
    def _setup_table_display_mode_combo(self):
        self.cbbTableDisplayMode.clear()
        self.cbbTableDisplayMode.addItems(list(TABLE_DISPLAY_MODE_LABELS))
        self.cbbTableDisplayMode.blockSignals(True)
        self.cbbTableDisplayMode.setCurrentIndex(self.table.display_mode.value)
        self.cbbTableDisplayMode.blockSignals(False)
        self.cbbTableDisplayMode.currentIndexChanged.connect(self.on_table_display_mode_changed)

    def _setup_filter_help_button(self):
        self.btnFilterHelp = QToolButton(self.grpTableView)
        self.btnFilterHelp.setObjectName("btnFilterHelp")
        self.btnFilterHelp.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion))
        self.btnFilterHelp.setAutoRaise(True)
        self.btnFilterHelp.setToolTip(
            "筛选会匹配名称与路径。\n"
            "多个条件用 ; 分隔，所有包含条件都必须命中。\n"
            "Boss        包含 Boss\n"
            "-Temp       排除包含 Temp 的对象\n"
            "=ShotGun    全字匹配名称或路径节点\n"
            "-=Debug     排除全字匹配 Debug 的对象"
        )
        self.horizontalLayout_2.insertWidget(2, self.btnFilterHelp)

    # 切换表格显示模式并重新应用筛选
    def on_table_display_mode_changed(self, index: int):
        if index < 0:
            return
        self.table.set_display_mode(index)
        self.apply_table_filter()

    # 切换对象类型筛选时立即刷新表格（与「应用筛选」一致，并记入对象列表历史）
    def _on_filter_type_changed(self, index: int):
        if index < 0 or self._restoring_history:
            return
        self.apply_table_filter(record_history=True)

    # 关键字变化时即时筛选（不每次写入历史，避免输入过程中堆叠快照）
    def _on_filter_keyword_changed(self, _text: str):
        if self._restoring_history:
            return
        self.apply_table_filter(record_history=False)

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
        # 日志绑定
        Logger().set_log_window_stream(self.add_log)
        Logger().set_status_bar_stream(lambda text: self.statusbar.showMessage(text))
        # 所有按键
        self.actReconnectWwise.triggered.connect(self.check_wwise_connection)
        self.btnGetSelectedObjects.clicked.connect(self.get_selected_objects)
        self.btnClearTable.clicked.connect(self.clear_object_list)
        self.btnMultiEditor.clicked.connect(self.open_in_multi_editor)
        self.btnBatchRename.clicked.connect(self.open_in_batch_rename)
        self.btnFindParent.clicked.connect(self.find_parent)
        self.btnFindChildren.clicked.connect(self.find_children)
        self.ledFilterKeyword.textChanged.connect(self._on_filter_keyword_changed)
        self.cbxCaseSensitive.toggled.connect(self._on_case_sensitive_changed)
        self.cbxOnlyIncludedEnabled.toggled.connect(self._on_only_included_toggled)
        self.cbbFilterType.currentIndexChanged.connect(self._on_filter_type_changed)
        self.btnObjectHistoryBack.clicked.connect(self.object_history_back)
        self.btnObjectHistoryForward.clicked.connect(self.object_history_forward)
        # 文件菜单
        self.actImportObjectList.triggered.connect(self.import_object_list)
        self.actExportObjectList.triggered.connect(self.export_object_list)
        # 编辑菜单
        self.actUndo.triggered.connect(waapi_utils.undo)
        self.actRedo.triggered.connect(waapi_utils.redo)

        self.setup_batch_processor(self.actDeleteObjects, lambda index, obj: waapi_utils.delete_object(obj))
        # 通用菜单（改变类型为仅表格类型列右键）
        self.setup_batch_processor(self.actCreateWorkUnit, lambda index, obj: common_utils.create_parent(obj, WwiseObjectType.WorkUnit))
        self.setup_batch_processor(self.actCreateActorMixer, lambda index, obj: common_utils.create_parent(obj, WwiseObjectType.ActorMixer))
        self.setup_batch_processor(self.actCreateVirtualFolder, lambda index, obj: common_utils.create_parent(obj, WwiseObjectType.Folder))
        self.setup_batch_processor(self.actCreateBlendContainer, lambda index, obj: common_utils.create_parent(obj, WwiseObjectType.BlendContainer))
        self.setup_batch_processor(self.actCreateRandomSequenceContainer, lambda index, obj: common_utils.create_parent(obj, WwiseObjectType.RandomContainer))
        self.setup_batch_processor(self.actCreateSwitchContainer, lambda index, obj: common_utils.create_parent(obj, WwiseObjectType.SwitchContainer))

        self.setup_batch_processor(self.actMoveToSelection, lambda index, obj: common_utils.move_to_selection(obj))
        self.setup_batch_processor(self.actCopyFromSelection, lambda index, obj: common_utils.copy_from_selection(obj))

        self.setup_batch_processor(self.actChangeToLowerCase, lambda index, obj: common_utils.rename_to_lower_case(obj))
        self.setup_batch_processor(self.actChangeToTitleCase, lambda index, obj: common_utils.rename_to_title_case(obj))
        self.setup_batch_processor(self.actChangeToUpperCase, lambda index, obj: common_utils.rename_to_upper_case(obj))
        self.setup_batch_processor(self.actRenameToShort, lambda index, obj: common_utils.rename_to_short_name(obj))
        self.setup_batch_processor(self.actRenameToFull, lambda index, obj: common_utils.rename_to_full_name(obj))
        self.setup_batch_processor(self.actRemovePrefix, lambda index, obj: common_utils.remove_name_prefix(obj))
        self.setup_batch_processor(self.actRemoveSuffix, lambda index, obj: common_utils.remove_name_suffix(obj))
        self.setup_batch_processor(self.actUseAcronym, lambda index, obj: common_utils.rename_with_acronym(obj))
        self.setup_batch_processor(self.actUpdateNoteAndColor, lambda index, obj: common_utils.update_notes_and_color(obj))
        self.setup_batch_processor(self.actSplitUnderScore, lambda index, obj: common_utils.split_underscore_to_folder(obj))

        self.actReplaceByTemplate.triggered.connect(self.open_template_replace_window)
        self.actRenameByDataTable.triggered.connect(self.open_table_rename_window)
        # 源文件菜单
        self.actTrimAudioSilence.triggered.connect(self.open_audio_silence_trimmer_window)
        self.setup_batch_processor(self.actApplyEditsToOriginal, lambda index, obj: audio_source_utils.apply_source_edits(obj))
        self.setup_batch_processor(self.actResetSourceEdits, lambda index, obj: audio_source_utils.reset_source_editor(obj))
        self.setup_batch_processor(self.actRenameOriginalToWwise, lambda index, obj: audio_source_utils.rename_original_to_wwise(obj))
        self.setup_batch_processor(self.actAutoImport, lambda index, obj: audio_source_utils.auto_import_by_path(obj))
        self.setup_batch_processor(self.actTidyOriginalFolders, lambda index, obj: audio_source_utils.tidy_original_folders(obj))
        self.actDeleteUnusedAKDFiles.triggered.connect(audio_source_utils.delete_unused_akd_files)
        # 本地化菜单
        self.setup_batch_processor(self.actLocalizeLanguages, lambda index, obj: localization_utils.localize_languages(obj))
        self.setup_batch_processor(self.actFillSilenceForRefLanguage, lambda index, obj: localization_utils.import_silence_for_ref_language(obj))
        self.setup_batch_processor(self.actFillSilenceForAllLanguages, lambda index, obj: localization_utils.import_silence_for_all_languages(obj))
        self.actFilterByLanguage.triggered.connect(self.filter_by_active_language)
        # 混音菜单
        self.setup_batch_processor(self.actDownMixFader, lambda index, obj: mixing_utils.down_mix_fader(obj))
        self.setup_batch_processor(self.actVolumeToGain, lambda index, obj: mixing_utils.volume_to_gain(obj))
        self.setup_batch_processor(self.actEnableEffectRender, lambda index, obj: mixing_utils.set_effect_slot_property(obj, 'Render', True))
        self.setup_batch_processor(self.actDisableEffectRender, lambda index, obj: mixing_utils.set_effect_slot_property(obj, 'Render', False))
        self.setup_batch_processor(self.actEnableEffectBypass, lambda index, obj: mixing_utils.set_effect_slot_property(obj, 'Bypass', True))
        self.setup_batch_processor(self.actDisableEffectBypass, lambda index, obj: mixing_utils.set_effect_slot_property(obj, 'Bypass', False))
        # Container菜单
        self.setup_batch_processor(self.actBreakContainer, lambda index, obj: container_utils.break_container(obj))
        self.setup_batch_processor(self.actReplaceParent, lambda index, obj: container_utils.replace_parent(obj))
        self.setup_batch_processor(self.actAssignSwitchMappings, lambda index, obj: container_utils.auto_assign_switch_mappings(obj))
        self.setup_batch_processor(self.actRemoveSwitchMappings, lambda index, obj: waapi_utils.remove_switch_mappings(obj))
        self.setup_batch_processor(self.actAssignToGenericPath, lambda index, obj: container_utils.assign_to_generic_path(obj))
        self.setup_batch_processor(self.actSplitTo1P3P, lambda index, obj: container_utils.split_by_net_role(obj, False, True))
        self.setup_batch_processor(self.actSplitTo1P2P3P, lambda index, obj: container_utils.split_by_net_role(obj, True, True))
        self.setup_batch_processor(self.actSplitTo1P2P, lambda index, obj: container_utils.split_by_net_role(obj, True, False))
        self.setup_batch_processor(self.actGroupAsRandom, lambda index, obj: container_utils.group_as_random(obj))
        self.setup_batch_processor(self.actRenameRandomChildren, lambda index, obj: container_utils.rename_random_children(obj))
        # Event菜单
        self.setup_batch_processor(self.actCreatePlayEvent, lambda index, obj: event_utils.create_play_event(obj))
        self.setup_batch_processor(self.actRenameEventByTarget, lambda index, obj: event_utils.rename_event_by_target(obj))
        self.actExportAllEvents.triggered.connect(event_utils.export_all_events)
        self.actHasEventReference.triggered.connect(lambda: self.filter_by_event_reference(True))
        self.actHasNoEventReference.triggered.connect(lambda: self.filter_by_event_reference(False))
        # SoundBank菜单
        self.setup_batch_processor(self.actCreateSoundBank, lambda index, obj: soundbank_utils.create_bank_for_object(obj))
        self.setup_batch_processor(self.actClearInclusions, lambda index, obj: waapi_utils.clear_bank_inclusions(obj))
        self.setup_batch_processor(self.actIncludeMediaOnly, lambda index, obj: soundbank_utils.set_inclusion_type(obj, ['media']))
        self.setup_batch_processor(self.actIncludeEventsAndStructures, lambda index, obj: soundbank_utils.set_inclusion_type(obj, ['events', 'structures']))
        self.setup_batch_processor(self.actIncludeAll, lambda index, obj: soundbank_utils.set_inclusion_type(obj, ['events', 'structures', 'media']))
        self.actCalculateBankSize.triggered.connect(self.calculate_bank_total_size)
        self.actAddToSelectedBank.triggered.connect(self.add_to_selected_bank)

        self.actBankAssignmentMatrix.triggered.connect(self.open_bank_assignment_matrix_window)
        self.actGenerateEventBankMap.triggered.connect(soundbank_utils.generate_event_bank_map)
        # GameSync菜单
        self.actCopyRtpcFromSelection.triggered.connect(self.copy_rtpc_from_selection)
        # 导入菜单
        self.actImportWorkUnit.triggered.connect(self.import_from_work_unit)
        self.actImportFMODEvent.triggered.connect(migration_utils.import_fmod_events)
        self.actImportFMODPreset.triggered.connect(migration_utils.import_fmod_presets)
        self.actImportScreenshot.triggered.connect(migration_utils.import_from_screenshot)
        # 其他菜单
        self.actHelpDoc.triggered.connect(lambda: webbrowser.open(DOCUMENTATION_URL))
        self.actProjectValidation.triggered.connect(self.open_project_validation_window)        
        self.actUnityAssetManager.triggered.connect(self.open_unity_asset_manager_window)

        self.table.model.inclusion_updated.connect(self._on_wwise_inclusion_cell_changed)

    # 连接批处理器到操作（processor 签名为 (index, obj)，与 batch_processor.create_async 一致）
    def setup_batch_processor(self, action, obj_func: Callable):
        def proc(index, obj):
            obj_func(index, obj)
            return True

        action.triggered.connect(
            lambda: batch_processor.create_async(
                [row_data.wwise_object for row_data in self.table.active_data],
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
                Logger().debug(f"Wwise已成功连接到{project_path}")
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
        gv.active_objects = waapi_utils.get_selected_objects()
        self.reset_filter(False)
        self.table.refresh_table(True)
        self.apply_table_filter()
        self._object_history_reset_with_current()

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
        gv.active_objects = []
        self.table.refresh_table(True)

    # 筛选表格内容
    def apply_table_filter(self, record_history: bool = False):
        self.table.filter_results(self.ledFilterKeyword.text(), self.cbxCaseSensitive.isChecked())
        type_text = self.cbbFilterType.currentText()
        if not type_text or type_text == "全部类型":
            self.table.filter_by_type(None)
        else:
            self.table.filter_by_type(WwiseObjectType(type_text))
        self.table.filter_inclusion_only(self.cbxOnlyIncludedEnabled.isChecked())
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

    # 获取当前筛选后仍可见的 Wwise 对象
    def get_visible_objects(self) -> list[WwiseObject]:
        return [row_data.wwise_object for row_data in self.table.active_data]

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

    # 按工程当前参考语言筛选对象
    def filter_by_active_language(self):
        active_language = localization_utils.get_current_language()
        gv.active_objects = [
            obj
            for obj in self.get_visible_objects()
            if localization_utils.get_sound_language(obj) == active_language
        ]
        self.show_obj_list()

    # 按是否被 Event 引用筛选对象
    def filter_by_event_reference(self, with_ref: bool):
        gv.active_objects = [
            obj
            for obj in self.get_visible_objects()
            if (with_ref and event_utils.has_event_reference(obj))
            or (not with_ref and not event_utils.has_event_reference(obj))
        ]
        self.show_obj_list()

    # 复制对象的路径
    def copy_object_path(self, item: QTableWidgetItem):
        if item.column() != PATH_COL:
            item = self.tblWwiseObjects.item(item.row(), PATH_COL)
        clipboard.copy(item.text())

    # 在Wwise中选中列表中双击的对象
    def show_object_in_wwise(self, item: QTableWidgetItem):
        if item.column() != PATH_COL:
            item = self.tblWwiseObjects.item(item.row(), PATH_COL)
        obj = waapi_utils.find_object_by_path(item.text())
        if obj:
            waapi_utils.select_objects_in_wwise([obj])

    # 导出对象列表
    def export_object_list(self):
        io_utils.export_to_json(self.get_visible_objects(), 'WAAPI_Tools_Objects')

    # 导入对象列表
    def import_object_list(self):
        gv.active_objects = io_utils.import_from_json()
        self.show_obj_list()

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
        trim_window = AudioSilenceTrimWindow(self.get_visible_objects())
        trim_window.show()
        trim_window.exec()

    # 计算列表中Bank的总大小
    def calculate_bank_total_size(self):
        visible_objects = self.get_visible_objects()
        wav_size, memory_wem_size, stream_wem_size, used_files = soundbank_utils.get_total_bank_size(
            visible_objects
        )
        total_wem_size = memory_wem_size + stream_wem_size
        text = (f'共统计{len(visible_objects)}个Bank\n共包含{len(used_files)}个音频文件\n原始wav大小: {wav_size}MB'
                f'\n压缩后的wem: {total_wem_size}MB\n内存加载的wem: {memory_wem_size}MB\n流式加载的wem: {stream_wem_size}MB')
        Logger().info(f'统计完毕，{text}')

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

    # 打开Unity资产管理器窗口
    @staticmethod
    def open_unity_asset_manager_window():
        asset_manager = UnityAssetManager()
        asset_manager.show()
        asset_manager.exec()

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
        # 停止所有正在运行的批处理线程
        if gv.batch_processor and hasattr(gv.batch_processor, "isRunning"):
            gv.batch_processor.stop()
            if gv.batch_processor.isRunning():
                gv.batch_processor.wait(3000)  # 等待最多3秒
        # 关闭进度条窗口
        if gv.progress_bar:
            gv.progress_bar.close()
        # 断开P4连接
        try:
            client = P4Client()
            if client.is_connected:
                client.disconnect()
        except Exception as e:
            Logger().error(f"断开P4连接时出错: {e}")
        # 关闭WAAPI连接
        try:
            waapi_utils.close_client()
        except Exception as e:
            Logger().error(f"关闭WAAPI连接时出错: {e}")
        Logger().debug("应用程序已关闭")
        event.accept()
