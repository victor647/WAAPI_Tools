from windows.base_analysis_dialog import BaseAnalysisDialog
import re
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QTableWidgetItem, QCheckBox, QGroupBox

from data import project_conventions
from libraries.table_view.table_cell_data import CellSeverity
from libraries.table_view.table_context_menu import install_row_object_context
from libraries.table_view.table_path_item import create_path_item
from libraries.table_view.table_severity_delegate import SeverityTableDelegate
from libraries.utils import audio_utils, user_config
from libraries.utils.qt_utils import resize_table_and_window
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import common_utils, audio_source_utils, soundbank_utils, localization_utils, event_utils, \
    container_utils, waapi_utils, mixing_utils, wwise_compat
from libraries.wwise_object import WwiseObjectType, WwiseObject
from ui.ProjectValidation_ui import Ui_ProjectValidation
from libraries.multi_thread import batch_processor


# 对象可用属性/引用名缓存（按对象类型）：同一类型返回的列表一致，避免对每个对象各查一次
_AVAILABLE_NAMES_CACHE: dict[str, set] = {}

# 检查结果表的路径列（第 0 列固定为「选中」）
PATH_COL = 4


def _available_names(obj: WwiseObject) -> set:
    type_name = obj.type.name
    names = _AVAILABLE_NAMES_CACHE.get(type_name)
    if names is None:
        names = set(waapi_utils.get_property_and_reference_names(obj))
        _AVAILABLE_NAMES_CACHE[type_name] = names
    return names


