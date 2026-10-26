from data import project_conventions
from libraries.utils.wwise import waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType

# 参与响度累加的属性名（Wwise 官方拼写）：
#   OutputBusVolume 是发送到下级总线的音量；BusVolume 只有 Bus / AuxBus 才有，属于总线链路
#   具体某个对象有没有这些属性由 WwiseObject.has_property 按类型过滤，无需按链路分开取
GAIN_PROPERTY_NAMES = ['Volume', 'MakeupGain', 'OutputBusVolume', 'BusVolume']


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


# 对象当前的有效输出总线（未被覆盖时是上层继承的总线）；没有分配时返回 None
# values 传批量预取的单对象属性字典时优先使用，避免逐对象查询
def get_output_bus(obj: WwiseObject, values: dict = None) -> WwiseObject:
    if values is not None:
        value = values.get('OutputBus')
    else:
        value = waapi_utils.get_object_property(obj, 'OutputBus')
    return WwiseObject(value) if value else None


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
    is_bus = 'Bus' in obj.type.value
    property_names = ['Volume', 'Pitch', 'Lowpass', 'Highpass']
    if not is_bus:
        property_names.append('MakeUpGain')
    properties = waapi_utils.get_object_properties(obj, property_names)
    volume = properties.get('Volume')
    pitch = properties.get('Pitch')
    lowpass = properties.get('Lowpass')
    highpass = properties.get('Highpass')
    gain = 0 if is_bus else properties.get('MakeUpGain')
    return volume != 0 or pitch != 0 or lowpass != 0 or highpass != 0 or gain != 0

# 将混音参数传递到下一层
def down_mix_fader(obj: WwiseObject):
    property_names = ['Volume', 'Pitch', 'Lowpass', 'Highpass']
    # Bus类对象不包含MakeUpGain属性
    if 'Bus' not in obj.type.value:
        property_names.append('MakeUpGain')
    _down_mix_fader(obj, property_names)

# 向下传递特定的混音参数
def down_mix_fader_param(obj: WwiseObject, param_name: str):
    _down_mix_fader(obj, [param_name])


def _down_mix_fader(obj: WwiseObject, property_names: list[str], values: dict = None):
    properties = values if values is not None else waapi_utils.get_object_properties(obj, property_names)
    deltas = {
        property_name: properties[property_name]
        for property_name in property_names
        if property_name in properties and properties[property_name] is not None
    }
    if not deltas:
        return
    for property_name in deltas:
        waapi_utils.set_object_property(obj, property_name, 0)

    children = waapi_utils.get_child_objects(obj)
    properties_by_id = waapi_utils.get_objects_properties(children, list(deltas))
    for child in children:
        child_properties = properties_by_id.get(child.id, {})
        child_values = {}
        for property_name, delta in deltas.items():
            param_base = child_properties.get(property_name)
            if param_base is None:
                continue
            child_value = param_base + delta
            waapi_utils.set_object_property(child, property_name, child_value)
            child_values[property_name] = child_value
        # 递归应用编辑
        if child.type != WwiseObjectType.Sound and child_values:
            _down_mix_fader(child, list(child_values), child_values)

# 音量调整改为增益
def volume_to_gain(obj: WwiseObject):
    properties = waapi_utils.get_object_properties(obj, ['Volume', 'MakeUpGain'])
    volume = properties.get('Volume')
    gain = properties.get('MakeUpGain')
    final_value = volume + gain
    waapi_utils.set_object_property(obj, 'Volume', 0)
    waapi_utils.set_object_property(obj, 'MakeUpGain', final_value)


