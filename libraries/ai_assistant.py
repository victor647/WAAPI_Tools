# AI 助手：把「表格中的 Wwise 对象」交给大模型处理。
# - 系统提示词模板见仓库根目录 ai_assistant_prompt.md，动态附加本次表格对象清单；
#   模型以 OpenAI 兼容 function calling 调用下方工具；
# - 工具实现复用 libraries.utils.wwise 下与 GUI 一致的 *_utils 封装，不在本模块直接操作 WAAPIClient；
# - 本模块不依赖 Qt，便于测试；HTTP 请求由 libraries.utils.ai_utils 提供。
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from libraries import tool_registry
from libraries.utils import ai_utils, path_utils, user_config
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import common_utils, event_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType

# 每个工具结果回传给模型的最大字符数，避免长列表撑爆上下文
RESULT_CHAR_LIMIT = 6000
# 工具结果按字符预算收缩：先减列表条数，再缩短超长字符串，保证回传的 JSON 始终完整可解析
MODEL_LIST_ITEM_CAP = 30
MODEL_STRING_LIMIT = 240

# 这些工具的结果本身就是"读取/统计大结果"的产物，不允许再落盘一次：
# 否则 read_result_file 会把自己读到的分页又写成新的 result_file，模型永远读不到内容
NO_OFFLOAD_TOOLS = frozenset({
    "read_result_file",
    "group_result_file",
    "count_tool_items",
    "group_tool_items",
    "aggregate_tool_chain",
})

# 大结果落盘目录（每次任务一个，任务结束自动删除）
_RESULT_DIR_PREFIX = "waapi_ai_"
_result_dir: str | None = None
_result_counter = 0

# 部分模型（如 MiniMax）会把内部推理写在 <think> 块里，展示给用户时去除
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

# 会修改 Wwise 工程内容的工具名；GUI 用它在任务结束后决定是否刷新表格
MUTATING_TOOL_NAMES = frozenset({
    "rename_case",
    "rename_with_acronym",
    "rename_object",
    "remove_name_prefix",
    "remove_name_suffix",
    "set_notes",
    "set_inclusion",
    "create_parent",
    "convert_type",
    "split_underscore_to_folder",
    "update_notes_and_color",
    "create_play_event",
    "delete_objects",
})

# create_parent / convert_type 支持的目标类型（与 GUI 右键菜单一致）
_WRAPPER_TYPE_NAMES = [
    "ActorMixer",
    "BlendContainer",
    "RandomSequenceContainer",
    "SwitchContainer",
    "Folder",
    "WorkUnit",
]

# 模型提示词模板文件：与 material.css 同级放在仓库根目录，打包时需作为资源一并打入
PROMPT_FILE_NAME = "ai_assistant_prompt.md"

# 模板文件缺失时的兜底提示词（保证功能可用，并在日志中提示打包问题）
_FALLBACK_TEMPLATE = (
    "你是嵌入在「WAAPI 工具集」软件中的 Wwise 音频工程助手。\n"
    "规则：只使用下方对象清单或工具返回结果中的 object_id；破坏性操作需用户明确要求；"
    "用中文简洁回复。\n"
    "警告：未找到提示词模板文件 ai_assistant_prompt.md，请检查打包配置是否包含该资源。"
)


class AiToolError(ValueError):
    pass


class AIAgentStopped(RuntimeError):
    """agent loop 被用户中止（不是代理错误）。"""


@dataclass
class AIAssistantResult:
    content: str = ""
    mutated: bool = False
    turn_count: int = 0
    tool_call_count: int = 0
    executed_tools: list[dict] = field(default_factory=list)


def _require_object_ids(args: dict) -> list[str]:
    # 工具入参统一支持 object_ids 数组（个别情况容忍单个字符串）
    value = args.get("object_ids")
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not value:
        raise AiToolError("缺少 object_ids 参数，应传入 Wwise 对象 id 数组")
    return [str(item) for item in value]


def _require_object_id(args: dict) -> str:
    value = args.get("object_id")
    if not value:
        raise AiToolError("缺少 object_id 参数")
    return str(value)


def _summary(ok_count: int, total: int, label: str, failures: list[str]) -> str:
    # 汇总一批对象上的操作结果
    text = f"{label}完成 {ok_count}/{total}"
    if failures:
        text += "；失败：" + "；".join(failures[:5])
    return text


def _rename_case(args: dict) -> str:
    case = args.get("case")
    case_functions = {
        "lower": common_utils.rename_to_lower_case,
        "title": common_utils.rename_to_title_case,
        "upper": common_utils.rename_to_upper_case,
    }
    if case not in case_functions:
        raise AiToolError("case 仅支持 lower/title/upper")
    ids = _require_object_ids(args)
    ok_count = 0
    failures = []
    for object_id in ids:
        try:
            if case_functions[case](WwiseObject.from_id(object_id)):
                ok_count += 1
        except Exception as e:
            failures.append(f"{object_id}: {e}")
    return _summary(ok_count, len(ids), f"名称改为{case} ", failures)


def _rename_with_acronym(args: dict) -> str:
    ids = _require_object_ids(args)
    ok_count = 0
    failures = []
    for object_id in ids:
        try:
            if common_utils.rename_with_acronym(WwiseObject.from_id(object_id)):
                ok_count += 1
        except Exception as e:
            failures.append(f"{object_id}: {e}")
    return _summary(ok_count, len(ids), "按约定缩写重命名 ", failures)


def _rename_object(args: dict) -> str:
    object_id = _require_object_id(args)
    new_name = str(args.get("new_name", "")).strip()
    if not new_name:
        raise AiToolError("缺少 new_name 参数")
    obj = WwiseObject.from_id(object_id)
    if new_name == obj.name:
        return "新名称与当前名称相同，未修改"
    if waapi_utils.rename_object(obj, new_name):
        return f"已重命名为 {new_name}"
    return f"重命名为 {new_name} 失败"


