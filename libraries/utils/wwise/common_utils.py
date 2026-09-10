import os.path
from data import project_conventions
from libraries.utils.wwise import audio_source_utils, soundbank_utils, event_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType
from libraries.utils.log_utils import Logger


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
    obj_type = obj.type
    if obj_path.startswith('\\Actor-Mixer Hierarchy'):
        if obj.type == WwiseObjectType.Sound:
            if audio_source_utils.sound_play_from_plugin(obj):
                return rename_to_short_name(obj)
            return rename_to_full_name(obj)
        return rename_to_short_name(obj)
    elif obj_path.startswith('\\Interactive Music Hierarchy'):
        if obj_type == 'MusicSegment' or obj_type == 'MusicTrack':
            return False
        return rename_to_short_name(obj)
    else:
        print(f"{obj_type} [{obj.name}] does not need to follow naming length convention.")
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
        actions = waapi_utils.get_child_objects(obj)
        for action in actions:
            action_type = waapi_utils.get_object_property(action, 'ActionType')
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
        for reference in references:
            ref_type = reference.type
            if ref_type == WwiseObjectType.EventAction:
                action_type = waapi_utils.get_object_property(reference, 'ActionType')
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
    for reference in references:
        ref_type = reference.type
        if ref_type == WwiseObjectType.EventAction:
            action_type = waapi_utils.get_object_property(reference, 'ActionType')
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
) -> bool:
    if 'Hierarchy' not in obj.path:
        return True
    cache_key = obj.id if check_ancestors else ""
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
        included = is_object_included(parent, inclusion_cache=inclusion_cache)
        if cache_key and inclusion_cache is not None:
            inclusion_cache[cache_key] = included
        return included
    included = waapi_utils.get_object_property(obj, 'Inclusion')
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
        included = is_object_included(parent, inclusion_cache=inclusion_cache)
    if cache_key and inclusion_cache is not None:
        inclusion_cache[cache_key] = included
    return included

# 启用对象
def set_object_inclusion(obj: WwiseObject, included: bool) -> bool:
    return waapi_utils.set_object_property(obj, 'Inclusion', included)

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

# 将对象转换类型
def convert_to_type(obj: WwiseObject, target_type: WwiseObjectType) -> bool:
    if obj.type == target_type:
        return False
    references = waapi_utils.get_object_references(obj)
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
