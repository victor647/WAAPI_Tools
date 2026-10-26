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
from dataclasses import dataclass, replace
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
from libraries.utils import path_utils, user_config
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
    # 工具分组：core 常驻；其它分组由 AI 按需 load_tools 加载
    group: str = "core"
    # 输出结构说明（MCP/AI 可用于链式调用时判断结果字段）
    output_schema: dict | None = None
    # 调用示例：[{title, description, arguments}]
    examples: tuple = ()
    # 复杂工具的补充说明（按需读取）
    reference: str = ""

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
    group: str = "core",
    output_schema: dict | None = None,
    examples: list | None = None,
    reference: str = "",
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
    spec = ToolSpec(
        name,
        description,
        normalized,
        handler,
        mutating=mutating,
        group=group,
        output_schema=output_schema,
        examples=tuple(examples or ()),
        reference=reference,
    )
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


# —— 工具发现：指南 / schema / 示例 / 深文档 ——
GUIDELINES_FILE_NAME = "ai_assistant_prompt.md"
_FALLBACK_GUIDELINES = (
    "你是 Wwise 自动化助手。只使用表格或工具结果里出现过的 object_id；"
    "查询优先用只读工具或 waql_query；改动工程前先向用户说明并确认；"
    "不要臆造 Wwise 路径、类型或 API。"
)


def _load_guidelines() -> str:
    path = path_utils.get_resource_path(GUIDELINES_FILE_NAME)
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read().strip()
        if text:
            return text
    except OSError as e:
        Logger().warning(f"读取工具指南失败：{path}（{e}），使用内置精简版")
    return _FALLBACK_GUIDELINES


def _handler_get_guidelines(args: dict) -> dict:
    note = (
        "> MCP 环境说明：`@table` / `@selection` 与 `gui_*` 工具仅在软件内 AI 助手可用；"
        "通过 MCP 调用时一律传真实 GUID。\n\n"
    )
    return {"instructions": note + _load_guidelines()}


def _handler_get_tool_schema(args: dict) -> dict:
    name = str(args.get("name") or "").strip()
    spec = get_tool(name)
    if spec is None:
        return {"error": f"未知工具：{name}"}
    return {
        "name": spec.name,
        "description": spec.description,
        "parameters": spec.parameters,
        "output_schema": spec.output_schema,
        "group": spec.group,
        "mutating": spec.mutating,
        "examples_count": len(spec.examples),
        "has_reference": bool(spec.reference),
    }


def _handler_get_tool_examples(args: dict) -> dict:
    name = str(args.get("name") or "").strip()
    keywords = [word.lower() for word in str(args.get("keywords") or "").split() if word]
    try:
        max_results = max(1, int(args.get("max_results", 10)))
    except (TypeError, ValueError):
        max_results = 10
    if name:
        spec = get_tool(name)
        if spec is None:
            return {"error": f"未知工具：{name}"}
        specs = [spec]
    else:
        specs = list(_TOOLS.values())
    matches = []
    truncated = False
    for spec in specs:
        for example in spec.examples:
            haystack = " ".join([
                spec.name,
                str(example.get("title", "")),
                str(example.get("description", "")),
                json.dumps(example.get("arguments", {}), ensure_ascii=False),
            ]).lower()
            if keywords and not any(word in haystack for word in keywords):
                continue
            if len(matches) >= max_results:
                truncated = True
                break
            matches.append({"tool": spec.name, **example})
        if truncated:
            break
    return {
        "count": len(matches),
        "truncated": truncated,
        "examples": matches,
    }


