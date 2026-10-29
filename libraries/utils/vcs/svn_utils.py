import os
import subprocess
import xml.etree.ElementTree as ET
from enum import Enum

from PySide6.QtCore import QDateTime, Qt

from libraries.singleton import Singleton
from data import project_conventions
from libraries.utils.log_utils import Logger


def _get_long_path_name(path: str) -> str:
    # Windows 下将 8.3 短路径（如 LIUZIQ~1）转为长路径；
    # svn 对同一工作副本的短/长路径写法会误判为加锁
    import ctypes

    buffer = ctypes.create_unicode_buffer(32768)
    get_long_path_name = ctypes.windll.kernel32.GetLongPathNameW
    get_long_path_name.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
    get_long_path_name.restype = ctypes.c_uint32
    length = get_long_path_name(path, buffer, len(buffer))
    if length == 0 or length >= len(buffer):
        return path
    return buffer.value


def _normalize_local_path(path: str) -> str:
    if os.name != "nt":
        return path
    if os.path.exists(path):
        return _get_long_path_name(path)
    # 文件尚不存在时，先规范化父目录再拼回文件名
    parent, name = os.path.split(path)
    if not parent:
        return path
    return os.path.join(_normalize_local_path(parent), name)


# 仓库 URL 或本地工作副本路径
class SVNPathType(Enum):
    UrlPath = 0
    LocalPath = 1


# 回退时的选项（语义与 P4RevertOption 对齐；SVN 无“仅回退服务器状态”，ServerOnly 尽力保留本地内容）
class SVNRevertOption(Enum):
    All = ""
    Unchanged = "-a"
    ServerOnly = "-k"


# 文件最近一次提交的信息
class SVNFileSubmitInfo:
    def __init__(self, revision: str, action: str, user: str, datetime: str, description: str):
        self.changelist = revision
        self.action = action
        self.revision = revision
        self.user = user
        self.datetime = datetime
        self.description = description


# SVN 中的路径，可以在 URL 与本地工作副本路径之间转换
class SVNPath(object):

    # good sample:
    #   SVNPath(url_path="https://svn.example.com/Project/Dir/a_file.ext")
    #   SVNPath(url_path="https://svn.example.com/Project/Dir", is_dir=True)
    #   SVNPath(local_path=r"C:/Work/Project/Dir/a_file.ext")
    def __init__(self, url_path: str = None, local_path: str = None, is_dir: bool = False):

        # convert local_path to absolute path
        if local_path:
            local_path = _normalize_local_path(os.path.abspath(local_path)).replace(os.path.sep, "/")

        # remove the last "/" for dirs
        if is_dir and url_path and url_path.endswith("/"):
            url_path = url_path[:-1]
        if is_dir and local_path and local_path.endswith("/"):
            local_path = local_path[:-1]

        self._url_path = url_path
        self._local_path = local_path
        self._is_dir = is_dir

    @property
    def url_path(self) -> str:
        if self._url_path is None:
            if self._local_path is None:
                Logger().error("Both url path and local path are None.")
                return ""
            self._url_path = SVNClient().convert_path(self._local_path, SVNPathType.UrlPath)
        return self._url_path

    # 仓库侧路径，供与模式无关的调用方使用
    @property
    def repo_path(self) -> str:
        return self.url_path

    @property
    def local_path(self) -> str:
        if self._local_path is None:
            if self._url_path is None:
                Logger().error("Both url path and local path are None.")
                return ""
            self._local_path = SVNClient().convert_path(self._url_path, SVNPathType.LocalPath).replace("\\", "/")
        return self._local_path

    @property
    def svn_url_path(self) -> str:
        return self.url_path

    @property
    def svn_local_path(self) -> str:
        return self.local_path

    @property
    def is_dir(self) -> bool:
        return self._is_dir

    @is_dir.setter
    def is_dir(self, value: bool):
        self._is_dir = value


