import re
import os

import clipboard
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QTableWidgetItem, QCheckBox, QGroupBox, QMenu

from data import project_conventions
from libraries.table_view.table_cell_data import CellSeverity
from libraries.table_view.table_severity_delegate import SeverityTableDelegate
from table.wwise_table_context_menu import add_common_object_actions
from libraries.utils import audio_utils
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import common_utils, audio_source_utils, soundbank_utils, localization_utils, event_utils, \
    container_utils, waapi_utils, mixing_utils
from libraries.wwise_object import WwiseObjectType, WwiseObject
from ui.ProjectValidation_ui import Ui_ProjectValidation
from libraries.multi_thread import batch_processor


# Wwise工程检查工具
class ProjectValidation(QDialog, Ui_ProjectValidation):

    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.setup_triggers()
        self.tblValidationResults.setItemDelegate(SeverityTableDelegate(self.tblValidationResults))
        self.__currentTitle = ''
        self.__mainWindow = main_window
        self.__builtInRTPCs = []
        self.problematicObjects = []

    def setup_triggers(self):
        self.btnSelectAll.clicked.connect(lambda: self.select_all(True))
        self.btnDeselectAll.clicked.connect(lambda: self.select_all(False))
        self.btnValidateEntireProject.clicked.connect(self.validate_entire_project)
        self.btnValidateListEntries.clicked.connect(
            lambda: self.validate_objects(self.__mainWindow.get_visible_objects())
        )
        self.btnValidateProjectSelection.clicked.connect(lambda: self.validate_objects(
            waapi_utils.get_selected_objects()))
        self.btnSendResultToMainWindow.clicked.connect(self.send_results_back)
        self.btnAutoFixSelection.clicked.connect(self.auto_fix_selection)
        self.tblValidationResults.customContextMenuRequested.connect(self.show_result_context_menu)

        # self.grpProjectStandards.toggled.connect(lambda toggled: ScriptingHelper.on_group_box_toggled(self.grpProjectStandards, toggled))
        # self.grpDesignStructure.toggled.connect(lambda toggled: ScriptingHelper.on_group_box_toggled(self.grpDesignStructure, toggled))
        # self.grpSoundLocalization.toggled.connect(lambda toggled: ScriptingHelper.on_group_box_toggled(self.grpSoundLocalization, toggled))
        # self.grpEventBank.toggled.connect(lambda toggled: ScriptingHelper.on_group_box_toggled(self.grpEventBank, toggled))
        # self.grpOthers.toggled.connect(lambda toggled: ScriptingHelper.on_group_box_toggled(self.grpOthers, toggled))

        self.tblValidationResults.itemDoubleClicked.connect(self.select_object_in_wwise)
        self.tblValidationResults.setColumnWidth(3, 600)

    # 每次运行前重置数据
    def reset_data(self):
        self.__builtInRTPCs = []
        self.problematicObjects = []
        self.tblValidationResults.setRowCount(0)

    # 全选或全不选检查条目
    def select_all(self, select: bool):
        for widget in self.children():
            if isinstance(widget, QGroupBox):
                widget.setChecked(select)
                for child in widget.children():
                    if isinstance(child, QCheckBox):
                        child.setChecked(select)

    # 在Wwise中选中对象
    def select_object_in_wwise(self, item: QTableWidgetItem):
        if waapi_utils.client is None:
            return
        if item.column() != 3:
            item = self.tblValidationResults.item(item.row(), 3)
        obj = waapi_utils.find_object_by_path(item.text())
        if obj:
            waapi_utils.select_objects_in_wwise([obj])

    # 结果表右键：通用对象动作 + 自动修复
    def show_result_context_menu(self, position):
        index = self.tblValidationResults.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        menu = QMenu(self)
        cell = self.tblValidationResults.item(row, index.column())
        if cell is not None and cell.text():
            menu.addAction('复制', lambda: clipboard.copy(cell.text()))
        if 0 <= row < len(self.problematicObjects):
            add_common_object_actions(menu, self.problematicObjects[row], self)
        problem_item = self.tblValidationResults.item(row, 1)
        if problem_item is not None:
            menu.addAction('自动修复', lambda: self.auto_fix(problem_item))
        menu.exec(self.tblValidationResults.viewport().mapToGlobal(position))

    # 将检查结果发送到主窗口
    def send_results_back(self):
        results = []
        items = self.tblValidationResults.selectedItems()
        for item in items:
            results.append(self.problematicObjects[item.row()])
        self.__mainWindow.activeObjects = results
        self.__mainWindow.show_obj_list()

    # 开始一键修复列表选中内容
    def auto_fix_selection(self):
        items = self.tblValidationResults.selectedItems()
        batch_processor.create_async(
            items,
            lambda index, item: self.auto_fix(item),
            '自动修复工程',
        )

    # 自动修复列表选中内容
    def auto_fix(self, item: QTableWidgetItem):
        index = item.row()
        problem_item = self.tblValidationResults.item(index, 1)
        # 已经修复的跳过
        if problem_item.data(Qt.ItemDataRole.BackgroundRole) != CellSeverity.Danger:
            return
        problem_type = problem_item.text()
        fixed = False
        obj = self.problematicObjects[index]
        # ProjectStandards
        if problem_type == self.cbxWrongCase.text():
            fixed = common_utils.rename_to_title_case(obj)
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
        batch_processor.create_async(
            global_objects,
            lambda index, obj: self.validate_object(obj),
            '工程检查',
            on_finished=self.on_validate_finished,
        )

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
        batch_processor.create_async(
            all_objects,
            lambda index, obj: self.validate_object(obj),
            '工程检查',
            on_finished=self.on_validate_finished,
        )

    # 将检查结果写入json文件
    def on_validate_finished(self):
        self.tblValidationResults.resizeColumnsToContents()
        problem_count = len(self.problematicObjects)
        if problem_count == 0:
            text = '在工程中未发现任何问题！'
        else:
            text = f'共发现{problem_count}处不符合工程规范！'
        Logger().info(f'检查完毕{text}')

    # 检查单个对象
    def validate_object(self, obj: WwiseObject):
        if not common_utils.is_object_included(obj):
            return
        obj_type = obj.type
        if obj_type == WwiseObjectType.EventAction:
            return

        if self.grpProjectStandards.isChecked():
            self.__currentTitle = self.grpProjectStandards.title()
            self.check_object_by_rule(obj, self.cbxWrongCase, is_not_camel_cased)
            self.check_object_by_rule(obj, self.cbxWrongNameLength, violates_naming_length)
            self.check_object_by_rule(obj, self.cbxColorTypeMismatch, color_mismatch_category)
            self.check_object_by_rule(obj, self.cbxNoRefNotesOrColorTag, wrong_reference_notes_or_color)

        if self.grpDesignStructure.isChecked():
            self.__currentTitle = self.grpDesignStructure.title()
            self.check_object_by_rule(obj, self.cbxNestedWorkUnit, is_work_unit_nested)
            self.check_object_by_rule(obj, self.cbxRedundantActorMixer, is_actor_mixer_redundant)
            self.check_object_by_rule(obj, self.cbxSingleChildContainer, container_has_single_child)
            self.check_object_by_rule(obj, self.cbxEmptyNode, is_node_empty)
            self.check_object_by_rule(obj, self.cbxDuplicatedParameter, self.is_duplicated_parameter)

        if self.grpSoundLocalization.isChecked():
            self.__currentTitle = self.grpSoundLocalization.title()
            self.check_object_by_rule(obj, self.cbxSourceNameDifferent, file_path_different_from_sound)
            self.check_object_by_rule(obj, self.cbxSourceNotImported, sound_missing_or_not_localized)
            self.check_object_by_rule(obj, self.cbxSilentPlaceholder, is_audio_source_silent)
            self.check_object_by_rule(obj, self.cbxSoundNotInEvent, sound_not_in_any_events)
            self.check_object_by_rule(obj, self.cbxInvalidTrimRange, audio_trim_out_of_range)

        if self.grpEventBank.isChecked():
            self.__currentTitle = self.grpEventBank.title()
            self.check_object_by_rule(obj, self.cbxWrongEventName, event_has_wrong_name)
            self.check_object_by_rule(obj, self.cbxEventDuplicatedByNetRole, event_has_net_role_naming)
            self.check_object_by_rule(obj, self.cbxEmptyEvent, is_event_empty)
            self.check_object_by_rule(obj, self.cbxEventNotInBank, event_not_included_in_any_banks)
            self.check_object_by_rule(obj, self.cbxAbnormalBankSize, is_bank_size_abnormal)

        if self.grpMistakes.isChecked():
            self.__currentTitle = self.grpMistakes.title()
            self.check_object_by_rule(obj, self.cbxUnassignedToBus, is_bus_unassigned)
            self.check_object_by_rule(obj, self.cbxUnassignedSwitchContainer, is_switch_container_unassigned)
            self.check_object_by_rule(obj, self.cbxSwitchTo1PByDefault, switch_to_1p_by_default)
            self.check_object_by_rule(obj, self.cbxMissingAttenuation, object_missing_attenuation)
            self.check_object_by_rule(obj, self.cbxSoundNotStreamed, sound_not_streamed)

    # 检查项目通用接口
    def check_object_by_rule(self, obj: WwiseObject, check_box: QCheckBox, check_function):
        if check_box.isChecked() and check_function(obj):
            self.record_problematic_object(obj, self.__currentTitle, check_box.text())

    # 记录不符合规范的对象
    def record_problematic_object(self, obj: WwiseObject, category: str, rule: str):
        row_count = self.tblValidationResults.rowCount()
        self.tblValidationResults.insertRow(row_count)
        rule_item = QTableWidgetItem(rule)
        rule_item.setData(Qt.ItemDataRole.BackgroundRole, CellSeverity.Danger)
        self.tblValidationResults.setItem(row_count, 0, QTableWidgetItem(category))
        self.tblValidationResults.setItem(row_count, 1, rule_item)
        self.tblValidationResults.setItem(row_count, 2, QTableWidgetItem(obj.type.name))
        self.tblValidationResults.setItem(row_count, 3, QTableWidgetItem(obj.path))
        self.problematicObjects.append(obj)

    # 检查是否存在重复绑定的RTPC
    def is_duplicated_parameter(self, parameter: WwiseObject):
        if parameter.type != WwiseObjectType.RTPC:
            return False
        built_in = waapi_utils.get_object_property(parameter, 'BindToBuiltInParam')
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


