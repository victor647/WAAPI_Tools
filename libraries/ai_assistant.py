# AI 助手：把「表格中的 Wwise 对象」交给大模型处理。
# - 系统提示词模板见仓库根目录 ai_assistant_prompt.md，动态附加本次表格对象清单；
#   模型以 OpenAI 兼容 function calling 调用下方工具；
# - 工具实现复用 libraries.utils.wwise 下与 GUI 一致的 *_utils 封装，不在本模块直接操作 WAAPIClient；
# - 本模块不依赖 Qt，便于测试；HTTP 请求由 libraries.utils.ai_utils 提供。
from __future__ import annotations

import json
import re
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
RESULT_CHAR_LIMIT = 3000

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
    schemas = [spec.to_openai_schema() for spec in tool_registry.list_tools()]
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
        prompt += f"，出于上下文长度限制仅列出前 {len(listed)} 个（可先筛选缩小表格范围）"
    prompt += "：\n" + json.dumps([json.loads(line) for line in object_lines], ensure_ascii=False)
    return prompt


def clean_display_content(content: str) -> str:
    # 去掉模型内部推理块，只保留面向用户的最终回答
    return _THINK_BLOCK_RE.sub("", content or "").strip()


def _extract_think(content: str) -> str:
    # 提取模型思考块（部分模型写在 <think>…</think> 里），用于日志展示
    match = re.search(r"<think>(.*?)</think>", content or "", re.DOTALL)
    return match.group(1).strip() if match else ""


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
    try:
        if registry_spec is not None:
            # 注册表工具返回 JSON 兼容的结构化结果，统一转成文本回传给模型
            value = tool_registry.execute_tool(name, arguments)
            result_text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        else:
            result_text = TOOL_HANDLERS[name](arguments)
            if not isinstance(result_text, str):
                result_text = str(result_text)
    except Exception as e:
        result_text = f"工具执行失败：{e}"
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


def run_assistant(
    prompt: str,
    objects: list[WwiseObject],
    *,
    on_log: Callable[[str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> AIAssistantResult:
    """与模型对话直到得到最终回复；期间自动执行模型请求的工具调用。"""
    proxy_url = user_config.get_ai_proxy_url()
    model = user_config.get_ai_model()
    api_key = user_config.get_ai_api_key()
    max_turns = user_config.get_ai_max_turns()
    max_context_objects = user_config.get_ai_max_context_objects()

    system_prompt = build_system_prompt(objects, max_context_objects)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
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
                    proxy_url,
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
    log(f"已发送请求到 AI 代理 {proxy_url}，表格对象 {len(objects)} 个")
    try:
        for turn in range(1, max_turns + 1):
            raise_if_stopped()
            data = chat_interruptible()
            try:
                message = data["choices"][0]["message"]
            except (KeyError, IndexError, TypeError) as e:
                raise ai_utils.AIChatError(f"AI 代理响应缺少 choices/message 字段：{str(data)[:300]}") from e

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
                    log(f"第 {turn} 轮调用工具 {name}（返回：{' '.join(tool_result.split())[:120]}）")
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
        _close_undo_group()
    result.content = f"达到最大对话轮数（{max_turns}）仍未得到最终回复，已停止；可在 user_config.json 的 ai.max_turns 中调大。"
    log(result.content)
    return result
