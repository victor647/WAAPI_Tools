# 构建元数据：主版本人工维护，小版本每次打包自动 +1。
# 两段式：prepare_build() 先计算候选版本并生成 globals/_build_info.py（PyInstaller 打包需要）；
#         commit_build() 在 PyInstaller 成功后才写入状态文件，保证失败构建不消耗版本号。
# 用法：打包脚本在 PyInstaller 前调用 prepare_build()，成功后调用 commit_build(meta)。
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

_PACKAGER_DIR = Path(__file__).resolve().parent
ROOT = _PACKAGER_DIR.parent
STATE_FILE = _PACKAGER_DIR / "build_state.json"
BUILD_INFO_FILE = ROOT / "globals" / "_build_info.py"


def _load_major_version() -> int:
    # 从 globals/constants.py 读取人工维护的主版本号（constants 无第三方依赖，可安全执行）
    spec = importlib.util.spec_from_file_location("_constants_probe", ROOT / "globals" / "constants.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return int(module.SOFTWARE_MAJOR_VERSION)


def _load_state() -> dict:
    if not STATE_FILE.is_file():
        return {}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _next_minor(major: int, state: dict) -> int:
    # 主版本变化或首次构建时从 0 开始，否则在上次小版本基础上 +1
    if state.get("major") != major:
        return 0
    try:
        return int(state.get("minor", 0)) + 1
    except (TypeError, ValueError):
        return 0


def _git_short_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def prepare_build() -> dict:
    # 计算候选构建版本号并生成 _build_info.py（不写状态文件，失败可重试同一版本号）
    major = _load_major_version()
    state = _load_state()
    minor = _next_minor(major, state)
    build_date = datetime.now().strftime("%Y/%m/%d")
    commit = _git_short_hash()
    version_text = f"V{major}.{minor} {build_date}"

    lines = [
        "# 由 packager/build_meta.py 自动生成，请勿手改",
        f'BUILD_VERSION = "{version_text}"',
        f"BUILD_MAJOR = {major}",
        f"BUILD_MINOR = {minor}",
        f'BUILD_DATE = "{build_date}"',
        f'BUILD_COMMIT = "{commit}"',
        "",
    ]
    BUILD_INFO_FILE.write_text("\n".join(lines), encoding="utf-8")

    return {
        "version": version_text,
        "major": major,
        "minor": minor,
        "build_date": build_date,
        "commit": commit,
    }


def staged_minor() -> int | None:
    # 读取最近一次打包暂存进 globals/_build_info.py 的小版本（即 exe 内嵌的版本）
    if not BUILD_INFO_FILE.is_file():
        return None
    match = re.search(r"^BUILD_MINOR\s*=\s*(\d+)", BUILD_INFO_FILE.read_text(encoding="utf-8"), re.MULTILINE)
    return int(match.group(1)) if match else None


def commit_build(info: dict) -> None:
    # 构建成功后把小版本写入状态文件；下次 prepare_build 会在此基础上 +1
    state = {
        "major": int(info["major"]),
        "minor": int(info["minor"]),
        "last_build_date": info["build_date"],
    }
    _save_state(state)


if __name__ == "__main__":
    import sys

    info = prepare_build()
    print(json.dumps(info, ensure_ascii=False, indent=2), file=sys.stdout)
    print("提示：以上为候选版本，构建成功后请调用 commit_build() 才会写入状态文件。", file=sys.stderr)
