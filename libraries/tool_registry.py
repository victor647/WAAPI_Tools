# 中立 Wwise 工具注册表：供「软件内手动工具 / AI 助手 / MCP」三方复用。
# 约束：本模块不得 import fastmcp、PySide6/Qt、waapi_mcp；只依赖 libraries 内的业务封装。
# 每个工具只定义一次（名称/描述/参数 schema/handler），各消费方自行生成自己的协议层：
# - AI 助手：tool_registry.list_tools() 生成 function calling schema，execute_tool() 派发；
# - MCP：waapi_mcp/registry_mcp_tools.py 按注册表批量生成 @mcp.tool；
# - 手动工具：继续直接调用 *_utils（注册表 handler 内部复用的就是这些封装）。
from __future__ import annotations

import os
import builtins
import json
import math
import re
import statistics
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable

from libraries.utils.wwise import (
    audio_source_utils,
    common_utils,
    container_utils,
    event_utils,
    game_sync_utils,
    localization_utils,
    mixing_utils,
    project_utils,
    soundbank_utils,
    transport_utils,
    waapi_utils,
)
from libraries.utils.log_utils import Logger
from libraries.wwise_object import WwiseObject, WwiseObjectType

# 单次可列出的音频源上限 / 可统计的对象上限，防止一次请求拖垮上下文
AUDIO_SOURCE_LIST_LIMIT = 300
SIZE_STAT_OBJECT_LIMIT = 100
INFO_OBJECT_LIMIT = 50
CHILD_LIST_LIMIT = 500
REF_LIST_LIMIT = 500
DESCENDANT_LIST_LIMIT = 1000


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    # OpenAI function-calling 的 parameters JSON schema
    parameters: dict
    handler: Callable[[dict], Any]
    mutating: bool = False

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


_TOOLS: dict[str, ToolSpec] = {}


def register_tool(
    name: str,
    description: str,
    parameters: dict,
    handler: Callable[[dict], Any],
    *,
    mutating: bool = False,
) -> ToolSpec:
    if name in _TOOLS:
        raise ValueError(f"工具已注册：{name}")
    # 统一 OpenAI function-calling 参数结构：顶层必须是 type=object，
    # 避免个别供应商拒绝缺 type/properties/required 的 schema
    if not isinstance(parameters, dict):
        parameters = {}
    normalized = {
        "type": "object",
        "properties": parameters.get("properties") if isinstance(parameters.get("properties"), dict) else {},
        "required": parameters.get("required") if isinstance(parameters.get("required"), list) else [],
    }
    spec = ToolSpec(name, description, normalized, handler, mutating=mutating)
    _TOOLS[name] = spec
    return spec


def list_tools() -> list[ToolSpec]:
    return list(_TOOLS.values())


def get_tool(name: str) -> ToolSpec | None:
    return _TOOLS.get(name)


def execute_tool(name: str, arguments: dict) -> Any:
    # 按名称执行注册表工具，返回 JSON 兼容的结构化结果
    spec = _TOOLS[name]
    return spec.handler(arguments)


def _require_object_ids(args: dict) -> list[str]:
    # 入参统一支持 object_ids 数组（个别情况容忍单个字符串）
    value = args.get("object_ids")
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not value:
        raise ValueError("缺少 object_ids 参数，应传入 Wwise 对象 id 数组")
    return [str(item) for item in value]


def _resolve_limit(args: dict, default: int):
    # limit=0 表示不限量（返回 None）；缺省用工具默认上限
    value = args.get("limit")
    if value is None:
        return default
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return default
    return limit if limit > 0 else None


def _object_ids_parameters(description: str) -> dict:
    return {
        "type": "object",
        "properties": {
            "object_ids": {
                "type": "array",
                "items": {"type": "string", "description": "Wwise 对象 GUID"},
                "description": description,
            }
        },
        "required": ["object_ids"],
    }


def _audio_sources_of(obj: WwiseObject) -> list:
    # 解析对象子树下的 AudioFileSource：Sound 走子级递归，Event 按播放目标展开
    if obj.type == WwiseObjectType.AudioSource:
        return [obj]
    if obj.type == WwiseObjectType.Event:
        sources = []
        for target in event_utils.get_event_targets(obj):
            sources.extend(waapi_utils.get_descendants_of_type(target, WwiseObjectType.AudioSource))
        return sources
    return waapi_utils.get_descendants_of_type(obj, WwiseObjectType.AudioSource)


