# 中立 Wwise 工具注册表：供「软件内手动工具 / AI 助手 / MCP」三方复用。
# 约束：本模块不得 import fastmcp、PySide6/Qt、waapi_mcp；只依赖 libraries 内的业务封装。
# 每个工具只定义一次（名称/描述/参数 schema/handler），各消费方自行生成自己的协议层：
# - AI 助手：tool_registry.list_tools() 生成 function calling schema，execute_tool() 派发；
# - MCP：waapi_mcp/registry_mcp_tools.py 按注册表批量生成 @mcp.tool；
# - 手动工具：继续直接调用 *_utils（注册表 handler 内部复用的就是这些封装）。
from __future__ import annotations

import os
import ast
import builtins
import json
import math
import re
import statistics
import time
from dataclasses import dataclass
from typing import Any, Callable

from libraries.utils.wwise import (
    audio_source_utils,
    common_utils,
    compression_utils,
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
from libraries.utils import user_config
from libraries.wwise_object import WwiseObject, WwiseObjectType

# 单次可列出的音频源上限 / 可统计的对象上限，防止一次请求拖垮上下文
AUDIO_SOURCE_LIST_LIMIT = 300
SIZE_STAT_OBJECT_LIMIT = 100
INFO_OBJECT_LIMIT = 200
CHILD_LIST_LIMIT = 500
REF_LIST_LIMIT = 500
DESCENDANT_LIST_LIMIT = 1000
SCAN_LIMIT_DEFAULT = 20000
_PROPERTY_OPS = ("==", "!=", ">", ">=", "<", "<=", "contains")


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
    arguments = arguments if isinstance(arguments, dict) else {}
    missing = [param for param in spec.parameters.get("required", []) if param not in arguments]
    if missing:
        hints = ", ".join(
            f"{param}（{spec.parameters['properties'].get(param, {}).get('description', '')}）"
            for param in missing
        )
        raise ValueError(f"缺少必填参数：{hints}")
    return spec.handler(arguments)


def describe_action(name: str, arguments: dict) -> dict:
    # 危险操作预览：执行前告诉上层/用户这次调用会动哪些对象、做什么，用于请求用户确认
    spec = _TOOLS.get(name)
    arguments = arguments if isinstance(arguments, dict) else {}
    object_ids = []
    for key in ("object_id", "object_ids"):
        value = arguments.get(key)
        if isinstance(value, str) and value:
            object_ids.append(value)
        elif isinstance(value, list):
            object_ids.extend(item for item in value if isinstance(item, str) and item)
    targets = []
    # 只为确认框展示解析少量对象名，避免确认前做几十次 WAAPI 调用
    for object_id in object_ids[:20]:
        try:
            info = waapi_utils.get_full_info_from_obj_id(object_id)
        except Exception:
            info = None
        if info is not None and info.is_valid:
            targets.append({"id": info.id, "name": info.name, "type": info.type.value, "path": info.path})
    # 描述只取第一句，避免长说明撑爆确认框
    summary = spec.description.split("。")[0] if spec else ""
    return {
        "tool": name,
        "summary": summary,
        "target_count": len(object_ids),
        "targets": targets,
        "other_arguments": {
            key: value for key, value in arguments.items()
            if key not in ("object_id", "object_ids", "confirmed")
        },
    }


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


def _audio_source_paths_by_id(sources: list[WwiseObject]) -> dict[str, str]:
    properties_by_id = waapi_utils.get_objects_properties(sources, ['originalFilePath'])
    return {
        source.id: audio_source_utils.get_source_absolute_path(
            source, properties_by_id.get(source.id)
        ) or ""
        for source in sources
    }


def _handler_get_objects_info(args: dict) -> dict:
    # 读取对象详情：名称/类型/路径/备注/启用状态
    ids = _require_object_ids(args)[:INFO_OBJECT_LIMIT]
    items = []
    errors = []
    objects = []
    for object_id in ids:
        try:
            objects.append(WwiseObject.from_id(object_id))
        except Exception as e:
            errors.append(f"{object_id}: {e}")
    object_properties = waapi_utils.get_objects_properties(objects, ['Notes', 'Inclusion'])
    inclusion_cache = {}
    for obj in objects:
        properties = object_properties.get(obj.id, {})
        items.append({
            "id": obj.id,
            "name": obj.name,
            "type": obj.type.value,
            "path": obj.path,
            "notes": properties.get('Notes'),
            "included": common_utils.is_object_included(
                obj,
                inclusion_cache=inclusion_cache,
                property_values_by_id=object_properties,
            ),
        })
    return {"items": items, "errors": errors}


def _handler_get_audio_sources(args: dict) -> dict:
    # 列出对象子树下的音频源及其磁盘源文件路径（读属性，不改工程）
    ids = _require_object_ids(args)
    limit = _resolve_limit(args, AUDIO_SOURCE_LIST_LIMIT)
    errors = []
    entries = []
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            for source in _audio_sources_of(obj):
                if limit is not None and len(entries) >= limit:
                    break
                entries.append((obj, source))
        except Exception as e:
            errors.append(f"{object_id}: {e}")
        if limit is not None and len(entries) >= limit:
            break
    source_paths = _audio_source_paths_by_id(list({source.id: source for _, source in entries}.values()))
    items = [
        {
            "parent": obj.name,
            "id": source.id,
            "name": source.name,
            "path": source.path,
            "file_path": source_paths.get(source.id, ""),
        }
        for obj, source in entries
    ]
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
    object_entries = []
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            object_entries.append((obj, _audio_sources_of(obj), None))
        except Exception as e:
            object_entries.append((object_id, [], str(e)))

    sources_by_id = {
        source.id: source
        for _obj, sources, error in object_entries
        if error is None
        for source in sources
    }
    source_paths = _audio_source_paths_by_id(list(sources_by_id.values()))
    for obj, sources, error in object_entries:
        if error is not None:
            per_object.append({"object": obj, "error": error})
            continue
        size_bytes = 0
        file_count = 0
        try:
            for source in sources:
                path = source_paths.get(source.id, "")
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
            per_object.append({"object": obj.name, "error": str(e)})
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


# 数值聚合：把工具结果/列表项里读到的值统一折算成可统计的数值
_AGGREGATE_NAMES = ("sum", "avg", "min", "max", "count")
# 未显式指定 value_path 时，按这些常见字段自动挑选数值（Duration 返回 {min,max,type}，取 max 表示音频长度）
_NUMBER_KEYS = ("value", "max", "min", "total", "sum", "duration", "size", "size_mb", "length", "count")
_ITEM_PLACEHOLDER_RE = re.compile(r"^\$([A-Za-z0-9_.]+)$")


def _as_number(value):
    # 折算成 float；bool 不是数值，其它类型返回 None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _numeric_value(value, value_path: str = "") -> tuple:
    # 取出参与聚合的数值，返回 (数值, 命中的字段名)；取不到返回 (None, "")
    # value_path 支持点号路径（如 "max" / "source.max"），未指定时按 _NUMBER_KEYS 自动挑选
    if value_path:
        cursor = value
        for part in value_path.split("."):
            if isinstance(cursor, dict) and part in cursor:
                cursor = cursor[part]
            else:
                return None, value_path
        return _as_number(cursor), value_path
    number = _as_number(value)
    if number is not None:
        return number, ""
    if isinstance(value, dict):
        for key in _NUMBER_KEYS:
            if key in value:
                number = _as_number(value[key])
                if number is not None:
                    return number, key
    return None, ""


def _number_stats(numbers: list) -> dict:
    if not numbers:
        return {}
    return {
        "count": len(numbers),
        "sum": round(sum(numbers), 6),
        "avg": round(sum(numbers) / len(numbers), 6),
        "min": round(min(numbers), 6),
        "max": round(max(numbers), 6),
    }


def _item_field(item, path: str):
    # 按点号路径从列表项里取值，返回 (值, 是否取到)
    cursor = item
    for part in path.split("."):
        if isinstance(cursor, dict) and part in cursor:
            cursor = cursor[part]
        else:
            return None, False
    return cursor, True


def _has_placeholders(arguments) -> bool:
    if not isinstance(arguments, dict):
        return False
    return any(isinstance(value, str) and _ITEM_PLACEHOLDER_RE.match(value) for value in arguments.values())


def _bind_item_arguments(arguments: dict, item) -> tuple:
    # 把参数里的 "$字段" 占位符替换成当前列表项的值，返回 (参数, 未解析的字段名)
    resolved = {}
    missing = []
    for key, value in arguments.items():
        if isinstance(value, str):
            match = _ITEM_PLACEHOLDER_RE.match(value)
            if match:
                found, ok = _item_field(item, match.group(1))
                if not ok:
                    missing.append(match.group(1))
                    continue
                resolved[key] = found
                continue
        resolved[key] = value
    return resolved, missing


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


def _call_tool_checked(tool_name: str, call_args: dict):
    # 校验必填参数后执行目标工具；返回 (结果, 错误)
    spec = get_tool(tool_name)
    if spec is None:
        return None, f"未知工具：{tool_name}"
    required = [name for name in spec.parameters.get("required", []) if name not in call_args]
    if required:
        hints = ", ".join(
            f"{name}（{spec.parameters['properties'].get(name, {}).get('description', '')}）" for name in required
        )
        return None, f"调用 {tool_name} 缺少必填参数：{hints}；请把参数放进 arguments 对象"
    try:
        return execute_tool(tool_name, call_args), ""
    except Exception as e:
        return None, f"调用 {tool_name} 失败：{e}；请检查 arguments 是否为该工具的参数对象"


def _resolve_list_result(tool_name: str, arguments: dict, list_path: str):
    # 执行目标工具并取出列表；返回 (items, list_key, error)
    tool_name = str(tool_name or "").strip()
    if not tool_name:
        return None, "", "缺少 tool_name 参数（要统计的查询工具名）"
    if tool_name in META_TOOL_NAMES:
        return None, "", f"不能对元工具 {tool_name} 再聚合，请传入普通查询工具"
    call_args = dict(arguments) if isinstance(arguments, dict) else {}
    # 聚合场景默认不限量，避免目标工具的默认上限截断统计结果
    call_args.setdefault("limit", 0)
    value, error = _call_tool_checked(tool_name, call_args)
    if error:
        return None, "", error
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
    # 通用多步聚合：按 steps 顺序执行查询，自动把上一步列表里的 id 作为下一步的 object_ids；
    # 参数里出现 "$字段" 占位符时改为"对上一步每个结果各调用一次"（该步必须放最后）；
    # 末步结果可按 group_by 分组计数，或用 aggregate 直接算出 sum/avg/min/max/count
    steps = args.get("steps")
    if not isinstance(steps, list) or not steps:
        return {"error": "需要 steps 数组，如 [{\"tool_name\": \"get_descendants_of_type\", \"arguments\": {...}}, ...]"}
    group_by = str(args.get("group_by") or "").strip()
    aggregate = str(args.get("aggregate") or "").strip().lower()
    if aggregate and aggregate not in _AGGREGATE_NAMES:
        return {"error": f"aggregate 仅支持 {' / '.join(_AGGREGATE_NAMES)}"}
    value_path = str(args.get("value_path") or "").strip()
    try:
        min_count = int(args.get("min_count") or 0)
    except (TypeError, ValueError):
        min_count = 0
    current_ids = None
    current_items = None
    entries = None
    reports = []
    items = []
    list_key = ""
    errors = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            return {"error": f"steps[{index}] 必须是对象"}
        tool_name = str(step.get("tool_name") or "").strip()
        arguments = step.get("arguments") if isinstance(step.get("arguments"), dict) else {}
        if _has_placeholders(arguments):
            # 逐项调用：占位符取自当前列表项，必须作为末步
            if current_items is None:
                return {"error": f"steps[{index}] 用了 $占位符，但没有上一步列表可绑定"}
            if index != len(steps) - 1:
                return {"error": f"steps[{index}] 用了 $占位符，占位符步骤必须放在最后一步"}
            mapped = []
            for item in current_items:
                bound, unresolved = _bind_item_arguments(arguments, item)
                if unresolved:
                    errors.append(f"列表项缺少字段 {'/'.join(sorted(set(unresolved)))}")
                    continue
                value, error = _call_tool_checked(tool_name, bound)
                if error:
                    errors.append(error)
                    continue
                mapped.append((item, value))
            reports.append({"step": index, "tool": tool_name, "mapped": len(mapped)})
            entries = mapped
            items, list_key, current_items, current_ids = [], "", None, None
            continue
        call_args = dict(arguments)
        if current_ids is not None:
            call_args["object_ids"] = current_ids
        items, list_key, error = _resolve_list_result(tool_name, call_args, step.get("list_path"))
        if error:
            return {"error": f"steps[{index}] {error}"}
        reports.append({"step": index, "tool": tool_name, "list_key": list_key, "count": len(items)})
        current_items = items
        current_ids = [item.get("id") for item in items if isinstance(item, dict) and item.get("id")]
        entries = None
    if aggregate:
        return _aggregate_chain_values(entries, items, aggregate, value_path, group_by, min_count, reports, errors)
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


def _aggregate_chain_values(entries, items, aggregate, value_path, group_by, min_count, reports, errors) -> dict:
    # 对末步结果做数值统计：entries 非空表示末步是逐项调用（值取调用结果），否则直接对列表项取值
    sources = entries if entries is not None else [(item, item) for item in items]
    numbers = []
    used_keys = set()
    skipped = 0
    groups: dict = {}
    for item, value in sources:
        number, key = _numeric_value(value, value_path)
        if number is None:
            skipped += 1
            continue
        if key:
            used_keys.add(key)
        numbers.append(number)
        if group_by:
            group = item.get(group_by) if isinstance(item, dict) else None
            group = str(group) if group not in (None, "") else "(未知)"
            groups.setdefault(group, []).append(number)
    stats = _number_stats(numbers)
    result = {
        "aggregate": aggregate,
        "value": stats.get(aggregate),
        "stats": stats,
        "total_items": len(sources),
        "skipped": skipped,
        "steps": reports,
    }
    if used_keys:
        result["value_key"] = used_keys.pop() if len(used_keys) == 1 else sorted(used_keys)
    if errors:
        result["errors"] = errors[:5]
    if not stats:
        result["hint"] = "没有取到可比数值：确认末步结果里是否含数值字段，或用 value_path 指定（如 Duration 传 \"max\"）"
    if group_by:
        group_rows = [{"group": key, **_number_stats(values)} for key, values in groups.items()]
        matched = sorted((row for row in group_rows if row["count"] > min_count), key=lambda r: r["count"], reverse=True) if min_count > 0 else []
        result.update({
            "group_by": group_by,
            "min_count": min_count,
            "matched_count": len(matched) if min_count > 0 else None,
            "matched_groups": matched,
            "groups": group_rows,
        })
    return result


# 脚本执行：仅允许白名单内建与受限模块，带循环/时间预算，进程内 exec（打包环境无需外部 Python）
SCRIPT_TIMEOUT_DEFAULT = 30.0
SCRIPT_TICK_BUDGET = 2000000
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
    "tuple", "zip", "callable", "chr", "ord", "hash", "dir", "hasattr", "getattr", "type", "Exception",
    "ValueError", "TypeError", "KeyError", "IndexError", "AttributeError", "NameError",
    "ImportError", "RuntimeError", "StopIteration", "ZeroDivisionError", "ArithmeticError",
    "OverflowError", "OSError", "PermissionError",
)


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    module = SCRIPT_ALLOWED_MODULES.get(name)
    if module is None:
        raise ImportError(f"脚本中不允许 import {name}（仅允许 {', '.join(sorted(SCRIPT_ALLOWED_MODULES))}）")
    return module


