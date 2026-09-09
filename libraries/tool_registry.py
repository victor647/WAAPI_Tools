# 中立 Wwise 工具注册表：供「软件内手动工具 / AI 助手 / MCP」三方复用。
# 约束：本模块不得 import fastmcp、PySide6/Qt、waapi_mcp；只依赖 libraries 内的业务封装。
# 每个工具只定义一次（名称/描述/参数 schema/handler），各消费方自行生成自己的协议层：
# - AI 助手：tool_registry.list_tools() 生成 function calling schema，execute_tool() 派发；
# - MCP：waapi_mcp/registry_mcp_tools.py 按注册表批量生成 @mcp.tool；
# - 手动工具：继续直接调用 *_utils（注册表 handler 内部复用的就是这些封装）。
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

from libraries.utils.wwise import audio_source_utils, common_utils, event_utils, waapi_utils
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
    items = []
    errors = []
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            for source in _audio_sources_of(obj):
                if len(items) >= AUDIO_SOURCE_LIST_LIMIT:
                    break
                file_path = audio_source_utils.get_source_file_path(source) or ""
                items.append({
                    "parent": obj.name,
                    "id": source.id,
                    "name": source.name,
                    "path": source.path,
                    "file_path": file_path,
                })
        except Exception as e:
            errors.append(f"{object_id}: {e}")
    return {"items": items, "errors": errors}


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
                path = audio_source_utils.get_source_file_path(source)
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
    items = []
    errors = []
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            children = waapi_utils.get_child_objects(obj, include_descendants=recursive)
            for child in children:
                if len(items) >= CHILD_LIST_LIMIT:
                    break
                items.append({
                    "parent": obj.name,
                    "id": child.id,
                    "name": child.name,
                    "type": child.type.value,
                    "path": child.path,
                })
        except Exception as e:
            errors.append(f"{object_id}: {e}")
    return {"items": items, "recursive": recursive, "errors": errors}


def _handler_list_descendants(args: dict) -> dict:
    # 一次性递归取全部后代（用于“在表格对象下查找/统计”类任务），可指定类型过滤
    ids = _require_object_ids(args)
    type_filter = (args.get("type_filter") or "").strip()
    items = []
    errors = []
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            children = waapi_utils.get_child_objects(obj, include_descendants=True)
            for child in children:
                if type_filter and child.type.value != type_filter:
                    continue
                if len(items) >= DESCENDANT_LIST_LIMIT:
                    break
                items.append({
                    "root": obj.name,
                    "id": child.id,
                    "name": child.name,
                    "type": child.type.value,
                    "path": child.path,
                })
        except Exception as e:
            errors.append(f"{object_id}: {e}")
    return {"items": items, "truncated": len(items) >= DESCENDANT_LIST_LIMIT, "errors": errors}


def _handler_get_references(args: dict) -> dict:
    # 查询“引用该对象”的对象；Wwise 中 Event 通过 EventAction(Action) 引用目标
    ids = _require_object_ids(args)
    objects = []
    errors = []
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            references = []
            for ref in waapi_utils.get_object_references(obj):
                if len(references) >= REF_LIST_LIMIT:
                    break
                references.append({
                    "id": ref.id,
                    "name": ref.name,
                    "type": ref.type.value,
                    "path": ref.path,
                })
            objects.append({"object": obj.name, "references": references})
        except Exception as e:
            errors.append(f"{object_id}: {e}")
    return {"objects": objects, "errors": errors}


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
    "列出对象的子级或全部后代（返回 id/name/type/path）。recursive=True（默认）一次性取全部后代；recursive=False 只取直接子级。需要全量递归查找时优先用 list_descendants",
    {
        "type": "object",
        "properties": {
            "object_ids": {
                "type": "array",
                "items": {"type": "string", "description": "Wwise 对象 GUID"},
                "description": "要展开层级的对象 id",
            },
            "recursive": {"type": "boolean", "default": True, "description": "True 取全部后代，False 只取直接子级"},
        },
        "required": ["object_ids"],
    },
    _handler_get_children,
)

register_tool(
    "list_descendants",
    "一次性递归列出对象下的全部后代（含孙级…），可选 type_filter 按类型过滤（如 Sound/Event/AudioFileSource）。用于「在对象下查找/统计所有 X」类任务，不要再逐层 get_children",
    {
        "type": "object",
        "properties": {
            "object_ids": {
                "type": "array",
                "items": {"type": "string", "description": "Wwise 对象 GUID"},
                "description": "要展开的根对象 id",
            },
            "type_filter": {"type": "string", "description": "可选：只返回该类型的后代，留空返回全部"},
        },
        "required": ["object_ids"],
    },
    _handler_list_descendants,
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
