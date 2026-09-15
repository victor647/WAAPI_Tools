import os
import re
import json
import shutil
import sys
from typing import Any

from libraries.utils import path_utils
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import project_utils

conventions = {}
# 当前内存中规范数据实际来自哪个文件；保存时写回同一个文件
_conventions_path = ""

# 工程规范文件名：优先新名，其次兼容旧名
CONVENTIONS_FILE_NAMES = ('project_conventions.json', 'ProjectConventions.json')
# 新建或从内置副本初始化时使用的文件名
CONVENTIONS_FILE_NAME = 'ProjectConventions.json'

# 名称大小写规范的校验方式：title=首字母大写，lower=全小写，upper=全大写
NAME_CASE_MODES = ('title', 'lower', 'upper')
DEFAULT_NAME_CASE_MODE = 'title'

# Bank 设置默认值：默认使用自动定义的 Bank，且不拆分 Event 与 Media
DEFAULT_USE_AUTO_DEFINED_BANK = True
DEFAULT_SPLIT_EVENT_MEDIA = False

# Event 设置默认值：默认不加 Play_ 前缀、引用对象使用深色、Event 与播放对象互为备注
DEFAULT_EVENT_PLAY_PREFIX = False
DEFAULT_EVENT_REF_DARK_COLOR = True
DEFAULT_EVENT_REF_NOTES = True


def _app_dir() -> str:
    # 打包后为 exe 所在目录（可写），开发环境为仓库根目录
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    try:
        return path_utils.find_dev_project_root()
    except RuntimeError:
        return ""


def _bundled_conventions_path() -> str:
    # 打包时随 exe 打入的工程规范副本（见 packager/WAAPI_Tools_GUI.spec 的 datas）
    if not getattr(sys, "frozen", False):
        return ""
    for name in CONVENTIONS_FILE_NAMES:
        bundled = path_utils.get_resource_path(name)
        if os.path.isfile(bundled):
            return bundled
    return ""


def _initialize_conventions_file() -> str:
    # 工程目录与应用目录都没有规范文件时，用打包内置副本初始化出一份可写文件；
    # 复制失败（例如目录只读）则本次直接使用内置副本
    bundled = _bundled_conventions_path()
    if not bundled:
        return ""
    target = os.path.join(_app_dir(), os.path.basename(bundled))
    try:
        shutil.copyfile(bundled, target)
        Logger().info(f"已使用内置工程规范初始化配置文件: {target}")
        return target
    except OSError as e:
        Logger().warning(f"写入工程规范文件失败，本次直接使用内置配置: {target} ({e})")
        return bundled


def _resolve_conventions_json_path(project_directory: str) -> str | None:
    # 依次查找：Wwise 工程目录、应用目录（exe 目录或仓库根目录），最后兜底当前工作目录
    directories = [directory for directory in (project_directory, _app_dir()) if directory]
    directories.append("")
    for directory in directories:
        for name in CONVENTIONS_FILE_NAMES:
            p = os.path.join(directory, name) if directory else name
            if os.path.isfile(p):
                return p
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
    global conventions, _conventions_path
    # 优先写回最近一次读取的文件；没有读取记录时再重新解析
    path = _conventions_path or get_conventions_path()
    if not path:
        # 没有现成文件时：工程目录优先（每工程独立规范），取不到工程目录则写到应用目录
        try:
            project_directory = project_utils.get_project_directory()
        except Exception:
            project_directory = ""
        directory = project_directory or _app_dir()
        path = os.path.join(directory, CONVENTIONS_FILE_NAME) if directory else CONVENTIONS_FILE_NAME
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new_conventions, f, ensure_ascii=False, indent=2)
    except OSError as e:
        Logger().error(f"写入工程规范文件失败：{path} ({e})")
        return False
    conventions = new_conventions
    _conventions_path = path
    return True


