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
    spec = ToolSpec(name, description, parameters, handler, mutating=mutating)
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
