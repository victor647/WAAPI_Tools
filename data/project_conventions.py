import os
import re
import json
from typing import Any

from libraries.utils.log_utils import Logger
from libraries.utils.wwise import project_utils

conventions = {}


def _resolve_conventions_json_path(project_directory: str) -> str | None:
    # 工程目录下优先 project_conventions.json，其次兼容旧名 ProjectConventions.json；再尝试当前工作目录
    for name in ('project_conventions.json', 'ProjectConventions.json'):
        p = os.path.join(project_directory, name)
        if os.path.isfile(p):
            return p
    for name in ('project_conventions.json', 'ProjectConventions.json'):
        if os.path.isfile(name):
            return name
    return None


# 返回当前生效的工程规范文件路径（找不到时返回 None）
def get_conventions_path() -> str | None:
    try:
        project_directory = project_utils.get_project_directory()
    except Exception:
        project_directory = ""
    return _resolve_conventions_json_path(project_directory)


# 保存工程规范到文件并刷新内存缓存
def save_conventions(new_conventions: dict) -> bool:
    global conventions
    path = get_conventions_path() or "project_conventions.json"
    if not os.path.isfile(path):
        # 工程目录下没有配置文件时，在工程目录新建；取不到工程目录再退回当前目录
        try:
            project_directory = project_utils.get_project_directory()
        except Exception:
            project_directory = ""
        if project_directory:
            path = os.path.join(project_directory, "project_conventions.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new_conventions, f, ensure_ascii=False, indent=2)
    except OSError as e:
        Logger().error(f"写入工程规范文件失败：{path} ({e})")
        return False
    conventions = new_conventions
    return True


# 初始化工程规范配置文件
def init():
    project_directory = project_utils.get_project_directory()
    json_path = _resolve_conventions_json_path(project_directory)
    if json_path and os.path.exists(json_path):
        global conventions
        with open(json_path, 'r', encoding='utf-8') as f:
            conventions = json.load(f)


# 使用颜色规范
def has_color_convention() -> bool:
    if not conventions or 'ColorMap' not in conventions:
        return False
    return conventions['ColorMap'] != {}


# 使用缩写规范
def has_acronym_convention() -> bool:
    if not conventions or 'AcronymMap' not in conventions:
        return False
    return conventions['AcronymMap'] != {}


# 根据对象的名称获取类型
def get_object_category(obj: Any) -> str:
    if not has_acronym_convention():
        return ''
    obj_path = getattr(obj, 'path', None)
    if obj_path is None and isinstance(obj, dict):
        obj_path = obj.get('path', '')
    if not obj_path:
        return ''
    splits = obj_path.split('\\')[1:]
    for name in splits:
        for key, value in conventions['AcronymMap'].items():
            if key in name:
                return key
    return ''


# 根据对象的类型获取应当的颜色
def get_color_by_category(category: str) -> int:
    if not has_color_convention():
        return 0
    for key, value in conventions['ColorMap'].items():
        if key in category:
            return value
    return 0


# 根据全名获取缩写名
def convert_category_to_acronym(category: str) -> str:
    if not has_acronym_convention():
        return category
    for key, value in conventions['AcronymMap'].items():
        if key in category:
            return value
    return category


# 根据全名获取缩写名
def convert_acronym_to_category(acronym: str) -> str:
    if not has_acronym_convention():
        return acronym
    for key, value in conventions['AcronymMap'].items():
        if acronym == value:
            return key
    return acronym


# 在名称中去除缩写
def remove_acronym_from_name(obj_name: str) -> str:
    if not has_acronym_convention():
        return obj_name
    for key, value in conventions['AcronymMap'].items():
        if value in obj_name:
            obj_name = obj_name.replace(value, key)
    return obj_name


# 添加缩写到名称中
def add_acronym_from_name(obj_name: str) -> str:
    if not has_acronym_convention():
        return obj_name
    for key, value in conventions['AcronymMap'].items():
        if key in obj_name:
            obj_name = obj_name.replace(key, value)
    return obj_name


# 根据容器类型获取对应末尾命名规范
def get_container_suffix_pattern(container_type: str) -> str:
    if not conventions or 'ContainerSuffix' not in conventions:
        return ''
    if container_type not in conventions['ContainerSuffix']:
        return ''
    return conventions['ContainerSuffix'][container_type]


# 获取1P/2P/3P的后缀
def get_net_role_suffix(role: str) -> str:
    if not conventions or 'NetRole' not in conventions:
        return '_' + role
    return conventions['NetRole']['Suffix'][role]


# 获取1P/2P/3P的SwitchGroup名称
def get_net_role_switch_group() -> str:
    if not conventions or 'NetRole' not in conventions:
        return 'Net_Role'
    return conventions['NetRole']['SwitchGroup']


# 获取1P/2P/3P的Switch名称
def get_net_role_switch_name(role: str) -> str:
    if not conventions or 'NetRole' not in conventions:
        return 'Net_Role'
    return conventions['NetRole']['SwitchValues'][role]


# 判定对象的名称是否包含123P的后缀
def get_net_role_suffix_from_name(obj_name: str) -> str:
    if not conventions:
        pattern = re.search(r'_[1-3]P$', obj_name)
        if not pattern:
            return ''
        return pattern.group()
    for suffix in conventions['NetRole']['Suffix'].values():
        if suffix in obj_name:
            return suffix
    return ''


# 获取1P默认的后缀
def get_default_net_role_suffix() -> str:
    if not conventions:
        return '_1P'
    return conventions['NetRole']['Suffix']['1P']


# 获取已经接入的语言列表
def get_implemented_languages() -> list:
    if not conventions or 'ImplementedLanguages' not in conventions:
        return ['Chinese', 'English']
    return conventions['ImplementedLanguages']


# 是否使用全名作为Sound节点名称
def use_full_name_in_sound() -> bool:
    if not conventions or 'FullNameInSound' not in conventions:
        return True
    return conventions['FullNameInSound']


# 事件是否以Play_开头
def has_event_play_prefix() -> bool:
    if not conventions or 'PlayPrefixInEvent' not in conventions:
        return False
    return conventions['PlayPrefixInEvent']
