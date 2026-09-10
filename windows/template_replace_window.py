from libraries.wwise_object import WwiseObjectType, WwiseObject
from ui.TemplateReplacer_ui import Ui_TemplateReplacer
from PySide6.QtWidgets import QDialog
from libraries.utils.wwise import common_utils, audio_source_utils, localization_utils, waapi_utils


# 批量替换内容工具
class TemplateReplacer(QDialog, Ui_TemplateReplacer):
    __oldName = ''
    __newName = ''

    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.cbxObjectType.clear()
        for member in (WwiseObjectType.AudioSource, WwiseObjectType.Event, WwiseObjectType.SoundBank):
            self.cbxObjectType.addItem(member.name, member)
        self.setup_triggers()
        self.__mainWindow = main_window

    def setup_triggers(self):
        self.btnDoReplace.clicked.connect(self.start_replacing)

    # 开始进行替换
    def start_replacing(self):
        self.__oldName = self.iptFindName.text()
        self.__newName = self.iptReplaceName.text()
        replace_type = self.cbxObjectType.currentData()
        waapi_utils.begin_undo_group(f'{replace_type}模板批量替换')
        # 统一入口：按「工具执行前自动获取子对象」展开，模板替换对全部类型生效
        if hasattr(self.__mainWindow, "collect_tool_targets"):
            target_objects = self.__mainWindow.collect_tool_targets()
        else:
            target_objects = self.__mainWindow.activeObjects
        for obj in target_objects:
            self.process_object(obj, replace_type)
        waapi_utils.end_undo_group(f'{replace_type}模板批量替换')

    # 处理单个对象（列表已统一展开子对象，不再递归）
    def process_object(self, obj: WwiseObject, replace_type: WwiseObjectType):
        if replace_type == WwiseObjectType.AudioSource and obj.type == WwiseObjectType.Sound:
            if self.__oldName in obj.name:
                self.replace_source_wave(obj)
        elif replace_type == WwiseObjectType.AudioSource and obj.type == WwiseObjectType.AudioSource:
            # AudioSource 由其所属 Sound 统一替换源文件，这里不重复处理
            pass
        elif replace_type == WwiseObjectType.Event and obj.type == WwiseObjectType.Event:
            if self.__oldName in obj.name:
                self.replace_event(obj)
        elif replace_type == WwiseObjectType.SoundBank and obj.type == WwiseObjectType.SoundBank:
            if self.__oldName in obj.name:
                self.replace_bank(obj)
        else:
            if self.__oldName in obj.name:
                self.rename_structure(obj)

    # 对结构名字重命名
    def rename_structure(self, obj: WwiseObject):
        new_sound_name = obj.name.replace(self.__oldName, self.__newName)
        waapi_utils.rename_object(obj, new_sound_name)

    # 对声音文件进行替换
    def replace_source_wave(self, obj: WwiseObject):
        self.rename_structure(obj)
        sources = waapi_utils.get_child_objects(obj)
        for source in sources:
            original_path = audio_source_utils.get_source_absolute_path(source)
            language = localization_utils.get_sound_language(source)
            new_wave_path = original_path.replace(self.__oldName, self.__newName)
            waapi_utils.delete_object(source)
            waapi_utils.import_audio_file(new_wave_path, obj, language)

    # 对事件名和内容进行替换
    def replace_event(self, obj: WwiseObject):
        new_event_name = obj.name.replace(self.__oldName, self.__newName).replace('_01', '')
        waapi_utils.rename_object(obj, new_event_name)
        for action in waapi_utils.get_child_objects(obj):
            target = waapi_utils.get_referenced_object(action, 'Target')
            if not target:
                continue
            target_full = waapi_utils.get_full_info_from_obj_id(target.id)
            new_target_path = target_full.path.replace(self.__oldName, self.__newName)
            new_target = waapi_utils.find_object_by_path(new_target_path)
            if new_target:
                waapi_utils.set_object_reference(action, 'Target', new_target)
                common_utils.update_notes_and_color(obj)

    # 对bank内容进行替换
    def replace_bank(self, bank: WwiseObject):
        new_bank_name = bank.name.replace(self.__oldName, self.__newName).replace('_01', '')
        waapi_utils.rename_object(bank, new_bank_name)
        old_inclusions = waapi_utils.get_bank_inclusions(bank)
        waapi_utils.clear_bank_inclusions(bank)
        for old_inclusion_obj in old_inclusions:
            target_full = waapi_utils.get_full_info_from_obj_id(old_inclusion_obj['object'])
            new_target_path = target_full.path.replace(self.__oldName, self.__newName)
            new_target = waapi_utils.find_object_by_path(new_target_path)
            waapi_utils.set_bank_inclusion_object(bank, new_target, False, old_inclusion_obj['filter'])
        return True
