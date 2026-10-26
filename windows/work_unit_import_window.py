from libraries.base_dialog import BaseDialog
import os
import shutil
import logging
import xml.etree.ElementTree as ElementTree
from libraries.utils import io_utils, user_config
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import (
    audio_source_utils, game_sync_utils, project_utils, waapi_utils, mixing_utils, wwise_compat,
)
from PySide6.QtWidgets import QDialog

from libraries.wwise_object import WwiseObjectType, WwiseObject
from ui.WorkUnitImporter_ui import Ui_WorkUnitImporter


def _ref_to_wobj(ref: WwiseObject) -> WwiseObject:
    """属性引用返回的 WwiseObject 可能缺少 type，必要时回读完整信息。"""
    if ref is None or not ref.id:
        return WwiseObject()
    if ref.wwise_dict and ref.wwise_dict.get('type'):
        return ref
    return waapi_utils.get_full_info_from_obj_id(ref.id)


# 导入WorkUnit到另一个Wwise工程
class WorkUnitImporter(BaseDialog, Ui_WorkUnitImporter):

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # 先回填持久化选项再连信号，避免回填过程触发一次保存
        self.load_user_settings()
        self.setup_triggers()
        self.__sourceProjectPath = ''
        self.__objectCount = 0

    def setup_triggers(self):
        self.btnStartImport.clicked.connect(self.start_import)
        for checkbox in (self.cbxImportEffects, self.cbxImportSourceFile, self.cbxImportConversion,
                         self.cbxImportAttenuation, self.cbxImportBus, self.cbxImportRTPC):
            checkbox.toggled.connect(self._on_option_changed)
        self.cbbMissingAction.currentIndexChanged.connect(self._on_option_changed)

    # 读取本窗口持久化的导入选项（user_config.json 的 window_settings.work_unit_import）
    def load_user_settings(self):
        saved = user_config.get_window_settings('work_unit_import')
        self.cbxImportEffects.setChecked(bool(saved.get('import_effects', self.cbxImportEffects.isChecked())))
        self.cbxImportSourceFile.setChecked(bool(saved.get('import_source_file', self.cbxImportSourceFile.isChecked())))
        self.cbxImportConversion.setChecked(bool(saved.get('import_conversion', self.cbxImportConversion.isChecked())))
        self.cbxImportAttenuation.setChecked(bool(saved.get('import_attenuation', self.cbxImportAttenuation.isChecked())))
        self.cbxImportBus.setChecked(bool(saved.get('import_bus', self.cbxImportBus.isChecked())))
        self.cbxImportRTPC.setChecked(bool(saved.get('import_rtpc', self.cbxImportRTPC.isChecked())))
        action = saved.get('missing_action')
        if action is not None:
            index = self.cbbMissingAction.findText(str(action))
            if index >= 0:
                self.cbbMissingAction.setCurrentIndex(index)

    # 把本窗口选项写回 user_config.json
    def save_user_settings(self):
        user_config.set_window_settings('work_unit_import', {
            'import_effects': self.cbxImportEffects.isChecked(),
            'import_source_file': self.cbxImportSourceFile.isChecked(),
            'import_conversion': self.cbxImportConversion.isChecked(),
            'import_attenuation': self.cbxImportAttenuation.isChecked(),
            'import_bus': self.cbxImportBus.isChecked(),
            'import_rtpc': self.cbxImportRTPC.isChecked(),
            'missing_action': self.cbbMissingAction.currentText(),
        })

    # 选项一变就落盘：窗口没有确定/取消按钮，Esc 关闭不会触发 closeEvent
    def _on_option_changed(self, _value=None):
        self.save_user_settings()

    # 从WorkUnit中根据名称导入对象
    def start_import(self):
        root, path = io_utils.import_from_xml('wwu')
        if not root or not path:
            return
        # 2025+ 的 Work Unit 根是 Containers / Busses，旧版本是各 Hierarchy
        found = [path.find(folder) for folder in wwise_compat.HIERARCHY_FOLDER_NAMES]
        index = min((item for item in found if item >= 0), default=-1)
        if index < 0:
            Logger().warning(f"未能从 Work Unit 路径中识别 Wwise 层级根：{path}")
            return
        rel_path = path[index:]
        self.__sourceProjectPath = path[:index]
        self.__objectCount = 0
        folder_path = os.path.dirname(rel_path)
        folder = waapi_utils.find_object_by_path(folder_path)
        if not folder:
            folder = waapi_utils.create_object_by_path(folder_path, 'Physical Folder')
        if folder:
            for node in root.find('AudioObjects'):
                self.parse_node(node, folder)
            Logger().info('导入完成，共导入{self.__objectCount}个对象！')
        self.lblCurrentObject.setText('')
        self.lblObjectCount.setText('')

    # 遍历Wwu节点
    def parse_node(self, node: ElementTree, parent_obj: WwiseObject):
        obj_type = WwiseObjectType(node.tag)
        if obj_type == WwiseObjectType.AudioSource:
            if self.cbxImportSourceFile.isChecked():
                self.import_audio_file(node, parent_obj)
            return

        obj_name = node.attrib.name
        obj_path = str(os.path.join(parent_obj.path, obj_name))
        obj = waapi_utils.find_object_by_path(obj_path)
        self.lblCurrentObject.setText(obj_name)
        self.__objectCount += 1
        self.lblObjectCount.setText(f'已导入{self.__objectCount}个对象')
        self.repaint()
        if not obj:
            obj = waapi_utils.create_child_object(obj_name, obj_type, parent_obj)
        if not obj:
            logging.error(f'Cannot create {obj_type} named {obj_name}!')
            return
        for element in node:
            if element.tag == 'ChildrenList':
                for child_node in element:
                    self.parse_node(child_node, obj)
            elif element.tag == 'PropertyList':
                for child_node in element:
                    import_property(child_node, obj)
            elif element.tag == 'ReferenceList':
                for child_node in element:
                    self.import_reference(child_node, obj)
            elif element.tag == 'ObjectLists':
                for child_node in element:
                    self.import_object_list(child_node, obj)
            elif element.tag == 'GroupingInfo':
                import_grouping_list(element.find('GroupingList'), obj)
            elif element.tag == 'Comment':
                waapi_utils.set_object_notes(obj, element.text)

    # 根据名称获取引用
    def import_reference(self, node: ElementTree, obj: WwiseObject):
        ref_name = node.attrib.name
        ref_type = ref_name
        value_node = node.find('ObjectRef')
        if value_node is None:
            return
        ref_obj_name = value_node.attrib.name

        if ref_name == 'OutputBus':
            if not self.cbxImportBus.isChecked():
                return
            ref_type = WwiseObjectType.Bus
        elif ref_name == 'SwitchGroupOrStateGroup':
            ref_type = WwiseObjectType.SwitchGroup
            if 'Ambience' in obj.path:
                ref_type = WwiseObjectType.StateGroup
        elif ref_name == 'DefaultSwitchOrState':
            import_default_switch(node, obj)
            return
        elif ref_name == 'Attenuation':
            if not self.cbxImportAttenuation.isChecked():
                return
        elif ref_name == 'Conversion':
            if not self.cbxImportConversion.isChecked():
                return

        ref_obj = waapi_utils.find_object_by_name_and_type(ref_obj_name, ref_type)
        if ref_obj:
            waapi_utils.set_object_reference(obj, ref_name, ref_obj)
        else:
            if self.cbbMissingAction.currentText() == '忽略':
                logging.error(f'Cannot find reference of type [{ref_type}] named [{ref_obj_name}]!')
            elif self.cbbMissingAction.currentText() == '警告':
                Logger().warning(f'导入失败，找不到名为{ref_obj_name}的{ref_type}, 无法设置引用！')
            elif self.cbbMissingAction.currentText() == '创建':
                new_obj = waapi_utils.create_object_at_default_location(ref_obj_name, ref_type)
                if not new_obj:
                    logging.error(f'Failed to create {ref_type} named {ref_obj_name}!')
                else:
                    waapi_utils.set_object_reference(obj, ref_name, new_obj)

    # 导入Effect/RTPC等对象
    def import_object_list(self, node: ElementTree, obj: WwiseObject):
        if node.attrib.name == 'RTPC' and self.cbxImportRTPC.isChecked():
            import_rtpc(node, obj)
        if node.attrib.name == 'Effects' and self.cbxImportEffects.isChecked():
            import_effects(node, obj)

    # 导入音频文件
    def import_audio_file(self, source_node: ElementTree, sound: WwiseObject):
        language = 'SFX'
        for info_node in source_node:
            if info_node.tag == 'Language':
                language = info_node.text
            elif info_node.tag == 'AudioFile':
                new_wav_path = str(os.path.join(project_utils.get_originals_folder(), language, info_node.text))
                if not os.path.exists(new_wav_path):
                    old_wav_path = os.path.join(self.__sourceProjectPath, 'Originals', language, info_node.text)
                    if os.path.exists(old_wav_path):
                        os.makedirs(os.path.dirname(new_wav_path), exist_ok=True)
                        shutil.copy(old_wav_path, new_wav_path)
                        waapi_utils.import_audio_file(new_wav_path, sound, language)
                    else:
                        logging.error(f'Original file [{old_wav_path}] not found!')
                        continue
                else:
                    existing_wav_path = audio_source_utils.get_source_absolute_path(sound)
                    if existing_wav_path is None or not os.path.samefile(new_wav_path, existing_wav_path):
                        waapi_utils.import_audio_file(new_wav_path, sound, language)


