# 构建元数据：版本号为日期版本「年.月.当月发布号」，如 2026.9.5。
# 同一天内重复打包/发布沿用同一版本号（不步进），换天后发布号 +1，跨月重置为 1。
# 两段式：prepare_build() 先计算候选版本并生成 globals/_build_info.py（PyInstaller 打包需要）；
#         commit_build() 在发布成功后才写入状态文件，保证失败构建不消耗发布号。
# 用法：打包脚本在 PyInstaller 前调用 prepare_build()，发布成功后调用 commit_build(meta)。
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

_PACKAGER_DIR = Path(__file__).resolve().parent
ROOT = _PACKAGER_DIR.parent
STATE_FILE = _PACKAGER_DIR / "build_state.json"
BUILD_INFO_FILE = ROOT / "globals" / "_build_info.py"


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


def _next_release(year: int, month: int, build_date: str, state: dict) -> int:
    # 跨月或首次构建从 1 开始；同一年月内换天 +1，同一天沿用上次的发布号
    if state.get("year") != year or state.get("month") != month:
        return 1
    try:
        release = int(state.get("release", 0))
    except (TypeError, ValueError):
        return 1
    if state.get("last_build_date") == build_date:
        return release
    return release + 1


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
    # 计算候选版本号并生成 _build_info.py（不写状态文件，失败可重试同一版本号）
    now = datetime.now()
    year, month = now.year, now.month
    build_date = now.strftime("%Y/%m/%d")
    state = _load_state()
    release = _next_release(year, month, build_date, state)
    commit = _git_short_hash()
    version_text = f"{year}.{month}.{release}"

    lines = [
        "# 由 packager/build_meta.py 自动生成，请勿手改",
        f'BUILD_VERSION = "{version_text}"',
        f"BUILD_YEAR = {year}",
        f"BUILD_MONTH = {month}",
        f"BUILD_RELEASE = {release}",
        f'BUILD_DATE = "{build_date}"',
        f'BUILD_COMMIT = "{commit}"',
        "",
    ]
    BUILD_INFO_FILE.write_text("\n".join(lines), encoding="utf-8")

    return {
        "version": version_text,
        "year": year,
        "month": month,
        "release": release,
        "build_date": build_date,
        "commit": commit,
    }


def staged_version() -> str | None:
    # 读取最近一次打包暂存进 globals/_build_info.py 的版本串（即 exe 内嵌的版本）
    if not BUILD_INFO_FILE.is_file():
        return None
    match = re.search(
        r'^BUILD_VERSION\s*=\s*"([^"]+)"', BUILD_INFO_FILE.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def commit_build(info: dict) -> None:
    # 发布成功后把发布号写入状态文件；下次 prepare_build 会在此基础上 +1
    state = {
        "year": int(info["year"]),
        "month": int(info["month"]),
        "release": int(info["release"]),
        "last_build_date": info["build_date"],
    }
    _save_state(state)


if __name__ == "__main__":
    import sys

    info = prepare_build()
    print(json.dumps(info, ensure_ascii=False, indent=2), file=sys.stdout)
    print("提示：以上为候选版本，发布成功后请调用 commit_build() 才会写入状态文件。", file=sys.stderr)