def _handler_get_tool_reference(args: dict) -> dict:
    name = str(args.get("name") or "").strip()
    spec = get_tool(name)
    if spec is None:
        return {"error": f"未知工具：{name}"}
    if spec.reference:
        reference = spec.reference
    else:
        lines = [f"# {spec.name}", "", spec.description, "", "## 参数"]
        required = set(spec.parameters.get("required") or [])
        for param_name, prop in spec.parameters.get("properties", {}).items():
            marker = "（必填）" if param_name in required else ""
            lines.append(f"- `{param_name}` {prop.get('type', '')}{marker}：{prop.get('description', '')}")
        if spec.output_schema:
            lines += ["", "## 输出", "```json", json.dumps(spec.output_schema, ensure_ascii=False, indent=2), "```"]
        if spec.examples:
            lines += ["", "## 示例"]
            for example in spec.examples[:5]:
                lines.append(f"### {example.get('title', '')}")
                lines.append(str(example.get("description", "")))
                lines.append("```json")
                lines.append(json.dumps(example.get("arguments", {}), ensure_ascii=False, indent=2))
                lines.append("```")
        reference = "\n".join(lines)
    return {
        "name": spec.name,
        "group": spec.group,
        "mutating": spec.mutating,
        "reference": reference,
        "output_schema": spec.output_schema,
        "examples": list(spec.examples)[:5],
    }


register_tool(
    "get_guidelines",
    "返回本工具集的使用指南：工具路由规则、修改/确认约定、WAQL 语法要点、Wwise 2025+ 路径与类型变化。会话开始时调用一次即可，内容不会变。外部 MCP 客户端在不确定如何选工具时应先调用它。",
    {"type": "object", "properties": {}, "required": []},
    _handler_get_guidelines,
    output_schema={
        "type": "object",
        "properties": {"instructions": {"type": "string", "description": "完整使用指南（Markdown）"}},
        "required": ["instructions"],
    },
)


register_tool(
    "get_tool_schema",
    "返回某个工具的完整定义（描述、参数 schema、输出 schema、分组、是否修改工程、示例数量）。在不确定参数或返回字段时调用；比反复试错更可靠。",
    {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "工具名，例如 waql_query / aggregate_tool_chain"},
        },
        "required": ["name"],
    },
    _handler_get_tool_schema,
)


register_tool(
    "get_tool_examples",
    "返回工具的真实调用示例（title / description / arguments），可按工具名和关键词筛选。刚发现的工具或不确定怎么写参数时先调它；官方建议的发现顺序是 get_guidelines → get_tool_examples → get_tool_schema → 调用工具。",
    {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "可选：只看某个工具的示例；省略则搜索全部工具"},
            "keywords": {"type": "string", "description": "可选：空格分隔的关键词，匹配示例标题/描述/参数"},
            "max_results": {"type": "integer", "description": "最多返回多少条，默认 10"},
        },
        "required": [],
    },
    _handler_get_tool_examples,
    output_schema={
        "type": "object",
        "properties": {
            "count": {"type": "integer"},
            "truncated": {"type": "boolean"},
            "examples": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "arguments": {"type": "object"},
                    },
                },
            },
        },
        "required": ["count", "truncated", "examples"],
    },
)


register_tool(
    "get_tool_reference",
    "返回某个工具的深入参考文档（参数说明、输出结构、示例）；工具自带深文档时直接返回，否则自动生成。适合复杂工具（聚合统计、自动转码、WAQL 等）在正式调用前阅读。",
    {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "工具名"},
        },
        "required": ["name"],
    },
    _handler_get_tool_reference,
)


# —— 工具分组与按需加载 ——
# core 常驻；其余分组由 AI 调 load_tools 后再暴露，减少每轮下发的工具数量。
_TOOL_GROUP_DESCRIPTIONS = {
    "auto_compression": "自动转码（Conversion）分析与应用",
    "soundbank": "SoundBank 创建、包含项、体积统计",
    "localization": "多语言样本导入、补静音、语言槽位",
    "rtpc_effects": "RTPC、Effect 槽、Output Bus、3D 定位",
    "source_files": "磁盘源文件编辑/导入/整理（多为危险操作）",
    "advanced": "临时脚本等高级逃生口",
}

_TOOL_GROUP_NAMES = {
    "soundbank": {
        "add_objects_to_bank", "clear_bank_inclusions", "create_bank_for_object",
        "create_sound_bank_by_name", "get_bank_inclusions", "get_total_bank_size",
        "set_bank_inclusion", "set_inclusion_type",
    },
    "localization": {
        "localize_languages", "import_silence", "add_silence", "get_wave_path_for_language",
    },
    "rtpc_effects": {
        "add_rtpc", "clear_rtpc", "copy_rtpc", "add_effect", "clear_effects",
        "get_or_create_bus", "set_output_bus", "set_sound_3d",
    },
    "source_files": {
        "apply_source_edits", "reset_source_editor", "replace_audio_file",
        "auto_import_by_path", "rename_original_to_wwise", "tidy_original_folders",
        "delete_unused_akd_files", "add_to_source_control",
    },
    "advanced": {"run_wwise_script"},
}

