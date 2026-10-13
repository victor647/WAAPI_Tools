import os
import shutil
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from libraries.utils.log_utils import Logger
from libraries.utils import user_config

# 检测是否运行在PyInstaller打包的环境中
def is_bundled() -> bool:
    return getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS')

# 获取资源文件路径（用于读取打包的资源文件）
def get_resource_path(relative_path: str) -> str:
    # 获取资源文件的完整路径
    # 在开发环境中返回相对于项目根目录的路径
    # 在打包环境中返回相对于临时解压目录的路径
    if is_bundled():
        # PyInstaller创建临时文件夹并存储路径在_MEIPASS中
        # 对于-F (one-file)模式，使用_MEIPASS
        # 对于-D (one-directory)模式，可能使用_internal文件夹
        base_path = getattr(sys, '_MEIPASS', None)
        if base_path is None:
            # 如果没有_MEIPASS，检查是否有_internal文件夹（one-directory模式）
            exe_dir = os.path.dirname(sys.executable)
            internal_path = os.path.join(exe_dir, '_internal')
            if os.path.exists(internal_path):
                base_path = internal_path
            else:
                # 回退到exe所在目录
                base_path = exe_dir
        return combine_path(base_path, relative_path)
    else:
        # 开发环境，返回相对于项目根目录的路径
        project_root = find_dev_project_root()
        return combine_path(project_root, relative_path)

# 获取项目根目录
def find_dev_project_root():
    start = Path(__file__).resolve()
    for parent in [start, *start.parents]:
        if (parent / "main.py").exists():
            return parent
    raise RuntimeError("Project root not found")

# 获取应用所在目录：打包后为 exe 所在目录，开发环境为仓库根目录（可写运行时文件放这里）
def get_app_dir() -> str:
    if is_bundled():
        return os.path.dirname(sys.executable)
    return str(find_dev_project_root())


# 获取应用数据路径（用于存储可写文件，如配置文件）
def get_app_data_path(filename: str = "") -> str:
    base_path = get_app_dir()
    if filename:
        return combine_path(base_path, filename)
    return base_path

# 检查文件是否被占用
def is_file_in_use(file_path: str) -> bool:
    try:
        with open(file_path, "a"):
            pass
        return False
    except PermissionError:
        return True

# 使用/连接路径
def combine_path(*paths) -> str:
    raw_path = str(os.path.join(*paths))
    return raw_path.replace("\\", "/")

# 在特定关键词后的相对路径
def trim_after(path: str, keyword: str) -> str:
    if keyword not in path:
        return path
    return path[path.index(keyword) + len(keyword):]

# 递归创建文件夹
def make_dir_recursive(directory):
    parent_dir = os.path.dirname(directory)
    if not os.path.exists(parent_dir):
        make_dir_recursive(parent_dir)
    os.makedirs(directory)

# 查找文件夹中所有文件，不查找子目录
def find_files_in_dir_non_recursive(folder: str, extension: str, ignore_keyword: str) -> list[str]:
    result_files = []
    for item in os.listdir(folder):
        if os.path.isdir(combine_path(folder, item)):
            continue
        if not item.endswith(extension):
            continue
        # 不要包含临时文件
        if item.startswith('~') or ignore_keyword in item:
            continue
        result_files.append(item)
    return result_files

# 获取路径中包含的所有文件夹路径
def get_all_paths(file_path, base_path) -> list[str]:
    # 检查 base_path 是否是 file_path 的前缀
    if os.path.commonpath([file_path, base_path]) != base_path:
        raise ValueError("Base path is not a prefix of the file path.")
    # 分割路径并逐级构建完整路径
    paths = []
    current_path = file_path
    while current_path != base_path:
        current_path = os.path.dirname(file_path)
        paths.append(current_path)
    return paths

# 获取文件上次修改日期，以YYYYMMDD格式
def get_modify_date(file_path: str) -> str:
    timestamp = os.path.getmtime(file_path)
    modified_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    return modified_date

# 打开文件或文件夹
def open_path(file_path: str):
    if os.path.exists(file_path):
        os.startfile(file_path)
    else:
        Logger().error(f"找不到路径{file_path}！")

# 打开所在文件夹并选中
def open_file_in_explorer(file_path: str):
    if os.path.exists(file_path):
        Logger().info(f"正在打开文件所在文件夹：{file_path}")
        subprocess.run(f'explorer /select,"{file_path.replace('/', '\\')}"')
    else:
        Logger().error(f"文件不存在：{file_path}，打开文件夹失败！")


def _norm_local_path(path: str) -> str:
    return os.path.abspath(path.replace("/", os.sep))


def _clear_readonly_file(path: str) -> None:
    if os.path.isfile(path):
        try:
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        except OSError:
            pass