def _handler_get_objects_info(args: dict) -> dict:
    # 读取对象详情：名称/类型/路径/备注/启用状态
    ids = _require_object_ids(args)[:INFO_OBJECT_LIMIT]
    items = []
    errors = []
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            items.append({
                "id": obj.id,
                "name": obj.name,
                "type": obj.type.value,
                "path": obj.path,
                "notes": common_utils.get_object_notes(obj),
                "included": common_utils.is_object_included(obj),
            })
        except Exception as e:
            errors.append(f"{object_id}: {e}")
    return {"items": items, "errors": errors}


def _handler_get_audio_sources(args: dict) -> dict:
    # 列出对象子树下的音频源及其磁盘源文件路径（读属性，不改工程）
    ids = _require_object_ids(args)
    limit = _resolve_limit(args, AUDIO_SOURCE_LIST_LIMIT)
    items = []
    errors = []
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            for source in _audio_sources_of(obj):
                if limit is not None and len(items) >= limit:
                    break
                file_path = audio_source_utils.get_source_absolute_path(source) or ""
                items.append({
                    "parent": obj.name,
                    "id": source.id,
                    "name": source.name,
                    "path": source.path,
                    "file_path": file_path,
                })
        except Exception as e:
            errors.append(f"{object_id}: {e}")
    return {
        "count": len(items),
        "truncated": limit is not None and len(items) >= limit,
        "items": items,
        "errors": errors,
    }


def _handler_calculate_audio_source_size(args: dict) -> dict:
    # 递归枚举每个对象下的 AudioFileSource，按磁盘 wav 实际大小统计（文件按路径去重）
    ids = _require_object_ids(args)[:SIZE_STAT_OBJECT_LIMIT]
    seen_paths = set()
    missing = []
    total_bytes = 0
    per_object = []
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            size_bytes = 0
            file_count = 0
            for source in _audio_sources_of(obj):
                path = audio_source_utils.get_source_absolute_path(source)
                if not path or path in seen_paths:
                    continue
                seen_paths.add(path)
                if os.path.exists(path):
                    try:
                        size_bytes += os.path.getsize(path)
                        file_count += 1
                    except OSError as e:
                        missing.append(f"{path}（{e}）")
                else:
                    missing.append(path)
            per_object.append({
                "object": obj.name,
                "files": file_count,
                "size_mb": round(size_bytes / 1048576, 3),
            })
        except Exception as e:
            per_object.append({"object": object_id, "error": str(e)})
    return {
        "total_files": len(seen_paths),
        "total_mb": round(total_bytes / 1048576, 3),
        "objects": per_object,
        "missing": {"count": len(missing), "samples": missing[:5]},
    }


def _handler_get_children(args: dict) -> dict:
    # 列出对象子级/后代（含 id/name/type/path），用于“层级里有什么”类查询
    ids = _require_object_ids(args)
    recursive = bool(args.get("recursive", True))
    limit = _resolve_limit(args, CHILD_LIST_LIMIT)
    items = []
    errors = []
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            children = waapi_utils.get_child_objects(obj, include_descendants=recursive)
            for child in children:
                if limit is not None and len(items) >= limit:
                    break
                items.append({
                    "parent": obj.name,
                    "parent_id": obj.id,
                    "id": child.id,
                    "name": child.name,
                    "type": child.type.value,
                    "path": child.path,
                })
        except Exception as e:
            errors.append(f"{object_id}: {e}")
    return {
        "count": len(items),
        "recursive": recursive,
        "truncated": limit is not None and len(items) >= limit,
        "items": items,
        "errors": errors,
    }


def _resolve_object_type(type_name: str) -> WwiseObjectType | None:
    # 兼容 WwiseObjectType 的 value 与 name（如 AudioFileSource / AudioSource）
    return next(
        (member for member in WwiseObjectType if member.value == type_name or member.name == type_name),
        None,
    )


