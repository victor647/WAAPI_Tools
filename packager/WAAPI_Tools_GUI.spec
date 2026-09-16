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
# 工程根目录的用户配置随包携带：exe 目录无 user_config.json 时由
# libraries/utils/user_config.py 复制出来，作为用户初始化的数据来源
user_config_file = os.path.join(root, "user_config.json")
if os.path.isfile(user_config_file):
    datas.append((user_config_file, "."))
# 工程规范文件同理：工程目录与 exe 目录都没有时由
# data/project_conventions.py 复制出来，作为工程规范的初始数据
conventions_file = os.path.join(root, "ProjectConventions.json")
if os.path.isfile(conventions_file):
    datas.append((conventions_file, "."))
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
    # 同时排除 PyCharm 等 IDE 注入的辅助模块：sitecustomize 会被 PyInstaller 的 hook-site
    # 当作隐藏导入，从而顺着 sitecustomize → matplotlib、datalore.display → pandas 把
    # 几十 MB 无关的包（matplotlib / pandas / PIL / pytest）打进 _internal
    excludes=[
        "PyQt6",
        "PyQt5",
        "sitecustomize",
        "usercustomize",
        "datalore",
        "backend_interagg",
        "pydevd",
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
