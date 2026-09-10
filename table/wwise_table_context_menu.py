import os

from libraries.utils.log_utils import Logger
from libraries.utils.wwise import audio_source_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType


# 打开 AudioSource 对应的音频预览窗口
def preview_audio_source(obj: WwiseObject, parent=None):
    from windows.audio_preview_window import AudioPreviewWindow

    file_path = audio_source_utils.get_source_absolute_path(obj)
    if not file_path or not os.path.exists(file_path):
        Logger().warning(f"找不到源文件：{file_path}")
        return
    AudioPreviewWindow(file_path, parent).show()


# 往菜单追加 Wwise 对象行的通用动作（各窗口再追加自己的专属动作）
def add_common_object_actions(menu, obj: WwiseObject, parent=None):
    menu.addAction('在Wwise中选中', lambda: waapi_utils.select_objects_in_wwise([obj]))
    if obj.type == WwiseObjectType.AudioSource:
        menu.addAction('预览', lambda: preview_audio_source(obj, parent))