# Wwise工程检查工具
class ProjectValidation(BaseAnalysisDialog, Ui_ProjectValidation):

    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.analysis_table = self.setup_analysis_table(
            self.tblValidationResults, ['类别', '问题', '类型', '路径']
        )
        self.load_check_states()
        # 规范开关关闭时对应检查项取消勾选并置灰
        if not project_conventions.is_color_enabled():
            self.cbxColorTypeMismatch.setChecked(False)
            self.cbxColorTypeMismatch.setEnabled(False)
        if not project_conventions.is_name_case_enabled():
            self.cbxWrongCase.setChecked(False)
            self.cbxWrongCase.setEnabled(False)
        if not project_conventions.is_path_length_enabled():
            self.cbxWrongNameLength.setChecked(False)
            self.cbxWrongNameLength.setEnabled(False)
        # 「引用备注/颜色标记」依赖深色标记或互为备注开关，两者都关闭时不可用
        if not (project_conventions.use_dark_color_for_event_ref()
                or project_conventions.use_event_ref_notes()):
            self.cbxNoRefNotesOrColorTag.setChecked(False)
            self.cbxNoRefNotesOrColorTag.setEnabled(False)
        self.setup_triggers()
        self.tblValidationResults.setItemDelegate(SeverityTableDelegate(self.tblValidationResults))
        self.__mainWindow = main_window
        self.__builtInRTPCs = []
        self.__validationPropertiesById = {}
        self.__validationInclusionCache = {}
        self.__pendingProblems = []
        self.__pendingWritten = 0
        self.problematicObjects = []

    def setup_triggers(self):
        self.btnSelectAll.clicked.connect(lambda: self.select_all(True))
        self.btnDeselectAll.clicked.connect(lambda: self.select_all(False))
        self.btnSaveChecks.clicked.connect(self.save_check_states)
        self.btnValidateEntireProject.clicked.connect(self.validate_entire_project)
        self.btnValidateListEntries.clicked.connect(self.validate_checked_objects)
        self.btnValidateProjectSelection.clicked.connect(lambda: self.validate_objects(
            waapi_utils.get_selected_objects()))
        self.btnSendResultToMainWindow.clicked.connect(self.send_results_back)
        self.btnAutoFixSelection.clicked.connect(self.auto_fix_selection)
        install_row_object_context(
            self.tblValidationResults,
            self.objects_at_row,
            path_columns=(PATH_COL,),
            extra_actions=self.add_result_extra_actions,
            default_action="select",
        )
        self.tblValidationResults.setColumnWidth(PATH_COL, 600)

    # 收集所有检查项的开关状态 {objectName: checked}
    def _check_states(self) -> dict:
        return {
            checkbox.objectName(): checkbox.isChecked()
            for checkbox in self.findChildren(QCheckBox)
        }

    # 保存检查项开关到 user_config（以本窗口为节点）
    def save_check_states(self):
        user_config.set_window_settings('project_validation', self._check_states())
        Logger().info('检查项设置已保存')

    # 打开窗口时恢复上次保存的检查项
    def load_check_states(self):
        saved = user_config.get_window_settings('project_validation')
        if not saved:
            return
        for checkbox in self.findChildren(QCheckBox):
            if checkbox.objectName() in saved:
                checkbox.setChecked(bool(saved[checkbox.objectName()]))

    # 每次运行前重置数据
    def reset_data(self):
        self.__builtInRTPCs = []
        self.__validationPropertiesById = {}
        self.__validationInclusionCache = {}
        self.__pendingProblems = []
        self.__pendingWritten = 0
        self.problematicObjects = []
        _AVAILABLE_NAMES_CACHE.clear()
        self.tblValidationResults.setRowCount(0)

    # 全选或全不选检查条目
    def select_all(self, select: bool):
        for widget in self.children():
            if isinstance(widget, QGroupBox):
                widget.setChecked(select)
                for child in widget.children():
                    if isinstance(child, QCheckBox):
                        child.setChecked(select)

    def objects_at_row(self, row: int) -> list:
        return [self.problematicObjects[row]] if 0 <= row < len(self.problematicObjects) else []

    def add_result_extra_actions(self, menu, item, payload):
        problem_item = self.tblValidationResults.item(item.row(), 2)
        if problem_item is not None:
            menu.addAction('自动修复', lambda: self.auto_fix(problem_item))

    # 将检查结果发送到主窗口
    def send_results_back(self):
        results = [
            self.problematicObjects[row]
            for row in self.analysis_table.selected_rows()
            if 0 <= row < len(self.problematicObjects)
        ]
        if not results:
            self.warn_no_selected_rows(title='工程检查', detail='请先在结果表「选中」列勾选要发送的对象。')
            return
        self.__mainWindow.activeObjects = results
        self.__mainWindow.show_obj_list()

    # 开始一键修复列表选中内容
    def auto_fix_selection(self):
        items = [
            self.tblValidationResults.item(row, 2)
            for row in self.analysis_table.selected_rows()
        ]
        items = [item for item in items if item is not None]
        if not items:
            self.warn_no_selected_rows(title='工程检查', detail='请先在结果表「选中」列勾选要修复的对象。')
            return
        batch_processor.create_async(
            items,
            lambda index, item: self.auto_fix(item),
            '自动修复工程',
        )

    # 自动修复列表选中内容
    def auto_fix(self, item: QTableWidgetItem):
        index = item.row()
        problem_item = self.tblValidationResults.item(index, 2)
        # 已经修复的跳过
        if problem_item.data(Qt.ItemDataRole.BackgroundRole) != CellSeverity.Danger:
            return
        problem_type = problem_item.text()
        fixed = False
        obj = self.problematicObjects[index]
        # ProjectStandards
        if problem_type == self.cbxWrongCase.text():
            fixed = rename_to_name_case(obj)
        elif problem_type == self.cbxWrongNameLength.text():
            fixed = common_utils.optimize_name_length(obj)
        elif problem_type == self.cbxColorTypeMismatch.text():
            fixed = common_utils.set_object_color_by_category(obj, True)
        elif problem_type == self.cbxNoRefNotesOrColorTag.text():
            fixed = common_utils.update_notes_and_color(obj)
        # DesignStructure
        elif problem_type == self.cbxNestedWorkUnit.text():
            fixed = fix_nested_work_unit(obj)
        elif problem_type == self.cbxRedundantActorMixer.text():
            fixed = common_utils.convert_to_type(obj, WwiseObjectType.Folder)
        elif problem_type == self.cbxSingleChildContainer.text():
            fixed = container_utils.break_container(obj)
        elif problem_type == self.cbxEmptyNode.text():
            fixed = waapi_utils.delete_object(obj)
        elif problem_type == self.cbxDuplicatedParameter.text():
            fixed = remove_duplicated_rtpc(obj)
        # SoundLocalization
        elif problem_type == self.cbxSourceNameDifferent.text():
            fixed = audio_source_utils.rename_original_to_wwise(obj)
        elif problem_type == self.cbxSourceNotImported.text():
            fixed = False
        elif problem_type == self.cbxSilentPlaceholder.text():
            fixed = False
        elif problem_type == self.cbxInvalidTrimRange.text():
            fixed = waapi_utils.set_object_property(obj, 'TrimEnd', -1)
        elif problem_type == self.cbxSoundNotInEvent.text():
            fixed = event_utils.create_play_event(obj)
        # EventBank
        elif problem_type == self.cbxWrongEventName.text():
            fixed = event_utils.rename_event_by_target(obj)
        elif problem_type == self.cbxEventDuplicatedByNetRole.text():
            fixed = remove_unnecessary_event(obj)
        elif problem_type == self.cbxEmptyEvent.text():
            fixed = waapi_utils.delete_object(obj)
        elif problem_type == self.cbxEventNotInBank.text():
            fixed = False
        elif problem_type == self.cbxAbnormalBankSize.text():
            fixed = False
        # Mistakes
        elif problem_type == self.cbxUnassignedToBus.text():
            fixed = mixing_utils.auto_assign_bus_by_category(obj)
        elif problem_type == self.cbxUnassignedSwitchContainer.text():
            fixed = container_utils.auto_assign_switch_mappings(obj)
        elif problem_type == self.cbxSwitchTo1PByDefault.text():
            fixed = container_utils.set_default_switch_to_3p(obj)
        elif problem_type == self.cbxMissingAttenuation.text():
            fixed = False
        elif problem_type == self.cbxSoundNotStreamed.text():
            fixed = waapi_utils.set_object_property(obj, 'IsStreamingEnabled', True)
        problem_item.setData(
            Qt.ItemDataRole.BackgroundRole,
            CellSeverity.Success if fixed else CellSeverity.Warning,
        )
        return fixed

    # 检查整个Wwise工程
    def validate_entire_project(self):
        self.reset_data()
        global_objects = waapi_utils.get_global_objects()
        self._start_validation(global_objects)

    # 检查对象列表及其所有子对象
    def validate_objects(self, objects):
        self.reset_data()
        all_objects = []
        for obj in objects:
            all_objects.append(obj)
            descendants = waapi_utils.get_child_objects(obj, True)
            for descendant in descendants:
                if descendant.name != '':
                    all_objects.append(descendant)
        self._start_validation(all_objects)

    # 只检查主窗口「选中」列已勾选的对象，未勾选行的子树跳过
    def validate_checked_objects(self):
        objects = self.collect_analysis_targets(expand=True)
        if not objects:
            self.warn_no_analysis_targets(title='工程检查')
            return
        self.reset_data()
        self._start_validation(objects)

    def _start_validation(self, objects: list[WwiseObject]):
        self.__validationObjects = objects
        self.__validationRequests = self._validation_property_requests()
        batch_processor.create_async(
            objects,
            self._validate_object_with_prefetch,
            '工程检查',
            on_finished=self.on_validate_finished,
            on_item_processed=self._on_validation_progress,
            progress_text_func=lambda index, obj: f"已找到 {len(self.__pendingProblems)} 条",
        )

    def _validation_property_requests(self) -> dict[str, list[str]]:
        requests = {}
        if self.grpDesignStructure.isChecked():
            if self.cbxNestedWorkUnit.isEnabled() and self.cbxNestedWorkUnit.isChecked():
                requests[WwiseObjectType.WorkUnit.value] = ['workUnitType']
            if self.cbxDuplicatedParameter.isEnabled() and self.cbxDuplicatedParameter.isChecked():
                requests[WwiseObjectType.RTPC.value] = ['BindToBuiltInParam']
        if self.grpSoundLocalization.isChecked():
            audio_source_properties = []
            if self.cbxSilentPlaceholder.isEnabled() and self.cbxSilentPlaceholder.isChecked():
                requests['SourcePlugin'] = ['classId']
                audio_source_properties.append('originalFilePath')
            if self.cbxInvalidTrimRange.isEnabled() and self.cbxInvalidTrimRange.isChecked():
                audio_source_properties.extend(['TrimEnd', 'playbackDuration'])
            if audio_source_properties:
                requests[WwiseObjectType.AudioSource.value] = list(dict.fromkeys(audio_source_properties))
        if self.grpMistakes.isChecked() and self.cbxSoundNotStreamed.isEnabled() and \
                self.cbxSoundNotStreamed.isChecked():
            requests[WwiseObjectType.Sound.value] = ['IsStreamingEnabled']
            requests[WwiseObjectType.MusicTrack.value] = ['IsStreamingEnabled']
        return requests

    def _validate_object_with_prefetch(self, index: int, obj: WwiseObject):
        if index == 0:
            self.__validationPropertiesById = {}
            unique_objects = {
                item.id: item for item in self.__validationObjects if item.id
            }
            property_sets = [
                waapi_utils.get_objects_properties(list(unique_objects.values()), ['Inclusion'])
            ]
            objects_by_type = {}
            for item in self.__validationObjects:
                object_type = (item.wwise_dict or {}).get('type')
                if object_type in self.__validationRequests and item.id:
                    objects_by_type.setdefault(object_type, {})[item.id] = item
            for object_type, property_names in self.__validationRequests.items():
                candidates = list(objects_by_type.get(object_type, {}).values())
                property_sets.append(waapi_utils.get_objects_properties(candidates, property_names))
            for property_set in property_sets:
                for object_id, properties in property_set.items():
                    self.__validationPropertiesById.setdefault(object_id, {}).update(properties)
        return self.validate_object(obj)

    # 批处理每完成一条：把工作线程新收集的问题边查边插入表格（主线程回调）
    def _on_validation_progress(self, payload):
        _index, _obj = payload
        self._flush_pending_problems()

    # 把工作线程已收集、尚未写入的问题行插入表格（仅在主线程调用）
    def _flush_pending_problems(self):
        for obj, category, rule in self.__pendingProblems[self.__pendingWritten:]:
            self.record_problematic_object(obj, category, rule)
        self.__pendingWritten = len(self.__pendingProblems)

    # 将检查结果写入json文件
    def on_validate_finished(self):
        # 收尾：补写剩余问题行并清理收集缓存
        self._flush_pending_problems()
        self.__pendingProblems = []
        resize_table_and_window(self.tblValidationResults, self)
        problem_count = len(self.problematicObjects)
        if problem_count == 0:
            text = '在工程中未发现任何问题！'
        else:
            text = f'共发现{problem_count}处不符合工程规范！'
        Logger().info(f'检查完毕{text}')

    # 检查单个对象
    def validate_object(self, obj: WwiseObject):
        if not common_utils.is_object_included(
            obj,
            inclusion_cache=self.__validationInclusionCache,
            property_values_by_id=self.__validationPropertiesById,
        ):
            return
        obj_type = obj.type
        if obj_type == WwiseObjectType.EventAction:
            return

        if self.grpProjectStandards.isChecked():
            title = self.grpProjectStandards.title()
            if project_conventions.is_name_case_enabled():
                self.check_object_by_rule(obj, self.cbxWrongCase, is_wrong_name_case, title)
            if project_conventions.is_path_length_enabled():
                self.check_object_by_rule(obj, self.cbxWrongNameLength, violates_naming_length, title)
            if project_conventions.is_color_enabled():
                self.check_object_by_rule(obj, self.cbxColorTypeMismatch, color_mismatch_category, title)
            self.check_object_by_rule(obj, self.cbxNoRefNotesOrColorTag, wrong_reference_notes_or_color, title)

        if self.grpDesignStructure.isChecked():
            title = self.grpDesignStructure.title()
            self.check_object_by_rule(
                obj,
                self.cbxNestedWorkUnit,
                lambda item: is_work_unit_nested(item, self.__validationPropertiesById.get(item.id)),
                title,
            )
            self.check_object_by_rule(obj, self.cbxRedundantActorMixer, is_actor_mixer_redundant, title)
            self.check_object_by_rule(obj, self.cbxSingleChildContainer, container_has_single_child, title)
            self.check_object_by_rule(obj, self.cbxEmptyNode, is_node_empty, title)
            self.check_object_by_rule(obj, self.cbxDuplicatedParameter, self.is_duplicated_parameter, title)

        if self.grpSoundLocalization.isChecked():
            title = self.grpSoundLocalization.title()
            self.check_object_by_rule(obj, self.cbxSourceNameDifferent, file_path_different_from_sound, title)
            self.check_object_by_rule(obj, self.cbxSourceNotImported, sound_missing_or_not_localized, title)
            self.check_object_by_rule(
                obj,
                self.cbxSilentPlaceholder,
                lambda item: is_audio_source_silent(item, self.__validationPropertiesById.get(item.id)),
                title,
            )
            self.check_object_by_rule(obj, self.cbxSoundNotInEvent, sound_not_in_any_events, title)
            self.check_object_by_rule(
                obj,
                self.cbxInvalidTrimRange,
                lambda item: audio_trim_out_of_range(item, self.__validationPropertiesById.get(item.id)),
                title,
            )

        if self.grpEventBank.isChecked():
            title = self.grpEventBank.title()
            self.check_object_by_rule(obj, self.cbxWrongEventName, event_has_wrong_name, title)
            self.check_object_by_rule(obj, self.cbxEventDuplicatedByNetRole, event_has_net_role_naming, title)
            self.check_object_by_rule(obj, self.cbxEmptyEvent, is_event_empty, title)
            self.check_object_by_rule(obj, self.cbxEventNotInBank, event_not_included_in_any_banks, title)
            self.check_object_by_rule(obj, self.cbxAbnormalBankSize, is_bank_size_abnormal, title)

        if self.grpMistakes.isChecked():
            title = self.grpMistakes.title()
            self.check_object_by_rule(obj, self.cbxUnassignedToBus, is_bus_unassigned, title)
            self.check_object_by_rule(obj, self.cbxUnassignedSwitchContainer, is_switch_container_unassigned, title)
            self.check_object_by_rule(obj, self.cbxSwitchTo1PByDefault, switch_to_1p_by_default, title)
            self.check_object_by_rule(obj, self.cbxMissingAttenuation, object_missing_attenuation, title)
            self.check_object_by_rule(
                obj,
                self.cbxSoundNotStreamed,
                lambda item: sound_not_streamed(item, self.__validationPropertiesById.get(item.id)),
                title,
            )

    # 检查项目通用接口：置灰（不可用）的检查项一律跳过
    def check_object_by_rule(self, obj: WwiseObject, check_box: QCheckBox, check_function, category: str):
        if check_box.isEnabled() and check_box.isChecked() and check_function(obj):
            self.__pendingProblems.append((obj, category, check_box.text()))

    # 记录不符合规范的对象
    def record_problematic_object(self, obj: WwiseObject, category: str, rule: str):
        row_count = self.tblValidationResults.rowCount()
        # 修复是破坏性操作，结果行默认不勾选，由用户明确选择
        self.analysis_table.prepare_row(row_count, checked=False)
        rule_item = QTableWidgetItem(rule)
        rule_item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Danger)
        self.tblValidationResults.setItem(row_count, 1, QTableWidgetItem(category))
        self.tblValidationResults.setItem(row_count, 2, rule_item)
        self.tblValidationResults.setItem(row_count, 3, QTableWidgetItem(obj.type.name))
        self.tblValidationResults.setItem(row_count, PATH_COL, create_path_item(obj.path))
        self.problematicObjects.append(obj)

    # 检查是否存在重复绑定的RTPC
    def is_duplicated_parameter(self, parameter: WwiseObject):
        if parameter.type != WwiseObjectType.RTPC:
            return False
        properties = self.__validationPropertiesById.get(parameter.id)
        built_in = (
            properties.get('BindToBuiltInParam')
            if properties is not None and 'BindToBuiltInParam' in properties
            else waapi_utils.get_object_property(parameter, 'BindToBuiltInParam')
        )
        if not built_in:
            return False
        if built_in in self.__builtInRTPCs:
            return True
        self.__builtInRTPCs.append(built_in)
        return False