# 导入属性值
def import_property(node: ElementTree, obj: WwiseObject):
    property_name = node.attrib.name
    if 'Value' in node.attrib:
        value = node.attrib['Value']
        waapi_utils.set_object_property(obj, property_name, value)
    elif node.find('ValueList'):
        value_list = node.find('ValueList')
        for value_node in value_list:
            if 'Platform' in value_node.attrib:
                platform = value_node.attrib['Platform']
                if project_utils.has_platform(platform):
                    waapi_utils.set_object_property(obj, property_name, value_node.text, platform)
            else:
                waapi_utils.set_object_property(obj, property_name, value_node.text)


# 导入组策略（如Switch分配）
def import_grouping_list(node: ElementTree, obj: WwiseObject):
    switch_group = _ref_to_wobj(waapi_utils.get_referenced_object(obj, 'SwitchGroupOrStateGroup'))
    if not switch_group:
        return
    children = waapi_utils.get_child_objects(obj)
    waapi_utils.remove_switch_mappings(obj)
    for grouping in node:
        switch_name = grouping.find('SwitchRef').attrib.name
        value = game_sync_utils.find_or_create_switch_value(switch_group, switch_name)
        for item_ref in grouping.find('ItemList'):
            item_name = item_ref.attrib.name
            for child in children:
                if child.name == item_name:
                    waapi_utils.assign_switch_mapping(child, value)


