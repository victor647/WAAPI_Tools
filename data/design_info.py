from libraries.utils.wwise import waapi_utils
from libraries.wwise_object import WwiseObject

FORCE_TO_MONO_THRESHOLD = 0.1

# 设计信息
class DesignInfo(object):

    def __init__(self, wwise_object: WwiseObject):
        self.wwise_object = wwise_object
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

    def get_data(self):
        if not self.wwise_object.is_valid or not self.wwise_object.is_designable:
            return
        names = set(waapi_utils.get_property_and_reference_names(self.wwise_object))
        self.available_names = names
        if "Volume" in names:
            volume = waapi_utils.get_object_property(self.wwise_object, "Volume")
            if volume:
                self.volume = volume
        if "OutputBus" in names:
            bus = waapi_utils.get_referenced_object(self.wwise_object, "OutputBus")
            if bus:
                self.output_bus = bus
        if "Attenuation" in names:
            attenuation = waapi_utils.get_referenced_object(self.wwise_object, "Attenuation")
            if attenuation:
                self.attenuation = attenuation
        if "Conversion" in names:
            setting = waapi_utils.get_referenced_object(self.wwise_object, "Conversion")
            if setting:
                self.conversion_setting = setting
        if "MaxSoundPerInstance" in names:
            limit = waapi_utils.get_object_property(self.wwise_object, "MaxSoundPerInstance")
            if isinstance(limit, (int, float)) and limit:
                self.playback_limit = limit
