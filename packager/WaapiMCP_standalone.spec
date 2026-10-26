# -*- mode: python ; coding: utf-8 -*-
"""WaapiMCP 独立打包 spec（onedir，产出 dist/WaapiMCP/，含 _internal）。

由 package_mcp.py 调用：python -m PyInstaller packager/WaapiMCP_standalone.spec
spec 本身被 .gitignore 忽略，本文件是各打包机本地生成/维护的产物模板。
"""

import os
import sys

sys.path.insert(0, os.path.abspath(SPECPATH))

from PyInstaller.utils.hooks import collect_all, copy_metadata

from bundle_helpers import load_mcp_stack_bundles, metadata_datas

packager_dir = os.path.abspath(SPECPATH)
root = os.path.dirname(packager_dir)
icon_ico_file = os.path.join(root, "icons", "Icon.ico")


def _safe_collect(name):
    try:
        datas, binaries, hiddenimports = collect_all(name)
        return datas, binaries, hiddenimports
    except Exception:
        return [], [], []


bundle = load_mcp_stack_bundles()
fastmcp_datas, fastmcp_binaries, fastmcp_hidden = _safe_collect("fastmcp")
slim_datas, slim_binaries, slim_hidden = _safe_collect("fastmcp_slim")

datas = (
    [(os.path.join(root, "ai_assistant_prompt.md"), ".")]
    + bundle["mcp_datas"]
    + bundle["rich_datas"]
    + bundle["pydantic_datas"]
    + bundle["pydantic_core_datas"]
    + bundle["jsspec_datas"]
    + bundle["pywin32_datas"]
    + fastmcp_datas
    + slim_datas
    + metadata_datas("mcp", "fastmcp", "fastmcp_slim", "pydantic", "pydantic_core", "rpds")
)
binaries = (
    bundle["mcp_binaries"]
    + bundle["pydantic_binaries"]
    + bundle["pydantic_core_binaries"]
    + bundle["rpds_binaries"]
    + bundle["pywin32_binaries"]
    + bundle["_pydantic_core_pyd_binary"]
    + bundle["_rpds_pyd_binary"]
    + fastmcp_binaries
    + slim_binaries
)
hiddenimports = (
    bundle["mcp_hidden"]
    + bundle["pydantic_hidden"]
    + bundle["pydantic_core_hidden"]
    + bundle["rpds_hidden"]
    + bundle["pywin32_hidden"]
    + fastmcp_hidden
    + slim_hidden
)

a = Analysis(
    [os.path.join(root, "waapi_mcp", "__main__.py")],
    pathex=[root, packager_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # MCP 是无界面服务：libraries.utils.io_utils 已改为惰性加载 Qt，这里整体排除 Qt 系
    # 额外排除项说明：
    #   sitecustomize / usercustomize / datalore / backend_interagg / pydevd：
    #     PyCharm 会把这些辅助模块注入 sys.path（Matplotlib 后端、Scientific 显示、调试器），
    #     PyInstaller 的 hook-site 会把 sitecustomize 当作隐藏导入，从而顺着
    #     sitecustomize → matplotlib、datalore.display → pandas → matplotlib / pytest
    #     把几十 MB 与运行无关的包打进 _internal。这里显式排除，保证在任何 IDE 环境下打包都干净。
    #   matplotlib / mpl_toolkits / pandas / PIL / pytest：MCP 侧完全用不到（音频分析只用 numpy + soundfile）。
    #   tzdata：pydantic 只是 import zoneinfo，只有在字段注解为 ZoneInfo 时才会真正构造
    #     时区对象；本工程的 MCP 工具签名全部是 dict/str/float 等基础类型，没有任何
    #     ZoneInfo 注解或时区名解析，所以 Windows 上不需要 tzdata 的 IANA 时区库。
    #     若以后新增了带 ZoneInfo 注解的 MCP 工具，需要把 "tzdata" 从这里去掉。
    excludes=[
        "PySide6",
        "shiboken6",
        "PyQt6",
        "qt_material",
        "clipboard",
        "sitecustomize",
        "usercustomize",
        "datalore",
        "backend_interagg",
        "pydevd",
        "matplotlib",
        "mpl_toolkits",
        "pandas",
        "PIL",
        "pytest",
        "_pytest",
        "tzdata",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WaapiMCP",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_ico_file if os.path.isfile(icon_ico_file) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WaapiMCP",
)
