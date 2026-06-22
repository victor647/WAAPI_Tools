#!/usr/bin/env python3
"""仅构建 MCP：产出 ``packager/dist/WaapiMCP/``（独立 ``_internal``）。

使用 ``WaapiMCP_standalone.spec`` + ``bundle_helpers.py``。与 ``package_gui.py`` 分别运行后，
用 ``publish_merged.py`` 合并拷贝到发布目录。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_PACKAGER_DIR = Path(__file__).resolve().parent
ROOT = _PACKAGER_DIR.parent
SPEC = _PACKAGER_DIR / "WaapiMCP_standalone.spec"
DISTPATH = _PACKAGER_DIR / "dist"
WORKDIR = _PACKAGER_DIR / "build" / "mcp"


def main() -> int:
    parser = argparse.ArgumentParser(description="PyInstaller：仅 MCP（WaapiMCP.exe）")
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="不传入 --clean（默认每次清理 PyInstaller 缓存）",
    )
    args = parser.parse_args()

    if not SPEC.is_file():
        print(f"未找到 spec: {SPEC}", file=sys.stderr)
        return 1
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("未安装 PyInstaller：pip install pyinstaller", file=sys.stderr)
        return 1

    DISTPATH.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(SPEC),
        "--noconfirm",
        "--distpath",
        str(DISTPATH),
        "--workpath",
        str(WORKDIR),
    ]
    if not args.no_clean:
        cmd.append("--clean")
    print(f"\n>>> {' '.join(cmd)}\n", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)
    out = DISTPATH / "WaapiMCP"
    print("\nDone.", flush=True)
    print(f"  产出: {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
