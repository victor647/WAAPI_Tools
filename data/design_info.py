from libraries.utils.wwise import waapi_utils
from libraries.wwise_object import WwiseObject

FORCE_TO_MONO_THRESHOLD = 0.1

# 对象可用属性/引用名缓存（按对象类型）：同一类型结果一致，避免每行各查一次
_AVAILABLE_NAMES_CACHE: dict[str, set] = {}


# 取对象类型上可用的属性/引用名（按类型缓存）
def available_names_of(wwise_object: WwiseObject) -> set:
    type_name = wwise_object.type.name
    names = _AVAILABLE_NAMES_CACHE.get(type_name)
    if names is None:
        names = set(waapi_utils.get_property_and_reference_names(wwise_object))
        _AVAILABLE_NAMES_CACHE[type_name] = names
    return names


# 设计信息
class DesignInfo(object):

    # properties 传批量预取的结果（waapi_utils.get_objects_properties），未传则逐属性查询
    def __init__(self, wwise_object: WwiseObject, properties: dict = None):
        self.wwise_object = wwise_object
        self._properties = properties
        self.volume: int = 0
        self.output_bus: WwiseObject = None
        self.attenuation: WwiseObject = WwiseObject()
        self.conversion_setting: WwiseObject = None
        self.playback_limit: int = 0
        # 对象上实际存在的属性/引用名，用于区分「属性不存在」与「存在但未设置值」
        self.available_names: set[str] = set()
        self.get_data()

    # 对象上是否存在该属性（不存在时表格显示「不适用」）
    def has_property(self, name: str) -> bool:
        return name in self.available_names

    # 读单个属性的值：预取结果直接命中，否则退回单对象查询
    def _value(self, name: str):
        if self._properties is not None:
            return self._properties.get(name)
        return waapi_utils.get_object_property(self.wwise_object, name)

    # 读引用属性并包装成对象（与 waapi_utils.get_referenced_object 同口径）
    def _reference(self, name: str) -> WwiseObject:
        value = self._value(name)
        return WwiseObject(value) if value else None

    def get_data(self):
        if not self.wwise_object.is_valid or not self.wwise_object.is_designable:
            return
        names = available_names_of(self.wwise_object)
        self.available_names = names
        if self._properties is None:
            requested_names = [
                name for name in ('Volume', 'OutputBus', 'Attenuation', 'Conversion', 'MaxSoundPerInstance')
                if name in names
            ]
            self._properties = waapi_utils.get_object_properties(self.wwise_object, requested_names)
        if "Volume" in names:
            volume = self._value("Volume")
            if volume:
                self.volume = volume
        if "OutputBus" in names:
            bus = self._reference("OutputBus")
            if bus:
                self.output_bus = bus
        if "Attenuation" in names:
            attenuation = self._reference("Attenuation")
            if attenuation:
                self.attenuation = attenuation
        if "Conversion" in names:
            setting = self._reference("Conversion")
            if setting:
                self.conversion_setting = setting
        if "MaxSoundPerInstance" in names:
            limit = self._value("MaxSoundPerInstance")
            if isinstance(limit, (int, float)) and limit:
                self.playback_limit = limit
