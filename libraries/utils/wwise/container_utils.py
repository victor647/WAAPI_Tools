import re

from data import project_conventions
from libraries.utils.wwise import waapi_utils, mixing_utils, wwise_compat
from libraries.wwise_object import WwiseObjectType, WwiseObject


# 打破Container并将内容移出
def break_container(container: WwiseObject) -> bool:
    children = waapi_utils.get_child_objects(container)
    parent = waapi_utils.get_parent_object(container)
    for child in children:
        waapi_utils.move_object(child, parent)
    return waapi_utils.delete_object(container)

# 替换父级对象并分配Switch Container
def replace_parent(obj: WwiseObject) -> bool:
    parent = waapi_utils.get_parent_object(obj)
    grand_parent = waapi_utils.get_parent_object(parent)
    waapi_utils.move_object(obj, grand_parent)
    if grand_parent.type == WwiseObjectType.SwitchContainer:
        mappings = waapi_utils.get_switch_mappings(grand_parent)
        for mapping in mappings:
            if mapping['child'] == parent.id:
                waapi_utils.assign_switch_mapping(obj, mapping['stateOrSwitch'])
    if waapi_utils.delete_object(parent):
        return waapi_utils.rename_object(obj, parent.name)
    return False

# region SwitchContainer
# 根据名称为Switch Container的下级自动分配
def auto_assign_switch_mappings(container: WwiseObject) -> bool:
    if container.type != WwiseObjectType.SwitchContainer:
        return False
    # 获取Switch Group中所有可能值
    switch_objects = get_available_switch_items(container)
    if len(switch_objects) == 0:
        return False

    # 找到Switch Container里面的所有子对象
    switch_container_children = waapi_utils.get_child_objects(container)
    assigned = False
    for child in switch_container_children:
        for switch_obj in switch_objects:
            # 两者名字任一包括即符合
            switch_name = switch_obj.name
            child_name = child.name
            if switch_name in child_name or child_name in switch_name:
                assigned |= waapi_utils.assign_switch_mapping(child, switch_obj)
    return assigned

# 获取SwitchContainer当前分配的Switch下面所有的选项
def get_available_switch_items(container: WwiseObject) -> list:
    if container.type != WwiseObjectType.SwitchContainer:
        return []
    group = waapi_utils.get_referenced_object(container, 'SwitchGroupOrStateGroup')
    if group:
        children = waapi_utils.get_child_objects(group)
        return children
    return []

# 设置为通用路径分配的对象
def assign_to_generic_path(obj: WwiseObject) -> bool:
    parent = waapi_utils.get_parent_object(obj)
    switch_items = get_available_switch_items(parent)
    if len(switch_items) == 0:
        return False

    mappings = waapi_utils.get_switch_mappings(parent)
    assigned = False
    for item in switch_items:
        found = False
        for mapping in mappings:
            if item.id == mapping['stateOrSwitch']:
                found = True
                break
        if not found:
            assigned |= waapi_utils.assign_switch_mapping(obj, item)
    return assigned

