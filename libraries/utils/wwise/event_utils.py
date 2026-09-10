import os
from data import project_conventions
from libraries.utils import io_utils, path_utils
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import common_utils, audio_source_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType


# 为每个选中的对象创建一个播放事件
def create_play_event(obj: WwiseObject) -> bool:
    obj_type = obj.type
    obj_path = obj.path
    if 'Container' not in obj_type.value and obj_type != WwiseObjectType.Sound:
        print(f'{obj_type} [{obj_path}] cannot be an event target.')
        return False

    event_name = get_event_name(obj)
    event = waapi_utils.find_object_by_name_and_type(event_name, WwiseObjectType.Event)
    # 已有事件，替换播放对象
    if event:
        targets = get_event_targets(event)
        if len(targets) == 0 or targets[0] != obj:
            clear_event_actions(event)
            create_event_action(event, obj, 1)
            print(f'Assigning {obj_type} [{obj_path}] to existing event [{event_name}].')
        else:
            print(f'An existing event [{event_name}] found for target {obj_type} [{obj_path}].')
    # 创建新的事件
    else:
        if '_' in event_name:
            event_path = project_conventions.remove_acronym_from_name(event_name.replace('_', '\\'))
            parent_path = os.path.dirname('\\Events\\' + event_path)
            parent = common_utils.create_folders_recursively(parent_path)
        else:
            parent_path = '\\Events\\Default Work Unit'
            parent = waapi_utils.find_object_by_path(parent_path)
        if not parent:
            return False
        event = waapi_utils.create_child_object(event_name, WwiseObjectType.Event, parent)
        create_event_action(event, obj, 1)
        # End的事件需要停止Start
        if obj.name == 'End':
            obj_start = common_utils.find_parallel_object(obj, 'Start')
            if obj_start:
                action = create_event_action(event, obj_start, 2)
                waapi_utils.set_object_property(action, 'FadeTime', 0.5)
    common_utils.update_notes_and_color(obj)
    return waapi_utils.select_objects_in_wwise([event])

# 为事件创建播放动作
def create_event_action(event: WwiseObject, target: WwiseObject, action_type: int) -> WwiseObject:
    if not event or not target:
        return WwiseObject()
    action = waapi_utils.create_child_object(event.name, WwiseObjectType.EventAction, event)
    waapi_utils.set_object_property(action, 'ActionType', action_type)
    set_action_target(action, target)
    return action

# 清除事件中所有的动作
def clear_event_actions(event: WwiseObject) -> bool:
    actions = waapi_utils.get_child_objects(event)
    for action in actions:
        waapi_utils.delete_object(action)
    return True

# 获取对象对应的事件名称
def get_event_name(obj: WwiseObject) -> str:
    obj_name = obj.name
    if obj.type == WwiseObjectType.Sound and project_conventions.use_full_name_in_sound():
        if '_' in obj_name and audio_source_utils.get_source_absolute_path(obj):
            event_name = obj_name
        else:
            event_name = common_utils.get_full_name_with_acronym(obj)
    elif '_' in obj_name:
        event_name = obj_name
    else:
        event_name = common_utils.get_full_name_with_acronym(obj)
    if obj.path.startswith('\\Interactive Music Hierarchy'):
        event_name = 'BGM_' + event_name
    if project_conventions.has_event_play_prefix():
        event_name = 'Play_' + event_name
    return event_name

# 获取Event的目标对象
def get_event_targets(event: WwiseObject) -> list:
    actions = waapi_utils.get_child_objects(event)
    if len(actions) == 0:
        print(f"Event [{event.name}] has no actions!")
        return []
    targets = []
    for action in actions:
        target = waapi_utils.get_referenced_object(action, 'Target')
        if not target:
            print(f"Event [{event.name}] has an action with no target!")
            continue
        if not target.name:
            print(f"Event [{event.name}] has an action with missing target!")
            continue
        target = waapi_utils.get_full_info_from_obj_id(target.id)
        if target and target.is_valid:
            targets.append(target)
    return targets

# 改变Action的目标对象
def set_action_target(action: WwiseObject, target: WwiseObject) -> bool:
    return waapi_utils.set_object_reference(action, 'Target', target)

# 根据播放对象重命名事件
def rename_event_by_target(event: WwiseObject) -> bool:
    if event.type != WwiseObjectType.Event:
        return False
    targets = get_event_targets(event)
    if len(targets) == 1:
        full_name = get_event_name(targets[0])
        waapi_utils.rename_object(event, full_name)
        common_utils.update_notes_and_color(event)
        return True
    return False

# 对象是否被某个事件所引用
def has_event_reference(obj) -> bool:
    references = waapi_utils.get_object_references(obj)
    for reference in references:
        if reference.type == WwiseObjectType.EventAction:
            return True
    return False

# 导出全部事件及其播放内容
def export_all_events():
    data = []
    all_events = waapi_utils.find_all_objects_by_type(WwiseObjectType.Event)
    for event in all_events:
        targets = get_event_targets(event)
        event_data = [event.name]
        for target in targets:
            event_data.append(target.path)
        data.append(event_data)
    io_utils.export_to_csv(data, 'All_Events')
    Logger().info(f'导出完成，共导出{len(data)}条事件')

# 获取事件所有音频资源的路径
def get_all_wave_paths(event_obj: WwiseObject, relative_path: bool) -> list:
    targets = get_event_targets(event_obj)
    if not targets:
        return []
    paths = []
    for target in targets:
        if target.type == WwiseObjectType.Sound:
            paths.append(audio_source_utils.get_source_absolute_path(target))
        else:
            # 递归查找子级
            def find_sounds_recursively(obj):
                for child in waapi_utils.get_child_objects(obj):
                    if child.type == WwiseObjectType.Sound:
                        path = audio_source_utils.get_source_absolute_path(child)
                        if relative_path:
                            path = path_utils.trim_after(path, "Originals\\")
                        paths.append(path)
                    else:
                        find_sounds_recursively(child)
            find_sounds_recursively(target)
    return paths