# 删除重复绑定的RTPC
def remove_duplicated_rtpc(obj: WwiseObject):
    # todo - reassign reference to existing rtpc
    obj_name = obj.name
    print(f'已删除重复绑定的RTPC[{obj_name}]')
    return waapi_utils.delete_object(obj)


# 删除非必要的Event
def remove_unnecessary_event(event: WwiseObject):
    event_name = event.name
    # 1P/3P后缀事件转换为播放上层SwitchContainer内容
    suffix = project_conventions.get_net_role_suffix_from_name(event_name)
    if suffix:
        new_event_name = event_name[:-len(suffix)]
        existing_event = waapi_utils.find_object_by_name_and_type(new_event_name, WwiseObjectType.Event)
        if existing_event:
            return True
        waapi_utils.rename_object(event, new_event_name)
        actions = waapi_utils.get_child_objects(event)
        for action in actions:
            target = waapi_utils.get_referenced_object(action, 'Target')
            if target and target.name.endswith(suffix):
                target_parent = waapi_utils.get_parent_object(target)
                if target_parent.type == WwiseObjectType.SwitchContainer:
                    return event_utils.set_action_target(action, target_parent)
    # Stop类型事件直接删除
    else:
        return waapi_utils.delete_object(event)


# 将嵌套的WorkUnit改为Folder类型
def fix_nested_work_unit(work_unit: WwiseObject):
    if len(work_unit.path.split('\\')) > 3:
        return common_utils.convert_to_type(work_unit, WwiseObjectType.Folder)
    return False