def _handler_get_descendants_of_type(args: dict) -> dict:
    # 按类型递归取后代：WAAPI 侧使用 WAQL 过滤，只回传目标类型，比全量列后代更省数据
    ids = _require_object_ids(args)
    type_name = str(args.get("child_type") or "").strip()
    include_path = bool(args.get("include_path", False))
    limit = _resolve_limit(args, DESCENDANT_LIST_LIMIT)
    child_type = _resolve_object_type(type_name)
    if child_type is None:
        valid = ", ".join(member.value for member in WwiseObjectType)
        return {"items": [], "errors": [f"未知类型「{type_name}」，可用值：{valid}"]}
    items = []
    errors = []
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            for child in waapi_utils.get_descendants_of_type(obj, child_type):
                if limit is not None and len(items) >= limit:
                    break
                item = {
                    "root": obj.name,
                    "root_id": obj.id,
                    "id": child.id,
                    "name": child.name,
                    "type": child.type.value,
                }
                if include_path:
                    item["path"] = child.path
                items.append(item)
        except Exception as e:
            errors.append(f"{object_id}: {e}")
    return {
        "count": len(items),
        "truncated": limit is not None and len(items) >= limit,
        "items": items,
        "errors": errors,
    }


# 元工具：对任意“返回列表”的工具结果做计数/分组，避免为每种查询单独写计数工具
META_TOOL_NAMES = frozenset({"count_tool_items", "group_tool_items", "aggregate_tool_chain"})
_LIST_KEYS = ("items", "objects", "data", "results", "matched_objects", "matched_groups", "groups")


def _extract_list(value, list_path: str = ""):
    # 从工具结果里取出目标列表：支持显式 list_path（如 "items"）或按常见键自动识别
    if isinstance(value, list):
        return value, ""
    if not isinstance(value, dict):
        return None, ""
    if list_path:
        cursor = value
        for part in list_path.split("."):
            cursor = cursor.get(part) if isinstance(cursor, dict) else None
            if cursor is None:
                return None, list_path
        return (cursor, list_path) if isinstance(cursor, list) else (None, list_path)
    for key in _LIST_KEYS:
        if isinstance(value.get(key), list):
            return value[key], key
    for key, item in value.items():
        if isinstance(item, list) and item:
            return item, key
    for key, item in value.items():
        if isinstance(item, list):
            return item, key
    return None, ""


def _resolve_list_result(tool_name: str, arguments: dict, list_path: str):
    # 执行目标工具并取出列表；返回 (items, list_key, error)
    tool_name = str(tool_name or "").strip()
    if not tool_name:
        return None, "", "缺少 tool_name 参数（要统计的查询工具名）"
    if tool_name in META_TOOL_NAMES:
        return None, "", f"不能对元工具 {tool_name} 再聚合，请传入普通查询工具"
    spec = get_tool(tool_name)
    if spec is None:
        return None, "", f"未知工具：{tool_name}"
    call_args = dict(arguments) if isinstance(arguments, dict) else {}
    # 聚合场景默认不限量，避免目标工具的默认上限截断统计结果
    call_args.setdefault("limit", 0)
    required = [name for name in spec.parameters.get("required", []) if name not in call_args]
    if required:
        hints = ", ".join(
            f"{name}（{spec.parameters['properties'].get(name, {}).get('description', '')}）" for name in required
        )
        return None, "", f"调用 {tool_name} 缺少必填参数：{hints}；请把参数放进 arguments 对象"
    try:
        value = execute_tool(tool_name, call_args)
    except Exception as e:
        return None, "", f"调用 {tool_name} 失败：{e}；请检查 arguments 是否为该工具的参数对象"
    items, list_key = _extract_list(value, str(list_path or "").strip())
    if items is None:
        return None, "", f"工具 {tool_name} 的结果里没有找到列表，可用 list_path 指定取值路径"
    return items, list_key, ""


def _handler_count_tool_items(args: dict) -> dict:
    # 通用计数：执行任意返回列表的工具并统计条数（不受模型侧结果截断影响）
    items, list_key, error = _resolve_list_result(
        args.get("tool_name"), args.get("arguments"), args.get("list_path")
    )
    if error:
        return {"error": error}
    return {
        "tool": str(args.get("tool_name") or "").strip(),
        "list_key": list_key,
        "total": len(items),
        "sample": items[:10],
    }