# 修复大小写命名规范
def fix_camel_case_naming(obj: WwiseObject):
    obj_name = obj.name
    split_char = '_'
    words = obj_name.split(split_char)
    if len(words) == 1:
        split_char = ' '
        words = obj_name.split(split_char)
    new_name = ''
    for word in words:
        if not re.match(r'^[A-Z\d][a-zA-Z\d]*$', word):
            word = word.title()
        new_name += word + split_char
    new_name = new_name[:-1]
    waapi_utils.rename_object(obj, new_name)
    return True


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
            target = waapi_utils.get_object_property(action, 'Target')
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
# 检查对象是否符合CamelCase命名规范
def is_not_camel_cased(obj: WwiseObject):
    obj_type = obj.type
    obj_path = obj.path
    if 'Factory' in obj_path:
        return False
    if obj_type == WwiseObjectType.EventAction:
        return False
    # 过滤根目录和MIDI对象
    if obj_type == WwiseObjectType.WorkUnit and len(obj_path.split('\\')) == 2:
        return False
    obj_name = obj.name
    if obj_type == WwiseObjectType.Folder and (obj_path.startswith('MIDI')):
        return False

    words = obj_name.split('_')
    if len(words) == 1:
        words = obj_name.split(' ')
    for word in words:
        if len(word) > 1 and not re.match(r'^[A-Z\d][a-zA-Z\d]*$', word):
            return True
    return False


