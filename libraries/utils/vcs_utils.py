from typing import TYPE_CHECKING

from libraries.utils import user_config

if TYPE_CHECKING:
    from libraries.utils.p4_utils import P4Client, P4Path
    from libraries.utils.svn_utils import SVNClient, SVNPath


def get_vcs_client() -> "P4Client | SVNClient":
    # 根据 user_config.json 的 version_control.mode 返回对应的版本控制客户端单例
    if user_config.get_version_control_mode() == "svn":
        from libraries.utils.svn_utils import SVNClient

        return SVNClient()
    from libraries.utils.p4_utils import P4Client

    return P4Client()


def get_vcs_path(local_path: str, is_dir: bool = False) -> "P4Path | SVNPath":
    # 根据 user_config.json 的 version_control.mode 返回对应的路径对象
    if user_config.get_version_control_mode() == "svn":
        from libraries.utils.svn_utils import SVNPath

        return SVNPath(local_path=local_path, is_dir=is_dir)
    from libraries.utils.p4_utils import P4Path

    return P4Path(local_path=local_path, is_dir=is_dir)