def _remove_prefix_or_suffix(args: dict) -> str:
    # 去除名称开头/末尾的下划线分段
    part = args.get("part")
    if part not in ("prefix", "suffix"):
        raise AiToolError("part 仅支持 prefix/suffix")
    ids = _require_object_ids(args)
    ok_count = 0
    failures = []
    for object_id in ids:
        try:
            obj = WwiseObject.from_id(object_id)
            if "_" not in obj.name:
                failures.append(f"{object_id}: 名称中不含下划线，跳过")
                continue
            if part == "prefix":
                changed = common_utils.remove_name_prefix(obj)
            else:
                changed = common_utils.remove_name_suffix(obj)
            if changed:
                ok_count += 1
        except Exception as e:
            failures.append(f"{object_id}: {e}")
    label = "去除开头分段 " if part == "prefix" else "去除末尾分段 "
    return _summary(ok_count, len(ids), label, failures)


def _set_notes(args: dict) -> str:
    object_id = _require_object_id(args)
    notes = str(args.get("notes", ""))
    obj = WwiseObject.from_id(object_id)
    if waapi_utils.set_object_notes(obj, notes):
        return f"已更新备注（{len(notes)} 字）"
    return "更新备注失败"


def _set_inclusion(args: dict) -> str:
    ids = _require_object_ids(args)
    included = bool(args.get("included"))
    ok_count = 0
    failures = []
    for object_id in ids:
        try:
            if common_utils.set_object_inclusion(WwiseObject.from_id(object_id), included):
                ok_count += 1
        except Exception as e:
            failures.append(f"{object_id}: {e}")
    label = "启用" if included else "停用"
    return _summary(ok_count, len(ids), label, failures)


def _to_target_type(args: dict, *, create_parent: bool) -> str:
    object_id = _require_object_id(args)
    type_name = args.get("target_type")
    if type_name not in _WRAPPER_TYPE_NAMES:
        raise AiToolError(f"target_type 仅支持 {'/'.join(_WRAPPER_TYPE_NAMES)}")
    obj = WwiseObject.from_id(object_id)
    if create_parent:
        created = common_utils.create_parent(obj, WwiseObjectType(type_name))
        if not created or not created.is_valid:
            return "创建父级失败"
        result = {
            "id": created.id,
            "name": created.name,
            "type": created.type.value,
            "path": created.path,
        }
        return "已创建父级：" + json.dumps(result, ensure_ascii=False)
    if common_utils.convert_to_type(obj, WwiseObjectType(type_name)):
        return f"已转换为 {type_name}（原对象 id 可能变化）"
    return "转换类型失败"


def _create_parent(args: dict) -> str:
    return _to_target_type(args, create_parent=True)


def _convert_type(args: dict) -> str:
    return _to_target_type(args, create_parent=False)


def _split_underscore_to_folder(args: dict) -> str:
    ids = _require_object_ids(args)
    ok_count = 0
    failures = []
    for object_id in ids:
        try:
            if common_utils.split_underscore_to_folder(WwiseObject.from_id(object_id)):
                ok_count += 1
        except Exception as e:
            failures.append(f"{object_id}: {e}")
    return _summary(ok_count, len(ids), "按下划线拆分到子文件夹 ", failures)


def _update_notes_and_color(args: dict) -> str:
    ids = _require_object_ids(args)
    ok_count = 0
    failures = []
    for object_id in ids:
        try:
            if common_utils.update_notes_and_color(WwiseObject.from_id(object_id)):
                ok_count += 1
        except Exception as e:
            failures.append(f"{object_id}: {e}")
    return _summary(ok_count, len(ids), "按约定更新备注与颜色 ", failures)


def _create_play_event(args: dict) -> str:
    ids = _require_object_ids(args)
    ok_count = 0
    failures = []
    for object_id in ids:
        try:
            if event_utils.create_play_event(WwiseObject.from_id(object_id)):
                ok_count += 1
        except Exception as e:
            failures.append(f"{object_id}: {e}")
    return _summary(ok_count, len(ids), "创建/更新 Play Event ", failures)


def _delete_objects(args: dict) -> str:
    # 危险操作：直接删除 Wwise 对象（含子树策略由 Wwise 决定）
    if args.get("confirmed") is not True:
        return "危险操作被拦截：请用户明确确认后，以 confirmed=true 重新调用"
    ids = _require_object_ids(args)
    ok_count = 0
    failures = []
    for object_id in ids:
        try:
            if waapi_utils.delete_object(WwiseObject.from_id(object_id)):
                ok_count += 1
        except Exception as e:
            failures.append(f"{object_id}: {e}")
    return _summary(ok_count, len(ids), "删除对象 ", failures)


# AI 助手专用：把对象发送到主窗口表格（默认替换表格内容；MCP/无界面环境不可用）
_table_sink: Callable[[list[str], bool], None] | None = None
# 本次任务的表格对象 id：支持在工具参数里用 "@table" 指代，避免模型罗列大量 id
_table_object_ids: list[str] = []
_SPECIAL_ID_TOKENS = ("@table", "@selection")


def set_table_sink(sink: Callable[[list[str], bool], None] | None) -> None:
    global _table_sink
    _table_sink = sink


def set_table_context(object_ids: list[str]) -> None:
    global _table_object_ids
    _table_object_ids = list(object_ids)


# 主线程 GUI 调用桥：由主窗口注入（无界面环境为空）
_gui_invoker: Callable[..., object] | None = None


def set_gui_invoker(invoker: Callable[..., object] | None) -> None:
    global _gui_invoker
    _gui_invoker = invoker


def _invoke_gui(runner, wait: bool = True):
    # runner(window) 在主线程执行；wait=False 用于"打开窗口给用户看"这类不需要返回值的操作
    if _gui_invoker is None:
        raise AiToolError("当前环境不支持操作软件界面（仅软件内 AI 助手可用）")
    return _gui_invoker(runner, wait)


def _resolve_special_token(token: str) -> list[str] | None:
    if token == "@table":
        return list(_table_object_ids)
    if token == "@selection":
        return [obj.id for obj in waapi_utils.get_selected_objects()]
    return None