# 检查对象是否命名长度不符合要求
def violates_naming_length(obj: WwiseObject):
    obj_path = obj.path
    obj_type = obj.type
    if obj_path.startswith('\\Actor-Mixer Hierarchy'):
        if obj.type == WwiseObjectType.AudioSource:
            return False
        if obj.type == WwiseObjectType.Sound:
            if audio_source_utils.sound_play_from_plugin(obj):
                return False
            return '_' not in obj.name
        return '_' in obj.name
    elif obj_path.startswith('\\Interactive Music Hierarchy'):
        if obj_type == 'MusicSegment' or obj_type == 'MusicTrack':
            return False
        return '_' in obj.name
    else:
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
    obj_type = obj.type
    # 对象是Event且播放别的对象
    if obj.type == WwiseObjectType.Event:
        targets = event_utils.get_event_targets(obj)
        if len(targets) == 1:
            target = targets[0]
            if WwiseObjectType.Bus in target.type:
                return False
            references = waapi_utils.get_object_references(target)
            # 对象被唯一事件引用时才检查备注
            if len(references) == 1:
                notes = common_utils.get_object_notes(obj)
                if notes != target.path:
                    return True
            return not has_dark_color_tag(target)
    else:
        references = waapi_utils.get_object_references(obj)
        notes = common_utils.get_object_notes(obj)
        obj_path = obj.path
        # 对象被SoundBank引用
        if obj_type == WwiseObjectType.Folder or obj_type == WwiseObjectType.WorkUnit:
            if obj_path.startswith('\\Events'):
                for reference in references:
                    if reference.type == WwiseObjectType.SoundBank:
                        if notes != f"Included by SoundBank [{reference.name}]":
                            return True
                        return not has_dark_color_tag(obj)
        # 对象被Event引用
        elif 'Hierarchy' in obj_path:
            for reference in references:
                if reference.type == WwiseObjectType.EventAction:
                    action_type = waapi_utils.get_object_property(reference, 'ActionType')
                    if action_type == 1:
                        event = waapi_utils.get_parent_object(reference)
                        if notes != f"Played by Event [{event.name}]":
                            return True
                    return not has_dark_color_tag(obj)
    return False


