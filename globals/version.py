# 运行时软件版本：打包时优先读取 packager/build_meta.py 生成的 globals/_build_info.py；
# 源码直跑（未打包）时显示主版本 + DEV，避免把未构建信息当成正式版本。
from __future__ import annotations

import sys

from globals.constants import SOFTWARE_MAJOR_VERSION


def _build_info():
    if not getattr(sys, "frozen", False):
        return None
    try:
        from globals import _build_info

        return _build_info
    except ImportError:
        return None


def get_software_version() -> str:
    # 窗口标题等处使用的完整版本串，例如 "V4.1 2026/09/09"
    info = _build_info()
    if info is not None:
        return getattr(info, "BUILD_VERSION", f"V{SOFTWARE_MAJOR_VERSION}")
    return f"V{SOFTWARE_MAJOR_VERSION} DEV"


def is_packaged_build() -> bool:
    return _build_info() is not None


def get_build_date() -> str:
    info = _build_info()
    return getattr(info, "BUILD_DATE", "") if info else ""


def get_build_commit() -> str:
    info = _build_info()
    return getattr(info, "BUILD_COMMIT", "") if info else ""