def _expand_special_ids(arguments: dict) -> tuple[dict, int]:
    # 把参数里的 "@table" / "@selection" 展开为真实 id 列表
    expanded = dict(arguments)
    expanded_count = 0
    for key, value in list(expanded.items()):
        values = value if isinstance(value, list) else [value]
        if not any(isinstance(item, str) and item in _SPECIAL_ID_TOKENS for item in values):
            continue
        resolved: list[str] = []
        for item in values:
            token_ids = _resolve_special_token(item) if isinstance(item, str) else None
            if token_ids:
                resolved.extend(token_ids)
                expanded_count += len(token_ids)
            elif isinstance(item, str):
                resolved.append(item)
        expanded[key] = resolved
    return expanded, expanded_count


def _set_table_objects(args: dict) -> str:
    ids = _require_object_ids(args)
    append = bool(args.get("append", False))
    if _table_sink is None:
        return "当前环境不支持“发送到表格”（该能力仅在软件界面的 AI 助手中可用）"
    _table_sink(ids, append)
    return f"已把 {len(ids)} 个对象{'追加到' if append else '替换为'}表格内容"


# —— 软件界面操作（与手动点按钮/菜单等价，主线程执行）——


def _gui_get_wwise_selection(args: dict) -> str:
    _invoke_gui(lambda window: window.get_selected_objects())
    return "已执行「获取Wwise选中对象」，表格已按 Wwise 当前选中刷新"


def _gui_find_children(args: dict) -> str:
    recursive = bool(args.get("recursive", True))
    keep_self = bool(args.get("keep_self", False))

    def runner(window):
        window.cbxRecursiveFind.setChecked(recursive)
        window.cbxKeepSelf.setChecked(keep_self)
        window.find_children()

    _invoke_gui(runner)
    return f"已查找下级（递归={recursive}，保留自身={keep_self}）并更新表格"


def _gui_find_parent(args: dict) -> str:
    recursive = bool(args.get("recursive", True))
    keep_self = bool(args.get("keep_self", False))

    def runner(window):
        window.cbxRecursiveFind.setChecked(recursive)
        window.cbxKeepSelf.setChecked(keep_self)
        window.find_parent()

    _invoke_gui(runner)
    return f"已查找上级（递归={recursive}，保留自身={keep_self}）并更新表格"


def _gui_set_filter(args: dict) -> str:
    keyword = str(args.get("keyword") or "")
    # 类型筛选控件支持多选：这里同时接受单个类型名与类型名数组
    raw_type = args.get("object_type") or []
    object_types = [name for name in (raw_type if isinstance(raw_type, list) else [raw_type]) if name]
    only_included = bool(args.get("only_included", False))
    case_sensitive = bool(args.get("case_sensitive", False))

    def runner(window):
        window.ledFilterKeyword.setText(keyword)
        window.cbxCaseSensitive.setChecked(case_sensitive)
        window.cbxOnlyIncludedEnabled.setChecked(only_included)
        window.cbbFilterType.set_checked_options(object_types)
        window.apply_table_filter(record_history=True)

    _invoke_gui(runner)
    return f"已应用筛选（关键字={keyword or '无'}，类型={'、'.join(object_types) or '全部'}）"


def _gui_open_window(args: dict) -> str:
    window_key = str(args.get("window") or "").strip()
    if not window_key:
        raise AiToolError("缺少 window 参数")
    name = _invoke_gui(lambda window: window.ai_open_window(window_key), wait=False)
    return name or f"已请求打开窗口：{window_key}"


def _gui_run_action(args: dict) -> str:
    action_name = str(args.get("action_name") or "").strip()
    if not action_name:
        raise AiToolError("缺少 action_name 参数（菜单 action 的 objectName）")
    if args.get("confirmed") is not True:
        raise AiToolError("触发菜单动作可能修改工程：请在用户明确要求后传 confirmed=true")
    _invoke_gui(lambda window: window.ai_run_action(action_name))
    return f"已触发菜单动作：{action_name}"


def _gui_list_actions(args: dict) -> dict:
    keyword = str(args.get("keyword") or "").strip().lower()
    actions = _invoke_gui(lambda window: window.ai_list_actions(keyword))
    return {"count": len(actions), "actions": actions}


def _select_in_wwise(args: dict) -> str:
    ids = _require_object_ids(args)
    objects = []
    failures = []
    for object_id in ids:
        try:
            objects.append(WwiseObject.from_id(object_id))
        except Exception as e:
            failures.append(f"{object_id}: {e}")
    if objects and waapi_utils.select_objects_in_wwise(objects):
        return f"已在 Wwise 中选中 {len(objects)} 个对象"
    return "在 Wwise 中选中对象失败"


def _result_file_path(raw_path) -> str:
    # 只允许读取本次任务落盘目录内的文件
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise AiToolError("缺少 result_file 参数（工具结果里返回的文件路径）")
    if not _result_dir:
        raise AiToolError("当前没有可读的结果文件目录")
    base = os.path.realpath(_result_dir)
    resolved = os.path.realpath(raw_path)
    if os.path.commonpath([resolved, base]) != base:
        raise AiToolError("result_file 只能指向本次任务生成的结果文件")
    if not os.path.isfile(resolved):
        raise AiToolError(f"结果文件不存在或已被清理：{raw_path}")
    return resolved


def _load_result_items(path: str) -> list:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "objects", "data", "results", "matched_objects", "groups"):
            if isinstance(data.get(key), list):
                return data[key]
        for item in data.values():
            if isinstance(item, list):
                return item
    return []


def _result_page(items: list, offset: int, limit: int, fields: list) -> dict:
    page = {
        "total": len(items),
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < len(items),
        "next_offset": offset + limit,
        "items": items[offset : offset + limit],
    }
    if fields:
        page["fields"] = fields
    return page


def _read_result_file(args: dict) -> dict:
    path = _result_file_path(args.get("result_file"))
    items = _load_result_items(path)
    try:
        offset = max(int(args.get("offset") or 0), 0)
        limit = int(args.get("limit") or 50)
    except (TypeError, ValueError):
        raise AiToolError("offset / limit 必须是整数")
    limit = max(limit, 1)
    raw_fields = args.get("fields")
    fields = [str(name) for name in raw_fields if str(name).strip()] if isinstance(raw_fields, list) else []
    if fields:
        # 只保留关心的字段，避免整份对象字典把单页预算撑爆
        items = [
            {name: item.get(name) for name in fields} if isinstance(item, dict) else item
            for item in items
        ]
    # 结果文件本身已是大结果的分页视图：这里按模型侧长度预算收缩单页，
    # 保证"读文件"的结果不会再被落盘一次（否则模型始终读不到内容）
    while limit > 1:
        page = _result_page(items, offset, limit, fields)
        if len(json.dumps(page, ensure_ascii=False)) <= RESULT_CHAR_LIMIT:
            return page
        limit //= 2
    return _result_page(items, offset, 1, fields)


