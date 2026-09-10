from data import project_conventions
from libraries.utils.wwise import waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType


# 判断一个对象是否是最上层可混音对象
def is_mixing_root(obj: WwiseObject) -> bool:
    parent = waapi_utils.get_parent_object(obj)
    if parent:
        if parent.type == WwiseObjectType.WorkUnit or parent.type == WwiseObjectType.Folder:
            return is_mixing_root(parent)
        return False
    return True

# 清除对象上绑定的效果器
def clear_effects(obj: WwiseObject) -> bool:
    return waapi_utils.clear_slots(obj, 'Effects')

# 创建新的bus
def get_or_create_bus(bus_name: str, parent_bus: WwiseObject) -> WwiseObject:
    bus = waapi_utils.find_object_by_name_and_type(bus_name, WwiseObjectType.Bus)
    if bus is None:
        bus = waapi_utils.create_child_object(bus_name, WwiseObjectType.Bus, parent_bus, 'replace')
    return bus

# 为对象分配Bus
def set_output_bus(obj: WwiseObject, bus_obj: WwiseObject) -> bool:
    print(f"Set output bus of {obj.type} [{obj.name}] to {bus_obj.name}")
    waapi_utils.set_object_property(obj, 'OverrideOutput', True)
    return waapi_utils.set_object_reference(obj, 'OutputBus', bus_obj)

# 根据对象类别自动分配Bus
def auto_assign_bus_by_category(obj: WwiseObject) -> bool:
    category = project_conventions.get_object_category(obj)
    if category:
        bus = waapi_utils.find_object_by_name_and_type(category, WwiseObjectType.Bus)
        if bus:
            return set_output_bus(obj, bus)
    return False

# 为对象设定3D开关
def set_sound_3d(sound: WwiseObject, is3d: bool):
    waapi_utils.set_object_property(sound, 'OverridePositioning', True)
    waapi_utils.set_object_property(sound, '3DSpatialization', 2 if is3d else 0)

# 对象的音量等参数是否有调整
def has_fader_edits(obj: WwiseObject) -> bool:
    volume = waapi_utils.get_object_property(obj, 'Volume')
    pitch = waapi_utils.get_object_property(obj, 'Pitch')
    lowpass = waapi_utils.get_object_property(obj, 'Lowpass')
    highpass = waapi_utils.get_object_property(obj, 'Highpass')
    if 'Bus' not in obj.type.value:
        gain = waapi_utils.get_object_property(obj, 'MakeUpGain')
    else:
        gain = 0
    return volume != 0 or pitch != 0 or lowpass != 0 or highpass != 0 or gain != 0

# 将混音参数传递到下一层
def down_mix_fader(obj: WwiseObject):
    down_mix_fader_param(obj, 'Volume')
    down_mix_fader_param(obj, 'Pitch')
    down_mix_fader_param(obj, 'Lowpass')
    down_mix_fader_param(obj, 'Highpass')
    # Bus类对象不包含MakeUpGain属性
    if 'Bus' not in obj.type.value:
        down_mix_fader_param(obj, 'MakeUpGain')

# 向下传递特定的混音参数
def down_mix_fader_param(obj: WwiseObject, param_name: str):
    param_delta = waapi_utils.get_object_property(obj, param_name)
    waapi_utils.set_object_property(obj, param_name, 0)
    children = waapi_utils.get_child_objects(obj)
    for child in children:
        param_base = waapi_utils.get_object_property(child, param_name)
        waapi_utils.set_object_property(child, param_name, param_base + param_delta)
        # 递归应用编辑
        if child.type != WwiseObjectType.Sound:
            down_mix_fader_param(child, param_name)

# 音量调整改为增益
def volume_to_gain(obj: WwiseObject):
    volume = waapi_utils.get_object_property(obj, 'Volume')
    gain = waapi_utils.get_object_property(obj, 'MakeUpGain')
    final_value = volume + gain
    waapi_utils.set_object_property(obj, 'Volume', 0)
    waapi_utils.set_object_property(obj, 'MakeUpGain', final_value)

# 将效果器设为渲染模式
def set_effect_slot_property(obj: WwiseObject, property_name: str, value: bool) -> bool:
    effect_slots = waapi_utils.get_object_property(obj, '@Effects')
    if effect_slots is None:
        return False
    for effect_slot in effect_slots:
        waapi_utils.set_object_property(WwiseObject(effect_slot), property_name, value)
    return True