def _script_modules() -> dict:
    return {
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


def _script_api_names() -> dict:
    # 名称清单：供模型查看"有哪些函数"，而 tools_api 里放的是真实模块对象
    names = {
        name: [fn for fn in dir(module) if not fn.startswith("_")]
        for name, module in _script_modules().items()
    }
    names["WwiseObject"] = ["from_id", "dict_from_id", "id", "name", "type", "path", "children", "parent", "is_valid"]
    names["WwiseObjectType"] = [member.value for member in WwiseObjectType]
    names["Logger"] = ["info", "warning", "error", "debug", "query"]
    return names


def _script_namespace(output: list, tick):
    safe_builtins = {name: getattr(builtins, name) for name in _SAFE_BUILTIN_NAMES}
    safe_builtins["__import__"] = _safe_import

    def _print(*values, sep=" ", end="\n"):
        output.append(sep.join(str(value) for value in values) + end)

    api_names = _script_api_names()

    def _help(name=None):
        if name and name in api_names:
            _print(f"{name}: {', '.join(api_names[name])}")
            return
        for module_name, functions in api_names.items():
            _print(f"{module_name}: {', '.join(functions)}")

    return {
        "__builtins__": safe_builtins,
        "__name__": "__ai_script__",
        "__budget_tick__": tick,
        "print": _print,
        "help": _help,
        "tools_api": _script_modules(),
        "api_names": api_names,
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


def _instrument_loops(tree: ast.AST) -> ast.AST:
    # 在每个循环体首部注入预算检查，避免死循环；不使用 sys.settrace（与 IDE 调试器冲突）
    def _tick_statement() -> ast.stmt:
        return ast.Expr(value=ast.Call(func=ast.Name(id="__budget_tick__", ctx=ast.Load()), args=[], keywords=[]))

    class _LoopInstrumenter(ast.NodeTransformer):
        def visit_While(self, node: ast.While):
            self.generic_visit(node)
            node.body.insert(0, _tick_statement())
            node.orelse.insert(0, _tick_statement())
            return node

        def visit_For(self, node: ast.For):
            self.generic_visit(node)
            node.body.insert(0, _tick_statement())
            node.orelse.insert(0, _tick_statement())
            return node

    return _LoopInstrumenter().visit(tree)


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
    deadline = time.monotonic() + max(timeout, 1.0)
    state = {"ticks": 0}

    def _tick():
        state["ticks"] += 1
        if _execution_guard is not None and _execution_guard():
            raise ExecutionInterrupted("脚本执行已按用户要求中止")
        if state["ticks"] > SCRIPT_TICK_BUDGET:
            raise TimeoutError(f"脚本执行超过循环次数预算（{SCRIPT_TICK_BUDGET}）")
        if time.monotonic() > deadline:
            raise TimeoutError(f"脚本执行超过 {timeout:g} 秒")

    namespace = _script_namespace(output, _tick)
    error = ""
    try:
        tree = _instrument_loops(ast.parse(code, mode="exec"))
        ast.fix_missing_locations(tree)
        exec(compile(tree, "<ai_script>", "exec"), namespace)
    except SyntaxError as e:
        error = f"脚本语法错误：第 {e.lineno} 行 {e.msg}"
    except ExecutionInterrupted:
        raise
    except TimeoutError as e:
        error = f"{e}"
    except Exception as e:
        error = f"{type(e).__name__}: {e}"

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


def _compare_property(value, op: str, expected) -> tuple:
    # 返回 (是否命中, 是否可比)。Duration 这类结构化属性（{min,max,type}）按数值参与比较，
    # 无法比较时显式返回 False，避免“静默不匹配”让调用方误以为结果真的是 0 个
    if op == "contains":
        return str(expected).lower() in str(value).lower(), True
    if op in ("==", "!="):
        equal = value == expected or str(value) == str(expected)
        if not equal:
            left, _ = _numeric_value(value)
            right = _as_number(expected)
            equal = left is not None and right is not None and left == right
        return (equal if op == "==" else not equal), True
    left, _ = _numeric_value(value)
    right = _as_number(expected)
    if left is None or right is None:
        return False, False
    if op == ">":
        return left > right, True
    if op == ">=":
        return left >= right, True
    if op == "<":
        return left < right, True
    return left <= right, True


def _handler_find_objects_by_property(args: dict) -> dict:
    # 通用属性筛选：在对象子树里按某个属性值过滤（如 Volume != 0），只回传命中的对象
    roots = _require_object_ids(args)
    property_name = str(args.get("property_name") or "").strip()
    if not property_name:
        return {"error": "缺少 property_name 参数（要筛选的属性名，如 Volume / Pitch）"}
    op = str(args.get("op") or "!=").strip()
    if op not in _PROPERTY_OPS:
        return {"error": f"op 仅支持 {' / '.join(_PROPERTY_OPS)}"}
    expected = args.get("value")
    child_type_name = str(args.get("child_type") or "").strip()
    child_type = _resolve_object_type(child_type_name) if child_type_name else None
    if child_type_name and child_type is None:
        valid = ", ".join(member.value for member in WwiseObjectType)
        return {"items": [], "errors": [f"未知类型「{child_type_name}」，可用值：{valid}"]}
    include_path = bool(args.get("include_path", False))
    limit = _resolve_limit(args, DESCENDANT_LIST_LIMIT)
    scan_limit = _resolve_limit(args, SCAN_LIMIT_DEFAULT)
    items = []
    errors = []
    scanned = 0
    # 与属性查询窗口一致：某类型读不到该属性即视为"该类型不含有此属性"，同类型后续对象直接跳过
    missing_types: dict[str, str] = {}
    # 属性存在但无法与 value 比较（如结构化属性配了不支持的操作）——显式汇报，避免静默给出 0 个命中
    incomparable_types: dict[str, str] = {}
    for root_id in roots:
        try:
            root = WwiseObject.from_id(root_id)
            candidates = (
                waapi_utils.get_descendants_of_type(root, child_type)
                if child_type
                else waapi_utils.get_child_objects(root, include_descendants=True)
            )
            if scan_limit is not None:
                remaining = scan_limit - scanned
                if remaining <= 0:
                    break
                candidates = candidates[:remaining]
            scanned += len(candidates)
            # 按「查询分页大小」分批取属性：每批一次 WAAPI 查询，避免逐个对象往返
            hit_limit = False
            for page in waapi_utils.iter_object_pages(candidates):
                # 同一批里按类型分组，已知不含该属性的类型整组跳过
                entries_by_type: dict[str, list] = {}
                for candidate in page:
                    type_name = candidate.type.name
                    if missing_types.get(type_name) == property_name:
                        continue
                    entries_by_type.setdefault(type_name, []).append(candidate)
                for type_name, entries in entries_by_type.items():
                    values_by_id = waapi_utils.get_objects_properties(entries, [property_name])
                    for candidate in entries:
                        value = values_by_id.get(candidate.id, {}).get(property_name)
                        if value is None:
                            missing_types[type_name] = property_name
                            continue
                        matched, comparable = _compare_property(value, op, expected)
                        if not comparable:
                            incomparable_types[type_name] = property_name
                            continue
                        if not matched:
                            continue
                        item = {
                            "root": root.name,
                            "root_id": root.id,
                            "id": candidate.id,
                            "name": candidate.name,
                            "type": candidate.type.value,
                            "value": value,
                        }
                        if include_path:
                            item["path"] = candidate.path
                        items.append(item)
                        if limit is not None and len(items) >= limit:
                            hit_limit = True
                            break
                    if hit_limit:
                        break
                if hit_limit:
                    break
            if limit is not None and len(items) >= limit:
                break
        except Exception as e:
            errors.append(f"{root_id}: {e}")
    detail = f"，不含有 {property_name} 的类型：{'/'.join(sorted(missing_types))}" if missing_types else ""
    if incomparable_types:
        detail += f"，无法比较 {property_name} 的类型：{'/'.join(sorted(incomparable_types))}"
    Logger().info(
        f"属性筛选 {property_name} {op} {expected}：扫描 {scanned} 个对象，匹配 {len(items)} 个{detail}")
    return {
        "count": len(items),
        "scanned": scanned,
        "truncated": scan_limit is not None and scanned > scan_limit,
        "types_without_property": sorted(missing_types),
        "types_not_comparable": sorted(incomparable_types),
        "items": items,
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
    "通用多步聚合，一次调用就能拿到结论（不要把大量 id 取回来自行累加）：按 steps 依次执行，自动把上一步结果的 id 作为下一步的 object_ids；某步参数里写 \"$id\"/\"$name\"/\"$path\" 占位符时，改为对上一步每个对象各调用一次（该步必须放最后）。三种用法：① 跨层级计数——末步配 group_by（可加 min_count），如统计含 >1 个 MusicTrack 的 MusicSegment；② 数值统计——aggregate 传 sum/avg/min/max/count，直接得到总时长/总体积/均值，value_path 指定从结果里取哪个字段；③ 列表项字段求和——单步取到列表后直接 aggregate + value_path，如 value_path=\"size_mb\"。示例：统计表格对象下全部音频源总时长 → steps=[{tool_name:\"get_descendants_of_type\",arguments:{object_ids:[\"@table\"],child_type:\"AudioFileSource\"}},{tool_name:\"get_object_property\",arguments:{object_id:\"$id\",property_name:\"Duration\"}}]，aggregate=\"sum\"",
    {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string", "description": "该步要执行的查询工具名"},
                        "arguments": {
                            "type": "object",
                            "description": "该步参数（除 object_ids 外；object_ids 由上一步自动注入）。可用 \"$id\"/\"$name\"/\"$path\" 占位符表示“上一步的每个对象”，此时该步会逐项调用，必须放最后一步",
                        },
                        "list_path": {"type": "string", "description": "可选：该步结果中列表字段路径"},
                    },
                    "required": ["tool_name", "arguments"],
                },
                "description": "查询步骤链：第 1 步用 arguments 里的 object_ids 指定根对象，后续步骤自动接收上一步的 id",
            },
            "group_by": {
                "type": "string",
                "description": "末步结果按哪个字段分组（如 root_id / parent_id / type）；配 aggregate 时分组返回各自的数值统计，省略则只返回各步条数",
            },
            "min_count": {
                "type": "integer",
                "description": "可选：只统计分组内数量大于该值的组（如统计含 >1 个 MusicTrack 的 MusicSegment 时传 1），返回 matched_count",
            },
            "aggregate": {
                "type": "string",
                "enum": list(_AGGREGATE_NAMES),
                "description": "可选：对末步结果做数值统计，sum=求和 / avg=平均 / min / max / count=计数。统计总时长、总体积、平均值时用它，不要自己累加",
            },
            "value_path": {
                "type": "string",
                "description": "可选：参与统计的数值字段路径（如 Duration 结果 {min,max,type} 传 \"max\"，列表项字段传 \"size_mb\"）。省略时自动挑选 value/max/min/total/size 等常见数值字段",
            },
        },
        "required": ["steps"],
    },
    _handler_aggregate_tool_chain,
)