def _handler_group_tool_items(args: dict) -> dict:
    # 通用分组统计：按列表项的某个字段分组计数，可选 min_count 只保留“数量大于该值”的分组
    group_by = str(args.get("group_by") or "").strip()
    if not group_by:
        return {"error": "缺少 group_by 参数（要按哪个字段分组，如 root_id / type / parent_id）"}
    items, list_key, error = _resolve_list_result(
        args.get("tool_name"), args.get("arguments"), args.get("list_path")
    )
    if error:
        return {"error": error}
    counts: dict = {}
    for item in items:
        key = item.get(group_by) if isinstance(item, dict) else None
        key = str(key) if key not in (None, "") else "(未知)"
        counts[key] = counts.get(key, 0) + 1
    groups = [{"group": key, "count": count} for key, count in counts.items()]
    try:
        min_count = int(args.get("min_count") or 0)
    except (TypeError, ValueError):
        min_count = 0
    matched = sorted((g for g in groups if g["count"] > min_count), key=lambda g: g["count"], reverse=True) if min_count > 0 else []
    return {
        "min_count": min_count,
        "matched_count": len(matched) if min_count > 0 else None,
        "matched_groups": matched,
        "total_items": len(items),
        "tool": str(args.get("tool_name") or "").strip(),
        "list_key": list_key,
        "group_by": group_by,
        "groups": groups,
    }


def _handler_aggregate_tool_chain(args: dict) -> dict:
    # 通用多步聚合：按 steps 顺序执行查询，自动把上一步列表里的 id 作为下一步的 object_ids，
    # 最后对末步结果按 group_by 分组统计（可选 min_count）
    steps = args.get("steps")
    if not isinstance(steps, list) or not steps:
        return {"error": "需要 steps 数组，如 [{\"tool_name\": \"get_descendants_of_type\", \"arguments\": {...}}, ...]"}
    group_by = str(args.get("group_by") or "").strip()
    try:
        min_count = int(args.get("min_count") or 0)
    except (TypeError, ValueError):
        min_count = 0
    current_ids = None
    reports = []
    items = []
    list_key = ""
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            return {"error": f"steps[{index}] 必须是对象"}
        tool_name = str(step.get("tool_name") or "").strip()
        call_args = dict(step.get("arguments") or {})
        if current_ids is not None:
            call_args["object_ids"] = current_ids
        items, list_key, error = _resolve_list_result(tool_name, call_args, step.get("list_path"))
        if error:
            return {"error": f"steps[{index}] {error}"}
        reports.append({"step": index, "tool": tool_name, "list_key": list_key, "count": len(items)})
        current_ids = [item.get("id") for item in items if isinstance(item, dict) and item.get("id")]
    if not group_by:
        return {"steps": reports, "total_items": len(items), "list_key": list_key}
    counts: dict = {}
    for item in items:
        key = item.get(group_by) if isinstance(item, dict) else None
        key = str(key) if key not in (None, "") else "(未知)"
        counts[key] = counts.get(key, 0) + 1
    groups = [{"group": key, "count": count} for key, count in counts.items()]
    matched = sorted((g for g in groups if g["count"] > min_count), key=lambda g: g["count"], reverse=True) if min_count > 0 else []
    return {
        "min_count": min_count,
        "matched_count": len(matched) if min_count > 0 else None,
        "matched_groups": matched,
        "total_items": len(items),
        "group_by": group_by,
        "steps": reports,
        "groups": groups,
    }


# 脚本执行：仅允许白名单内建与受限模块，带行数/时间预算，进程内 exec（打包环境无需外部 Python）
SCRIPT_TIMEOUT_DEFAULT = 30.0
SCRIPT_LINE_BUDGET = 200000
SCRIPT_ALLOWED_MODULES = {"json": json, "re": re, "math": math, "statistics": statistics, "time": time}
# 上层（AI 助手）可注入中止判断，脚本执行期间据此响应“停止”
_execution_guard: Callable[[], bool] | None = None


class ExecutionInterrupted(RuntimeError):
    """脚本执行被上层（用户中止）打断。"""


def set_execution_guard(guard: Callable[[], bool] | None) -> None:
    global _execution_guard
    _execution_guard = guard


