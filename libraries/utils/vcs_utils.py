import os
from typing import TYPE_CHECKING

from data import project_conventions
from libraries.utils.log_utils import Logger

if TYPE_CHECKING:
    from libraries.utils.p4_utils import P4Client, P4Path
    from libraries.utils.svn_utils import SVNClient, SVNPath


# 是否使用 SVN（版本控制类型来自工程规范文件的 VersionControl 节点）
def is_svn() -> bool:
    return project_conventions.get_version_control_mode() == "svn"


def get_vcs_client() -> "P4Client | SVNClient":
    # 根据工程规范里的版本控制类型返回对应的客户端单例
    if is_svn():
        from libraries.utils.svn_utils import SVNClient

        return SVNClient()
    from libraries.utils.p4_utils import P4Client

    return P4Client()


def get_vcs_path(local_path: str, is_dir: bool = False) -> "P4Path | SVNPath":
    # 根据工程规范里的版本控制类型返回对应的路径对象
    if is_svn():
        from libraries.utils.svn_utils import SVNPath

        return SVNPath(local_path=local_path, is_dir=is_dir)
    from libraries.utils.p4_utils import P4Path

    return P4Path(local_path=local_path, is_dir=is_dir)


# 文件作者查询缓存：{规范化本地路径: 作者}；同一 WorkUnit 下的对象共用一次查询
_author_cache: dict[str, str] = {}
# 版本控制可用性：探测一次后缓存（None 表示还没探测）
_available: bool | None = None


# 版本控制是否可用：svn 看命令能否执行，p4 看能否连上服务器
def is_available() -> bool:
    global _available
    if _available is None:
        _available = _probe_available()
    return _available


# 清空可用性与作者缓存（切换工程或版本控制设置变化后调用）
def clear_cache() -> None:
    global _available
    _author_cache.clear()
    _available = None


# 文件最后一次提交的作者；未纳入版本控制或查询失败返回空串
def get_file_author(file_path: str) -> str:
    if not file_path or not os.path.isfile(file_path):
        return ""
    key = os.path.normcase(os.path.abspath(file_path))
    if key in _author_cache:
        return _author_cache[key]
    author = ""
    if is_available():
        try:
            author = get_vcs_client().get_last_changed_author(get_vcs_path(key)) or ""
        except Exception as e:
            Logger().error(f"查询版本控制作者失败：{file_path} ({e})")
    _author_cache[key] = author
    return author


def _probe_available() -> bool:
    try:
        client = get_vcs_client()
    except Exception as e:
        # p4python 未安装等情况：只提示一次，之后按不可用处理
        Logger().warning(f"版本控制客户端不可用（{project_conventions.get_version_control_mode()}）：{e}")
        return False
    available = bool(client.is_available())
    Logger().debug(f"版本控制可用性：{type(client).__name__} -> {available}")
    return available


# 本地文件是否受版本控制管理：决定文件移动走版本控制 move 还是普通文件移动
def is_file_managed(local_path: str) -> bool:
    if not local_path or not is_available():
        return False
    try:
        client = get_vcs_client()
        if is_svn():
            # SVN 的工作副本根依赖路径本身，这里全部用本地元数据判断，不访问服务器
            return bool(client.is_versioned(local_path) or client.has_local_modification(local_path))
        vcs_path = get_vcs_path(local_path)
        return bool(client.is_in_depot(vcs_path) or client.is_in_pending_changelist(vcs_path))
    except Exception as e:
        Logger().debug(f"判断文件是否受版本控制管理失败：{local_path} ({e})")
        return False
