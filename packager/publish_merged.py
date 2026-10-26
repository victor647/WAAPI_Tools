#!/usr/bin/env python3
"""将 ``package_gui`` + ``package_mcp`` 的产出合并拷贝到发布目录（单一 ``_internal``）。

默认从：
  - ``packager/dist/WAAPI_Tools/``（``WAAPI_Tools.exe`` + ``_internal``）
  - ``packager/dist/WaapiMCP/``（``WaapiMCP.exe`` + ``_internal``）

合并到 ``<dest>/``（默认 ``S:/sound_tools/waapi_tools``）：两个 exe 同级，
``_internal`` 为两边文件并集（MCP 侧覆盖同名文件）。

``S:/sound_tools/waapi_tools`` 即 Wwise Add-ons 相对引用的目录：
``Add-ons/Commands`` 上三级到 ``S:/``，再进 ``sound_tools/waapi_tools``。

另将仓库内 ``.agents/skills/wwise-waapi/``（SKILL.md 与 reference.md）复制到发布目录
``waapi-mcp-workflows/``（与 exe 同级）；需要 skill 时将其重命名为 ``wwise-waapi`` 后放入
目标工程的 ``.cursor/skills/``（或 ``.agents/skills/``）目录。

示例::

  python packager/publish_merged.py
  python packager/publish_merged.py --dest D:/Other/WAAPI_Release
  python packager/publish_merged.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
import time
from pathlib import Path

_PACKAGER_DIR = Path(__file__).resolve().parent
ROOT = _PACKAGER_DIR.parent
# 默认发布目录：Wwise Add-ons 通过 ../../../sound_tools/waapi_tools 相对引用此处的 exe
DEFAULT_DEST = Path("S:/sound_tools/waapi_tools")

_DIST = _PACKAGER_DIR / "dist"
GUI_APP = _DIST / "WAAPI_Tools"
MCP_APP = _DIST / "WaapiMCP"
# skill 源目录（整目录复制：SKILL.md + reference.md）
MCP_WORKFLOW_SKILL_SRC_DIR = ROOT / ".agents" / "skills" / "wwise-waapi"
MCP_WORKFLOW_SKILL_REL_DIR = Path("waapi-mcp-workflows")
# 目标文件被占用时改名让位所用的标记（用于事后清理遗留文件）
ASIDE_MARKER = ".publishold-"
# 覆盖目标前的重试次数与间隔，用于等待杀毒/索引等短暂占用释放
COPY_RETRY_ATTEMPTS = 4
COPY_RETRY_DELAY_SECONDS = 0.5

sys.path.insert(0, str(_PACKAGER_DIR))
from build_meta import commit_build, prepare_build, staged_version  # noqa: E402


class PublishLockedError(RuntimeError):
    """目标文件被其它进程占用，且无法改名让位。"""

    def __init__(self, paths: list[Path], side: str = ""):
        self.paths = list(paths)
        self.side = side
        prefix = f"{side} " if side else ""
        super().__init__(f"{prefix}目标文件被占用: " + ", ".join(str(p) for p in self.paths))


def _is_lock_error(exc: OSError) -> bool:
    # Windows: 5=拒绝访问，32=文件正被另一进程使用
    return isinstance(exc, PermissionError) or getattr(exc, "winerror", None) in (5, 32)


def _aside_path(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d%H%M%S")
    candidate = path.with_name(f"{path.name}{ASIDE_MARKER}{stamp}")
    index = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}{ASIDE_MARKER}{stamp}-{index}")
        index += 1
    return candidate


def _is_file_locked(path: Path) -> bool:
    # 运行中的 exe 会拒绝写句柄，用只读+写打开探测即可判断是否被占用
    if not path.exists():
        return False
    try:
        with open(path, "r+b"):
            return False
    except OSError as e:
        if not _is_lock_error(e):
            return False
        # 只读属性（而不是被占用）也会导致写入失败：交给 _copy_file 的让位逻辑处理
        try:
            if not (os.stat(path).st_mode & stat.S_IWRITE):
                return False
        except OSError:
            pass
        return True


def _move_aside(path: Path, side: str = "") -> Path:
    # 把被占用的目标改名让位：正在运行的进程继续用旧文件，发布目录能写入新文件
    target = _aside_path(path)
    try:
        os.rename(path, target)
    except OSError as e:
        raise PublishLockedError([path], side=side) from e
    return target


def _copy_file(src: Path, dst: Path, side: str = "") -> bool:
    # 覆盖目标文件；先重试，仍被占用则让位后再写入
    last_error = None
    for _ in range(COPY_RETRY_ATTEMPTS):
        try:
            shutil.copy2(src, dst)
            return False
        except OSError as e:
            if not _is_lock_error(e):
                raise
            last_error = e
            time.sleep(COPY_RETRY_DELAY_SECONDS)
    moved = _move_aside(dst, side) if dst.exists() else None
    try:
        shutil.copy2(src, dst)
    except OSError as e:
        raise PublishLockedError([dst, moved] if moved else [dst], side=side) from e
    reason = "被占用" if _is_file_locked(moved) else "无法直接覆盖（只读或权限限制）"
    print(
        f"注意：{side or '目标'}文件 {dst.name} {reason}，旧文件已改名为 {moved.name}，本次发布继续写入新文件",
        flush=True,
    )
    return True


def _remove_tree(path: Path, side: str = "") -> bool:
    # 删除目录；文件仍被占用时改名让位，由后续清理提示处理
    for _ in range(COPY_RETRY_ATTEMPTS):
        try:
            shutil.rmtree(path)
            return False
        except OSError as e:
            if not _is_lock_error(e):
                raise
            time.sleep(COPY_RETRY_DELAY_SECONDS)
    moved = _move_aside(path, side)
    print(f"注意：{side or '目标'}{path.name} 中的文件被占用，旧目录已改名为 {moved.name}，本次发布继续写入新目录", flush=True)
    return True


def _cleanup_aside_paths(directory: Path) -> list[Path]:
    # 清理历次让位留下的旧文件/目录；仍被占用的保留并返回
    remaining: list[Path] = []
    for p in sorted(directory.glob(f"*{ASIDE_MARKER}*")):
        try:
            _force_remove(p)
        except OSError:
            remaining.append(p)
    return remaining


def _force_remove(path: Path) -> None:
    # 让位出来的旧文件可能带只读属性（例如 SVN needs-lock），删之前先去掉
    if path.is_dir():
        for child in path.rglob("*"):
            if child.is_file():
                try:
                    os.chmod(child, stat.S_IWRITE | stat.S_IREAD)
                except OSError:
                    pass
        shutil.rmtree(path)
        return
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass
    path.unlink()


def _resolve_dest(path_arg: Path | None) -> Path:
    if path_arg is None:
        return DEFAULT_DEST
    p = Path(path_arg)
    return p.resolve() if p.is_absolute() else (ROOT / p).resolve()


def _merge_tree(src: Path, dst: Path) -> None:
    for p in src.rglob("*"):
        if p.is_file():
            rel = p.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)


def _update_tree(src: Path, dst: Path) -> list[Path]:
    # 只覆盖同名文件，不删除目标里多出来的文件（例如 MCP 仍在使用的那部分）；
    # 被占用而无法覆盖的文件跳过并返回，避免把正在运行的 MCP 的依赖删掉或改名
    skipped: list[Path] = []
    for p in src.rglob("*"):
        if not p.is_file():
            continue
        target = dst / p.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(p, target)
        except OSError as e:
            if not _is_lock_error(e):
                raise
            skipped.append(target)
    return skipped


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
        print(
            f"[dry-run] 目标占用情况：GUI={'占用' if _is_file_locked(dest / 'WAAPI_Tools.exe') else '空闲'}，"
            f"MCP={'占用' if _is_file_locked(dest / 'WaapiMCP.exe') else '空闲'}",
            flush=True,
        )
        if copy_skill and MCP_WORKFLOW_SKILL_SRC_DIR.is_dir():
            skill_dst = dest / MCP_WORKFLOW_SKILL_REL_DIR
            print(f"[dry-run] 将复制 MCP 工作流 SKILL: {MCP_WORKFLOW_SKILL_SRC_DIR} -> {skill_dst}", flush=True)
        elif copy_skill:
            print(f"[dry-run] 跳过 SKILL（源不存在）: {MCP_WORKFLOW_SKILL_SRC_DIR}", flush=True)
        return

    dest.mkdir(parents=True, exist_ok=True)
    # 先清理上次遗留的让位文件（可能仍被占用，忽略结果）
    _cleanup_aside_paths(dest)

    # MCP 被占用（AI 宿主正在运行发布目录里的 WaapiMCP.exe）时：跳过 MCP，只发布 GUI。
    # 此时不能整体重建 _internal（会删掉 MCP 依赖并撞上被占用的 DLL），改为就地覆盖 GUI 的文件。
    skip_mcp = _is_file_locked(dest / "WaapiMCP.exe")
    if skip_mcp:
        print("检测到 MCP 正在运行（WaapiMCP.exe 被占用）：本次跳过 MCP，只发布 GUI。", flush=True)

    replaced_in_use = _copy_file(gexe, dest / "WAAPI_Tools.exe", side="GUI")
    if not skip_mcp:
        replaced_in_use = _copy_file(mexe, dest / "WaapiMCP.exe", side="MCP") or replaced_in_use

    out_i = dest / "_internal"
    if skip_mcp:
        if out_i.exists():
            skipped = _update_tree(gi, out_i)
            if skipped:
                print(
                    f"注意：{len(skipped)} 个 _internal 文件被正在运行的 MCP 占用，本次保留旧文件"
                    f"（例如 {skipped[0].name}）",
                    flush=True,
                )
        else:
            shutil.copytree(gi, out_i)
        print(f"已更新 _internal（仅 GUI 文件，就地覆盖，保留 MCP 依赖）: {gi} -> {out_i}", flush=True)
    else:
        if out_i.exists():
            replaced_in_use = _remove_tree(out_i, side="GUI/MCP 共用") or replaced_in_use
        shutil.copytree(gi, out_i)
        _merge_tree(mi, out_i)
        print(f"已合并 _internal: {gi} + {mi} -> {out_i}", flush=True)

    if copy_skill:
        if MCP_WORKFLOW_SKILL_SRC_DIR.is_dir():
            skill_dst = dest / MCP_WORKFLOW_SKILL_REL_DIR
            skill_dst.mkdir(parents=True, exist_ok=True)
            copied = []
            for source_file in sorted(MCP_WORKFLOW_SKILL_SRC_DIR.iterdir()):
                if source_file.is_file():
                    shutil.copy2(source_file, skill_dst / source_file.name)
                    copied.append(source_file.name)
            print(
                f"已复制 MCP 工作流 SKILL: {MCP_WORKFLOW_SKILL_SRC_DIR} -> {skill_dst}"
                f"（{', '.join(copied)}）",
                flush=True,
            )
        else:
            print(f"跳过 SKILL（源不存在）: {MCP_WORKFLOW_SKILL_SRC_DIR}", flush=True)

    remaining = _cleanup_aside_paths(dest)
    if skip_mcp:
        print(
            "提示：本次未更新 MCP（WaapiMCP.exe 与 MCP 的 _internal 文件保持原样）；"
            "需要更新 MCP 时请先在 AI 宿主中停止 MCP 服务再重新发布。",
            flush=True,
        )
    elif replaced_in_use:
        print(
            "提示：本次发布替换了已被占用的文件（见上方提示），正在运行的程序仍在使用旧版本，请重启它以加载新版本。",
            flush=True,
        )
    if remaining:
        print("提示：以下旧文件/目录仍被占用未能删除，关闭相关程序后可手动删除：", flush=True)
        for p in remaining:
            print(f"  - {p}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="合并拷贝 GUI+MCP 构建到发布目录")
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        metavar="DIR",
        help=f"发布目录（默认 {DEFAULT_DEST}，Wwise Add-ons 相对引用目录）",
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
        help="不复制 .agents/skills/wwise-waapi/ 下的 skill 文件",
    )
    parser.add_argument(
        "--no-version",
        action="store_true",
        help="不递增版本号（例如同一构建重复发布到多个目录时使用）",
    )
    args = parser.parse_args()

    dest = _resolve_dest(args.dest)
    gui_d = Path(args.gui_dir) if args.gui_dir else GUI_APP
    mcp_d = Path(args.mcp_dir) if args.mcp_dir else MCP_APP

    print(f"目标目录: {dest}", flush=True)
    print(f"源 GUI: {gui_d}", flush=True)
    print(f"源 MCP: {mcp_d}", flush=True)

    copy_skill = not args.no_skill
    # 发布号只在成功发布时递增一次；dry-run 或 --no-version 不参与
    meta = None
    if not args.dry_run and not args.no_version:
        prev_staged = staged_version()
        meta = prepare_build()
        if prev_staged is not None and prev_staged != meta["version"]:
            print(
                f"构建产物内嵌版本为 {prev_staged}，"
                f"本次将发布 {meta['version']}，"
                "看起来没有重新打包或该构建已发布过。",
                file=sys.stderr,
            )
            print("如确需强制发布且不递增版本，请加 --no-version。", file=sys.stderr)
            return 1
        print(f"本次发布版本：{meta['version']}", flush=True)

    try:
        merge_onedir(gui_d.resolve(), mcp_d.resolve(), dest.resolve(), args.dry_run, copy_skill)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    except PublishLockedError as e:
        label = f"{e.side} " if e.side else ""
        print(f"\n发布失败：{label}目标文件被占用，无法写入。", file=sys.stderr)
        for p in e.paths:
            print(f"  - {p}", file=sys.stderr)
        print(
            "GUI 被占用：请关闭正在运行的 WAAPI_Tools.exe 后重试。\n"
            "MCP 被占用：正常会自动跳过 MCP 只发布 GUI；若仍报错，请在 AI 宿主（Cursor/Codex 等）中停止 MCP 服务后重试。",
            file=sys.stderr,
        )
        return 2
    except OSError as e:
        print(f"\n发布失败：{e}", file=sys.stderr)
        return 1

    if not args.dry_run:
        print(f"\nDone. 已写入: {dest}", flush=True)
        if meta is not None:
            commit_build(meta)
            print(f"已递增版本号：{meta['version']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