_SAFE_BUILTIN_NAMES = (
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "format",
    "frozenset", "int", "isinstance", "issubclass", "iter", "len", "list", "map", "max", "min",
    "next", "range", "repr", "reversed", "round", "set", "slice", "sorted", "str", "sum",
    "tuple", "zip", "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "RuntimeError", "StopIteration", "ZeroDivisionError",
)


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    module = SCRIPT_ALLOWED_MODULES.get(name)
    if module is None:
        raise ImportError(f"脚本中不允许 import {name}（仅允许 {', '.join(sorted(SCRIPT_ALLOWED_MODULES))}）")
    return module


def _script_namespace(output: list):
    safe_builtins = {name: getattr(builtins, name) for name in _SAFE_BUILTIN_NAMES}
    safe_builtins["__import__"] = _safe_import

    def _print(*values, sep=" ", end="\n"):
        output.append(sep.join(str(value) for value in values) + end)

    return {
        "__builtins__": safe_builtins,
        "__name__": "__ai_script__",
        "print": _print,
        "Logger": Logger,
        "WwiseObject": WwiseObject,
        "WwiseObjectType": WwiseObjectType,
        "waapi_utils": waapi_utils,
        "common_utils": common_utils,
        "audio_source_utils": audio_source_utils,
        "soundbank_utils": soundbank_utils,
        "localization_utils": localization_utils,
        "event_utils": event_utils,
        "container_utils": container_utils,
        "mixing_utils": mixing_utils,
        "game_sync_utils": game_sync_utils,
        "project_utils": project_utils,
        "transport_utils": transport_utils,
    }


def _handler_run_wwise_script(args: dict) -> dict:
    # 执行模型临时编写的 Wwise 脚本（已由 AI 层包在撤销组内）
    code = str(args.get("code") or "")
    if not code.strip():
        return {"error": "缺少 code 参数（要执行的 Python 脚本）"}
    if args.get("confirmed") is not True:
        return {"error": "执行脚本属于危险操作：请在用户明确同意后传 confirmed=true"}
    try:
        timeout = float(args.get("timeout") or SCRIPT_TIMEOUT_DEFAULT)
    except (TypeError, ValueError):
        timeout = SCRIPT_TIMEOUT_DEFAULT

    output: list[str] = []
    namespace = _script_namespace(output)
    deadline = time.monotonic() + max(timeout, 1.0)
    budget = {"lines": 0}

    def _guard(frame, event, arg):
        if event == "line":
            budget["lines"] += 1
            if _execution_guard is not None and _execution_guard():
                raise ExecutionInterrupted("脚本执行已按用户要求中止")
            if budget["lines"] > SCRIPT_LINE_BUDGET:
                raise TimeoutError(f"脚本执行超过行数预算（{SCRIPT_LINE_BUDGET} 行）")
            if time.monotonic() > deadline:
                raise TimeoutError(f"脚本执行超过 {timeout:g} 秒")
        return _guard

    error = ""
    sys.settrace(_guard)
    try:
        exec(compile(code, "<ai_script>", "exec"), namespace)
    except ExecutionInterrupted:
        raise
    except TimeoutError as e:
        error = f"{e}"
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    finally:
        sys.settrace(None)

    result = namespace.get("result")
    text = "".join(output)
    Logger().query(f"AI 脚本执行（{len(code)} 字符）：\n{code}")
    if text.strip():
        Logger().query(f"AI 脚本输出：\n{text.rstrip()}")
    if error:
        Logger().error(f"AI 脚本执行失败：{error}")
    return {
        "ok": not error,
        "output": text[:4000],
        "result": None if result is None else repr(result)[:2000],
        "error": error,
    }


def _handler_get_references(args: dict) -> dict:
    # 查询“引用该对象”的对象；Wwise 中 Event 通过 EventAction(Action) 引用目标
    ids = _require_object_ids(args)
    limit = _resolve_limit(args, REF_LIST_LIMIT)
    objects = []
    errors = []
    total = 0
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            references = []
            for ref in waapi_utils.get_object_references(obj):
                if limit is not None and len(references) >= limit:
                    break
                references.append({
                    "id": ref.id,
                    "name": ref.name,
                    "type": ref.type.value,
                    "path": ref.path,
                })
            total += len(references)
            objects.append({"object": obj.name, "references": references})
        except Exception as e:
            errors.append(f"{object_id}: {e}")
    return {
        "count": total,
        "truncated": limit is not None and total >= limit,
        "objects": objects,
        "errors": errors,
    }


