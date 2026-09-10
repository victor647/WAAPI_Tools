import libraries.utils.wwise.waapi_utils  # noqa: F401
from libraries.utils.wwise import waapi_utils
from libraries.wwise_object import WwiseObject

sounds = waapi_utils.find_all_objects_by_type(waapi_utils.WwiseObjectType.Sound)[:5]
print("sounds:", len(sounds), flush=True)

single = waapi_utils.get_object_property(sounds[0], "Volume")
print("single get_object_property:", repr(single), flush=True)

bags = waapi_utils.get_objects_properties(sounds, ["Volume"])
print("bulk returned:", len(bags), flush=True)
for bag in bags[:5]:
    print("  ", bag.id, sorted(bag.wwise_dict.keys()), "Volume=", bag.wwise_dict.get("Volume"), flush=True)