# 导入默认的Switch或State值
def import_default_switch(node: ElementTree, obj: WwiseObject):
    switch_group = _ref_to_wobj(waapi_utils.get_referenced_object(obj, 'SwitchGroupOrStateGroup'))
    if not switch_group:
        return
    switch_name = node.find('ObjectRef').attrib.name
    option = game_sync_utils.find_or_create_switch_value(switch_group, switch_name)
    if option:
        waapi_utils.set_object_reference(obj, 'DefaultSwitchOrState', option)


# 导入RTPC（仅对2022版本后生效）
def import_rtpc(node: ElementTree, obj: WwiseObject):
    game_sync_utils.clear_rtpc(obj)
    for ref_node in node:
        points = []
        rtpc_name = ''
        rtpc_node = ref_node.find('Local').find('RTPC')
        for sub_ref_node in rtpc_node.find('ReferenceList'):
            ref_type = sub_ref_node.attrib.name
            if ref_type == 'ControlInput':
                rtpc_name = sub_ref_node.find('ObjectRef').attrib.name
            elif ref_type == 'Curve':
                for point_node in sub_ref_node.find('Custom').find('Curve').find('PointList'):
                    shape = point_node.find('SegmentShape')
                    point = {
                        'x': float(point_node.find('XPos').text),
                        'y': float(point_node.find('YPos').text),
                        'shape': shape.text if shape else 'Linear'
                    }
                    points.append(point)
        if rtpc_name != '':
            rtpc_obj = waapi_utils.find_object_by_name_and_type(rtpc_name, WwiseObjectType.RTPC)
            if rtpc_obj:
                property_name = rtpc_node.find('PropertyList').find('Property').attrib['Value']
                waapi_utils.add_rtpc(obj, rtpc_obj, property_name, points)
            else:
                Logger().warning(f'导入失败，找不到名为{rtpc_name}的RTPC, 无法设置引用！')


# 导入对象上绑定的插件
def import_effects(node: ElementTree, obj: WwiseObject):
    mixing_utils.clear_effects(obj)
    for ref_node in node:
        effect_node = ref_node.find('Local').find('EffectSlot').find('ReferenceList').find('Reference')
        if 'PluginName' in effect_node.attrib:
            share_set = effect_node.find('ObjectRef')
            share_set_name = share_set.attrib.name
            waapi_utils.add_effect(obj, share_set_name)
