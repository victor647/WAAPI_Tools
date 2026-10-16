import os
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import waapi_utils

wwise_version = 0
# 工程路径缓存：会话内工程路径不变，避免每次换算 Originals 目录都发起一次 WAAPI 查询
_project_path_cache = ""


# 清空工程级缓存（切换/重新连接工程后调用）
def clear_project_cache() -> None:
    global _project_path_cache, wwise_version
    _project_path_cache = ""
    wwise_version = 0


# 获取工程路径
def get_project_path() -> str:
    global _project_path_cache
    if not _project_path_cache:
        _project_path_cache = waapi_utils.get_project_property('filePath') or ""
    return _project_path_cache


# 获取工程配置的所有平台（[{id, name, baseName, ...}]）
def get_platforms() -> list:
    return list(waapi_utils.get_project_info('platforms') or [])


# 平台名：兼容 WAAPI 返回的 dict / 对象两种形态
def _platform_name(platform) -> str:
    return platform.get('name') if isinstance(platform, dict) else getattr(platform, 'name', '')


# 获取当前平台名称（取 currentPlatformId 对应的平台；取不到时退回工程的第一个平台）
def get_current_platform_name() -> str:
    current_id = str(waapi_utils.get_project_info('currentPlatformId') or '').strip('{}').lower()
    platforms = get_platforms()
    for platform in platforms:
        platform_id = platform.get('id') if isinstance(platform, dict) else getattr(platform, 'id', '')
        if platform_id and current_id and str(platform_id).strip('{}').lower() == current_id:
            return _platform_name(platform)
    for platform in platforms:
        name = _platform_name(platform)
        if name:
            return name
    return ""


# 判断工程是否带有特定名称的平台
def has_platform(platform_name: str) -> bool:
    return any(_platform_name(platform) == platform_name for platform in get_platforms())


# 获取工程所在文件夹
def get_project_directory() -> str:
    return os.path.dirname(get_project_path())


# 获取Originals所在目录
def get_originals_folder() -> str:
    directory = get_project_directory()
    return os.path.join(directory, 'Originals')


# 获取项目的Wwise版本
def get_project_version() -> int:
    global wwise_version
    if wwise_version == 0:
        ver = waapi_utils.get_authoring_info("version")
        wwise_version = ver['year'] if isinstance(ver, dict) else ver.year
    return wwise_version


# 保存工程：把 Wwise 内存里的改动写回工程文件（用户自己的未保存改动会一并落盘）
def save_project() -> bool:
    saved = waapi_utils.save_project()
    if saved:
        Logger().info('已保存工程')
    else:
        Logger().error('保存工程失败')
    return saved