def _handler_check_event_references(args: dict) -> dict:
    # 按工程口径判断“是否被 Event 引用”：引用中含 EventAction(Action) 即视为被 Event 引用
    ids = _require_object_ids(args)
    objects = []
    errors = []
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            objects.append({
                "object": obj.name,
                "referenced_by_event": event_utils.has_event_reference(obj),
            })
        except Exception as e:
            errors.append(f"{object_id}: {e}")
    return {
        "objects": objects,
        "referenced_by_event_count": sum(1 for item in objects if item["referenced_by_event"]),
        "errors": errors,
    }


register_tool(
    "get_objects_info",
    "读取表格中对象的详细信息（备注、启用状态等），一次最多 50 个对象",
    _object_ids_parameters("要查询详情的对象 id"),
    _handler_get_objects_info,
)

register_tool(
    "get_audio_sources",
    "列出对象子树下的所有音频源（AudioFileSource，Event 按播放目标展开）及其磁盘源文件路径",
    _object_ids_parameters("要查询音频源的对象 id"),
    _handler_get_audio_sources,
)

register_tool(
    "calculate_audio_source_size",
    "统计对象子树音频资源的磁盘文件大小：递归收集 AudioFileSource 的源文件路径，按路径去重后求和，返回每个对象与合计的 MB",
    _object_ids_parameters("要统计音频资源大小的对象 id"),
    _handler_calculate_audio_source_size,
)

register_tool(
    "get_children",
    "列出对象的子级或全部后代（返回 id/name/type/path）。recursive=True（默认）一次性取全部后代；recursive=False 只取直接子级。若只要某类型后代，优先用 get_descendants_of_type",
    {
        "type": "object",
        "properties": {
            "object_ids": {
                "type": "array",
                "items": {"type": "string", "description": "Wwise 对象 GUID"},
                "description": "要展开层级的对象 id",
            },
            "recursive": {"type": "boolean", "default": True, "description": "True 取全部后代，False 只取直接子级"},
            "limit": {"type": "integer", "description": "数量上限，默认 500；传 0 表示不限量"},
        },
        "required": ["object_ids"],
    },
    _handler_get_children,
)

register_tool(
    "get_descendants_of_type",
    "按类型递归查找对象下的全部后代（如所有 MusicSegment / MusicTrack / Sound / Event）。在 Wwise 侧按类型过滤，比列出全部后代更省数据。拿到结果后要把这些 id 一次性批量传给下一步工具，不要逐个/逐层调用；需要计数或分组统计时用 group_tool_items / count_tool_items 包裹本工具。需要不限类型的全部后代时才用 get_children(recursive=true)",
    {
        "type": "object",
        "properties": {
            "object_ids": {
                "type": "array",
                "items": {"type": "string", "description": "Wwise 对象 GUID"},
                "description": "要展开的根对象 id",
            },
            "child_type": {
                "type": "string",
                "description": "目标类型（WwiseObjectType 值或名称），如 Sound / Event / AudioFileSource / SwitchContainer",
            },
            "include_path": {
                "type": "boolean",
                "default": False,
                "description": "是否返回完整 path（默认 false，节省篇幅；需要核对层级路径时传 true）",
            },
            "limit": {"type": "integer", "description": "数量上限，默认 1000；传 0 表示不限量（聚合链路内部默认不限量）"},
        },
        "required": ["object_ids", "child_type"],
    },
    _handler_get_descendants_of_type,
)

register_tool(
    "count_tool_items",
    "通用计数：执行任意“返回列表”的工具并统计条数（total），避免为每种查询单独写计数工具。tool_name 传查询工具名，arguments 传该工具的参数，list_path 可选（默认自动识别 items/objects/data 等列表字段）",
    {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "要执行的查询工具名，如 get_descendants_of_type / get_references",
            },
            "arguments": {
                "type": "object",
                "description": "传给该工具的参数对象（与直接调用时一致）",
            },
            "list_path": {"type": "string", "description": "可选：结果中列表字段的路径，如 items；留空自动识别"},
        },
        "required": ["tool_name", "arguments"],
    },
    _handler_count_tool_items,
)