# region ProjectStandards
# 取出参与大小写检查的名称分段；返回 None 表示该对象不参与检查
def name_case_words(obj: WwiseObject):
    obj_type = obj.type
    obj_path = obj.path
    if 'Factory' in obj_path:
        return None
    if obj_type == WwiseObjectType.EventAction:
        return None
    # 过滤根目录和MIDI对象
    if obj_type == WwiseObjectType.WorkUnit and len(obj_path.split('\\')) == 2:
        return None
    obj_name = obj.name
    if obj_type == WwiseObjectType.Folder and (obj_path.startswith('MIDI')):
        return None

    words = obj_name.split('_')
    if len(words) == 1:
        words = obj_name.split(' ')
    return words


# 检查对象名是否符合设置里选择的大小写方式（首字母大写/全小写/全大写）
def is_wrong_name_case(obj: WwiseObject):
    words = name_case_words(obj)
    if words is None:
        return False
    mode = project_conventions.get_name_case_mode()
    for word in words:
        if len(word) <= 1:
            continue
        if mode == 'lower':
            pattern = r'^[a-z\d]+$'
        elif mode == 'upper':
            pattern = r'^[A-Z\d]+$'
        else:
            pattern = r'^[A-Z\d][a-zA-Z\d]*$'
        if not re.match(pattern, word):
            return True
    return False