# 对象是否因为引用设置了特殊颜色
def has_dark_color_tag(obj: WwiseObject):
    if not waapi_utils.get_object_property(obj, 'OverrideColor'):
        return False
    color = common_utils.get_object_color(obj)
    parent = waapi_utils.get_parent_object(obj)
    if not parent:
        return False
    parent_color = common_utils.get_object_color(parent)
    return parent_color - color == 13
# endregion ProjectStandards


# region DesignStructure
# 检查WorkUnit是否只包含子级WorkUnit
def is_work_unit_nested(work_unit: WwiseObject):
    if work_unit.type != WwiseObjectType.WorkUnit:
        return False
    # 物理文件夹会只有一个路径，故跳过
    path_splits = work_unit.path.split('\\')
    if len(path_splits) <= 2:
        return False
    work_unit_type = waapi_utils.get_object_property(work_unit, 'workUnitType')
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
    if actor_mixer.type != WwiseObjectType.ActorMixer:
        return False
    parent = waapi_utils.get_parent_object(actor_mixer)
    if parent.type == WwiseObjectType.WorkUnit:
        return False
    effects = waapi_utils.get_object_property(actor_mixer, 'Effect')
    rtpcs = waapi_utils.get_object_property(actor_mixer, '@RTPC')
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
    if 'Actor-Mixer Hierarchy' not in obj_path and 'Interactive Music Hierarchy' not in obj_path:
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
    children = waapi_utils.get_child_objects(sound)
    for audio_source in children:
        source_path = audio_source_utils.get_source_file_path(audio_source)
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
    implemented_languages = project_conventions.get_implemented_languages()
    if localization_utils.get_sound_language(sound) == 'SFX':
        path = audio_source_utils.get_source_file_path(sound)
        if not path:
            return not audio_source_utils.sound_play_from_plugin(sound)
        return not os.path.exists(path)
    else:
        children = waapi_utils.get_child_objects(sound)
        missing_languages = len(implemented_languages)
        for child in children:
            language = localization_utils.get_sound_language(child)
            if language in implemented_languages:
                missing_languages -= 1
        return missing_languages > 0


