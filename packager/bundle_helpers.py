# -*- coding: utf-8 -*-
"""PyInstaller spec 共用：collect_all / 手动 .pyd / pywin32 等（供独立 MCP spec 复用）。"""

from __future__ import annotations

import importlib.util
import os

from PyInstaller.utils.hooks import collect_all, copy_metadata


def spec_root_from_packager(packager_dir: str) -> str:
    return os.path.normpath(os.path.join(packager_dir, ".."))


def _pydantic_core_pyd_binary() -> list:
    spec = importlib.util.find_spec("pydantic_core._pydantic_core")
    if spec and spec.origin and spec.origin.endswith((".pyd", ".so")):
        return [(spec.origin, "pydantic_core")]
    return []


def _rpds_pyd_binary() -> list:
    spec = importlib.util.find_spec("rpds.rpds")
    if spec and spec.origin and spec.origin.endswith((".pyd", ".so")):
        return [(spec.origin, "rpds")]
    return []


def _pywin32_bundle():
    import sys

    if sys.platform != "win32":
        return [], [], []
    binaries: list = []
    datas: list = []
    hidden = [
        "win32api",
        "win32con",
        "win32job",
        "pywintypes",
        "pythoncom",
    ]
    try:
        spec = importlib.util.find_spec("win32api")
        origin = getattr(spec, "origin", None) if spec else None
        if not origin or not isinstance(origin, str):
            return datas, binaries, hidden
        win32_dir = os.path.dirname(origin)
        site_packages = os.path.dirname(win32_dir)
        p32_dir = os.path.join(site_packages, "pywin32_system32")
        for folder, dest in ((win32_dir, "win32"), (p32_dir, "pywin32_system32")):
            if not os.path.isdir(folder):
                continue
            for name in os.listdir(folder):
                path = os.path.join(folder, name)
                if os.path.isfile(path) and name.lower().endswith((".pyd", ".dll")):
                    binaries.append((path, dest))
    except Exception:
        pass
    return datas, binaries, hidden


def metadata_datas(*names: str) -> list:
    out: list = []
    for name in names:
        try:
            out.extend(copy_metadata(name))
        except Exception:
            pass
    return out


def load_mcp_extra_bundles() -> dict:
    """MCP 栈常用：pydantic / rpds / jsonschema_specifications / pywin32。"""
    out: dict = {}
    try:
        out["pydantic_datas"], out["pydantic_binaries"], out["pydantic_hidden"] = collect_all("pydantic")
    except Exception:
        out["pydantic_datas"], out["pydantic_binaries"], out["pydantic_hidden"] = [], [], []
    try:
        out["pydantic_core_datas"], out["pydantic_core_binaries"], out["pydantic_core_hidden"] = collect_all(
            "pydantic_core"
        )
    except Exception:
        out["pydantic_core_datas"], out["pydantic_core_binaries"], out["pydantic_core_hidden"] = [], [], []
    try:
        out["rpds_datas"], out["rpds_binaries"], out["rpds_hidden"] = collect_all("rpds")
    except Exception:
        out["rpds_datas"], out["rpds_binaries"], out["rpds_hidden"] = [], [], []
    try:
        out["jsspec_datas"], out["jsspec_binaries"], out["jsspec_hidden"] = collect_all("jsonschema_specifications")
    except Exception:
        out["jsspec_datas"], out["jsspec_binaries"], out["jsspec_hidden"] = [], [], []
    pywin32_datas, pywin32_binaries, pywin32_hidden = _pywin32_bundle()
    out["pywin32_datas"] = pywin32_datas
    out["pywin32_binaries"] = pywin32_binaries
    out["pywin32_hidden"] = pywin32_hidden
    out["_pydantic_core_pyd_binary"] = _pydantic_core_pyd_binary()
    out["_rpds_pyd_binary"] = _rpds_pyd_binary()
    return out


def load_mcp_stack_bundles() -> dict:
    """mcp + rich + load_mcp_extra_bundles。"""
    b = load_mcp_extra_bundles()
    try:
        b["mcp_datas"], b["mcp_binaries"], b["mcp_hidden"] = collect_all("mcp")
    except Exception:
        b["mcp_datas"], b["mcp_binaries"], b["mcp_hidden"] = [], [], []
    try:
        b["rich_datas"], b["rich_binaries"], b["rich_hidden"] = collect_all("rich")
    except Exception:
        b["rich_datas"], b["rich_binaries"], b["rich_hidden"] = [], [], []
    return b
