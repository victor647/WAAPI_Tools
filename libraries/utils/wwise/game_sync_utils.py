from libraries.utils.wwise import waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType


# 清除对象上绑定的RTPC
def clear_rtpc(obj: WwiseObject) -> bool:
    return waapi_utils.clear_slots(obj, 'RTPC')

# 替换对象上的RTPC
def copy_rtpc(source_obj: WwiseObject, target_objects: list) -> bool:
    return waapi_utils.paste_object_property(source_obj, target_objects, 'Rtpc')

# 在SwitchGroup或StateGroup中查找或创建对应名称的选项
def find_or_create_switch_value(switch_or_state_group: WwiseObject, value_name: str) -> WwiseObject:
    sg = switch_or_state_group
    if not sg:
        return WwiseObject()
    if not (sg.wwise_dict or {}).get('type'):
        sg = waapi_utils.get_full_info_from_obj_id(sg.id)
    if not sg or not sg.id:
        return WwiseObject()
    existing_values = waapi_utils.get_child_objects(sg)
    for value in existing_values:
        if value.name == value_name:
            return value
    switch_type = (
        WwiseObjectType.SwitchValue if sg.type == WwiseObjectType.SwitchGroup else WwiseObjectType.StateValue
    )
    return waapi_utils.create_child_object(value_name, switch_type, sg)