# 音量偏移计算缓存：批量分析时同一批音频的上级对象大量重复，按对象 id 缓存避免反复走 WAAPI
class GainOffsetCache(object):

    def __init__(self):
        self.__ancestors: dict = {}
        self.__node_gain: dict = {}
        self.__node_bus: dict = {}

    # 祖先链（含 Output Bus 等上级）
    def get_ancestors(self, obj: WwiseObject) -> list:
        key = obj.id
        if key not in self.__ancestors:
            self.__ancestors[key] = waapi_utils.get_ancestor_objects(obj)
        return self.__ancestors[key]

    # 单个对象上参与累加的属性取值（只含该类型实际拥有的属性）
    def get_node_values(self, obj: WwiseObject) -> dict:
        key = obj.id
        if key not in self.__node_gain:
            values = waapi_utils.get_object_properties(obj, GAIN_PROPERTY_NAMES)
            self.__node_gain[key] = {
                name: float(value) for name, value in values.items() if isinstance(value, (int, float))
            }
        return self.__node_gain[key]

    # 单个对象上参与累加的属性合计
    def get_node_gain(self, obj: WwiseObject) -> float:
        return sum(self.get_node_values(obj).values())

    # 对象自身引用的 Output Bus（未设置或无效时为 None）
    def get_node_bus(self, obj: WwiseObject):
        key = obj.id
        if key not in self.__node_bus:
            bus = get_output_bus(obj)
            self.__node_bus[key] = bus if bus and bus.is_valid else None
        return self.__node_bus[key]

    # 链路累加：链路中每个对象只查一次
    def get_chain_gain(self, chain: list) -> float:
        return sum(self.get_node_gain(node) for node in chain)

    # 从链路中找最终生效的 Output Bus：取最深的那个设置了 Output Bus 的对象所引用的 Bus
    def find_output_bus(self, chain: list):
        for node in chain:
            bus = self.get_node_bus(node)
            if bus:
                return bus
        return None

    # 该对象牵涉到的所有对象 id（对象链路 + 总线链路），用于判断某次改动会影响哪些音频
    def get_chain_ids(self, obj: WwiseObject) -> set:
        chain = [obj] + self.get_ancestors(obj)
        ids = {node.id for node in chain}
        bus = self.find_output_bus(chain)
        if bus:
            ids.add(bus.id)
            ids.update(node.id for node in self.get_ancestors(bus))
        return ids


# 单个对象的音量偏移（单位 dB）；对象类型不含这些属性时返回 0
def get_node_gain_offset(obj: WwiseObject, cache: GainOffsetCache = None) -> float:
    return (cache or GainOffsetCache()).get_node_gain(obj)


# 单个对象上参与累加的属性取值（只含该类型实际拥有的属性）
def get_node_gain_values(obj: WwiseObject, cache: GainOffsetCache = None) -> dict:
    return (cache or GainOffsetCache()).get_node_values(obj)


# 对象自身及其所有上级对象的音量偏移之和（Actor-Mixer 层级链路）
def get_object_gain_offset(chain: list, cache: GainOffsetCache = None) -> float:
    return (cache or GainOffsetCache()).get_chain_gain(chain)


# 音量调整明细：返回 (对象链路明细, 总线链路明细)，每项为 [(节点, {属性名: 数值}), ...]
def get_gain_details(obj: WwiseObject, cache: GainOffsetCache = None) -> tuple:
    if not obj or not obj.is_valid:
        return [], []
    cache = cache or GainOffsetCache()
    chain = [obj] + cache.get_ancestors(obj)
    object_details = [(node, cache.get_node_values(node)) for node in chain]
    bus = cache.find_output_bus(chain)
    if not bus:
        return object_details, []
    bus_chain = [bus] + cache.get_ancestors(bus)
    return object_details, [(node, cache.get_node_values(node)) for node in bus_chain]


# 明细里所有层级的属性值合计
def sum_gain_details(details: list) -> float:
    return sum(sum(values.values()) for _node, values in details)


# 计算对象的响度偏移，返回 (对象链路偏移, 总线链路偏移)，单位 dB；
# 传入 cache 可在批量处理时复用上级对象的查询结果
def get_gain_offsets(obj: WwiseObject, cache: GainOffsetCache = None) -> tuple:
    object_details, bus_details = get_gain_details(obj, cache)
    return sum_gain_details(object_details), sum_gain_details(bus_details)

# 将效果器设为渲染模式
def set_effect_slot_property(obj: WwiseObject, property_name: str, value: bool) -> bool:
    effect_slots = waapi_utils.get_object_property(obj, '@Effects')
    if effect_slots is None:
        return False
    for effect_slot in effect_slots:
        waapi_utils.set_object_property(WwiseObject(effect_slot), property_name, value)
    return True