# 按设置的大小写方式重命名对象，用于自动修复「不符合大小写规范」
def rename_to_name_case(obj: WwiseObject) -> bool:
    words = name_case_words(obj)
    if words is None:
        return False
    mode = project_conventions.get_name_case_mode()
    split_char = '_' if '_' in obj.name else ' '
    fixed_words = []
    for word in words:
        if mode == 'lower':
            fixed_words.append(word.lower())
        elif mode == 'upper':
            fixed_words.append(word.upper())
        elif len(word) <= 1:
            fixed_words.append(word)
        else:
            fixed_words.append(word[0].upper() + word[1:])
    new_name = split_char.join(fixed_words)
    if new_name == obj.name:
        return False
    return waapi_utils.rename_object(obj, new_name)


# 检查对象是否命名长度不符合要求
def violates_naming_length(obj: WwiseObject):
    obj_path = obj.path
    if wwise_compat.is_music_object(obj):
        if obj.type in (WwiseObjectType.MusicSegment, WwiseObjectType.MusicTrack):
            return False
        return '_' in obj.name
    if wwise_compat.is_containers_path(obj_path):
        if obj.type == WwiseObjectType.AudioSource:
            return False
        if obj.type == WwiseObjectType.Sound:
            if audio_source_utils.sound_play_from_plugin(obj):
                return False
            return '_' not in obj.name
        return '_' in obj.name
    return False


# 检查对象的颜色是否符合类型规范
def color_mismatch_category(obj: WwiseObject):
    if obj.type == WwiseObjectType.AudioSource:
        return False
    category = project_conventions.get_object_category(obj)
    if not category:
        return False
    obj_color = common_utils.get_object_color(obj)
    color = project_conventions.get_color_by_category(category)
    if color == obj_color or color == obj_color + 13:
        return False
    print(f"Color of {obj.type} [{obj.name}] is {obj_color}, should be {color}")
    return True


