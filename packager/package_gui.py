#!/usr/bin/env python3
"""仅构建 GUI：产出 ``packager/dist/WAAPI_Tools/``（独立 ``_internal``）。

使用 ``WAAPI_Tools_GUI.spec``。与 ``package_mcp.py`` 分别运行后，用 ``publish_merged.py``
将两边合并拷贝到发布目录（默认 ``S:/sound_tools/waapi_tools``，即 Wwise Add-ons
通过 ``../../../sound_tools/waapi_tools`` 相对引用的目录）。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_PACKAGER_DIR = Path(__file__).resolve().parent
ROOT = _PACKAGER_DIR.parent
SPEC = _PACKAGER_DIR / "WAAPI_Tools_GUI.spec"
DISTPATH = _PACKAGER_DIR / "dist"
WORKDIR = _PACKAGER_DIR / "build" / "gui"

sys.path.insert(0, str(_PACKAGER_DIR))
from build_meta import prepare_build  # noqa: E402
from default_configs import write_default_configs  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="PyInstaller：仅 GUI（WAAPI_Tools.exe）")
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

    meta = prepare_build()
    print(f"候选构建版本：{meta['version']}（版本号将在 publish_merged 成功发布时递增）", flush=True)

    # 打包前用代码默认值重写默认配置模板，保证随包默认值干净且不会过期
    for template in write_default_configs():
        print(f"默认配置模板: {template}", flush=True)

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
    # PyInstaller 的二进制依赖分析会沿 PATH 查找 DLL；若 PATH 里有其它 Qt/ICU
    # （例如 poppler、其它工具的运行时），会把不匹配的 DLL 打进包导致
    # "DLL load failed: 找不到指定的程序"。这里只保留系统目录与当前 Python 目录。
    clean_env = dict(os.environ)
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    keep = []
    for part in os.environ.get("PATH", "").split(os.pathsep):
        low = part.lower().rstrip("\\")
        if low.startswith(system_root.lower()) or "python" in low:
            keep.append(part)
    if not keep:
        keep = [os.path.join(system_root, "System32"), system_root]
    clean_env["PATH"] = os.pathsep.join(keep)
    print(f">>> 打包使用精简 PATH（排除无关 DLL 目录）\n", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True, env=clean_env)
    out = DISTPATH / "WAAPI_Tools"
    print("\nDone.", flush=True)
    print(f"  产出: {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