_active_groups: set[str] = set()


def _assign_default_groups() -> None:
    # 注册阶段显式指定过 group 的工具保持原样；其余按名字归入专业分组
    for group, names in _TOOL_GROUP_NAMES.items():
        for name in names:
            spec = _TOOLS.get(name)
            if spec is not None and spec.group == "core":
                _TOOLS[name] = replace(spec, group=group)


def reset_active_groups() -> None:
    _active_groups.clear()


def active_groups() -> set:
    return set(_active_groups)


def grouped_tool_specs(include_groups=None) -> list:
    # include_groups=None 表示全部工具（MCP/调试）；否则 core + 已加载分组
    if include_groups is None:
        return list(_TOOLS.values())
    allowed = {"core", *include_groups}
    return [spec for spec in _TOOLS.values() if spec.group in allowed]


def _handler_list_tool_groups(args: dict) -> dict:
    groups = []
    for name, description in _TOOL_GROUP_DESCRIPTIONS.items():
        tools = sorted(spec.name for spec in _TOOLS.values() if spec.group == name)
        groups.append({
            "group": name,
            "description": description,
            "tool_count": len(tools),
            "tools": tools,
            "loaded": name in _active_groups,
        })
    return {
        "groups": groups,
        "core_count": sum(1 for spec in _TOOLS.values() if spec.group == "core"),
        "loaded_groups": sorted(_active_groups),
        "hint": "需要某组工具时调用 load_tools(group=...)，下一轮起可用",
    }


def _handler_load_tools(args: dict) -> dict:
    group = str(args.get("group") or "").strip()
    if not group:
        return {"error": f"缺少 group 参数，可用值：{'/'.join(_TOOL_GROUP_DESCRIPTIONS)}"}
    if group not in _TOOL_GROUP_DESCRIPTIONS:
        return {"error": f"未知分组「{group}」，可用值：{'/'.join(_TOOL_GROUP_DESCRIPTIONS)}"}
    _active_groups.add(group)
    tools = sorted(spec.name for spec in _TOOLS.values() if spec.group == group)
    return {
        "group": group,
        "activated": True,
        "tools": tools,
        "loaded_groups": sorted(_active_groups),
        "hint": "这些工具从下一轮对话开始可以调用；不确定参数时用 get_tool_schema / get_tool_examples",
    }


register_tool(
    "list_tool_groups",
    "列出可用的工具分组（core 之外的 SoundBank / 本地化 / RTPC 效果 / 源文件 / 高级脚本等）及各组工具名。当前已加载的分组会标记 loaded。找不到需要的工具时先调它，再用 load_tools 加载对应分组。",
    {"type": "object", "properties": {}, "required": []},
    _handler_list_tool_groups,
)


