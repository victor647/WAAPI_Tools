# 在「开发目录运行」与「PyInstaller 打包成 exe」两种场景下，把 Python 能找到 libraries 的路径设对
# 开发时：仓库根目录在 waapi_mcp 的上两级（…/WAAPI_Tools）
# 冻结后：第三方库与 libraries 被打进临时目录 sys._MEIPASS，必须把该目录加入 sys.path

from __future__ import annotations

import sys
from pathlib import Path


def _is_frozen() -> bool:
    # 判断当前是否运行在 PyInstaller 打包后的可执行文件中（sys.frozen 为 True）
    return bool(getattr(sys, "frozen", False))


def ensure_project_root() -> Path:
    # 将「可导入 libraries 包」的目录插入 sys.path 最前，并返回该目录
    # - 未打包：使用本文件所在目录的上上级，即 WAAPI_Tools 仓库根
    # - 已打包：使用 PyInstaller 解压资源所在目录 _MEIPASS（内含打进去的 libraries）
    if _is_frozen() and hasattr(sys, "_MEIPASS"):
        # 关键步骤：冻结环境下依赖 _MEIPASS，而不是 exe 所在磁盘路径
        root = str(sys._MEIPASS)
        if root not in sys.path:
            sys.path.insert(0, root)
        return Path(root)
    # 开发环境：waapi_mcp/bootstrap.py -> 父级 waapi_mcp -> 再上级为仓库根
    repo = Path(__file__).resolve().parent.parent
    r = str(repo)
    if r not in sys.path:
        sys.path.insert(0, r)
    return repo
