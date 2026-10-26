import os

from PySide6.QtWidgets import QTableWidget

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


# 往菜单追加 Wwise 对象行的通用动作（在Wwise中选中 / AudioSource 预览）
# 复制项由各表格按列能力统一生成，避免同一列出现多个复制入口
def add_common_object_actions(menu, obj: WwiseObject, parent=None):
    menu.addAction('在Wwise中选中', lambda: waapi_utils.select_objects_in_wwise([obj]))
    if obj.type == WwiseObjectType.AudioSource:
        menu.addAction('预览', lambda: preview_audio_source(obj, parent))


# 在一批对象里挑出有效的，并在 Wwise 中选中（表格双击/右键的公共实现）
def select_row_objects(objects: list) -> None:
    valid_objects = [obj for obj in (objects or []) if obj and obj.is_valid]
    if not valid_objects:
        Logger().warning('该行没有对应的 Wwise 对象，无法在 Wwise 中选中')
        return
    waapi_utils.select_objects_in_wwise(valid_objects)


# 表格行的默认行为：双击某行时在 Wwise 中选中该行对应的对象。
# 所有含 Wwise 对象的表格都接这个，object_resolver(row) 返回该行的对象列表（可为多个）。
def connect_double_click_select(table: QTableWidget, object_resolver):
    table.itemDoubleClicked.connect(lambda item: select_row_objects(object_resolver(item.row())))
