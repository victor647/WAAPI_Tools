from libraries.utils.wwise import waapi_utils
from libraries.utils.log_utils import Logger
from libraries.wwise_object import WwiseObject


# 通过Transport播放
def play_sound(obj: WwiseObject) -> int:
    if not waapi_utils.is_connected():
        Logger().warning("Wwise未连接，无法执行播放操作！")
        return -1
    return waapi_utils.play_sound_in_transport(obj)

# 通过Transport停止
def stop_sound(transport_id: int):
    if not waapi_utils.is_connected():
        Logger().warning("Wwise未连接，无法执行停止操作！")
        return
    waapi_utils.stop_sound_in_transport(transport_id)