def _group_result_file(args: dict) -> dict:
    path = _result_file_path(args.get("result_file"))
    group_by = str(args.get("group_by") or "").strip()
    if not group_by:
        raise AiToolError("缺少 group_by 参数（按哪个字段分组，如 root_id / type）")
    items = _load_result_items(path)
    counts: dict = {}
    for item in items:
        key = item.get(group_by) if isinstance(item, dict) else None
        key = str(key) if key not in (None, "") else "(未知)"
        counts[key] = counts.get(key, 0) + 1
    try:
        min_count = int(args.get("min_count") or 0)
    except (TypeError, ValueError):
        min_count = 0
    groups = [{"group": key, "count": count} for key, count in counts.items()]
    matched = (
        sorted((group for group in groups if group["count"] > min_count), key=lambda g: g["count"], reverse=True)
        if min_count > 0
        else []
    )
    return {
        "matched_count": len(matched) if min_count > 0 else None,
        "total_items": len(items),
        "group_by": group_by,
        "min_count": min_count,
        "groups": groups,
        "matched_groups": matched,
    }


TOOL_HANDLERS: dict[str, Callable[[dict], str]] = {
    "rename_case": _rename_case,
    "rename_with_acronym": _rename_with_acronym,
    "rename_object": _rename_object,
    "remove_name_prefix": lambda args: _remove_prefix_or_suffix(args),
    "remove_name_suffix": lambda args: _remove_prefix_or_suffix(args),
    "set_notes": _set_notes,
    "set_inclusion": _set_inclusion,
    "create_parent": _create_parent,
    "convert_type": _convert_type,
    "split_underscore_to_folder": _split_underscore_to_folder,
    "update_notes_and_color": _update_notes_and_color,
    "create_play_event": _create_play_event,
    "delete_objects": _delete_objects,
    "set_table_objects": _set_table_objects,
    "read_result_file": _read_result_file,
    "group_result_file": _group_result_file,
    "gui_get_wwise_selection": _gui_get_wwise_selection,
    "gui_find_children": _gui_find_children,
    "gui_find_parent": _gui_find_parent,
    "gui_set_filter": _gui_set_filter,
    "gui_open_window": _gui_open_window,
    "gui_list_actions": _gui_list_actions,
    "gui_run_action": _gui_run_action,
    "select_objects_in_wwise": _select_in_wwise,
}


def _object_ids_schema(description: str, required: bool = True) -> dict:
    # object_ids 数组参数的公共 JSON Schema
    return {
        "type": "object",
        "properties": {
            "object_ids": {
                "type": "array",
                "items": {"type": "string", "description": "Wwise 对象 GUID（来自表格上下文）"},
                "description": description,
            }
        },
        "required": ["object_ids"] if required else [],
    }