# 检查对象是否缺少引用的备注与颜色标记
def wrong_reference_notes_or_color(obj: WwiseObject):
    # 备注与深色标记各自受设置开关控制，关闭的那部分不参与检查
    use_notes = project_conventions.use_event_ref_notes()
    use_dark_color = project_conventions.use_dark_color_for_event_ref()
    obj_type = obj.type
    # 对象是Event且播放别的对象
    if obj.type == WwiseObjectType.Event:
        targets = event_utils.get_event_targets(obj)
        if len(targets) == 1:
            target = targets[0]
            if 'Bus' in target.type.value:
                return False
            references = waapi_utils.get_object_references(target)
            # 对象被唯一事件引用时才检查备注
            if use_notes and len(references) == 1:
                notes = common_utils.get_object_notes(obj)
                if notes != target.path:
                    return True
            return use_dark_color and not has_dark_color_tag(target)
    else:
        references = waapi_utils.get_object_references(obj)
        action_references = [
            reference for reference in references
            if reference.type == WwiseObjectType.EventAction
        ]
        action_properties = waapi_utils.get_objects_properties(action_references, ['ActionType'])
        notes = common_utils.get_object_notes(obj) if use_notes else ''
        obj_path = obj.path
        # 对象被SoundBank引用
        if obj_type == WwiseObjectType.Folder or obj_type == WwiseObjectType.WorkUnit:
            if obj_path.startswith('\\Events'):
                for reference in references:
                    if reference.type == WwiseObjectType.SoundBank:
                        if use_notes and notes != f"Included by SoundBank [{reference.name}]":
                            return True
                        return use_dark_color and not has_dark_color_tag(obj)
        # 对象被Event引用
        elif 'Hierarchy' in obj_path:
            for reference in references:
                if reference.type == WwiseObjectType.EventAction:
                    action_type = action_properties.get(reference.id, {}).get('ActionType')
                    if action_type == 1:
                        event = waapi_utils.get_parent_object(reference)
                        if use_notes and notes != f"Played by Event [{event.name}]":
                            return True
                    return use_dark_color and not has_dark_color_tag(obj)
    return False


# 对象是否因为引用设置了特殊颜色
def has_dark_color_tag(obj: WwiseObject):
    properties = waapi_utils.get_object_properties(obj, ['OverrideColor', 'Color'])
    if not properties.get('OverrideColor'):
        return False
    color = properties.get('Color')
    parent = waapi_utils.get_parent_object(obj)
    if not parent:
        return False
    parent_color = common_utils.get_object_color(parent)
    return parent_color - color == 13
# endregion ProjectStandards


# region DesignStructure
# 检查WorkUnit是否只包含子级WorkUnit
def is_work_unit_nested(work_unit: WwiseObject, properties: dict = None):
    if work_unit.type != WwiseObjectType.WorkUnit:
        return False
    # 物理文件夹会只有一个路径，故跳过
    path_splits = work_unit.path.split('\\')
    if len(path_splits) <= 2:
        return False
    work_unit_type = properties.get('workUnitType') if properties and 'workUnitType' in properties \
        else waapi_utils.get_object_property(work_unit, 'workUnitType')
    if work_unit_type == WwiseObjectType.Folder:
        return False
    children = waapi_utils.get_child_objects(work_unit)
    # 空的占位WorkUnit可以接受
    if len(children) == 0:
        return False
    for child in children:
        if child.type != WwiseObjectType.WorkUnit:
            return False
    return work_unit.name != 'Default Work Unit'


# 检查ActorMixer是否包含有效信息
def is_actor_mixer_redundant(actor_mixer: WwiseObject):
    if not wwise_compat.is_property_container(actor_mixer):
        return False
    parent = waapi_utils.get_parent_object(actor_mixer)
    if parent.type == WwiseObjectType.WorkUnit:
        return False
    names = _available_names(actor_mixer)
    effects_name = next((name for name in ('Effects', '@Effects', 'Effect') if name in names), None)
    rtpcs_name = next((name for name in ('RTPC', '@RTPC') if name in names), None)
    property_names = [name for name in (effects_name, rtpcs_name) if name]
    properties = waapi_utils.get_object_properties(actor_mixer, property_names)
    effects = properties.get(effects_name) if effects_name else None
    rtpcs = properties.get(rtpcs_name) if rtpcs_name else None
    if effects or rtpcs:
        return False
    return not mixing_utils.has_fader_edits(actor_mixer)


# 检查是否存在不包含或仅包含一个子节点的Container
def container_has_single_child(container: WwiseObject):
    if not container.is_container:
        return False
    # 音乐容器可以只包含一首
    if container.type == 'MusicPlaylistContainer':
        return False
    children = waapi_utils.get_child_objects(container)
    return len(children) == 1