# 初始化工程规范配置文件
def init():
    global conventions, _conventions_path
    # 未连接 Wwise 时取不到工程目录，退回应用目录的规范文件，避免整个应用拿不到规范数据
    json_path = get_conventions_path()
    if not json_path:
        json_path = _initialize_conventions_file()
    if json_path and os.path.exists(json_path):
        with open(json_path, "r", encoding='utf-8') as f:
            conventions = json.load(f)
        # 记住实际读取的文件（只读的内置副本除外，保存时另行寻找可写位置）
        _conventions_path = "" if json_path == _bundled_conventions_path() else json_path


# 规范配置节点：新结构为 <X>Convention 子节点（Enabled + 数据表），兼容旧的顶层平铺字段
def _convention_section(name: str) -> dict:
    if not conventions:
        return {}
    section = conventions.get(name)
    return section if isinstance(section, dict) else {}


# 规范开关：关闭时对应转换与检查全部跳过；旧配置的 EnableAcronymColor 兼容映射到缩写与颜色
def _enabled_flag(section_name: str, legacy_keys: tuple = (), default: bool = True) -> bool:
    section = _convention_section(section_name)
    if 'Enabled' in section:
        return bool(section['Enabled'])
    if conventions:
        for key in legacy_keys:
            if key in conventions:
                return bool(conventions[key])
    return default


# 缩写映射表（分类全名 -> 缩写）
def get_acronym_map() -> dict:
    section = _convention_section('AcronymConvention')
    if 'AcronymMap' in section:
        return section['AcronymMap'] or {}
    if not conventions:
        return {}
    return conventions.get('AcronymMap') or {}


# 颜色映射表（分类全名 -> Wwise 颜色值）
def get_color_map() -> dict:
    section = _convention_section('ColorConvention')
    if 'ColorMap' in section:
        return section['ColorMap'] or {}
    if not conventions:
        return {}
    return conventions.get('ColorMap') or {}


# Event 设置：被 Event 引用的对象是否使用同色系深色（仅影响自动调整颜色的工具）
def use_dark_color_for_event_ref() -> bool:
    section = _convention_section('EventConvention')
    if 'RefDarkColor' in section:
        return bool(section['RefDarkColor'])
    # 旧配置把该项放在颜色规范里
    legacy = _convention_section('ColorConvention')
    if 'EventRefDarkColor' in legacy:
        return bool(legacy['EventRefDarkColor'])
    return DEFAULT_EVENT_REF_DARK_COLOR


# Event 设置：Event 与播放对象是否互为备注（关闭后自动更新备注的工具不再改动 Notes）
def use_event_ref_notes() -> bool:
    section = _convention_section('EventConvention')
    if 'RefNotes' in section:
        return bool(section['RefNotes'])
    # 旧配置把该项放在顶层
    if not conventions or 'EventRefNotes' not in conventions:
        return DEFAULT_EVENT_REF_NOTES
    return bool(conventions['EventRefNotes'])


def is_acronym_enabled() -> bool:
    return _enabled_flag('AcronymConvention', ('EnableAcronym', 'EnableAcronymColor'))


def is_color_enabled() -> bool:
    return _enabled_flag('ColorConvention', ('EnableColor', 'EnableAcronymColor'))


def is_name_case_enabled() -> bool:
    return _enabled_flag('NameCaseConvention', ('EnableNameCase',))


# 大小写检查方式（无该字段时按旧配置当作首字母大写）
def get_name_case_mode() -> str:
    section = _convention_section('NameCaseConvention')
    mode = section.get('Mode')
    if isinstance(mode, str) and mode in NAME_CASE_MODES:
        return mode
    return DEFAULT_NAME_CASE_MODE


def is_path_length_enabled() -> bool:
    return _enabled_flag('PathLengthConvention', ('EnablePathLength',))