def build_tool_schemas() -> list[dict]:
    # 供 chat/completions 的 tools 参数使用（function calling 格式）
    def function_schema(name: str, description: str, parameters: dict) -> dict:
        return {"type": "function", "function": {"name": name, "description": description, "parameters": parameters}}

    # 先注册表（libraries/tool_registry.py，AI/MCP/手动三方共用），再拼接仍在过渡期的本地工具
    # 脚本执行默认关闭（IDE 调试器下可能不稳定），开关在设置窗口的 AI 助手页
    script_enabled = user_config.get_ai_enable_script_tool()
    schemas = [
        spec.to_openai_schema()
        for spec in tool_registry.list_tools()
        if spec.name != "run_wwise_script" or script_enabled
    ]
    schemas.extend([
        function_schema(
            "rename_case",
            "批量把对象名称改为全小写 / Title Case / 全大写",
            {
                "type": "object",
                "properties": {
                    "object_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要重命名的对象 id",
                    },
                    "case": {"type": "string", "enum": ["lower", "title", "upper"], "description": "目标大小写规则"},
                },
                "required": ["object_ids", "case"],
            },
        ),
        function_schema(
            "rename_with_acronym",
            "按工程约定把对象名称前缀替换为类型缩写",
            _object_ids_schema("要重命名的对象 id"),
        ),
        function_schema(
            "rename_object",
            "把单个对象重命名为指定名称",
            {
                "type": "object",
                "properties": {
                    "object_id": {"type": "string", "description": "Wwise 对象 GUID"},
                    "new_name": {"type": "string", "description": "新名称"},
                },
                "required": ["object_id", "new_name"],
            },
        ),
        function_schema(
            "remove_name_prefix",
            "去除对象名称开头第一个下划线之前的分段",
            _object_ids_schema("要去除前缀的对象 id"),
        ),
        function_schema(
            "remove_name_suffix",
            "去除对象名称末尾最后一个下划线之后的分段",
            _object_ids_schema("要去除后缀的对象 id"),
        ),
        function_schema(
            "set_notes",
            "写入单个对象的备注（Notes）文本",
            {
                "type": "object",
                "properties": {
                    "object_id": {"type": "string", "description": "Wwise 对象 GUID"},
                    "notes": {"type": "string", "description": "新的备注内容"},
                },
                "required": ["object_id", "notes"],
            },
        ),
        function_schema(
            "set_inclusion",
            "批量启用或停用对象（Inclusion）",
            {
                "type": "object",
                "properties": {
                    "object_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要切换启用的对象 id",
                    },
                    "included": {"type": "boolean", "description": "True 启用，False 停用"},
                },
                "required": ["object_ids", "included"],
            },
        ),
        function_schema(
            "create_parent",
            "在单个对象的当前层级插入一层指定类型的父级对象并移入，返回新父级信息",
            {
                "type": "object",
                "properties": {
                    "object_id": {"type": "string", "description": "Wwise 对象 GUID"},
                    "target_type": {
                        "type": "string",
                        "enum": _WRAPPER_TYPE_NAMES,
                        "description": "要创建的父级类型",
                    },
                },
                "required": ["object_id", "target_type"],
            },
        ),
        function_schema(
            "convert_type",
            "把单个对象转换为其他类型（复制子级、迁移引用；转换后原对象 id 会变化）",
            {
                "type": "object",
                "properties": {
                    "object_id": {"type": "string", "description": "Wwise 对象 GUID"},
                    "target_type": {
                        "type": "string",
                        "enum": _WRAPPER_TYPE_NAMES,
                        "description": "目标类型",
                    },
                },
                "required": ["object_id", "target_type"],
            },
        ),
        function_schema(
            "split_underscore_to_folder",
            "按下划线把对象名称第一段作为文件夹并移入",
            _object_ids_schema("要拆分移动的对象 id"),
        ),
        function_schema(
            "update_notes_and_color",
            "按工程颜色约定更新对象的备注与颜色",
            _object_ids_schema("要更新备注与颜色的对象 id"),
        ),
        function_schema(
            "create_play_event",
            "为对象创建或更新引用它的 Play Event",
            _object_ids_schema("要创建 Play Event 的对象 id"),
        ),
        function_schema(
            "delete_objects",
            "删除对象（危险：Wwise 中直接删除，无法通过本工具恢复；仅在用户明确要求时使用，且必须 confirmed=true）",
            {
                "type": "object",
                "properties": {
                    "object_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要删除的对象 id",
                    },
                    "confirmed": {"type": "boolean", "description": "用户明确确认删除后传 true"},
                },
                "required": ["object_ids", "confirmed"],
            },
        ),
        function_schema(
            "select_objects_in_wwise",
            "在 Wwise 工程浏览器中选中并查看对象",
            _object_ids_schema("要在 Wwise 中选中的对象 id"),
        ),
        function_schema(
            "set_table_objects",
            "把对象发送到主窗口表格：默认**替换**表格当前内容，append=true 时改为追加。用户说“把结果发送到表格 / 放到表格里 / 替换表格”时用",
            {
                "type": "object",
                "properties": {
                    "object_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要发送到表格的对象 id",
                    },
                    "append": {
                        "type": "boolean",
                        "description": "默认 false=替换表格内容；true=追加到现有内容",
                    },
                },
                "required": ["object_ids"],
            },
        ),
        function_schema(
            "read_result_file",
            "分页读取工具结果落盘文件（当工具返回 result_file 时使用）。offset/limit 控制分页，返回 total/has_more/next_offset/items；fields 可只取关心的字段（如 [\"id\",\"name\"]）让单页装下更多条目。只求计数/分组/求和时不要读文件，直接用 count_tool_items / group_tool_items / aggregate_tool_chain",
            {
                "type": "object",
                "properties": {
                    "result_file": {"type": "string", "description": "工具结果里返回的 result_file 路径"},
                    "offset": {"type": "integer", "description": "起始下标，默认 0"},
                    "limit": {"type": "integer", "description": "本次读取条数，默认 50"},
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "可选：只返回这些字段，如 [\"id\",\"name\"]；条目字段多时可显著提高单页容量",
                    },
                },
                "required": ["result_file"],
            },
        ),
        function_schema(
            "group_result_file",
            "对工具结果落盘文件按字段分组统计（如按 root_id 统计每个对象下有多少条），min_count 可只保留数量大于该值的分组并返回 matched_count",
            {
                "type": "object",
                "properties": {
                    "result_file": {"type": "string", "description": "工具结果里返回的 result_file 路径"},
                    "group_by": {"type": "string", "description": "分组字段，如 root_id / parent_id / type"},
                    "min_count": {"type": "integer", "description": "可选：只保留数量大于该值的分组"},
                },
                "required": ["result_file", "group_by"],
            },
        ),
        function_schema(
            "gui_get_wwise_selection",
            "软件界面操作：等同点击「获取Wwise选中对象」按钮，把 Wwise 当前选中的对象取到表格（无需参数）",
            {"type": "object", "properties": {}},
        ),
        function_schema(
            "gui_find_children",
            "软件界面操作：等同点击「查找下级」按钮（可按递归/保留原始层级选项），用表格内对象的下级替换表格内容",
            {
                "type": "object",
                "properties": {
                    "recursive": {"type": "boolean", "default": True, "description": "是否递归查找全部下级"},
                    "keep_self": {"type": "boolean", "default": False, "description": "是否保留原始对象"},
                },
            },
        ),
        function_schema(
            "gui_find_parent",
            "软件界面操作：等同点击「查找上级」按钮（可按递归/保留原始层级选项），用上级替换表格内容",
            {
                "type": "object",
                "properties": {
                    "recursive": {"type": "boolean", "default": True, "description": "是否递归查到最上层"},
                    "keep_self": {"type": "boolean", "default": False, "description": "是否保留原始对象"},
                },
            },
        ),
        function_schema(
            "gui_set_filter",
            "软件界面操作：等同在表格筛选区输入关键字/选择类型/勾选选项并应用筛选",
            {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "筛选关键字（支持 ; 多条件、-排除、=全字匹配）"},
                    "object_type": {"type": "string", "description": "对象类型筛选，如 Sound / Event；留空为全部类型"},
                    "only_included": {"type": "boolean", "default": False, "description": "仅显示启用对象"},
                    "case_sensitive": {"type": "boolean", "default": False, "description": "区分大小写"},
                },
            },
        ),
        function_schema(
            "gui_open_window",
            "软件界面操作：打开软件里的功能窗口（等同点菜单/按钮）。可用值：property_query(属性查询) / multi_editor(多项编辑器) / batch_rename(批量重命名) / table_rename(读表重命名) / audio_silence_trim(裁剪静音) / bank_matrix(Bank分配矩阵) / project_validation(工程检查) / unity_asset(UnityAsset管理) / settings(设置)",
            {
                "type": "object",
                "properties": {
                    "window": {"type": "string", "description": "要打开的窗口标识（见工具说明）"},
                },
                "required": ["window"],
            },
        ),
        function_schema(
            "gui_run_action",
            "软件界面操作：触发菜单里的某个 action（按 objectName，如 actTemplateReplace / actRenameByDataTable）。不确定有哪些动作时先用 gui_list_actions 查；仅当用户明确要求执行该菜单功能时使用，需 confirmed=true",
            {
                "type": "object",
                "properties": {
                    "action_name": {"type": "string", "description": "菜单 action 的 objectName"},
                    "confirmed": {"type": "boolean", "description": "用户已明确要求执行时传 true"},
                },
                "required": ["action_name", "confirmed"],
            },
        ),
        function_schema(
            "gui_list_actions",
            "软件界面操作：列出软件里的菜单动作（objectName / 名称 / 是否可用 / 使用说明），可用 keyword 过滤。用于在不确定时先发现能做什么，再用 gui_run_action 触发",
            {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "可选关键字，按动作名称或 objectName 过滤"},
                },
            },
        ),
    ])
    # 注册表已是唯一权威；本地遗留工具仅保留注册表未收录的名字，避免同名重复下发
    seen: set[str] = set()
    unique_schemas = []
    for schema in schemas:
        name = schema["function"]["name"]
        if name in seen:
            continue
        seen.add(name)
        unique_schemas.append(schema)
    return unique_schemas


