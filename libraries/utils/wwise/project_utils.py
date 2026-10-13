import os
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


# 判断工程是否带有特定名称的平台
def has_platform(platform_name: str) -> bool:
    platforms = waapi_utils.get_project_info('platforms')
    for platform in platforms:
        n = platform.get('name') if isinstance(platform, dict) else getattr(platform, 'name', None)
        if n == platform_name:
            return True
    return False


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