# 检查对象是否不包含子对象
def is_node_empty(obj: WwiseObject):
    obj_path = obj.path
    if not wwise_compat.is_containers_path(obj_path):
        return False
    obj_type = obj.type
    if obj.type == WwiseObjectType.Sound or obj.type == WwiseObjectType.AudioSource:
        return False
    if obj.name == 'Default Work Unit':
        return False
    children = waapi_utils.get_child_objects(obj)
    return len(children) == 0
# endregion DesignStructure


# region SoundLocalization
# 检查源文件是否与Sound命名一致
def file_path_different_from_sound(sound: WwiseObject):
    if sound.type != WwiseObjectType.Sound:
        return False
    sound_name = sound.name
    suffix = project_conventions.get_net_role_suffix_from_name(sound_name)
    audio_sources = [
        child for child in waapi_utils.get_child_objects(sound)
        if child.type == WwiseObjectType.AudioSource
    ]
    properties_by_id = waapi_utils.get_objects_properties(audio_sources, ['originalFilePath'])
    for audio_source in audio_sources:
        source_path = audio_source_utils.get_source_absolute_path(
            audio_source, properties_by_id.get(audio_source.id, {})
        )
        if source_path:
            source_name = os.path.basename(source_path)[:-4]
            if sound_name != source_name:
                if not suffix:
                    return True
                # 带有身份结尾的特殊情况
                elif sound_name[:-len(suffix)] != source_name:
                    return True
    return False


# 检测音效是否丢失或缺失中英文中的某个语言
def sound_missing_or_not_localized(sound: WwiseObject):
    if sound.type != WwiseObjectType.Sound:
        return False
    # 未接入语言不需要本地化；其余工程语言都需要存在对应语音
    unimplemented_languages = project_conventions.get_unimplemented_languages()
    implemented_languages = [
        language
        for language in localization_utils.get_all_language_names()
        if language not in unimplemented_languages
    ]
    if localization_utils.get_sound_language(sound) == 'SFX':
        path = audio_source_utils.get_source_absolute_path(sound)
        if not path:
            return not audio_source_utils.sound_play_from_plugin(sound)
        return not os.path.exists(path)
    else:
        children = waapi_utils.get_child_objects(sound)
        audio_sources = [child for child in children if child.type == WwiseObjectType.AudioSource]
        missing_languages = len(implemented_languages)
        source_properties = waapi_utils.get_objects_properties(
            audio_sources, ['audioSource:language'])
        for child in audio_sources:
            language = localization_utils.get_sound_language(
                child, source_properties.get(child.id, {})
            )
            if language in implemented_languages:
                missing_languages -= 1
        return missing_languages > 0


# 检查样本是否是静音替代资源
def is_audio_source_silent(source: WwiseObject, properties: dict = None):
    source_type = source.type
    if source_type != WwiseObjectType.AudioSource:
        # 检查Wwise Silence插件的情况
        if source_type == WwiseObjectType.SourcePlugin:
            class_id = properties.get('classId') if properties and 'classId' in properties \
                else waapi_utils.get_object_property(source, 'classId')
            return class_id == 6619138
        return False
    source_path = audio_source_utils.get_source_absolute_path(source, properties)
    silent = audio_utils.is_sound_completely_silent(source_path)
    if silent:
        return True


# 检查声音是否被事件所引用
def sound_not_in_any_events(sound: WwiseObject):
    if sound.type != WwiseObjectType.Sound:
        return False
    references = waapi_utils.get_object_references(sound)
    if len(references) == 0:
        parent = waapi_utils.get_parent_object(sound)
        if wwise_compat.is_property_container(parent) or parent.type == WwiseObjectType.WorkUnit:
            return True
        return sound_not_in_any_events(parent)
    return False


# 检查样本的裁剪末尾是否超出时长范围
def audio_trim_out_of_range(audio_source: WwiseObject, properties: dict = None):
    if audio_source.type != WwiseObjectType.AudioSource:
        return False
    if properties is None or not {'TrimEnd', 'playbackDuration'} <= properties.keys():
        missing_properties = [
            name for name in ('TrimEnd', 'playbackDuration')
            if properties is None or name not in properties
        ]
        properties = {
            **(properties or {}),
            **waapi_utils.get_object_properties(audio_source, missing_properties),
        }
    trim_end = properties.get('TrimEnd')
    if trim_end == -1:
        return False
    duration = properties.get('playbackDuration')
    if duration:
        return trim_end > duration['playbackDurationMax']
    return False
# endregion SoundLocalization


# region EventBank
# 检查事件是否正确命名
def event_has_wrong_name(event: WwiseObject):
    if event.type != WwiseObjectType.Event:
        return False
    event_name = event.name
    # 暂时跳过Stop的Event
    if event_name.startswith('Stop_'):
        return False
    targets = event_utils.get_event_targets(event)
    if len(targets) == 0:
        return False
    for target in targets:
        if 'Bus' in target.type.value:
            return False
        correct_name = event_utils.get_event_name(target)
        if correct_name == event_name:
            return False
    return True


# 检查是否存在1P/3P结尾
def event_has_net_role_naming(event: WwiseObject):
    if event.type != WwiseObjectType.Event:
        return False
    event_name = event.name
    suffix = project_conventions.get_net_role_suffix_from_name(event_name)
    return suffix is not None


