# -*- mode: python ; coding: utf-8 -*-
"""WAAPI 工具集 GUI 打包 spec（onedir，产出 dist/WAAPI_Tools/，含 _internal）。

由 package_gui.py 调用：python -m PyInstaller packager/WAAPI_Tools_GUI.spec
spec 本身被 .gitignore 忽略，本文件是各打包机本地生成/维护的产物模板。
"""

import os
import sys

sys.path.insert(0, os.path.abspath(SPECPATH))

from PyInstaller.utils.hooks import collect_all

packager_dir = os.path.abspath(SPECPATH)
root = os.path.dirname(packager_dir)


def _safe_collect(name):
    try:
        datas, binaries, hiddenimports = collect_all(name)
        return datas, binaries, hiddenimports
    except Exception:
        return [], [], []


qt_material_datas, qt_material_binaries, qt_material_hidden = _safe_collect("qt_material")

# 运行时通过 path_utils.get_resource_path 读取的仓库资源（解压到 bundle 根目录）
datas = [
    (os.path.join(root, "material.css"), "."),
    (os.path.join(root, "ai_assistant_prompt.md"), "."),
] + qt_material_datas
binaries = qt_material_binaries
hiddenimports = qt_material_hidden

a = Analysis(
    [os.path.join(root, "main.py")],
    pathex=[root, packager_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # GUI 使用 PySide6；排除本机可能同时安装的其它 Qt 绑定，避免 PyInstaller 报多绑定冲突
    excludes=["PyQt6", "PyQt5"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WAAPI_Tools",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WAAPI_Tools",
)