def load_prompt_template() -> str:
    # 读取提示词模板（开发环境读取仓库根目录；打包后读取 _MEIPASS/_internal 内的资源）
    resource_path = path_utils.get_resource_path(PROMPT_FILE_NAME)
    try:
        with open(resource_path, encoding="utf-8") as f:
            template = f.read().strip()
        if template:
            return template
    except OSError as e:
        Logger().error(f"读取 AI 提示词模板失败：{resource_path}（{e}），使用内置兜底提示词")
    return _FALLBACK_TEMPLATE


def build_system_prompt(objects: list[WwiseObject], max_context_objects: int = 300) -> str:
    # 系统提示词 = 模板文件全文 + 本次表格对象清单（动态生成）
    total = len(objects)
    listed = objects[:max_context_objects]
    object_lines = []
    for obj in listed:
        if obj.wwise_dict:
            object_lines.append(json.dumps(
                {"id": obj.id, "name": obj.name, "type": obj.type.value, "path": obj.path},
                ensure_ascii=False,
            ))
    prompt = load_prompt_template()
    prompt += f"\n\n## 当前表格对象\n本次表格中共有 {total} 个对象"
    if total > len(listed):
        prompt += (
            f"，出于上下文长度限制仅列出前 {len(listed)} 个；"
            "调用工具时可传 object_ids=[\"@table\"] 指代全部表格对象，无需罗列完整 id"
        )
    else:
        prompt += "；调用工具时也可传 object_ids=[\"@table\"] 指代全部表格对象"
    prompt += "：\n" + json.dumps([json.loads(line) for line in object_lines], ensure_ascii=False)
    return prompt


def clean_display_content(content: str) -> str:
    # 去掉模型内部推理块，只保留面向用户的最终回答
    return _THINK_BLOCK_RE.sub("", content or "").strip()


def _extract_think(content: str) -> str:
    # 提取模型思考块（部分模型写在 <think>…</think> 里），用于日志展示
    match = re.search(r"<think>(.*?)</think>", content or "", re.DOTALL)
    return match.group(1).strip() if match else ""


def _shorten_string(text: str) -> str:
    # 路径类字段很长时保留首尾，避免单条就把字符预算吃光
    if len(text) <= MODEL_STRING_LIMIT:
        return text
    head = MODEL_STRING_LIMIT // 2
    tail = MODEL_STRING_LIMIT - head
    return f"{text[:head]}…{text[-tail:]}"


def _shrink_for_model(value, item_cap: int):
    if isinstance(value, dict):
        shrunk = {key: _shrink_for_model(item, item_cap) for key, item in value.items()}
        # 标量字段（count/total/matched_count 等）排到前面，确保被收敛时仍然可见
        scalars = {key: item for key, item in shrunk.items() if not isinstance(item, (list, dict))}
        others = {key: item for key, item in shrunk.items() if isinstance(item, (list, dict))}
        return {**scalars, **others}
    if isinstance(value, list):
        if len(value) > item_cap:
            return {
                "items": [_shrink_for_model(item, item_cap) for item in value[:item_cap]],
                "total": len(value),
                "truncated": True,
                "omitted": len(value) - item_cap,
            }
        return [_shrink_for_model(item, item_cap) for item in value]
    if isinstance(value, str):
        return _shorten_string(value)
    return value


def set_result_dir(path: str | None) -> None:
    # 指定本次任务的大结果落盘目录；None 时退回"就地收缩"模式（如 MCP 调用）
    global _result_dir, _result_counter
    _result_dir = path
    _result_counter = 0


def _cleanup_stale_result_dirs(max_age_seconds: int = 6 * 3600) -> None:
    # 清理异常退出遗留的旧结果目录（正常结束时会在任务尾部删除）
    base = tempfile.gettempdir()
    cutoff = time.time() - max_age_seconds
    try:
        names = os.listdir(base)
    except OSError:
        return
    for name in names:
        if not name.startswith(_RESULT_DIR_PREFIX):
            continue
        path = os.path.join(base, name)
        try:
            if os.path.isdir(path) and os.path.getmtime(path) < cutoff:
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            continue


def _next_result_path() -> str:
    global _result_counter
    _result_counter += 1
    return os.path.join(_result_dir, f"result_{_result_counter}.json")


def _offload_result(value) -> str | None:
    # 完整结果写入临时文件，返回路径；失败返回 None（调用方退回就地收缩）
    if not _result_dir:
        return None
    try:
        os.makedirs(_result_dir, exist_ok=True)
        path = _next_result_path()
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False)
    except OSError as e:
        Logger().warning(f"AI 结果落盘失败，将就地缩减：{e}")
        return None
    return path


def _result_summary(value) -> dict:
    summary = {}
    if isinstance(value, dict):
        for key in ("count", "total", "total_items", "matched_count", "scanned", "truncated"):
            item = value.get(key)
            if item is not None and not isinstance(item, (list, dict)):
                summary[key] = item
    return summary


