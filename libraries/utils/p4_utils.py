import os
import re
import glob
from enum import Enum
from P4 import P4, P4Exception
from PySide6.QtCore import QDateTime

from libraries.utils.log_utils import Logger
from libraries.singleton import Singleton

P4_SERVER = "10.21.100.45:1666"
P4_CHARSET = "utf8"
P4_CHANGELIST_DESCRIPTION = "【FFSoundTool】自动创建的修改"

NEW_CHANGELIST_REGEX = re.compile(r"Change (\d+) created.")

# 仓库或本地路径
class P4PathType(Enum):
    DepotPath = 0
    LocalPath = 1

# 回退时的选项
class P4RevertOption(Enum):
    All = ""
    Unchanged = "-a"
    ServerOnly = "-k"

# 文件最近一次提交的信息
class P4FileSubmitInfo:
    def __init__(self, fstat_result, change_info):
        self.changelist = fstat_result.get('headChange')
        self.action = fstat_result.get('headAction')
        self.revision = fstat_result.get('headRev')
        self.user = change_info.get("user")
        self.datetime = QDateTime.fromSecsSinceEpoch(int(change_info.get("time"))).toString("yyyy-MM-dd hh:mm:ss")
        self.description = change_info.get("desc")


class P4WorkspaceRootSetResult(Enum):
    UPDATE_SUCCESS = 0
    ALREADY_RIGHT = 1
    FAILED = 2

# P4仓库中的路径，可以在Depot和Workspace中转换
class P4Path(object):

    # good sample:
    #   P4Path(depot_path="//Project/Dir/a_file.ext")
    #   P4Path(depot_path="//Project/Dir", is_dir=True)
    # bad sample:
    #   P4Path(depot_path="//Project/Dir")                      # is_dir is necessary
    #   P4Path(depot_path="//Project/Dir/", is_dir=True)        # the last "/" is not accepted
    def __init__(self, depot_path: str = None, local_path: str = None, is_dir: bool = False):

        # convert local_path to absolute path
        if local_path:
            local_path = os.path.abspath(local_path).replace(os.path.sep, "/")

        # remove the last "/" or "/..." if is_dir
        if is_dir and depot_path:
            if depot_path.endswith("/"):
                depot_path = depot_path[:-1]
            if depot_path.endswith("/..."):
                depot_path = depot_path[:-4]
        if is_dir and local_path:
            if local_path.endswith("/"):
                local_path = local_path[:-1]
            if local_path.endswith(os.path.sep + "..."):
                local_path = local_path[:-4]

        self._depot_path = depot_path
        self._local_path = local_path
        self._p4_depot_path = None
        self._p4_local_path = None
        self._is_dir = is_dir

    @property
    def depot_path(self) -> str:
        if self._depot_path is None:
            if self._local_path is None:
                Logger().error("Both depot path and local path are None.")
                return ""
            self._depot_path = P4Client().convert_path(self._local_path, P4PathType.DepotPath)
        return self._depot_path

    @property
    def local_path(self) -> str:
        if self._local_path is None:
            if self._depot_path is None:
                Logger().error("Both depot path and local path are None.")
                return ""
            self._local_path = P4Client().convert_path(self._depot_path, P4PathType.LocalPath).replace("\\", "/")
        return self._local_path

    # path without special characters
    @property
    def p4_depot_path(self) -> str:
        if self.depot_path is None:
            return ""
        if self._p4_depot_path is None:
            self._p4_depot_path = self._to_safe_path(self.depot_path)
            if self._is_dir and (not self._p4_depot_path.endswith("/")):
                self._p4_depot_path += "/..."
        return self._p4_depot_path

    # path without special characters
    @property
    def p4_local_path(self) -> str:
        if self.local_path is None:
            return ""
        if self._p4_local_path is None:
            self._p4_local_path = self._to_safe_path(self.local_path)
            if self._is_dir and (not self._p4_local_path.endswith("/")):
                self._p4_local_path += "/..."

        return self._p4_local_path

    @staticmethod
    def _to_safe_path(path: str) -> str:
        path = path.replace("%", "%25")
        path = path.replace("#", "%23")
        path = path.replace("@", "%40")
        path = path.replace("*", "%2A")
        # path = path.replace(":", "%3A")
        return path

    @property
    def is_dir(self) -> bool:
        return self._is_dir

    @is_dir.setter
    def is_dir(self, value: bool):
        if value != self._is_dir:
            # p4 path changed, clear cache
            self._p4_depot_path = None
            self._p4_local_path = None
        self._is_dir = value