register_tool(
    "find_objects_by_property",
    "通用属性筛选（与「属性查询」窗口同口径）：逐对象用 waapi_utils.get_object_properties 读取属性，某类型首次读不到该属性即视为该类型不含有它并跳过后续同类型对象（types_without_property 汇报）；结构化属性（如 AudioFileSource 的 Duration 返回 {min,max,type}）按数值参与比较，真的无法比较时在 types_not_comparable 汇报，不要把它当成 0 个命中。用户说「找出 Volume/Pitch/… 不为 0 的子对象」时用；建议传 child_type 收窄扫描范围，scan_limit 可用 0 取消上限。返回 count 与 items，可直接把 items 里的 id 交给 set_table_objects；只求数量级结论（求和/计数/平均）改用 aggregate_tool_chain",
    {
        "type": "object",
        "properties": {
            "object_ids": {
                "type": "array",
                "items": {"type": "string", "description": "Wwise 对象 GUID"},
                "description": "要扫描的根对象 id（表格对象）",
            },
            "property_name": {"type": "string", "description": "要筛选的属性名，如 Volume / Pitch / Lowpass"},
            "op": {
                "type": "string",
                "enum": list(_PROPERTY_OPS),
                "default": "!=",
                "description": "比较方式，默认 !=（如找出 Volume != 0）",
            },
            "value": {"type": ["number", "string", "boolean"], "description": "比较值，如 0"},
            "child_type": {"type": "string", "description": "可选：只在某类型后代中筛选（如 Sound），留空扫描全部后代"},
            "include_path": {"type": "boolean", "default": False, "description": "是否返回完整 path"},
            "limit": {"type": "integer", "description": "命中数量上限，默认 1000；0 表示不限量"},
            "scan_limit": {"type": "integer", "description": "扫描对象数量上限，默认 5000；0 表示不限量"},
        },
        "required": ["object_ids", "property_name", "value"],
    },
    _handler_find_objects_by_property,
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

# —— 自动转码（按音频时长分配 Conversion）——
AUTO_COMPRESSION_PLAN_LIMIT = 200


def _auto_compression_threshold(value, fallback: float) -> float:
    # 0 是合法的短音效阈值，只在缺省时回退到设置里保存的值
    if value is None or value == "":
        return float(fallback)
    return float(value)


def _auto_compression_analysis(args: dict, create_missing: bool = False) -> dict:
    # 计算自动转码方案；失败时返回 {"error": ...}
    ids = _require_object_ids(args)
    saved = user_config.get_window_settings(compression_utils.WINDOW_SETTINGS_KEY)
    try:
        short = _auto_compression_threshold(
            args.get("short_threshold"),
            saved.get("short_threshold", compression_utils.DEFAULT_SHORT_THRESHOLD),
        )
        long = _auto_compression_threshold(
            args.get("long_threshold"),
            saved.get("long_threshold", compression_utils.DEFAULT_LONG_THRESHOLD),
        )
    except (TypeError, ValueError):
        return {"error": "short_threshold / long_threshold 必须是秒数（数字）"}
    if short >= long:
        return {"error": f"短音效阈值（{short} 秒）必须小于长音效阈值（{long} 秒）"}
    default_conversion = compression_utils.resolve_default_conversion(
        args.get("default_conversion_id") or ""
    )
    if default_conversion is None:
        names = ", ".join(
            obj.name for obj in waapi_utils.find_all_objects_by_type(WwiseObjectType.Conversion)[:20]
        )
        return {"error": (
            "找不到默认档 Conversion：请传 default_conversion_id，"
            "或先在「自动转码设置」窗口里选一次默认档。"
            f"工程里的 Conversion：{names or '（无）'}"
        )}
    analysis = compression_utils.analyze_auto_compression(
        [WwiseObject.from_id(object_id) for object_id in ids],
        short,
        long,
        default_conversion,
        create_missing=create_missing,
    )
    analysis["error"] = ""
    analysis["default_conversion"] = default_conversion
    analysis["short_threshold"] = short
    analysis["long_threshold"] = long
    return analysis


def _auto_compression_conversion_names(analysis: dict) -> dict:
    # 各档位实际使用的 Conversion 名称；长/短档缺失时给出待创建的名称
    default_name = analysis["default_conversion"].name
    names = {}
    for category in (
        compression_utils.MEDIUM_CATEGORY,
        compression_utils.LONG_CATEGORY,
        compression_utils.SHORT_CATEGORY,
    ):
        conversion = analysis["conversions"].get(category)
        names[category] = conversion.name if conversion else (
            default_name + compression_utils.CATEGORY_SUFFIXES.get(category, "")
        )
    return names


def _handler_auto_compression_plan(args: dict) -> dict:
    # 只分析不修改：给出各档数量与需要打开 OverrideConversion 的节点
    analysis = _auto_compression_analysis(args)
    if analysis.get("error"):
        return analysis
    summary = analysis["summary"]
    override_plans = [plan for plan in analysis["plans"] if plan.override_enabled]
    result = {
        "default_conversion": analysis["default_conversion"].name,
        "short_threshold": analysis["short_threshold"],
        "long_threshold": analysis["long_threshold"],
        "conversions": _auto_compression_conversion_names(analysis),
        "will_create": [name for _category, name in analysis["missing_categories"]],
        "target_count": analysis["target_count"],
        "source_count": analysis["source_count"],
        "override_count": len(override_plans),
        "plans": [
            {
                "id": plan.target.id,
                "name": plan.target.name,
                "type": plan.target.type.value,
                "path": plan.target.path,
                "category": plan.effective_category,
                "counts": plan.counts_by_category,
            }
            for plan in override_plans[:AUTO_COMPRESSION_PLAN_LIMIT]
        ],
        "truncated": len(override_plans) > AUTO_COMPRESSION_PLAN_LIMIT,
        "summary": summary,
    }
    if not summary.get("valid_duration_count"):
        result["hint"] = "表格对象下没有读到有效的 AudioFileSource 播放时长，无法给出转码方案"
    return result


def _handler_auto_compression_apply(args: dict) -> dict:
    # 危险：批量打开 OverrideConversion 并设置 Conversion（会改工程）
    if args.get("confirmed") is not True:
        return {"error": "危险操作被拦截：请显式传入 confirmed=true 确认执行"}
    analysis = _auto_compression_analysis(args, create_missing=True)
    if analysis.get("error"):
        return analysis
    override_plans = [plan for plan in analysis["plans"] if plan.override_enabled]
    failed = []
    page_size = max(1, user_config.get_tool_page_size())
    for start in range(0, len(override_plans), page_size):
        failed.extend(compression_utils.apply_conversion_plans(override_plans[start:start + page_size]))
    failed = sorted(set(failed))
    summary = analysis["summary"]
    Logger().info(
        f"自动转码应用完成：目标节点 {len(override_plans)} 个，失败 {len(failed)} 个，"
        f"新建档位 Conversion {len(analysis['created_categories'])} 个"
    )
    return {
        "applied_count": len(override_plans) - len(failed),
        "failed_count": len(failed),
        "failed": failed[:50],
        "default_conversion": analysis["default_conversion"].name,
        "conversions": _auto_compression_conversion_names(analysis),
        "created_conversions": sorted(analysis["created_categories"]),
        "override_count": len(override_plans),
        "summary": summary,
    }


register_tool(
    "auto_compression_plan",
    "分析「自动转码」方案（只读，不改工程）：递归收集表格对象子树里的 ActorMixer 与 Container，读取其下 AudioFileSource 的播放时长，按短/长阈值把音频分成短/中/长三档，再按每个节点的多数结果（父级继承 + 占优比例）决定它该用哪一档 Conversion；长/短档用默认档 Conversion 名称加 _Long / _Short 后缀。用户说「按音频时长自动设置转码 / 长短音效分开转码 / 自动分配 Conversion」时先用它出方案，用户确认后再调 auto_compression_apply。返回各档数量 summary、需要 OverrideConversion 的节点 plans、以及待新建的 Conversion 名称",
    {
        "type": "object",
        "properties": {
            "object_ids": {
                "type": "array",
                "items": {"type": "string", "description": "Wwise 对象 GUID"},
                "description": "要分析的根对象 id（表格对象；其子树里的 ActorMixer / Container 会被逐个判定）",
            },
            "short_threshold": {
                "type": "number",
                "description": "短音效时长阈值（秒），不超过该值算短档；省略则用「自动转码设置」里保存的值",
            },
            "long_threshold": {
                "type": "number",
                "description": "长音效时长阈值（秒），不小于该值算长档；省略则用「自动转码设置」里保存的值",
            },
            "default_conversion_id": {
                "type": "string",
                "description": "默认档（中音效）使用的 Conversion 对象 GUID；省略则用「自动转码设置」里保存的默认档",
            },
        },
        "required": ["object_ids"],
    },
    _handler_auto_compression_plan,
)


register_tool(
    "auto_compression_apply",
    "按 auto_compression_plan 的结果应用自动转码（会改工程）：为命中的节点打开 OverrideConversion 并设置对应档位的 Conversion；长/短档 Conversion 缺失时先复制默认档生成 _Long / _Short 副本。属于批量修改工程，必须 confirmed=true；建议先调 auto_compression_plan 把方案讲给用户、得到同意后再执行",
    {
        "type": "object",
        "properties": {
            "object_ids": {
                "type": "array",
                "items": {"type": "string", "description": "Wwise 对象 GUID"},
                "description": "要处理的根对象 id（与 auto_compression_plan 传同一批）",
            },
            "short_threshold": {
                "type": "number",
                "description": "短音效时长阈值（秒）；省略则用「自动转码设置」里保存的值",
            },
            "long_threshold": {
                "type": "number",
                "description": "长音效时长阈值（秒）；省略则用「自动转码设置」里保存的值",
            },
            "default_conversion_id": {
                "type": "string",
                "description": "默认档 Conversion 对象 GUID；省略则用「自动转码设置」里保存的默认档",
            },
            "confirmed": {
                "type": "boolean",
                "description": "用户明确同意后传 true（软件内 AI 助手会按修改策略代填）",
            },
        },
        "required": ["object_ids", "confirmed"],
    },
    _handler_auto_compression_apply,
    mutating=True,
)


# MCP legacy 工具迁移目录：注册后 AI 助手与 MCP 共用同一份工具定义
from libraries import wwise_tool_catalog as _wwise_tool_catalog  # noqa: E402, F401