def _filesystem_move_file(src: str, dst: str) -> bool:
    src = _norm_local_path(src)
    dst = _norm_local_path(dst)
    if src == dst:
        return True
    if not os.path.isfile(src):
        Logger().warning(f"move_file: 源文件不存在: {src}")
        return False
    dst_dir = os.path.dirname(dst)
    if dst_dir and not os.path.exists(dst_dir):
        os.makedirs(dst_dir, exist_ok=True)
    _clear_readonly_file(src)
    if os.path.exists(dst):
        _clear_readonly_file(dst)
        try:
            os.remove(dst)
        except OSError as e:
            Logger().error(f"move_file: 无法删除或覆盖目标文件: {dst} ({e})")
            return False
    try:
        shutil.move(src, dst)
    except OSError as e:
        Logger().error(f"move_file: 移动失败: {src} -> {dst} ({e})")
        return False
    return True


# 移动文件；覆盖只读目标时会先去掉只读
# 移动文件；覆盖只读目标时会先去掉只读。
# 源文件若受版本控制管理，则走版本控制 move（保留 SVN/P4 历史与待提交状态）
def move_file(src: str, dst: str, change_desc: str = None) -> bool:
    from libraries.utils import vcs_utils      # 延迟导入：vcs_utils 会读工程规范，避免模块级循环依赖

    src = _norm_local_path(src)
    dst = _norm_local_path(dst)
    if src == dst:
        return True
    if vcs_utils.is_file_managed(src):
        dst_dir = os.path.dirname(dst)
        if dst_dir and not os.path.exists(dst_dir):
            os.makedirs(dst_dir, exist_ok=True)
        result = vcs_utils.get_vcs_client().move(
            vcs_utils.get_vcs_path(src), vcs_utils.get_vcs_path(dst), change_desc)
        if result is None:
            Logger().error(f"move_file: 版本控制 move 失败，未回退为本地移动：{src} -> {dst}")
            return False
        return True
    return _filesystem_move_file(src, dst)


# 路径缩写：按 _ 拆出的字段只要在路径前面的任意节点出现过就用 ... 代替，只保留新字段；
# 最后一级完整保留。所有界面显示路径的地方都走这里，不要再各自实现一套。
def compact_path(path: str) -> str:
    if not isinstance(path, str) or not path:
        return path
    separator = "\\" if "\\" in path else "/"
    parts = path.split(separator)
    seen_tokens: set[str] = set()
    compact_parts = []
    for part in parts:
        if not part:
            compact_parts.append(part)
            continue
        leading_underscores = len(part) - len(part.lstrip("_"))
        tokens = part[leading_underscores:].split("_")
        # 先按历史出现情况判断，再记录本节点字段
        flags = [token in seen_tokens for token in tokens]
        seen_tokens.update(token for token in tokens if token)
        compact = "_" * leading_underscores
        pending_elided = False
        for token, was_seen in zip(tokens, flags):
            if was_seen:
                pending_elided = True
                continue
            if compact and not pending_elided:
                compact += "_"
            elif pending_elided:
                compact += "..." if not compact.endswith("...") else ""
                pending_elided = False
            compact += token
        if pending_elided:
            compact += "..." if not compact.endswith("...") else ""
        compact_parts.append(compact)
    return separator.join(compact_parts)


# Wwise 顶级根目录名称集合（覆盖 Hierarchy、Events、Banks 等根）
WWISE_ROOT_FOLDERS = {
    "actor-mixer hierarchy",
    "interactive music hierarchy",
    "master-mixer hierarchy",
    "events",
    "soundbanks",
    "game syncs",
    "control surface sessions",
    "dynamic dialogue",
    "virtual acoustics",
}


# 去除 Wwise 路径的顶级根目录（如 \Actor-Mixer Hierarchy\... 转为 \Default Work Unit\...）
def strip_root_path(path: str) -> str:
    if not isinstance(path, str) or not path:
        return path
    separator = "\\" if "\\" in path else "/"
    stripped = path.lstrip(separator)
    parts = stripped.split(separator)
    if not parts:
        return path
    first_token = parts[0].strip().lower()
    if first_token in WWISE_ROOT_FOLDERS or "hierarchy" in first_token:
        remainder = separator.join(parts[1:])
        if path.startswith(separator):
            return separator + remainder
        return remainder
    return path


# 界面里显示的路径文本：按 user_config 的「路径隐藏根目录」与「路径显示简写」开关格式化
def get_display_path(path: str) -> str:
    if not isinstance(path, str) or not path:
        return path
    result = path
    if user_config.get_tool_path_hide_root():
        result = strip_root_path(result)
    if user_config.get_tool_path_display_compact():
        result = compact_path(result)
    return result