register_tool(
    "group_tool_items",
    "通用分组统计：执行任意“返回列表”的工具，按列表项某字段分组计数（如按 root_id 统计每个对象下有多少个后代），可选 min_count 只保留“数量大于该值”的分组并给出 matched_count。适合“有多少个对象包含超过 N 个 XX”这类问题",
    {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "要执行的查询工具名，如 get_descendants_of_type",
            },
            "arguments": {
                "type": "object",
                "description": "传给该工具的参数对象（与直接调用时一致）",
            },
            "group_by": {
                "type": "string",
                "description": "分组字段，如 root_id / parent_id / type / name",
            },
            "list_path": {"type": "string", "description": "可选：结果中列表字段的路径，如 items；留空自动识别"},
            "min_count": {
                "type": "integer",
                "description": "可选：只保留数量大于该值的分组（统计包含超过 1 个 MusicTrack 的 MusicSegment 时传 1）",
            },
        },
        "required": ["tool_name", "arguments", "group_by"],
    },
    _handler_group_tool_items,
)

register_tool(
    "aggregate_tool_chain",
    "通用多步聚合：按 steps 依次执行查询，自动把上一步结果的 id 作为下一步的 object_ids（无需模型转发大量 id），最后按 group_by 分组统计。适合「先找出所有 A，再统计每个 A（或有多少个 A）包含超过 N 个 B」这类跨层级问题；例如统计包含超过 1 个 MusicTrack 的 MusicSegment 数量只需一次调用",
    {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string", "description": "该步要执行的查询工具名"},
                        "arguments": {"type": "object", "description": "该步参数（除 object_ids 外；object_ids 由上一步自动注入）"},
                        "list_path": {"type": "string", "description": "可选：该步结果中列表字段路径"},
                    },
                    "required": ["tool_name", "arguments"],
                },
                "description": "查询步骤链，第 1 步用 arguments 里的 object_ids 指定根对象，后续步骤自动接收上一步的 id",
            },
            "group_by": {
                "type": "string",
                "description": "末步结果按哪个字段分组（如 root_id / parent_id / type）；省略则只返回各步条数",
            },
            "min_count": {
                "type": "integer",
                "description": "可选：只统计分组内数量大于该值的组（如统计含 >1 个 MusicTrack 的 MusicSegment 时传 1），返回 matched_count",
            },
        },
        "required": ["steps"],
    },
    _handler_aggregate_tool_chain,
)

register_tool(
    "run_wwise_script",
    "执行一段临时 Python 脚本处理表格对象（适合复杂组合逻辑：多级遍历、过滤、聚合统计、批量修改）。脚本里可直接使用注入的 waapi_utils / common_utils / audio_source_utils / event_utils / container_utils / soundbank_utils / localization_utils / mixing_utils / game_sync_utils / project_utils / transport_utils 以及 WwiseObject / WwiseObjectType / Logger；禁止 import os/sys/subprocess 等。用 print(...) 输出结果，或把返回值赋给 result。危险操作（会改工程）必须传 confirmed=true，执行会被包在撤销组里",
    {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "要执行的 Python 脚本"},
            "confirmed": {
                "type": "boolean",
                "description": "用户已明确同意执行脚本时传 true；否则拒绝执行",
            },
            "timeout": {"type": "integer", "description": "执行时间上限（秒），默认 30"},
        },
        "required": ["code", "confirmed"],
    },
    _handler_run_wwise_script,
    mutating=True,
)

register_tool(
    "get_references",
    "查询「引用该对象」的所有对象（含类型）。用户问「被谁引用 / 谁在用 / 被 Event、SoundBank 引用吗」时用；注意 Wwise 中 Event 是通过 EventAction(Action) 引用目标的",
    _object_ids_parameters("要查询引用的对象 id"),
    _handler_get_references,
)

register_tool(
    "check_event_references",
    "按工程口径统计对象是否被 Event 引用（引用列表含 EventAction/Action 即算），返回每个对象结果与合计数量",
    _object_ids_parameters("要检查的对象 id"),
    _handler_check_event_references,
)

# MCP legacy 工具迁移目录：注册后 AI 助手与 MCP 共用同一份工具定义
from libraries import wwise_tool_catalog as _wwise_tool_catalog  # noqa: E402, F401