# Sound 节点是否使用完整名称（隶属路径长度规范）；兼容旧的顶层 FullNameInSound
def use_full_name_in_sound() -> bool:
    section = _convention_section('PathLengthConvention')
    if 'FullNameInSound' in section:
        return bool(section['FullNameInSound'])
    if not conventions or 'FullNameInSound' not in conventions:
        return True
    return conventions['FullNameInSound']


# 使用颜色规范
def has_color_convention() -> bool:
    if not is_color_enabled():
        return False
    return get_color_map() != {}


# 使用缩写规范
def has_acronym_convention() -> bool:
    if not is_acronym_enabled():
        return False
    return get_acronym_map() != {}


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
        for key, value in get_acronym_map().items():
            if key in name:
                return key
    return ''


# 根据对象的类型获取应当的颜色
def get_color_by_category(category: str) -> int:
    if not has_color_convention():
        return 0
    for key, value in get_color_map().items():
        if key in category:
            return value
    return 0


# 根据全名获取缩写名
def convert_category_to_acronym(category: str) -> str:
    if not has_acronym_convention():
        return category
    for key, value in get_acronym_map().items():
        if key in category:
            return value
    return category


# 根据全名获取缩写名
def convert_acronym_to_category(acronym: str) -> str:
    if not has_acronym_convention():
        return acronym
    for key, value in get_acronym_map().items():
        if acronym == value:
            return key
    return acronym


# 在名称中去除缩写
def remove_acronym_from_name(obj_name: str) -> str:
    if not has_acronym_convention():
        return obj_name
    for key, value in get_acronym_map().items():
        if value in obj_name:
            obj_name = obj_name.replace(value, key)
    return obj_name


# 添加缩写到名称中
def add_acronym_from_name(obj_name: str) -> str:
    if not has_acronym_convention():
        return obj_name
    for key, value in get_acronym_map().items():
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


# 获取1P/2P/3P的Bus后缀；未单独配置时跟随名称后缀。
# 把2P的Bus后缀填成3P的后缀即表示不区分2P/3P Bus，此时两者复用同一个Bus
def get_net_role_bus_suffix(role: str) -> str:
    if not conventions or 'NetRole' not in conventions:
        return '_' + role
    net_role = conventions['NetRole']
    bus_suffix = (net_role.get('BusSuffix') or {}).get(role)
    if bus_suffix:
        return bus_suffix
    return (net_role.get('Suffix') or {}).get(role, '_' + role)


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


# 获取未接入的语言列表（这些语言不参与本地化检查）
def get_unimplemented_languages() -> list:
    if not conventions or 'UnimplementedLanguages' not in conventions:
        return []
    return conventions['UnimplementedLanguages']


# Event 设置：事件是否以 Play_ 开头（旧配置放在顶层 PlayPrefixInEvent）
def has_event_play_prefix() -> bool:
    section = _convention_section('EventConvention')
    if 'PlayPrefix' in section:
        return bool(section['PlayPrefix'])
    if not conventions or 'PlayPrefixInEvent' not in conventions:
        return DEFAULT_EVENT_PLAY_PREFIX
    return bool(conventions['PlayPrefixInEvent'])


# Bank 设置：是否使用自动定义的 Bank
def use_auto_defined_bank() -> bool:
    section = _convention_section('BankConvention')
    if 'UseAutoDefinedBank' in section:
        return bool(section['UseAutoDefinedBank'])
    return DEFAULT_USE_AUTO_DEFINED_BANK


# Bank 设置：拆分开关的配置值（不受「自动定义的Bank」影响，供设置界面回显）
def get_split_event_media_setting() -> bool:
    section = _convention_section('BankConvention')
    if 'SplitEventMedia' in section:
        return bool(section['SplitEventMedia'])
    return DEFAULT_SPLIT_EVENT_MEDIA


# Bank 是否按 Event / Media 拆分：仅在关闭「使用自动定义的Bank」后才生效
def split_bank_event_media() -> bool:
    if use_auto_defined_bank():
        return False
    return get_split_event_media_setting()