def _offload_envelope(value, path: str) -> dict:
    items = value.get("items") if isinstance(value, dict) else value
    preview = []
    if isinstance(items, list):
        preview = [_shrink_for_model(item, MODEL_LIST_ITEM_CAP) for item in items[:3]]
    return {
        "result_file": path,
        "offloaded": True,
        **_result_summary(value),
        "preview": preview,
        "hint": (
            "结果较大，已完整写入 result_file：用 read_result_file 分页读取，"
            "或用 group_result_file 分组统计；任务结束后文件会自动删除"
        ),
    }


def _serialize_for_model(value) -> str:
    text = json.dumps(_shrink_for_model(value, MODEL_LIST_ITEM_CAP), ensure_ascii=False)
    if len(text) <= RESULT_CHAR_LIMIT:
        return text
    path = _offload_result(value)
    if path:
        return json.dumps(_offload_envelope(value, path), ensure_ascii=False)
    # 无法落盘时退回逐级收缩：10/3/0 条
    for item_cap in (10, 3, 0):
        text = json.dumps(_shrink_for_model(value, item_cap), ensure_ascii=False)
        if len(text) <= RESULT_CHAR_LIMIT:
            return text
    return json.dumps(_shrink_for_model(value, 0), ensure_ascii=False)[: RESULT_CHAR_LIMIT - 20] + "…（已截断）"




def _execute_tool_call(name: str, raw_arguments: str, executed: list[dict]) -> str:
    # 执行一次工具调用并返回回传给模型的结果文本
    registry_spec = tool_registry.get_tool(name)
    if registry_spec is None and name not in TOOL_HANDLERS:
        return f"未知工具：{name}"
    try:
        arguments = json.loads(raw_arguments) if raw_arguments else {}
        if not isinstance(arguments, dict):
            arguments = {}
    except ValueError:
        arguments = {}
    if name == "run_wwise_script" and not user_config.get_ai_enable_script_tool():
        return "脚本执行已在「设置 → AI 助手」中关闭；请改用现成工具（如 find_objects_by_property / aggregate_tool_chain）"
    arguments, _expanded_count = _expand_special_ids(arguments)
    try:
        if registry_spec is not None:
            # 注册表工具返回 JSON 兼容的结构化结果，统一转成文本回传给模型
            value = tool_registry.execute_tool(name, arguments)
            if isinstance(value, str):
                result_text = value
            elif name in NO_OFFLOAD_TOOLS:
                # 分页/元工具的结果不再落盘，宁可收缩也不能让模型读不到
                result_text = json.dumps(_shrink_for_model(value, MODEL_LIST_ITEM_CAP), ensure_ascii=False)
            else:
                result_text = _serialize_for_model(value)
        else:
            result_text = TOOL_HANDLERS[name](arguments)
            if not isinstance(result_text, str):
                result_text = _serialize_for_model(result_text)
    except tool_registry.ExecutionInterrupted as e:
        # 用户中止：向上抛出，由 agent loop 结束本次任务
        raise AIAgentStopped(str(e)) from e
    except Exception as e:
        result_text = f"工具执行失败：{e}"
        if isinstance(e, TypeError) and registry_spec is not None:
            required = registry_spec.parameters.get("required") or []
            if required:
                result_text += f"；该工具必填参数：{', '.join(required)}（请放在本次调用的参数对象里）"
    executed.append({"name": name, "arguments": arguments, "result": result_text[:200]})
    if len(result_text) > RESULT_CHAR_LIMIT:
        result_text = result_text[:RESULT_CHAR_LIMIT] + "…（结果过长，已截断）"
    return result_text


def _is_mutating_tool(name: str) -> bool:
    # 本地遗留工具名与注册表 spec.mutating 二选一命中即视为会改动工程
    if name in MUTATING_TOOL_NAMES:
        return True
    spec = tool_registry.get_tool(name)
    return bool(spec and spec.mutating)


# 追问上下文：AI 以提问收尾时保留本轮对话，用户回答后接着执行；
# 其它情况（正常总结/中止）下一轮重新开始，避免旧结论影响后续无关指令
_CONVERSATION_HISTORY_CAP = 60
_conversation: dict | None = None


def reset_conversation() -> None:
    global _conversation
    _conversation = None


def _looks_like_question(text: str) -> bool:
    return "？" in (text or "") or "?" in (text or "")


def _conversation_seed(objects: list, prompt: str, system_prompt: str) -> tuple:
    # 表格对象没变才沿用历史；返回 (表格对象签名, 本轮消息列表)
    signature = tuple(sorted(obj.id for obj in objects))
    resumed = _conversation if (_conversation and _conversation.get("signature") == signature) else None
    messages = [{"role": "system", "content": system_prompt}]
    if resumed:
        messages.extend(resumed["messages"])
    messages.append({"role": "user", "content": prompt})
    return signature, messages


def _store_conversation(signature: tuple, messages: list, content: str) -> None:
    global _conversation
    if content and _looks_like_question(content):
        history = list(messages[1:]) + [{"role": "assistant", "content": content}]
        _conversation = {"signature": signature, "messages": history[-_CONVERSATION_HISTORY_CAP:]}
    else:
        _conversation = None


def _created_objects_for_table(created: list) -> list:
    # Folder/WorkUnit 只是为放对象搭出来的脚手架，不算"产出的对象"
    scaffold = {WwiseObjectType.Folder, WwiseObjectType.WorkUnit}
    unique: dict = {}
    for obj in created:
        if obj.type not in scaffold:
            unique[obj.id] = obj
    return list(unique.values())


def _send_created_objects_to_table(result: "AIAssistantResult", log) -> None:
    # 任务结束时把本次新建的对象发到表格，方便用户直接查看/继续处理
    created = _created_objects_for_table(waapi_utils.take_recorded_objects())
    if not created:
        return
    if any(item.get("name") == "set_table_objects" for item in result.executed_tools):
        log(f"本次任务新建了 {len(created)} 个对象（表格内容已由 AI 指定，未覆盖）")
        return
    if _table_sink is None:
        log(f"本次任务新建了 {len(created)} 个对象")
        return
    _table_sink([obj.id for obj in created], False)
    log(f"本次任务新建的 {len(created)} 个对象已发送到表格")