# 检查样本是否是静音替代资源
def is_audio_source_silent(source: WwiseObject):
    source_type = source.type
    if source_type != WwiseObjectType.AudioSource:
        # 检查Wwise Silence插件的情况
        if source_type == 'SourcePlugin':
            class_id = waapi_utils.get_object_property(source, 'classId')
            return class_id == 6619138
        return False
    source_path = audio_source_utils.get_source_file_path(source)
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
        if parent.type == WwiseObjectType.ActorMixer or parent.type == WwiseObjectType.WorkUnit:
            return True
        return sound_not_in_any_events(parent)
    return False


# 检查样本的裁剪末尾是否超出时长范围
def audio_trim_out_of_range(audio_source: WwiseObject):
    if audio_source.type != WwiseObjectType.AudioSource:
        return False
    trim_end = waapi_utils.get_object_property(audio_source, 'TrimEnd')
    if trim_end == -1:
        return False
    duration = waapi_utils.get_object_property(audio_source, 'playbackDuration')
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
        if WwiseObjectType.Bus in target.type:
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
    bus = waapi_utils.get_object_property(obj, 'OutputBus')
    if bus is None:
        return False
    is_master = bus.name == 'Master Audio Bus'
    override = waapi_utils.get_object_property(obj, 'OverrideOutput')
    if override:
        return is_master
    # 非override的对象需要检查是否上级已经检查过了
    parent = waapi_utils.get_parent_object(obj)
    if parent and not waapi_utils.get_object_property(parent, 'OutputBus'):
        return is_master
    return False


# 检查SwitchContainer是否未分配播放对象
def is_switch_container_unassigned(container: WwiseObject):
    if WwiseObjectType.SwitchContainer not in container.type:
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
    group = waapi_utils.get_object_property(container, 'SwitchGroupOrStateGroup')
    if 'name' in group:
        default_switch = waapi_utils.get_object_property(container, 'DefaultSwitchOrState')
        return 'name' in default_switch and '1P' in default_switch.name
    return False


# 3D对象未设置衰减曲线
def object_missing_attenuation(obj: WwiseObject):
    if not obj.path.startswith('\\Actor-Mixer Hierarchy'):
        return False
    override = waapi_utils.get_object_property(obj, 'OverridePositioning')
    if not override and not mixing_utils.is_mixing_root(obj):
        return False
    spatialization_mode = waapi_utils.get_object_property(obj, '3DSpatialization')
    if not spatialization_mode:
        return False
    if spatialization_mode == 0:
        return '_3P' in obj.name
    attenuation = waapi_utils.get_object_property(obj, 'Attenuation')
    return 'name' not in attenuation


# 检查语音、环境声和音乐是否设为Streaming
def sound_not_streamed(obj: WwiseObject):
    obj_type = obj.type
    if obj_type == 'MusicTrack' or obj.type == WwiseObjectType.Sound:
        category = project_conventions.get_object_category(obj)
        if category == 'Ambience' or category == 'Voice' or category == 'Music':
            streaming = waapi_utils.get_object_property(obj, 'IsStreamingEnabled')
            return not streaming
    return False
# endregion Mistakes