# 将一个对象根据自己，队友(可选)和敌人拆分成子对象
def split_by_net_role(obj: WwiseObject, has_teammate: bool, has_enemy: bool) -> bool:
    # Actor Mixer和Virtual Folder无法被放在SwitchContainer下面
    if wwise_compat.is_property_container(obj) or obj.type == WwiseObjectType.Folder:
        return False
    if not has_teammate and not has_enemy:
        return False
    original_name = obj.name
    suffix_1p = project_conventions.get_net_role_suffix('1P')
    suffix_2p = project_conventions.get_net_role_suffix('2P')
    suffix_3p = project_conventions.get_net_role_suffix('3P')
    bus_suffix_1p = project_conventions.get_net_role_bus_suffix('1P')
    bus_suffix_2p = project_conventions.get_net_role_bus_suffix('2P')
    bus_suffix_3p = project_conventions.get_net_role_bus_suffix('3P')
    obj_teammate = obj_enemy = None
    # 拆分结构并重组到SwitchContainer下面
    old_parent = waapi_utils.get_parent_object(obj)
    new_parent = waapi_utils.create_child_object(original_name + '_Temp', WwiseObjectType.SwitchContainer, old_parent, 'rename')
    waapi_utils.move_object(obj, new_parent)
    waapi_utils.rename_object(obj, original_name + suffix_1p)
    if has_teammate:
        obj_teammate = waapi_utils.copy_object(obj, new_parent)
        waapi_utils.rename_object(obj_teammate, original_name + suffix_2p)
    if has_enemy:
        obj_enemy = waapi_utils.copy_object(obj, new_parent)
        waapi_utils.rename_object(obj_enemy, original_name + suffix_3p)
    waapi_utils.rename_object(new_parent, original_name)
    # 创建并分配bus
    original_bus = mixing_utils.get_output_bus(obj)
    if original_bus and not original_bus.name:
        original_bus = waapi_utils.get_full_info_from_obj_id(original_bus.id)
    if original_bus and original_bus.name != 'Master Audio Bus':
        original_bus_name = original_bus.name
        bus_self = mixing_utils.get_or_create_bus(original_bus_name + bus_suffix_1p, original_bus)
        # 2P 与 3P 的后缀填成一样（如都填 _3P）即代表不区分，get_or_create_bus 会复用同一个 Bus
        bus_teammate = mixing_utils.get_or_create_bus(original_bus_name + bus_suffix_2p, original_bus) if has_teammate else None
        bus_enemy = mixing_utils.get_or_create_bus(original_bus_name + bus_suffix_3p, original_bus) if has_enemy else None
        mixing_utils.set_output_bus(obj, bus_self)
        if has_teammate:
            mixing_utils.set_output_bus(obj_teammate, bus_teammate)
        if has_enemy:
            mixing_utils.set_output_bus(obj_enemy, bus_enemy)
    # 为1P和3P对象设置空间开关
    mixing_utils.set_sound_3d(obj, False)
    if has_teammate:
        mixing_utils.set_sound_3d(obj_teammate, True)
    if has_enemy:
        mixing_utils.set_sound_3d(obj_enemy, True)
    role_switch_group = waapi_utils.find_object_by_name_and_type(project_conventions.get_net_role_switch_group(), WwiseObjectType.SwitchGroup)
    if role_switch_group is None:
        return False
    # 为SwitchContainer分配SwitchGroup
    waapi_utils.set_object_reference(new_parent, 'SwitchGroupOrStateGroup', role_switch_group)
    for switch_value in waapi_utils.get_child_objects(role_switch_group):
        switch_name = switch_value.name
        if switch_name == project_conventions.get_net_role_switch_name('1P'):
            waapi_utils.assign_switch_mapping(obj, switch_value)
        elif has_teammate and switch_name == project_conventions.get_net_role_switch_name('2P'):
            waapi_utils.assign_switch_mapping(obj_teammate, switch_value)
            # 默认不能是1P
            if not has_enemy:
                waapi_utils.set_object_reference(new_parent, 'DefaultSwitchOrState', switch_value)
        elif has_enemy and switch_name == project_conventions.get_net_role_switch_name('3P'):
            waapi_utils.assign_switch_mapping(obj_enemy, switch_value)
            waapi_utils.set_object_reference(new_parent, 'DefaultSwitchOrState', switch_value)
    return True

# 将SwitchContainer的默认值设为3P
def set_default_switch_to_3p(container: WwiseObject) -> bool:
    switches = get_available_switch_items(container)
    switch_name = project_conventions.get_net_role_switch_name('3P')
    for switch in switches:
        if switch_name in switch.name:
            return waapi_utils.set_object_property(container, 'DefaultSwitchOrState', switch)
    return False
# endregion SwitchContainer

# region RandomContainer
# 重命名随机容器下的对象为数字
def rename_random_children(container: WwiseObject) -> bool:
    if container.type != WwiseObjectType.RandomContainer:
        return False
    children = waapi_utils.get_child_objects(container)
    renamed = False
    for i in range(len(children)):
        renamed |= waapi_utils.rename_object(children[i], '{:02d}'.format(i + 1))
    return renamed

# 将对象根据命名规范自动归类到随机容器
def group_as_random(obj: WwiseObject) -> bool:
    if obj.type != WwiseObjectType.Sound:
        return False
    obj_name = obj.name
    pattern = re.search(r'_\d+$', obj_name) or re.search(r'-\d+$', obj_name)
    if pattern is None:
        return False
    parent = waapi_utils.get_parent_object(obj)
    if parent.type == WwiseObjectType.RandomContainer:
        return False
    parent_name = obj_name.replace(pattern.group(), '')
    parent_container = waapi_utils.find_object_by_name_and_type(parent_name, WwiseObjectType.RandomContainer)
    if not parent_container:
        parent_container = waapi_utils.create_child_object(parent_name, WwiseObjectType.RandomContainer, parent)
    return waapi_utils.move_object(obj, parent_container)
# endregion RandomContainer