def run_assistant(
    prompt: str,
    objects: list[WwiseObject],
    *,
    on_log: Callable[[str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> AIAssistantResult:
    """与模型对话直到得到最终回复；期间自动执行模型请求的工具调用。"""
    # 连接信息：代理模式 / 官方 API 模式（含 Anthropic 原生协议）
    connection = ai_utils.resolve_connection(
        user_config.get_ai_mode(),
        user_config.get_ai_proxy_url(),
        user_config.get_ai_provider(),
        user_config.get_ai_base_url(),
    )
    model = user_config.get_ai_model()
    api_key = user_config.get_ai_api_key()
    max_turns = user_config.get_ai_max_turns()
    max_context_objects = user_config.get_ai_max_context_objects()

    system_prompt = build_system_prompt(objects, max_context_objects)
    conversation_signature, messages = _conversation_seed(objects, prompt, system_prompt)
    schemas = build_tool_schemas()
    result = AIAssistantResult()

    def log(text: str):
        if on_log:
            on_log(text)

    def raise_if_stopped():
        if should_stop and should_stop():
            raise AIAgentStopped("已按用户要求中止 AI 处理")

    def chat_interruptible():
        # HTTP 请求在守护线程中执行，主循环可随时因中止请求退出，不等待网络超时
        holder: dict = {}
        stop_poll = 0.1

        def request():
            try:
                holder["data"] = ai_utils.chat_completion(
                    connection,
                    messages,
                    tools=schemas,
                    model=model,
                    api_key=api_key,
                )
            except Exception as e:
                holder["error"] = e

        thread = threading.Thread(target=request, daemon=True)
        thread.start()
        while thread.is_alive():
            raise_if_stopped()
            time.sleep(stop_poll)
        if "error" in holder:
            raise holder["error"]
        return holder.get("data")

    # agent 任务级撤销组：只包住本次任务产生的写操作，异常/中止/超时也保证收尾
    undo_label = f"AI 任务：{' '.join(prompt.split())[:40]}"
    _undo_state = {"open": False}

    def _ensure_undo_open():
        if _undo_state["open"]:
            return
        if waapi_utils.begin_undo_group(undo_label):
            _undo_state["open"] = True
            log(f"已开启撤销组「{undo_label}」：本次任务的全部修改可一次性撤销")
        else:
            log("警告：未能开启撤销组，本次修改将无法一键撤销")

    def _close_undo_group():
        if _undo_state.pop("open", False):
            waapi_utils.end_undo_group(undo_label)
            log("已结束撤销组：可在 Wwise 用「撤销」一次性回退本次任务的全部修改")

    log(f"已加载 AI 提示词模板：{PROMPT_FILE_NAME}（{len(system_prompt)} 字符）")
    log(
        f"已发送请求到 AI（{connection['mode']}/{connection['protocol']}）{connection['chat_url']}，"
        f"表格对象 {len(objects)} 个"
    )
    # 脚本执行期间同样响应中止请求
    tool_registry.set_execution_guard(lambda: bool(should_stop and should_stop()))
    set_table_context([obj.id for obj in objects])
    # 记录本次任务新建的对象，任务结束时把它们发送到表格
    waapi_utils.start_object_recording()
    _cleanup_stale_result_dirs()
    try:
        result_dir = tempfile.mkdtemp(prefix=_RESULT_DIR_PREFIX)
    except OSError:
        result_dir = None
    set_result_dir(result_dir)
    try:
        for turn in range(1, max_turns + 1):
            raise_if_stopped()
            data = chat_interruptible()
            message = data.get("message") if isinstance(data, dict) else None
            if not isinstance(message, dict):
                raise ai_utils.AIChatError(f"AI 服务响应缺少 message 字段：{str(data)[:300]}")

            assistant_content = message.get("content") or ""
            think_text = _extract_think(assistant_content)
            if think_text:
                log(f"AI 思考（第 {turn} 轮）：{think_text}")

            tool_calls = message.get("tool_calls")
            if tool_calls:
                result.turn_count = turn
                result.tool_call_count += len(tool_calls)
                assistant_message = {
                    "role": "assistant",
                    "content": assistant_content,
                    "tool_calls": tool_calls,
                }
                messages.append(assistant_message)
                for index, call in enumerate(tool_calls):
                    function = call.get("function") or {}
                    name = function.get("name") or ""
                    arguments = function.get("arguments") or ""
                    if _is_mutating_tool(name):
                        _ensure_undo_open()
                    tool_result = _execute_tool_call(name, arguments, result.executed_tools)
                    if _is_mutating_tool(name):
                        result.mutated = True
                    log(
                        f"第 {turn} 轮调用工具 {name}（参数：{' '.join(str(arguments).split())[:120]}"
                        f"；返回：{' '.join(tool_result.split())[:120]}）"
                    )
                    call_id = call.get("id") or f"tool_call_{turn}_{index}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": tool_result,
                    })
                # agent loop：提示模型根据结果继续推进，直到目标完成
                messages.append({
                    "role": "user",
                    "content": (
                        "请根据上面各工具的结果继续推进这个目标：如果还有需要查询/处理的步骤就继续调用工具，"
                        "一次可以并行请求多个工具；只有确认所有步骤都已完成、结论已核对后，才给出面向用户的中文最终总结。"
                    ),
                })
                log(f"第 {turn} 轮工具执行完成，继续推进…")
                continue

            raise_if_stopped()
            result.content = assistant_content.strip()
            result.turn_count = turn
            log(f"对话完成（共 {result.turn_count} 轮）")
            return result

    finally:
        _send_created_objects_to_table(result, log)
        _store_conversation(conversation_signature, messages, result.content)
        tool_registry.set_execution_guard(None)
        set_table_context([])
        set_table_sink(None)
        set_result_dir(None)
        if result_dir:
            shutil.rmtree(result_dir, ignore_errors=True)
        _close_undo_group()
    result.content = f"达到最大对话轮数（{max_turns}）仍未得到最终回复，已停止；可在 user_config.json 的 ai.max_turns 中调大。"
    log(result.content)
    return result