# P4操作的封装
class P4Client(metaclass=Singleton):

    def __init__(self):

        self.client = P4()
        self.client.port = P4_SERVER
        self.client.charset = P4_CHARSET

    # region login info

    @property
    def username(self) -> str:
        return self.client.user

    @username.setter
    def username(self, value: str):
        self.client.user = value

    @property
    def password(self) -> str:
        return self.client.password

    @password.setter
    def password(self, value: str):
        self.client.password = value

    @property
    def workspace_name(self) -> str:
        return self.client.client

    @workspace_name.setter
    def workspace_name(self, value: str):
        self.client.client = value

    @property
    def workspace_root(self) -> str:
        client_spec = self.client.fetch_client(self.workspace_name)
        return client_spec["Root"]

    # endregion

    # P4.connected() and ticket valid
    @property
    def is_connected(self) -> bool:
        if not self.client.connected():
            return False
        try:
            self.client.run("login", "-s")
        except P4Exception:
            return False
        return True

    # call by push button after login info is set
    # P4.connect then check workspace root matched
    def connect(self) -> bool:
        if not self._is_login_info_valid():
            Logger().warning("P4 login info not set. Username is necessary.")
            return False

        self.client.connect()

        if not self.is_connected:
            return False

        # whether set right workspace
        if self._set_workspace_by_root() != P4WorkspaceRootSetResult.FAILED:
            self.client.connect()
        return self.is_connected

    def disconnect(self):
        self.client.disconnect()
        Logger().info("P4已断开连接.")

    # region connection check

    def _is_login_info_valid(self) -> bool:
        return len(self.username) > 0

    def _auto_parse_workspace_root(self):

        dir_path = os.path.abspath("")
        dir_name = ""

        while len(dir_path) > 0:
            if dir_name == "Dev":
                dir_name = os.path.basename(dir_path)
                if dir_name == "DTS":
                    # has "DTS" level
                    dir_path, dir_name = os.path.split(dir_path)
                break

            dir_path, dir_name = os.path.split(dir_path)

    def _set_workspace_by_root(self) -> P4WorkspaceRootSetResult:
        if not self.client.connect():
            Logger().warning("P4 is not connected when trying to set workspace by root.")
            return P4WorkspaceRootSetResult.FAILED
        connect_client_info = self.run_command("info")
        if connect_client_info is None:
            return P4WorkspaceRootSetResult.FAILED
        connect_client_info = connect_client_info[0]
        connect_root = connect_client_info["clientRoot"] if "clientRoot" in connect_client_info else "."
        connect_host = connect_client_info["clientHost"]

        if os.path.realpath(connect_root) == os.path.realpath(self.workspace_root):
            # already connected to the right workspace
            return P4WorkspaceRootSetResult.ALREADY_RIGHT

        # try to find workspace by root
        Logger().debug("Try to find workspace by root '%s'." % self.workspace_root)
        client_info_list = self.run_command("clients", "--me")
        if client_info_list is None:
            return P4WorkspaceRootSetResult.FAILED
        for client_info in client_info_list:
            if "Host" not in client_info:
                continue
            if "Root" not in client_info:
                continue
            if client_info["Host"] != connect_host:
                continue
            if os.path.realpath(client_info["Root"]) == os.path.realpath(self.workspace_root):
                # host and root matched
                self.workspace_name = client_info["client"]
                Logger().debug("Auto set workspace to '%s'." % self.workspace_name)
                return P4WorkspaceRootSetResult.UPDATE_SUCCESS

        # not found
        Logger().warning("Failed to find workspace by root '%s'." % self.workspace_root)
        return P4WorkspaceRootSetResult.FAILED

    # endregion

    # print p4 warnings and errors stack
    def print_client_exception_log(self) -> None:
        for w in self.client.warnings:
            Logger().warning(str(w))
        for e in self.client.errors:
            Logger().error(str(e))

    # 创建或获取已有的ChangeList
    def get_change_id_by_desc(self, description: str) -> str:
        if description is None:
            description = P4_CHANGELIST_DESCRIPTION

        # search exist change id by description
        exist_change_list = self.run_command(
            "changes",
            "--me", "-c", self.client.client,
            "-L", "-s", "pending")
        if exist_change_list is None:
            return "default"

        for change_info in exist_change_list:
            if "desc" not in change_info:
                continue
            if change_info["desc"].startswith(description):
                # desc may end with "\n", so use startswith
                return change_info["change"]

        # change with given description not found, create a new one
        if not self.client.connected():
            Logger().error("P4 is not connected when trying to create new change list.")
            return "default"
        change_create_result = self.client.save_change({"Change": "new", "Description": description})
        new_change_id = NEW_CHANGELIST_REGEX.match(change_create_result[-1])
        if new_change_id is None:
            Logger().error("P4创建新的修改列表失败！")
            return "default"

        new_change_id = new_change_id.group(1)
        Logger().info(f"新的修改列表已创建: {new_change_id}")

        return new_change_id

    # 在本地与云端路径之间转换
    def convert_path(self, in_path: str, out_path_type: P4PathType) -> str | None:
        result = self.run_command("where", in_path)
        if not result:
            return ""
        key = "path" if out_path_type == P4PathType.LocalPath else "depotFile"
        out_path = result[0][key]
        Logger().debug(f"P4Path: {in_path} converted to {out_path}")
        return out_path

    # 检测本地文件是否在待提交的CL中
    def is_in_pending_changelist(self, path: P4Path) -> bool:
        result = self.run_command("opened", path.p4_local_path)
        # 如果返回是非空list且包含我们的文件, 即处于pending changelist
        return isinstance(result, list) and len(result) > 0

    # 检测本地文件在云端是否已存在
    def is_in_depot(self, path: P4Path) -> bool:
        with self.client.at_exception_level(P4.RAISE_ERRORS):
            result = self.run_command("files", "-e", path.p4_depot_path)
        return True if isinstance(result, list) and len(result) > 0 else False

    # 获取Depot文件夹中所有文件
    def get_sub_files_on_depot(self, dir_path: P4Path) -> list[P4Path]:
        result = self.run_command("files", "-e", dir_path.p4_depot_path)
        if not isinstance(result, list):
            Logger().warning("Failed to get files under '%s' on P4 depot." % dir_path.depot_path)
            return []

        return [P4Path(depot_path=path_info["depotFile"]) for path_info in result]

    # 获取上次提交的记录
    def query_last_submit_info(self, file_path: P4Path) -> P4FileSubmitInfo | None:
        result = self.run_command("fstat", "-T", "headChange,headAction,headRev", file_path.p4_depot_path)
        if not result or len(result) == 0:
            return None
        result = result[0]
        change_info = self.run_command("describe", "-s", result.get('headChange'))
        info = P4FileSubmitInfo(result, change_info[0])
        return info


    # 拉取更新文件或目录（可强制拉取）
    def sync(self, path: P4Path, force: bool = False) -> bool:
        with self.client.at_exception_level(P4.RAISE_ERRORS):
            if force:
                result = self.run_command("sync", "-k", path.p4_depot_path)
            else:
                result = self.run_command("sync", path.p4_depot_path)
        return result

    # 迁出文件或目录到指定描述的CL
    def checkout(self, path: P4Path, change_desc: str = P4_CHANGELIST_DESCRIPTION) -> bool:
        # 迁出文件夹中所有文件
        if path.is_dir:
            result = self.run_command("files", "-e", path.p4_depot_path)
            if not isinstance(result, list):
                return False

            flag = True
            for depot_file_info in result:
                if "depotFile" not in depot_file_info:
                    continue
                flag = flag and self.checkout(
                    P4Path(depot_path=depot_file_info["depotFile"]), change_desc)
            return flag

        # 迁出文件夹中所有文件
        if os.path.isdir(path.local_path):
            result = True
            for file_path in glob.glob(os.path.join(path.local_path, "**"), recursive=True):
                if not os.path.isfile(file_path):
                    continue
                result = result and self.checkout(P4Path(local_path=file_path), change_desc)
            return result

        change_id = self.get_change_id_by_desc(change_desc)

        # 如果已经被迁出
        result = self.run_command("opened", path.p4_depot_path)
        if isinstance(result, list) and len(result) > 0:
            other_change_id = result[0]["change"]
            if other_change_id == change_id:
                return True
            else:
                Logger().info(f"文件{path.local_path}已经被另一个CL{other_change_id}迁出，移动到{change_id}")
                # 移动到另一个CL
                return self.reopen_to_change(path, change_desc)

        # 确认文件在Depot存在
        with self.client.at_exception_level(P4.RAISE_ERRORS):
            result = self.run_command("files", "-e", path.p4_depot_path)
        if isinstance(result, list) and len(result) > 0:
            # file exist in depot, checkout to change id
            result = self.run_command("edit", "-c", change_id, path.p4_depot_path)
            return result
        return False

    # 锁定文件
    def lock(self, path: P4Path):
        self.run_command("lock", path.p4_local_path)

    # 解锁文件
    def unlock(self, path: P4Path, revert_unchanged: bool = True):
        self.run_command("unlock", path.p4_local_path)
        if revert_unchanged:
            self.revert(path, P4RevertOption.Unchanged)

    # 添加文件
    def add(self, path: P4Path, change_desc: str = P4_CHANGELIST_DESCRIPTION) -> bool:
        change_id = self.get_change_id_by_desc(change_desc)
        return self.run_command("add", "-c", change_id, path.p4_local_path)

    # 移动或重命名文件（目标已存在时需 -f 覆盖，含 depot 中只读等情况）
    def move(self, src_path: P4Path, dst_path: P4Path, change_desc: str = P4_CHANGELIST_DESCRIPTION) -> bool:
        change_id = self.get_change_id_by_desc(change_desc)
        if not self.checkout(src_path, change_desc):
            return False
        dst_local = dst_path.local_path
        force = os.path.isfile(dst_local)
        if force and self.is_in_depot(dst_path):
            if not self.checkout(dst_path, change_desc):
                Logger().warning(f"P4 无法迁出将覆盖的目标文件: {dst_local}")
        if force:
            return self.run_command("move", "-f", "-c", change_id, src_path.p4_depot_path, dst_path.p4_depot_path)
        return self.run_command("move", "-c", change_id, src_path.p4_depot_path, dst_path.p4_depot_path)

    # 删除（会先回退）
    def delete(self, path: P4Path, change_desc: str = P4_CHANGELIST_DESCRIPTION) -> bool:
        change_id = self.get_change_id_by_desc(change_desc)
        return self.run_command("delete", "-c", change_id, path.p4_depot_path)

    # 指定不同模式回退
    def revert(self, path: P4Path, option: P4RevertOption = P4RevertOption.All) -> bool:
        # 已经存在 在changelist中推出去
        return self.run_command("revert", option.value, path.p4_depot_path)

    # 按照CL回退
    def revert_by_changelist(self, change_id: str = "", option: P4RevertOption = P4RevertOption.Unchanged) -> bool:
        # 已经存在 在changelist中推出去
        if not change_id:
            change_id = self.get_change_id_by_desc(P4_CHANGELIST_DESCRIPTION)
        return self.run_command("revert", "-c", change_id, option.value)

    # 移动到另一个变更列表
    def reopen_to_change(self, path: P4Path, change_desc: str = P4_CHANGELIST_DESCRIPTION) -> bool:
        change_id = self.get_change_id_by_desc(change_desc)
        return self.run_command("reopen", "-c", change_id, path.p4_depot_path)

    # 执行命令行
    def run_command(self, cmd: str, *args):
        if not self.is_connected:
            Logger().error("P4未连接，无法执行'%s %s'." % (cmd, " ".join(args)))
            return None
        try:
            result = self.client.run(cmd, *args)
            Logger().debug("P4执行命令 '%s %s'." % (cmd, " ".join(args)))
            for message in self.client.messages:
                Logger().debug(message)
            return result
        except P4Exception:
            Logger().error("P4执行命令失败 '%s %s'" % (cmd, " ".join(args)))
            self.print_client_exception_log()
            return None