# 检查事件是否不包含动作或目标
def is_event_empty(event: WwiseObject):
    if event.type != WwiseObjectType.Event:
        return False
    targets = event_utils.get_event_targets(event)
    return len(targets) == 0


# 检查事件是否被Bank所引用
def event_not_included_in_any_banks(event: WwiseObject):
    if event.type != WwiseObjectType.Event:
        return False
    parent = waapi_utils.get_parent_object(event)
    if not parent:
        return True
    references = waapi_utils.get_object_references(parent)
    for reference in references:
        if reference.type == WwiseObjectType.SoundBank:
            return False
    return event_not_included_in_any_banks(parent)


# 检查Bank大小是否在1-10MB之间
def is_bank_size_abnormal(bank: WwiseObject):
    if bank.type != WwiseObjectType.SoundBank:
        return False
    wav_size = memory_wem_size = stream_wem_size = 0
    used_files = []
    _, memory_wem_size, stream_wem_size, _ = soundbank_utils.get_bank_size(bank, wav_size, memory_wem_size, stream_wem_size, used_files)
    total_wem_size = memory_wem_size + stream_wem_size
    abnormal = total_wem_size < 1 or total_wem_size > 10
    if abnormal:
        bank_name = bank.name
        size_str = 'too small' if total_wem_size < 1 else 'too large'
        print(f'Bank [{bank_name}] has size of {total_wem_size}MB, {size_str}!')
    return abnormal
# endregion EventBank


# region Mistakes
# 检查是否分配了Bus
def is_bus_unassigned(obj: WwiseObject):
    names = _available_names(obj)
    if 'OutputBus' not in names:
        return False
    property_names = ['OutputBus']
    if 'OverrideOutput' in names:
        property_names.append('OverrideOutput')
    properties = waapi_utils.get_object_properties(obj, property_names)
    bus = mixing_utils.get_output_bus(obj, properties)
    if bus is None:
        return False
    is_master = bus.name == 'Master Audio Bus'
    override = properties.get('OverrideOutput', 0)
    if override:
        return is_master
    # 非override的对象需要检查是否上级已经检查过了
    parent = waapi_utils.get_parent_object(obj)
    if parent:
        parent_has_bus = (
            'OutputBus' in _available_names(parent)
            and mixing_utils.get_output_bus(parent)
        )
        if not parent_has_bus:
            return is_master
    return False


# 检查SwitchContainer是否未分配播放对象
def is_switch_container_unassigned(container: WwiseObject):
    if container.type != WwiseObjectType.SwitchContainer:
        return False
    mappings = waapi_utils.get_switch_mappings(container)
    if len(mappings) == 0:
        return True
    children = waapi_utils.get_child_objects(container)
    for child in children:
        found = False
        for mapping in mappings:
            if mapping['child'] == child.id:
                found = True
                break
        if not found:
            return True
    return False


# SwitchContainer默认播放1P声音
def switch_to_1p_by_default(container: WwiseObject):
    if container.type != WwiseObjectType.SwitchContainer:
        return False
    group = waapi_utils.get_referenced_object(container, 'SwitchGroupOrStateGroup')
    if group and group.name:
        default_switch = waapi_utils.get_referenced_object(container, 'DefaultSwitchOrState')
        return bool(default_switch and default_switch.name and '1P' in default_switch.name)
    return False


# 3D对象未设置衰减曲线
def object_missing_attenuation(obj: WwiseObject):
    if not wwise_compat.is_containers_path(obj.path) or wwise_compat.is_music_object(obj):
        return False
    names = _available_names(obj)
    property_names = []
    if 'OverridePositioning' in names:
        property_names.append('OverridePositioning')
    if '3DSpatialization' in names:
        property_names.append('3DSpatialization')
    properties = waapi_utils.get_object_properties(obj, property_names)
    override = properties.get('OverridePositioning', 0)
    if not override and not mixing_utils.is_mixing_root(obj):
        return False
    if '3DSpatialization' not in names:
        return False
    spatialization_mode = properties.get('3DSpatialization')
    if not spatialization_mode:
        return False
    if spatialization_mode == 0:
        return '_3P' in obj.name
    if 'Attenuation' not in names:
        return True
    attenuation = waapi_utils.get_referenced_object(obj, 'Attenuation')
    return not (attenuation and attenuation.name)


# 检查语音、环境声和音乐是否设为Streaming
def sound_not_streamed(obj: WwiseObject, properties: dict = None):
    obj_type = obj.type
    if obj_type == WwiseObjectType.MusicTrack or obj.type == WwiseObjectType.Sound:
        category = project_conventions.get_object_category(obj)
        if category == 'Ambience' or category == 'Voice' or category == 'Music':
            streaming = properties.get('IsStreamingEnabled') if properties and 'IsStreamingEnabled' in properties \
                else waapi_utils.get_object_property(obj, 'IsStreamingEnabled')
            return not streaming
    return False
# endregion Mistakes
