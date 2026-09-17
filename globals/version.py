# 运行时软件版本：打包时读取 packager/build_meta.py 生成的 globals/_build_info.py（日期版本，如 2026.9.5）；
# 源码直跑（未打包）时显示当前年月 + DEV，避免把未构建信息当成正式版本。
from __future__ import annotations

import sys
from datetime import datetime


def _build_info():
    if not getattr(sys, "frozen", False):
        return None
    try:
        from globals import _build_info

        return _build_info
    except ImportError:
        return None


def get_software_version() -> str:
    # 窗口标题等处使用的版本串，例如 "2026.9.5"
    info = _build_info()
    version = getattr(info, "BUILD_VERSION", "") if info is not None else ""
    if version:
        return version
    now = datetime.now()
    return f"{now.year}.{now.month}.DEV"


def is_packaged_build() -> bool:
    return _build_info() is not None


def get_build_date() -> str:
    info = _build_info()
    return getattr(info, "BUILD_DATE", "") if info else ""


def get_build_commit() -> str:
    info = _build_info()
    return getattr(info, "BUILD_COMMIT", "") if info else ""
