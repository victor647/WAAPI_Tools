#!/usr/bin/env python3
"""将 ``package_gui`` + ``package_mcp`` 的产出合并拷贝到发布目录（单一 ``_internal``）。

默认从：
  - ``packager/dist/WAAPI_Tools/``（``WAAPI_Tools.exe`` + ``_internal``）
  - ``packager/dist/WaapiMCP/``（``WaapiMCP.exe`` + ``_internal``）

合并到 ``<dest>/``（默认 ``D:/Audio_P4/Tools/WAAPI_Tools``）：两个 exe 同级，
``_internal`` 为两边文件并集（MCP 侧覆盖同名文件）。

另将仓库内 ``.cursor/skills/wwise-waapi/SKILL.md`` 复制到发布目录
``waapi-mcp-workflows/SKILL.md``（与 exe 同级）；需要 Cursor skill 时可将 ``waapi-mcp-workflows/``
拷到目标工程 ``.cursor/skills/`` 下。

示例::

  python packager/publish_merged.py
  python packager/publish_merged.py --dest D:/Other/WAAPI_Release
  python packager/publish_merged.py --dry-run
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_PACKAGER_DIR = Path(__file__).resolve().parent
ROOT = _PACKAGER_DIR.parent
# 默认：相对仓库根，解析为 D:\\Audio_P4\\Tools\\WAAPI_Tools（与 TechAudio\\Tools\\WAAPI_Tools 同级 Tools 目录）
DEFAULT_DEST_REL = Path("../../../Tools/WAAPI_Tools")

_DIST = _PACKAGER_DIR / "dist"
GUI_APP = _DIST / "WAAPI_Tools"
MCP_APP = _DIST / "WaapiMCP"
MCP_WORKFLOW_SKILL_SRC = ROOT / ".cursor" / "skills" / "wwise-waapi" / "SKILL.md"
MCP_WORKFLOW_SKILL_REL = Path("waapi-mcp-workflows/SKILL.md")


def _resolve_dest(path_arg: Path | None) -> Path:
    if path_arg is None:
        return (ROOT / DEFAULT_DEST_REL).resolve()
    p = Path(path_arg)
    return p.resolve() if p.is_absolute() else (ROOT / p).resolve()


def _merge_tree(src: Path, dst: Path) -> None:
    for p in src.rglob("*"):
        if p.is_file():
            rel = p.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)


def merge_onedir(
    gui_app_dir: Path, mcp_app_dir: Path, dest: Path, dry_run: bool, copy_skill: bool
) -> None:
    gexe = gui_app_dir / "WAAPI_Tools.exe"
    mexe = mcp_app_dir / "WaapiMCP.exe"
    gi = gui_app_dir / "_internal"
    mi = mcp_app_dir / "_internal"

    for label, p in (
        ("GUI exe", gexe),
        ("MCP exe", mexe),
        ("GUI _internal", gi),
        ("MCP _internal", mi),
    ):
        if not p.exists():
            raise FileNotFoundError(f"{label} 不存在: {p}（请先运行 package_gui.py / package_mcp.py）")

    if dry_run:
        print(f"[dry-run] 将写入: {dest}", flush=True)
        if copy_skill and MCP_WORKFLOW_SKILL_SRC.is_file():
            skill_dst = dest / MCP_WORKFLOW_SKILL_REL
            print(f"[dry-run] 将复制 MCP 工作流 SKILL: {MCP_WORKFLOW_SKILL_SRC} -> {skill_dst}", flush=True)
        elif copy_skill:
            print("[dry-run] 跳过 SKILL（源不存在）", flush=True)
        return

    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(gexe, dest / "WAAPI_Tools.exe")
    shutil.copy2(mexe, dest / "WaapiMCP.exe")

    out_i = dest / "_internal"
    if out_i.exists():
        shutil.rmtree(out_i)
    shutil.copytree(gi, out_i)
    _merge_tree(mi, out_i)
    print(f"已合并 _internal: {gi} + {mi} -> {out_i}", flush=True)

    if copy_skill:
        if MCP_WORKFLOW_SKILL_SRC.is_file():
            skill_dst = dest / MCP_WORKFLOW_SKILL_REL
            skill_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(MCP_WORKFLOW_SKILL_SRC, skill_dst)
            print(f"已复制 MCP 工作流 SKILL: {MCP_WORKFLOW_SKILL_SRC} -> {skill_dst}", flush=True)
        else:
            print(f"跳过 SKILL（源不存在）: {MCP_WORKFLOW_SKILL_SRC}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="合并拷贝 GUI+MCP 构建到发布目录")
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        metavar="DIR",
        help=f"发布目录（默认相对仓库 {DEFAULT_DEST_REL}，即 D:/Audio_P4/Tools/WAAPI_Tools）",
    )
    parser.add_argument(
        "--gui-dir",
        type=Path,
        default=None,
        help=f"覆盖 GUI 构建目录（默认 {GUI_APP}）",
    )
    parser.add_argument(
        "--mcp-dir",
        type=Path,
        default=None,
        help=f"覆盖 MCP 构建目录（默认 {MCP_APP}）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只检查路径，不写盘")
    parser.add_argument(
        "--no-skill",
        action="store_true",
        help="不复制 .cursor/skills/wwise-waapi/SKILL.md",
    )
    args = parser.parse_args()

    dest = _resolve_dest(args.dest)
    gui_d = Path(args.gui_dir) if args.gui_dir else GUI_APP
    mcp_d = Path(args.mcp_dir) if args.mcp_dir else MCP_APP

    print(f"目标目录: {dest}", flush=True)
    print(f"源 GUI: {gui_d}", flush=True)
    print(f"源 MCP: {mcp_d}", flush=True)

    copy_skill = not args.no_skill

    try:
        merge_onedir(gui_d.resolve(), mcp_d.resolve(), dest.resolve(), args.dry_run, copy_skill)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1

    if not args.dry_run:
        print(f"\nDone. 已写入: {dest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