register_tool(
    "load_tools",
    "按需加载一个工具分组，使该组工具从下一轮对话起出现在可用工具列表里（减少每轮工具 schema 的上下文占用）。先用 list_tool_groups 查看分组与工具名。",
    {
        "type": "object",
        "properties": {
            "group": {"type": "string", "description": "分组名，如 soundbank / localization / rtpc_effects / source_files / auto_compression / advanced"},
        },
        "required": ["group"],
    },
    _handler_load_tools,
)


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
    output_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "path": {"type": "string"},
                    },
                },
            },
        },
    },
    examples=[
        {
            "title": "读取当前表格对象详情",
            "description": "用 @table 指代主窗口表格里的对象",
            "arguments": {"object_ids": ["@table"]},
        },
    ],
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
    output_schema={
        "type": "object",
        "properties": {
            "total_files": {"type": "integer", "description": "去重后的源文件数"},
            "total_mb": {"type": "number", "description": "合计 MB"},
            "objects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "object": {"type": "string"},
                        "files": {"type": "integer"},
                        "size_mb": {"type": "number"},
                    },
                },
            },
            "missing": {"type": "object", "description": "读不到的路径数量与样例"},
        },
    },
    examples=[
        {
            "title": "统计表格对象的音频磁盘占用",
            "description": "按源 wav 路径去重后求和",
            "arguments": {"object_ids": ["@table"]},
        },
    ],
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
    output_schema={
        "type": "object",
        "properties": {
            "count": {"type": "integer"},
            "truncated": {"type": "boolean"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "path": {"type": "string"},
                    },
                },
            },
        },
    },
    examples=[
        {
            "title": "取所有 MusicSegment",
            "description": "递归查找指定类型后代",
            "arguments": {"object_ids": ["@table"], "child_type": "MusicSegment", "limit": 0},
        },
        {
            "title": "取所有音频源",
            "description": "AudioFileSource 用于时长/体积统计",
            "arguments": {"object_ids": ["@table"], "child_type": "AudioFileSource", "limit": 0},
        },
    ],
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
    output_schema={
        "type": "object",
        "properties": {
            "tool": {"type": "string"},
            "list_key": {"type": "string"},
            "total": {"type": "integer", "description": "列表条数"},
            "sample": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["total"],
    },
    examples=[
        {
            "title": "统计表格对象下的 Sound 数量",
            "description": "先查询再用工具侧计数，不需要把列表取回",
            "arguments": {
                "tool_name": "get_descendants_of_type",
                "arguments": {"object_ids": ["@table"], "child_type": "Sound"},
            },
        },
    ],
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
    output_schema={
        "type": "object",
        "properties": {
            "total_items": {"type": "integer"},
            "group_by": {"type": "string"},
            "min_count": {"type": "integer"},
            "matched_count": {"type": ["integer", "null"]},
            "groups": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "group": {"type": "string"},
                        "count": {"type": "integer"},
                    },
                },
            },
            "matched_groups": {"type": "array", "items": {"type": "object"}},
        },
    },
    examples=[
        {
            "title": "按所属根对象分组统计 Sound",
            "description": "只保留数量大于 5 的分组",
            "arguments": {
                "tool_name": "get_descendants_of_type",
                "arguments": {"object_ids": ["@table"], "child_type": "Sound"},
                "group_by": "root_id",
                "min_count": 5,
            },
        },
    ],
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
    output_schema={
        "type": "object",
        "properties": {
            "steps": {"type": "array", "items": {"type": "object"}, "description": "每一步的工具与条数"},
            "total_items": {"type": "integer"},
            "aggregate": {"type": "string"},
            "value": {"type": ["number", "integer", "null"], "description": "请求的聚合值（sum/avg/min/max/count）"},
            "stats": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                    "sum": {"type": "number"},
                    "avg": {"type": "number"},
                    "min": {"type": "number"},
                    "max": {"type": "number"},
                },
            },
            "value_key": {"type": "string", "description": "实际参与统计的字段名"},
            "skipped": {"type": "integer", "description": "取不到数值而跳过的条数"},
            "groups": {"type": "array", "items": {"type": "object"}},
            "matched_count": {"type": ["integer", "null"]},
            "matched_groups": {"type": "array", "items": {"type": "object"}},
        },
    },
    examples=[
        {
            "title": "统计所有音频源总时长",
            "description": "逐项读取 Duration 并求和，一次调用完成",
            "arguments": {
                "steps": [
                    {
                        "tool_name": "get_descendants_of_type",
                        "arguments": {"object_ids": ["@table"], "child_type": "AudioFileSource", "limit": 0},
                    },
                    {
                        "tool_name": "get_object_property",
                        "arguments": {"object_id": "$id", "property_name": "Duration"},
                    },
                ],
                "aggregate": "sum",
                "value_path": "max",
            },
        },
        {
            "title": "统计含超过 1 个 MusicTrack 的 MusicSegment",
            "description": "跨层级计数，末步按 root_id 分组并过滤",
            "arguments": {
                "steps": [
                    {
                        "tool_name": "get_descendants_of_type",
                        "arguments": {"object_ids": ["@table"], "child_type": "MusicSegment", "limit": 0},
                    },
                    {
                        "tool_name": "get_descendants_of_type",
                        "arguments": {"child_type": "MusicTrack", "limit": 0},
                    },
                ],
                "group_by": "root_id",
                "min_count": 1,
            },
        },
    ],
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
    output_schema={
        "type": "object",
        "properties": {
            "count": {"type": "integer"},
            "scanned": {"type": "integer"},
            "truncated": {"type": "boolean"},
            "types_without_property": {"type": "array", "items": {"type": "string"}},
            "types_not_comparable": {"type": "array", "items": {"type": "string"}},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "value": {},
                    },
                },
            },
            "errors": {"type": "array", "items": {"type": "string"}},
        },
    },
    examples=[
        {
            "title": "找出 Volume 不为 0 的 Sound",
            "description": "用 child_type 收窄扫描范围",
            "arguments": {
                "object_ids": ["@table"],
                "property_name": "Volume",
                "op": "!=",
                "value": 0,
                "child_type": "Sound",
                "scan_limit": 0,
                "limit": 0,
            },
        },
        {
            "title": "找出时长大于 0 的音频源",
            "description": "Duration 返回 {min,max,type}，工具会自动按数值比较",
            "arguments": {
                "object_ids": ["@table"],
                "property_name": "Duration",
                "op": ">",
                "value": 0,
                "child_type": "AudioFileSource",
                "scan_limit": 0,
                "limit": 0,
            },
        },
    ],
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