# SVN操作的封装（公开 API 与 P4Client 对齐，底层调用 svn 命令行）
class SVNClient(metaclass=Singleton):

    def __init__(self):
        self.executable = project_conventions.get_svn_executable()
        self._username = project_conventions.get_svn_username()
        self._password = project_conventions.get_svn_password()
        self._commit_message = project_conventions.get_svn_commit_message()
        self._wc_root = None

    # region login info

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str):
        self._username = value

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, value: str):
        self._password = value

    @property
    def workspace_name(self) -> str:
        if not self._wc_root:
            return ""
        return os.path.basename(self._wc_root)

    @property
    def workspace_root(self) -> str:
        return self._wc_root or ""

    # endregion

    # 当前目录（或已连接的工作副本）是否处于 SVN 工作副本中
    @property
    def is_connected(self) -> bool:
        target = self._wc_root if self._wc_root else "."
        exit_code, _, _ = self._run(["info", "--show-item", "wc-root", target])
        return exit_code == 0

    # 连接 SVN：探测当前目录所在工作副本根目录
    def connect(self) -> bool:
        exit_code, wc_root, err = self._run(["info", "--show-item", "wc-root", "."])
        if exit_code != 0 or not wc_root.strip():
            Logger().warning(f"SVN 连接失败，当前目录不在 SVN 工作副本中: {err.strip()}")
            return False
        self._wc_root = _normalize_local_path(wc_root.strip()).replace("\\", "/")
        Logger().info(f"SVN 已连接，工作副本根目录: {self._wc_root}")
        return True

    def disconnect(self):
        self._wc_root = None
        Logger().info("SVN已断开连接.")

    # 直接执行 svn 命令，返回 (exit_code, stdout, stderr)
    def _run(self, args: list) -> tuple:
        cmd = [self.executable, "--non-interactive"] + args
        if self._username:
            cmd += ["--username", self._username]
        if self._password:
            cmd += ["--password", self._password]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        except FileNotFoundError:
            Logger().error(f"找不到 svn 可执行文件: {self.executable}")
            return 127, "", ""
        except subprocess.TimeoutExpired:
            Logger().error(f"svn 命令超时: {' '.join(cmd)}")
            return 124, "", ""
        Logger().debug(f"SVN执行命令: {' '.join(cmd)}")
        return proc.returncode, proc.stdout, proc.stderr

    # 执行 svn 子命令；info/status/log 解析为 dict 列表，其余返回输出行列表；失败返回 None
    def run_command(self, cmd: str, *args):
        if not self.is_connected:
            Logger().error(f"SVN未连接，无法执行'svn {cmd} {' '.join(args)}'.")
            return None
        xml_args = list(args)
        if cmd in ("info", "status", "log") and "--xml" not in xml_args:
            xml_args.insert(0, "--xml")
        exit_code, out, err = self._run([cmd] + xml_args)
        if exit_code != 0:
            Logger().error(f"SVN执行命令失败 'svn {cmd} {' '.join(args)}': {err.strip()}")
            return None
        if cmd in ("info", "status", "log"):
            return self._parse_xml(out, cmd)
        return [line for line in out.splitlines() if line.strip()]

    @staticmethod
    def _parse_xml(out: str, cmd: str) -> list:
        try:
            root = ET.fromstring(out)
        except ET.ParseError:
            Logger().error("SVN 解析 XML 输出失败.")
            return []
        if cmd == "info":
            return [SVNClient._info_entry_to_dict(entry) for entry in root.iter("entry")]
        if cmd == "status":
            return [SVNClient._status_entry_to_dict(entry) for entry in root.iter("entry")]
        if cmd == "log":
            return [SVNClient._log_entry_to_dict(entry) for entry in root.iter("logentry")]
        return []

    @staticmethod
    def _info_entry_to_dict(entry) -> dict:
        info = {}
        for tag in ("url", "relative-url", "repos-root-url"):
            node = entry.find(tag)
            info[tag] = node.text if node is not None else ""
        commit = entry.find("commit")
        if commit is not None:
            info["revision"] = commit.get("revision", "")
            author = commit.find("author")
            info["author"] = author.text if author is not None else ""
        return info

    @staticmethod
    def _status_entry_to_dict(entry) -> dict:
        info = {"path": entry.get("path", "")}
        wc_status = entry.find("wc-status")
        if wc_status is not None:
            info["item"] = wc_status.get("item", "")
            info["props"] = wc_status.get("props", "")
        return info

    @staticmethod
    def _log_entry_to_dict(entry) -> dict:
        info = {"revision": entry.get("revision", "")}
        author = entry.find("author")
        date = entry.find("date")
        msg = entry.find("msg")
        info["author"] = author.text if author is not None else ""
        info["date"] = date.text if date is not None else ""
        info["msg"] = msg.text if msg is not None else ""
        info["paths"] = []
        paths = entry.find("paths")
        if paths is not None:
            for path in paths.findall("path"):
                info["paths"].append({"action": path.get("action", ""), "path": path.text or ""})
        return info

    # 获取或创建 changelist：SVN 的 changelist 以名称为标识（等价于 P4 用描述查找）
    # 返回 changelist 名称；为空表示不使用 changelist
    def get_change_id_by_desc(self, description: str = None) -> str:
        if description is None:
            description = self._commit_message
        return description or ""

    # 在本地路径与仓库 URL 之间转换
    def convert_path(self, in_path: str, out_path_type: SVNPathType) -> str:
        if not in_path:
            return ""
        if out_path_type == SVNPathType.UrlPath:
            exit_code, out, err = self._run(["info", "--show-item", "url", _normalize_local_path(in_path)])
            if exit_code == 0 and out.strip():
                url = out.strip()
                Logger().debug(f"SVNPath: {in_path} converted to {url}")
                return url
            # 尚未纳入版本控制的文件 svn info 会失败，退化为「工作副本根 URL + 相对路径」
            Logger().debug(f"SVN info 失败，按工作副本相对路径转换: {in_path} ({err.strip()})")
            return self._local_to_url_by_wc_root(in_path)

        # URL -> 本地路径：依赖当前工作副本的仓库根
        if not self._wc_root:
            if not self.connect():
                return ""
        repo_root_url = self._get_repo_root_url()
        if not repo_root_url or not in_path.startswith(repo_root_url):
            Logger().warning(f"SVN 无法将 URL 转换为本地路径（不在当前工作副本内）: {in_path}")
            return ""
        relative = in_path[len(repo_root_url):].lstrip("/")
        local = os.path.join(self._wc_root, relative.replace("/", os.sep))
        Logger().debug(f"SVNPath: {in_path} converted to {local}")
        return local.replace("\\", "/")

    def _get_repo_root_url(self) -> str:
        if not self._wc_root:
            return ""
        exit_code, out, _ = self._run(["info", "--show-item", "repos-root-url", self._wc_root])
        if exit_code != 0:
            return ""
        return out.strip()

    def _local_to_url_by_wc_root(self, in_path: str) -> str:
        if not self._wc_root:
            if not self.connect():
                return ""
        try:
            abs_path = _normalize_local_path(os.path.abspath(in_path))
            abs_root = os.path.abspath(self._wc_root)
            if os.path.commonpath([abs_path, abs_root]) != abs_root:
                return ""
        except ValueError:
            return ""
        exit_code, out, _ = self._run(["info", "--show-item", "url", self._wc_root])
        if exit_code != 0 or not out.strip():
            return ""
        relative = os.path.relpath(abs_path, abs_root).replace(os.sep, "/")
        return out.strip() + "/" + relative

    @staticmethod
    def _path_arg(path: SVNPath) -> str:
        # 优先使用本地路径（changelist/revert 等操作只能作用于工作副本）
        return path.local_path or path.url_path

    # 检测本地文件是否有未提交修改（SVN 无“迁出”概念，本地有 A/M/D/R 等状态即视为待提交）
    def is_in_pending_changelist(self, path: SVNPath) -> bool:
        target = self._path_arg(path)
        if not target:
            return False
        result = self.run_command("status", target)
        if not result:
            return False
        return any(
            entry.get("item") in ("added", "modified", "deleted", "replaced", "merged", "conflicted")
            for entry in result
        )

    # 检测文件或 URL 在仓库中是否已存在
    def is_in_depot(self, path: SVNPath) -> bool:
        url = path.url_path
        if not url:
            return False
        exit_code, _, _ = self._run(["info", url])
        return exit_code == 0

    # 获取仓库目录下所有文件（不含子目录项）
    def get_sub_files_on_depot(self, dir_path: SVNPath) -> list[SVNPath]:
        url = dir_path.url_path.rstrip("/")
        if not url:
            return []
        exit_code, out, _ = self._run(["list", "-R", url])
        if exit_code != 0:
            Logger().warning(f"Failed to get files under '{url}' on SVN repository.")
            return []
        result = []
        for line in out.splitlines():
            line = line.strip()
            if not line or line.endswith("/"):
                continue
            result.append(SVNPath(url_path=f"{url}/{line}"))
        return result

    # 获取上次提交的记录
    def query_last_submit_info(self, file_path: SVNPath) -> SVNFileSubmitInfo | None:
        target = self._path_arg(file_path)
        if not target:
            return None
        result = self.run_command("log", "-v", "-l", "1", target)
        if not result:
            return None
        log_entry = result[0]
        revision = log_entry.get("revision", "")
        action_letter = ""
        paths = log_entry.get("paths", [])
        if paths:
            action_letter = paths[0].get("action", "")
        action_map = {"A": "add", "M": "modify", "D": "delete", "R": "replace"}
        action = action_map.get(action_letter, action_letter)
        date_text = log_entry.get("date", "")
        datetime_text = ""
        if date_text:
            date_time = QDateTime.fromString(date_text, Qt.DateFormat.ISODate)
            datetime_text = date_time.toString("yyyy-MM-dd hh:mm:ss")
        return SVNFileSubmitInfo(
            revision=revision,
            action=action,
            user=log_entry.get("author", ""),
            datetime=datetime_text,
            description=log_entry.get("msg", ""),
        )

    # svn 命令是否可执行（只看本地命令，不探测工作副本与网络）
    def is_available(self) -> bool:
        exit_code, _, _ = self._run(["--version", "--quiet"])
        if exit_code != 0:
            Logger().warning(f"SVN 不可用，请检查设置-版本控制里的 svn 可执行文件：{self.executable}")
            return False
        return True

    # 读取文件最后一次提交的作者：svn info 读本地工作副本元数据，不访问服务器
    def get_last_changed_author(self, path: SVNPath) -> str:
        target = self._path_arg(path)
        if not target:
            return ""
        exit_code, out, err = self._run(["info", "--show-item", "last-changed-author", target])
        if exit_code != 0:
            Logger().debug(f"SVN 读取作者失败：{target} ({err.strip()})")
            return ""
        return out.strip()

    # 本地文件是否已纳入版本控制（读本地工作副本，不访问服务器）
    def is_versioned(self, local_path: str) -> bool:
        if not local_path:
            return False
        exit_code, _, _ = self._run(["info", local_path])
        return exit_code == 0

    # 本地文件是否有未提交改动（status 读本地工作副本）
    def has_local_modification(self, local_path: str) -> bool:
        if not local_path:
            return False
        exit_code, out, _ = self._run(["status", local_path])
        if exit_code != 0:
            return False
        for line in out.splitlines():
            if not line.strip():
                continue
            # 第一列是 item 状态（A/M/D/R/C 等），第二列是属性状态
            if line[0] in "AMDRC" or line[1:2] == "M":
                return True
        return False

    # 拉取更新文件或目录（可强制拉取）
    def sync(self, path: SVNPath, force: bool = False) -> bool:
        local = path.local_path
        if not local:
            Logger().warning("SVN sync 需要本地工作副本路径.")
            return False
        args = ["update"]
        if force:
            args.append("--force")
        args.append(local)
        return self.run_command(args[0], *args[1:]) is not None

    # 更新指定本地文件/目录；不要求事先 connect 到当前目录所在工作副本
    def update_path(self, local_path: str) -> tuple[bool, str]:
        if not local_path:
            return False, "路径为空"
        exit_code, out, err = self._run(["update", local_path])
        if exit_code != 0:
            message = (err or out).strip()
            Logger().error(f"SVN 更新失败：{local_path} ({message})")
            return False, message
        Logger().info(f"SVN 更新完成：{local_path}")
        return True, (out or "").strip()

    # 将文件加入指定 changelist（SVN 中工作副本文件默认可写，无“迁出”概念）
    def checkout(self, path: SVNPath, change_desc: str = None) -> bool:
        change_id = self.get_change_id_by_desc(change_desc)
        if not change_id:
            return True
        if path.is_dir:
            if path.local_path and os.path.isdir(path.local_path):
                result = True
                for file_path in self._list_versioned_files(path.local_path):
                    result = result and self._assign_to_changelist(file_path, change_id)
                return result
            Logger().warning("SVN 无法对远程目录执行 checkout，请使用本地目录路径.")
            return False
        return self._assign_to_changelist(self._path_arg(path), change_id)

    # 收集目录下所有已纳入版本控制的文件（跳过未版本化/忽略项）
    def _list_versioned_files(self, directory: str) -> list:
        status = self.run_command("status", "-v", directory)
        if status is None:
            return []
        result = []
        for entry in status:
            if entry.get("item") in ("unversioned", "ignored"):
                continue
            rel_path = entry.get("path", "")
            if not rel_path:
                continue
            if not os.path.isabs(rel_path):
                rel_path = os.path.join(directory, rel_path)
            if os.path.isfile(rel_path):
                result.append(rel_path)
        return result

    def _assign_to_changelist(self, path: str, change_id: str) -> bool:
        return self.run_command("changelist", change_id, path) is not None

    # 锁定文件
    def lock(self, path: SVNPath):
        self.run_command("lock", self._path_arg(path))

    # 解锁文件
    def unlock(self, path: SVNPath, revert_unchanged: bool = True):
        self.run_command("unlock", self._path_arg(path))
        if revert_unchanged:
            self.revert(path, SVNRevertOption.Unchanged)

    # 添加文件
    def add(self, path: SVNPath, change_desc: str = None) -> bool:
        local = path.local_path
        if not local:
            Logger().warning("SVN add 需要本地工作副本路径.")
            return False
        if self.run_command("add", local) is None:
            return False
        change_id = self.get_change_id_by_desc(change_desc)
        if not change_id:
            return True
        return self._assign_to_changelist(local, change_id)

    # 移动或重命名文件（目标已存在时需 --force 覆盖）
    def move(self, src_path: SVNPath, dst_path: SVNPath, change_desc: str = None) -> bool:
        src = self._path_arg(src_path)
        dst = self._path_arg(dst_path)
        if not src or not dst:
            return False
        args = ["move"]
        if os.path.isfile(dst):
            args.append("--force")
        args += [src, dst]
        if self.run_command(*args) is None:
            return False
        change_id = self.get_change_id_by_desc(change_desc)
        if not change_id:
            return True
        return self._assign_to_changelist(dst, change_id)

    # 删除（SVN 仅支持本地路径，防止误删仓库文件）
    def delete(self, path: SVNPath, change_desc: str = None) -> bool:
        local = path.local_path
        if not local:
            Logger().warning("SVN delete 需要本地工作副本路径（防止误删仓库文件）.")
            return False
        if self.run_command("delete", "--force", local) is None:
            return False
        change_id = self.get_change_id_by_desc(change_desc)
        if not change_id:
            return True
        return self._assign_to_changelist(local, change_id)

    # 指定不同模式回退
    def revert(self, path: SVNPath, option: SVNRevertOption = SVNRevertOption.All) -> bool:
        target = self._path_arg(path)
        if not target:
            return False
        if option == SVNRevertOption.All:
            return self.run_command("revert", "--recursive", target) is not None
        if option == SVNRevertOption.Unchanged:
            # 内容已修改的文件不回退
            if self._status_item(path) in ("modified", "merged", "conflicted"):
                Logger().info(f"文件内容已修改，跳过回退: {target}")
                return True
            return self.run_command("revert", "--recursive", target) is not None
        # ServerOnly：SVN 无“仅回退服务器状态”概念；回退会保留本地内容的计划新增/替换
        if self._status_item(path) in ("added", "replaced"):
            return self.run_command("revert", "--recursive", target) is not None
        Logger().info(f"SVN 不支持仅回退服务器状态，跳过: {target}")
        return True

    def _status_item(self, path: SVNPath) -> str:
        target = self._path_arg(path)
        if not target:
            return ""
        result = self.run_command("status", target)
        if not result:
            return ""
        return result[0].get("item", "")

    # 按照 changelist 回退
    def revert_by_changelist(self, change_id: str = "", option: SVNRevertOption = SVNRevertOption.Unchanged) -> bool:
        if not change_id:
            change_id = self.get_change_id_by_desc()
        if not change_id or not self._wc_root:
            Logger().warning("SVN revert_by_changelist 需要 changelist 名称和工作副本.")
            return False
        if option == SVNRevertOption.Unchanged:
            entries = self.run_command("status", "--changelist", change_id, self._wc_root)
            if entries is None:
                return False
            for entry in entries:
                if entry.get("item") in ("modified", "merged", "conflicted"):
                    continue
                path = entry.get("path", "")
                if path and not os.path.isabs(path):
                    path = os.path.join(self._wc_root, path)
                self.run_command("revert", path)
            return True
        return self.run_command("revert", "--changelist", change_id, "--recursive", self._wc_root) is not None

    # 移动到另一个 changelist
    def reopen_to_change(self, path: SVNPath, change_desc: str = None) -> bool:
        change_id = self.get_change_id_by_desc(change_desc)
        if not change_id:
            return True
        return self._assign_to_changelist(self._path_arg(path), change_id)
