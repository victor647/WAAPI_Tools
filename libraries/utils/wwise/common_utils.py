import os.path
from data import project_conventions
from libraries.utils.wwise import audio_source_utils, soundbank_utils, event_utils, waapi_utils, wwise_compat
from libraries.wwise_object import WwiseObject, WwiseObjectType
from libraries.wwise_object_properties import BUILTIN_ACCESSORS
from libraries.utils.log_utils import Logger


# 找到 Wwise 主窗口句柄：只匹配可见、有标题且面积正常的 Wwise.exe 顶层窗口，
# 避免选中 Wwise 的 1x1 辅助窗口（如 GDI+ Window）
def find_wwise_main_window() -> int:
    if os.name != 'nt':
        return 0
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    candidates = []
    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [enum_proc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    def _exe_name(hwnd) -> str:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ''
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not handle:
            return ''
        try:
            size = wintypes.DWORD(1024)
            path_buf = ctypes.create_unicode_buffer(size.value)
            if not kernel32.QueryFullProcessImageNameW(handle, 0, path_buf, ctypes.byref(size)):
                return ''
            return os.path.basename(path_buf.value).lower()
        finally:
            kernel32.CloseHandle(handle)

    def _enum_window(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        title_buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buf, length + 1)
        if 'wwise' not in title_buf.value.lower():
            return True
        if _exe_name(hwnd) != 'wwise.exe':
            return True
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True
        area = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
        if area < 10000:
            return True
        candidates.append((area, hwnd))
        return True

    user32.EnumWindows(enum_proc(_enum_window), 0)
    return max(candidates)[1] if candidates else 0


# 激活 Wwise 主窗口但不改变最大化/最小化状态：
# 不调用 ak.wwise.ui.bringToForeground（它会把最大化窗口还原成普通尺寸）
def activate_wwise_window() -> bool:
    if os.name != 'nt':
        return False
    import ctypes
    from ctypes import wintypes

    hwnd = find_wwise_main_window()
    if not hwnd:
        return False
    user32 = ctypes.windll.user32
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
    user32.keybd_event.restype = None
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE：仅最小化时恢复
    user32.BringWindowToTop(hwnd)
    if user32.GetForegroundWindow() != hwnd:
        user32.SetForegroundWindow(hwnd)
    if user32.GetForegroundWindow() == hwnd:
        return True
    # 后台进程调用 SetForegroundWindow 会被 Windows 前台锁拦截；
    # 模拟一次 Alt 按键可解除前台锁，不改变窗口最大化/普通状态
    VK_MENU = 0x12
    KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    user32.SetForegroundWindow(hwnd)
    return user32.GetForegroundWindow() == hwnd


# 重命名为包含完整路径的名称
def rename_to_full_name(obj: WwiseObject) -> bool:
    full_name = get_full_name_with_acronym(obj)
    return waapi_utils.rename_object(obj, full_name)

# 通过递归拼成全名，用于创建Event或SoundBank
def get_full_name_with_acronym(obj: WwiseObject) -> str:
    full_name = get_full_name(obj, obj.name)
    return get_name_with_acronym(full_name)

# 获取全名
def get_full_name(obj: WwiseObject, name: str) -> str:
    parent = waapi_utils.get_parent_object(obj)
    if parent is None:
        return name
    parent_name = parent.name
    if parent.path == f'\\{parent_name}':
        return name
    obj_name = obj.name
    # 上层名称重复，跳过
    if parent_name in obj_name:
        return get_full_name(parent, name)
    return get_full_name(parent, f'{parent_name}_{name}')

# 优化对象的名称长度
def optimize_name_length(obj: WwiseObject) -> bool:
    obj_path = obj.path
    # 2025+ 音频与音乐都在 \Containers 下，先按对象类型区分音乐层级
    if wwise_compat.is_music_object(obj):
        if obj.type in (WwiseObjectType.MusicSegment, WwiseObjectType.MusicTrack):
            return False
        return rename_to_short_name(obj)
    if wwise_compat.is_containers_path(obj_path):
        if obj.type == WwiseObjectType.Sound:
            if audio_source_utils.sound_play_from_plugin(obj):
                return rename_to_short_name(obj)
            return rename_to_full_name(obj)
        return rename_to_short_name(obj)
    print(f"{obj.type} [{obj.name}] does not need to follow naming length convention.")
    return False

# 重命名为不包含重复名称的最简名称
def rename_to_short_name(obj: WwiseObject) -> bool:
    short_name = get_short_name(obj, obj.name)
    return waapi_utils.rename_object(obj, short_name)

def get_short_name(obj: WwiseObject, name: str) -> str:
    parent = waapi_utils.get_parent_object(obj)
    if not parent:
        return name
    parent_name = parent.name
    if parent_name in name:
        name = name.replace(parent_name + '_', '')
    else:
        acronym = project_conventions.convert_category_to_acronym(parent_name)
        if acronym != parent_name and acronym in name:
            name = name.replace(acronym + '_', '')
    return get_short_name(parent, name)

# 检查是否符合颜色规范
def has_wrong_color(obj: WwiseObject) -> bool:
    if not project_conventions.has_color_convention():
        return False
    obj_type = obj.type
    reference = waapi_utils.get_object_references(obj)
    obj_color = get_object_color(obj)
    parent = waapi_utils.get_parent_object(obj)
    if not parent:
        return False
    parent_color = get_object_color(parent)
    if len(reference) == 0:
        # 最上一层或带引用对象的下级
        if parent_color == 0 or obj_color - parent_color == 13:
            return False
        return obj_color != parent_color
    elif obj_type != WwiseObjectType.RTPC and obj_type != WwiseObjectType.Bus:
        # 存在引用，检查是否深浅对应
        parent = waapi_utils.get_parent_object(obj)
        parent_color = get_object_color(parent)
        return parent_color - obj_color != 13
    return False

# 获取对象的备注
def get_object_notes(obj: WwiseObject) -> str:
    return waapi_utils.get_object_property(obj, 'Notes')

# 处理对象与 Event / SoundBank 的引用关系：want_notes / want_color 决定处理哪一部分，
# clear_stale_notes 决定没有引用时是否清空已有备注
def update_event_reference_links(obj: WwiseObject, want_notes: bool, want_color: bool,
                                 clear_stale_notes: bool = True) -> bool:
    use_notes = want_notes and project_conventions.use_event_ref_notes()
    use_color = want_color and project_conventions.has_color_convention()
    # 两项都不需要处理时无事可做
    if not use_notes and not use_color:
        return False
    if use_color:
        set_object_color_by_category(obj, False)
    # 对象是Event
    if obj.type == WwiseObjectType.Event:
        actions = [
            action for action in waapi_utils.get_child_objects(obj)
            if action.type == WwiseObjectType.EventAction
        ]
        action_properties = waapi_utils.get_objects_properties(actions, ['ActionType'])
        for action in actions:
            action_type = action_properties.get(action.id, {}).get('ActionType')
            if action_type == 1:
                target = waapi_utils.get_referenced_object(action, 'Target')
                event_name = obj.name
                if target:
                    target = waapi_utils.get_full_info_from_obj_id(target.id)
                    if use_notes:
                        waapi_utils.set_object_notes(target, f'Played by Event [{event_name}]')
                        waapi_utils.set_object_notes(obj, target.path)
                    if use_color:
                        set_object_color_by_category(target, False)
                        set_dark_color(target)
                        set_light_color(obj)
                    return True
    # 对象是Event播放目标
    else:
        references = waapi_utils.get_object_references(obj)
        action_references = [
            reference for reference in references
            if reference.type == WwiseObjectType.EventAction
        ]
        action_properties = waapi_utils.get_objects_properties(action_references, ['ActionType'])
        for reference in references:
            ref_type = reference.type
            if ref_type == WwiseObjectType.EventAction:
                action_type = action_properties.get(reference.id, {}).get('ActionType')
                if action_type == 1:
                    event = waapi_utils.get_parent_object(reference)
                    event_name = event.name
                    target_path = obj.path
                    if use_notes:
                        waapi_utils.set_object_notes(obj, f'Played by Event [{event_name}]')
                        waapi_utils.set_object_notes(event, target_path)
                    if use_color:
                        set_dark_color(obj)
                        set_object_color_by_category(event, False)
                    return True
            elif ref_type == WwiseObjectType.SoundBank:
                if use_notes:
                    waapi_utils.set_object_notes(obj, f"Included by SoundBank [{reference.name}]")
                if use_color:
                    set_object_color_by_category(reference, False)
                    set_dark_color(obj)
                return True
        if use_notes and clear_stale_notes:
            waapi_utils.set_object_notes(obj, '')
        if use_color:
            set_object_color_by_category(obj, False)
    return False


# 更新带引用对象的备注和颜色
def update_notes_and_color(obj: WwiseObject) -> bool:
    return update_event_reference_links(obj, want_notes=True, want_color=True)


# 只更新 Event / SoundBank 引用相关的备注；没有引用时保留原有备注
def update_reference_notes(obj: WwiseObject) -> bool:
    return update_event_reference_links(obj, want_notes=True, want_color=False, clear_stale_notes=False)


# 只按分类设置对象及其引用对象的颜色
def update_object_colors(obj: WwiseObject) -> bool:
    return update_event_reference_links(obj, want_notes=False, want_color=True)


# 是否因为引用需要使用深色标记
def should_use_dark_color(obj: WwiseObject) -> bool:
    references = waapi_utils.get_object_references(obj)
    action_references = [
        reference for reference in references
        if reference.type == WwiseObjectType.EventAction
    ]
    action_properties = waapi_utils.get_objects_properties(action_references, ['ActionType'])
    for reference in references:
        ref_type = reference.type
        if ref_type == WwiseObjectType.EventAction:
            action_type = action_properties.get(reference.id, {}).get('ActionType')
            if action_type == 1:
                return True
        elif ref_type == WwiseObjectType.SoundBank:
            return True
    return False

# 将对象的颜色设为深色
def set_dark_color(obj: WwiseObject) -> bool:
    # 设置里关闭「Event 引用使用深色」时，自动调色不再区分深浅
    if not project_conventions.use_dark_color_for_event_ref():
        return False
    light_color = get_object_color(obj)
    # 已经是深色了，不需要设置
    if light_color <= 13:
        return False
    dark_color = light_color - 13
    set_object_color(obj, dark_color)
    children = waapi_utils.get_child_objects(obj)
    for child in children:
        set_object_color(child, light_color)
    return True

# 将对象的颜色设为浅色
def set_light_color(obj: WwiseObject) -> bool:
    if not project_conventions.use_dark_color_for_event_ref():
        return False
    parent = waapi_utils.get_parent_object(obj)
    parent_color = get_object_color(parent)
    if 0 < parent_color <= 13:
        return set_object_color(obj, parent_color + 13)
    return False

# 支持单独设置 Inclusion 的对象类型（可由 Wwise 直接启用/停用并纳入 SoundBank）
INCLUSION_SETTABLE_TYPES = {
    WwiseObjectType.Folder,
    WwiseObjectType.WorkUnit,
    WwiseObjectType.ActorMixer,
    WwiseObjectType.PropertyContainer,
    WwiseObjectType.Sound,
    WwiseObjectType.RandomContainer,
    WwiseObjectType.BlendContainer,
    WwiseObjectType.SwitchContainer,
    WwiseObjectType.MusicSwitchContainer,
    WwiseObjectType.Event,
}


# 判断对象能否单独设置启用状态
def can_set_object_inclusion(obj: WwiseObject) -> bool:
    if not obj:
        return False
    return obj.type in INCLUSION_SETTABLE_TYPES


def is_object_included(
    obj: WwiseObject,
    check_ancestors=True,
    inclusion_cache: dict[str, bool] | None = None,
    property_values_by_id: dict[str, dict] = None,
    platform=None,
) -> bool:
    if 'Hierarchy' not in obj.path:
        return True
    cache_key = f'{obj.id}@{platform}' if check_ancestors and platform else (obj.id if check_ancestors else "")
    if cache_key and inclusion_cache is not None and cache_key in inclusion_cache:
        return inclusion_cache[cache_key]
    if obj.type == WwiseObjectType.AudioSource:
        if not check_ancestors:
            return True
        parent = waapi_utils.get_parent_object(obj)
        if not parent:
            if cache_key and inclusion_cache is not None:
                inclusion_cache[cache_key] = True
            return True
        included = is_object_included(
            parent,
            inclusion_cache=inclusion_cache,
            property_values_by_id=property_values_by_id,
            platform=platform,
        )
        if cache_key and inclusion_cache is not None:
            inclusion_cache[cache_key] = included
        return included
    properties = (property_values_by_id or {}).get(obj.id)
    included = (
        properties.get('Inclusion')
        if properties is not None and 'Inclusion' in properties
        else waapi_utils.get_object_property(obj, 'Inclusion', platform=platform)
    )
    if included is None:
        if cache_key and inclusion_cache is not None:
            inclusion_cache[cache_key] = True
        return True
    if included and check_ancestors:
        parent = waapi_utils.get_parent_object(obj)
        if not parent:
            if cache_key and inclusion_cache is not None:
                inclusion_cache[cache_key] = True
            return True
        included = is_object_included(
            parent,
            inclusion_cache=inclusion_cache,
            property_values_by_id=property_values_by_id,
            platform=platform,
        )
    if cache_key and inclusion_cache is not None:
        inclusion_cache[cache_key] = included
    return included

# 启用对象
def set_object_inclusion(obj: WwiseObject, included: bool) -> bool:
    return waapi_utils.set_object_property(obj, 'Inclusion', included)


# 解除属性在指定平台上的链接，之后对该平台的修改不会影响其它平台
def unlink_object_property(obj: WwiseObject, property_name: str, platform: str) -> bool:
    if not platform:
        return False
    return waapi_utils.set_object_property_linked(obj, property_name, platform, False)


# 查询属性在指定平台上是否仍链接到默认值；返回 None 表示当前 Wwise 版本不支持查询
def is_object_property_linked(obj: WwiseObject, property_name: str, platform: str) -> bool | None:
    if not platform:
        return None
    return waapi_utils.get_object_property_linked(obj, property_name, platform)


# 把属性重新链接回默认值，是 unlink_object_property 的逆向操作
def link_object_property(obj: WwiseObject, property_name: str, platform: str) -> bool:
    if not platform:
        return False
    return waapi_utils.set_object_property_linked(obj, property_name, platform, True)


# 只修改指定平台上的启用状态：先 unlink，再写入平台值
def set_object_inclusion_for_platform(obj: WwiseObject, included: bool, platform: str) -> bool:
    if not platform:
        return False
    if not unlink_object_property(obj, 'Inclusion', platform):
        return False
    return waapi_utils.set_object_property(obj, 'Inclusion', included, platform=platform)

# 获取对象的颜色
def get_object_color(obj: WwiseObject) -> int:
    return waapi_utils.get_object_property(obj, 'Color')

# 根据对象的类型自动识别并设置颜色
def set_object_color_by_category(obj: WwiseObject, check_dark: bool) -> bool:
    if not obj:
        return False
    category = project_conventions.get_object_category(obj)
    if not category:
        return False
    color = project_conventions.get_color_by_category(category)
    result = set_object_color(obj, color)
    if check_dark and project_conventions.use_dark_color_for_event_ref() and should_use_dark_color(obj):
        return set_dark_color(obj)
    return result

# 设置对象的颜色
def set_object_color(obj: WwiseObject, color: int) -> bool:
    print(f"Color of {obj.type} [{obj.name}] set to {color}")
    waapi_utils.set_object_property(obj, 'OverrideColor', True)
    return waapi_utils.set_object_property(obj, 'Color', color)

def rename_to_lower_case(obj: WwiseObject) -> bool:
    new_name = obj.name.lower()
    if new_name != obj.name:
        return waapi_utils.rename_object(obj, new_name)
    return False

def rename_to_title_case(obj: WwiseObject) -> bool:
    new_name = obj.name.title()
    if new_name != obj.name:
        return waapi_utils.rename_object(obj, new_name)
    return False

def rename_to_upper_case(obj: WwiseObject) -> bool:
    new_name = obj.name.upper()
    if new_name != obj.name:
        return waapi_utils.rename_object(obj, new_name)
    return False

# 移除对象开头_前面的名字
def remove_name_prefix(obj: WwiseObject) -> bool:
    old_name = obj.name
    index = old_name.find('_')
    new_name = old_name[index+1:]
    return waapi_utils.rename_object(obj, new_name)

# 移除对象末尾_后面的名字
def remove_name_suffix(obj: WwiseObject) -> bool:
    old_name = obj.name
    index = old_name.rfind('_')
    new_name = old_name[:index]
    return waapi_utils.rename_object(obj, new_name)


# 使用带有缩写的名称
def get_name_with_acronym(obj_name) -> str:
    index = obj_name.find('_')
    if index <= 0:
        return project_conventions.convert_category_to_acronym(obj_name)
    prefix = obj_name[:index]
    acronym = project_conventions.convert_category_to_acronym(prefix)
    if prefix == acronym:
        return obj_name
    return acronym + obj_name[index:]

# 使用类型的简写作为名称
def rename_with_acronym(obj: WwiseObject) -> bool:
    obj_name = obj.name
    new_name = get_name_with_acronym(obj_name)
    if obj_name == new_name:
        return False
    return waapi_utils.rename_object(obj, new_name)

# 为对象创建父级
def create_parent(obj: WwiseObject, target_type: WwiseObjectType) -> WwiseObject:
    # 先在父级创建一个不同名的新对象
    old_parent = waapi_utils.get_parent_object(obj)
    original_name = obj.name
    new_parent = waapi_utils.create_child_object(original_name + '_Temp', target_type, old_parent, 'rename')
    if new_parent is None:
        return WwiseObject()
    waapi_utils.move_object(obj, new_parent)
    # 将新对象重命名成原对象名
    waapi_utils.rename_object(new_parent, original_name)
    print(f'Parent of type {target_type} created for {obj}')
    return new_parent

# 为路径依次创建文件夹
def create_folders_recursively(path: str) -> WwiseObject:
    obj = waapi_utils.find_object_by_path(path)
    if obj:
        return obj
    splits = path.split('\\')
    node_path = '\\' + splits[1]
    parent = waapi_utils.find_object_by_path(node_path)
    node = WwiseObject()
    for i in range(2, len(splits)):
        node_name = project_conventions.convert_acronym_to_category(splits[i])
        node_path = f'{node_path}\\{node_name}'
        node = waapi_utils.find_object_by_path(node_path)
        if not node:
            node = waapi_utils.create_child_object(node_name, WwiseObjectType.Folder, parent)
            # 没有WorkUnit无法创建VirtualFolder
            if not node:
                node = waapi_utils.create_child_object(node_name, WwiseObjectType.WorkUnit, parent)
            set_object_color_by_category(node, False)
        parent = node
    return node

# 根据命名中的下划线移到文件夹中
def split_underscore_to_folder(obj: WwiseObject) -> bool:
    obj_name = obj.name
    if '_' not in obj_name:
        return False
    splits = obj_name.split('_')
    folder_name = splits[0]
    # 先找已有文件夹，找不到就创建
    folder_path = str(os.path.join(os.path.dirname(obj.path), folder_name))
    folder = waapi_utils.find_object_by_path(folder_path)
    if not folder:
        parent = waapi_utils.get_parent_object(obj)
        folder = waapi_utils.create_child_object(folder_name, WwiseObjectType.Folder, parent)
    waapi_utils.move_object(obj, folder)
    return waapi_utils.rename_object(obj, obj_name[len(folder_name) + 1:])

# 内置访问器基本都是只读的，只有下面这些能写回
WRITABLE_BUILTIN_PROPERTIES = frozenset(("notes",))


# 属性/引用能否写回：内置访问器（id/name/path/children/descendants 等）只读，直接跳过
def is_writable_property_name(name: str) -> bool:
    lower = name.lower()
    return lower not in BUILTIN_ACCESSORS or lower in WRITABLE_BUILTIN_PROPERTIES


# 从属性值里挑出能写回的项：普通标量属性 + 带 id 的引用；列表与无 id 的复合值写不回去
def writable_property_values(values: dict) -> dict:
    return {
        name: value for name, value in values.items()
        if value is not None and not isinstance(value, list)
        and (not isinstance(value, dict) or value.get("id"))
    }


# 读取对象的全部属性/引用当前值：返回 {小写名称: 值}
# 只读内置访问器不读取：既写不回去，像 descendants/children 还会返回大量数据
def read_all_property_values(obj: WwiseObject) -> dict:
    names = [
        name for name in waapi_utils.get_property_and_reference_names(obj)
        if is_writable_property_name(name)
    ]
    snapshot = {}
    if names:
        values = waapi_utils.get_objects_properties_raw([obj], names).get(obj.id, {})
        snapshot = {name.lower(): value for name, value in values.items()}
    # 备注不一定出现在属性名列表里，单独补读一次，避免改类型后丢备注
    if "notes" not in snapshot:
        notes = waapi_utils.get_object_property(obj, "Notes")
        if notes:
            snapshot["notes"] = notes
    return snapshot


# 把属性快照写回对象：只写目标类型也有的属性/引用，跳过只读访问器、列表与空值
# target_names 为目标对象当前的属性/引用名（用它的大小写，值从快照里按小写查）
# 返回写入失败的名称
def restore_property_values(obj: WwiseObject, snapshot: dict, target_names: list) -> list:
    failed = []
    scalar_values = {}
    for name in target_names:
        lower = name.lower()
        value = snapshot.get(lower)
        if value is None or isinstance(value, list):
            continue
        if not is_writable_property_name(lower):
            continue
        if lower == "notes":
            if not waapi_utils.set_object_notes(obj, str(value)):
                failed.append(name)
        elif isinstance(value, dict):
            if value.get("id") and not waapi_utils.set_object_reference(
                obj, name, WwiseObject(value)
            ):
                failed.append(name)
        else:
            scalar_values[name] = value
    # 普通属性一次批量写入，失败再逐个重试，避免个别属性不可写拖垮整批
    if scalar_values and not waapi_utils.set_object_property_values(obj, scalar_values):
        for name, value in scalar_values.items():
            if not waapi_utils.set_object_property(obj, name, value):
                failed.append(name)
    return failed


# 将对象转换类型：改类型会新建对象，因此先把旧对象上的全部属性读出来，改完再写回共有部分
def convert_to_type(obj: WwiseObject, target_type: WwiseObjectType) -> bool:
    if obj.type == target_type:
        return False
    references = waapi_utils.get_object_references(obj)
    snapshot = read_all_property_values(obj)
    if not snapshot:
        Logger().warning(f"读取属性失败，改变类型后不会恢复属性：{obj.path}")
    # 先在父级创建一个不同名的新对象
    parent = waapi_utils.get_parent_object(obj)
    original_name = obj.name
    new_obj = waapi_utils.create_child_object(original_name + '_Temp', target_type, parent, 'rename')
    # 创建失败，返回
    if new_obj is None:
        Logger().info(f"改变类型失败：{obj.path}）→ {target_type.name}")
        return False
    # 将所有子对象移至新对象上
    for child in waapi_utils.get_child_objects(obj):
        waapi_utils.move_object(child, new_obj)
    # 刷新SwitchContainer分配
    if parent.type == WwiseObjectType.SwitchContainer:
        mappings = waapi_utils.get_switch_mappings(parent)
        for mapping in mappings:
            if mapping['child'] == obj.id:
                waapi_utils.assign_switch_mapping(new_obj, mapping['stateOrSwitch'])
    if waapi_utils.delete_object(obj):
        waapi_utils.rename_object(new_obj, original_name)
    if snapshot:
        refreshed = waapi_utils.get_full_info_from_obj_id(new_obj.id)
        if refreshed.is_valid:
            new_obj = refreshed
        # 只写回两个类型 schema 共有的属性/引用
        target_names = waapi_utils.get_property_and_reference_names(new_obj)
        failed_names = restore_property_values(new_obj, snapshot, target_names)
        if failed_names:
            Logger().warning(
                f"改变类型后有 {len(failed_names)} 个属性未能恢复：{obj.path}"
                f"（{'，'.join(failed_names)}）"
            )
    # 刷新引用
    for reference in references:
        if reference.type == WwiseObjectType.SoundBank:
            soundbank_utils.replace_bank_inclusion_with_object(reference, new_obj)
        elif reference.type == WwiseObjectType.EventAction:
            event_utils.set_action_target(reference, new_obj)
    Logger().info(f"改变类型成功：{obj.path} → {target_type.name}")
    return True

# 将选中对象复制到目标对象下
def copy_from_selection(obj: WwiseObject) -> bool:
    selections = waapi_utils.get_selected_objects()
    if len(selections) == 0:
        return False
    for selection in selections:
        waapi_utils.copy_object(selection, obj)
    return True

# 将对象移动到选中对象下
def move_to_selection(obj: WwiseObject) -> bool:
    selections = waapi_utils.get_selected_objects()
    if len(selections) == 0:
        return False
    return waapi_utils.move_object(obj, selections[0])

# 在对象的同一层级查找指定名字的对象
def find_parallel_object(source_obj: WwiseObject, name: str) -> WwiseObject:
    parent = waapi_utils.get_parent_object(source_obj)
    for child in waapi_utils.get_child_objects(parent):
        if child.name == name:
            return child
    return WwiseObject()

# 在对象中筛选未启用的
def filter_objects_by_inclusion(objects: list, inclusion: bool) -> list:
    objects_filtered = []
    for obj in objects:
        included = is_object_included(obj)
        if inclusion == included:
            objects_filtered.append(obj)
    return objects_filtered

# 在对象中筛选特定类型的
def filter_objects_by_type(objects: list, filter_type: str) -> list:
    if filter_type == 'All':
        return objects
    remaining_objects = [obj for obj in objects if obj.type == filter_type]
    return remaining_objects