# —— 通用 WAQL 查询（只读逃生口）——
WAQL_RESULT_LIMIT_DEFAULT = 1000


def _handler_waql_query(args: dict) -> dict:
    waql = str(args.get("waql") or "").strip()
    if not waql:
        return {"error": "缺少 waql 参数（例如 from type Sound where @Volume < 0）"}
    raw_fields = args.get("return_fields")
    return_fields = [
        str(item).strip() for item in raw_fields
        if str(item).strip()
    ] if isinstance(raw_fields, list) else []
    try:
        limit = int(args.get("limit", WAQL_RESULT_LIMIT_DEFAULT))
    except (TypeError, ValueError):
        limit = WAQL_RESULT_LIMIT_DEFAULT
    items = waapi_utils.query_waql(waql, return_fields)
    total = len(items)
    if limit > 0:
        items = items[:limit]
    return {
        "count": len(items),
        "total": total,
        "truncated": total > len(items),
        "items": items,
    }


register_tool(
    "waql_query",
    "执行只读 WAQL 查询（Wwise Authoring Query Language），适合现有工具覆盖不了的任意筛选/遍历/投影，等价于 ak.wwise.core.object.get + waql。示例：`from type Sound where @Volume < 0 orderby name take 50`、`from object \"{GUID}\" select descendants where type = \"MusicTrack\"`、`from type Event select children select target`。能力：from type/object/search/project；where（= != < > : 正则 /re/、and/or、!()）；select children/descendants/ancestors/parent/referencesTo；orderby/distinct/skip/take；列表函数 count()/any()/all()/first()/last()/at(N)/where()。注意：WAQL 没有算术运算；字符串用双引号；`from type` 走索引，比 `where type = ...` 快；访问原始值用 @PropertyName（不带 @ 会按 override 解析）。",
    {
        "type": "object",
        "properties": {
            "waql": {
                "type": "string",
                "description": "WAQL 查询语句，例如 from type Sound where @Volume < 0",
            },
            "return_fields": {
                "type": "array",
                "items": {"type": "string", "description": "WAAPI 返回表达式"},
                "description": "可选返回表达式数组，例如 [\"name\", \"path\", \"OutputBus.name as bus\"]；省略则返回 id/name/type/path",
            },
            "limit": {
                "type": "integer",
                "description": f"最多返回多少条，默认 {WAQL_RESULT_LIMIT_DEFAULT}；0 表示不限量",
            },
        },
        "required": ["waql"],
    },
    _handler_waql_query,
    output_schema={
        "type": "object",
        "properties": {
            "count": {"type": "integer", "description": "本次返回条数"},
            "total": {"type": "integer", "description": "查询命中总数"},
            "truncated": {"type": "boolean", "description": "是否因 limit 被截断"},
            "items": {
                "type": "array",
                "items": {"type": "object"},
                "description": "对象或投影结果（默认含 id/name/type/path）",
            },
        },
        "required": ["count", "total", "truncated", "items"],
    },
    examples=[
        {
            "title": "查找负音量的 Sound",
            "description": "按属性筛选并排序，取前 50 条",
            "arguments": {"waql": "from type Sound where @Volume < 0 orderby name take 50"},
        },
        {
            "title": "取某对象下所有 MusicTrack",
            "description": "用对象 GUID 做根，投影名称与路径",
            "arguments": {
                "waql": "from object \"{GUID}\" select descendants where type = \"MusicTrack\"",
                "return_fields": ["name", "path"],
            },
        },
        {
            "title": "列出事件及其播放目标",
            "description": "Event -> Action -> Target 的链式查询",
            "arguments": {"waql": "from type Event select children select target"},
        },
        {
            "title": "反向查找播放某对象的 Event",
            "description": "referencesTo 反查 Action，再取父级 Event",
            "arguments": {
                "waql": "\"{GUID}\" select referencesTo where type = \"Action\" select parent",
                "return_fields": ["name", "path"],
            },
        },
    ],
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
    "分析「自动转码」方案（只读，不改工程）：递归收集表格对象子树里的 PropertyContainer（旧版称 ActorMixer）与 Container，读取其下 AudioFileSource 的播放时长，按短/长阈值把音频分成短/中/长三档，再按每个节点的多数结果（父级继承 + 占优比例）决定它该用哪一档 Conversion；长/短档用默认档 Conversion 名称加 _Long / _Short 后缀。用户说「按音频时长自动设置转码 / 长短音效分开转码 / 自动分配 Conversion」时先用它出方案，用户确认后再调 auto_compression_apply。返回各档数量 summary、需要 OverrideConversion 的节点 plans、以及待新建的 Conversion 名称",
    {
        "type": "object",
        "properties": {
            "object_ids": {
                "type": "array",
                "items": {"type": "string", "description": "Wwise 对象 GUID"},
                "description": "要分析的根对象 id（表格对象；其子树里的 PropertyContainer（旧版 ActorMixer）/ Container 会被逐个判定）",
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
    group="auto_compression",
    output_schema={
        "type": "object",
        "properties": {
            "default_conversion": {"type": "string"},
            "short_threshold": {"type": "number"},
            "long_threshold": {"type": "number"},
            "conversions": {"type": "object", "description": "medium/long/short 档使用的 Conversion 名称"},
            "will_create": {"type": "array", "items": {"type": "string"}},
            "target_count": {"type": "integer"},
            "source_count": {"type": "integer"},
            "override_count": {"type": "integer", "description": "需要打开 OverrideConversion 的节点数"},
            "plans": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "path": {"type": "string"},
                        "category": {"type": "string", "enum": ["short", "medium", "long"]},
                        "counts": {"type": "object"},
                    },
                },
            },
            "truncated": {"type": "boolean"},
            "summary": {"type": "object", "description": "各档数量与有效时长统计"},
        },
    },
    examples=[
        {
            "title": "按音频时长生成自动转码方案",
            "description": "阈值省略时用设置窗口保存的 0.5s / 5s",
            "arguments": {"object_ids": ["@table"]},
        },
        {
            "title": "自定义长短阈值",
            "description": "1 秒以内算短、8 秒以上算长",
            "arguments": {"object_ids": ["@table"], "short_threshold": 1, "long_threshold": 8},
        },
    ],
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
    group="auto_compression",
    output_schema={
        "type": "object",
        "properties": {
            "applied_count": {"type": "integer"},
            "failed_count": {"type": "integer"},
            "failed": {"type": "array", "items": {"type": "string"}},
            "override_count": {"type": "integer"},
            "default_conversion": {"type": "string"},
            "conversions": {"type": "object"},
            "created_conversions": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "object"},
        },
    },
    examples=[
        {
            "title": "应用自动转码方案",
            "description": "先 plan、用户确认后再 apply；confirmed 由软件内 AI 按修改策略代填",
            "arguments": {"object_ids": ["@table"], "confirmed": True},
        },
    ],
)


# MCP legacy 工具迁移目录：注册后 AI 助手与 MCP 共用同一份工具定义
from libraries import wwise_tool_catalog as _wwise_tool_catalog  # noqa: E402, F401

_assign_default_groups()
