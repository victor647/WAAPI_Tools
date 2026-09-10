# AI 客户端：支持 OpenAI 兼容协议（代理/多数厂商官方）与 Anthropic 官方协议。
# 仅使用标准库；连接参数由调用方从 user_config 读取后传入，保持可测试。
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

# 未配置地址时的默认端点（官方 OpenAI 兼容端点）
DEFAULT_BASE_URL = "https://api.openai.com"

_ANTHROPIC_VERSION = "2023-06-01"
# Anthropic Messages API 必填 max_tokens
ANTHROPIC_MAX_TOKENS = 4096

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)

# 官方 API 模式可选的服务提供方；带 chat_path/models_path 时按该路径拼接
PROVIDERS: dict[str, dict] = {
    "openai": {"label": "OpenAI", "base_url": "https://api.openai.com", "protocol": "openai"},
    "deepseek": {"label": "DeepSeek", "base_url": "https://api.deepseek.com", "protocol": "openai"},
    "qwen": {"label": "通义千问（兼容模式）", "base_url": "https://dashscope.aliyuncs.com/compatible-mode", "protocol": "openai"},
    "moonshot": {"label": "Kimi / Moonshot", "base_url": "https://api.moonshot.cn", "protocol": "openai"},
    "zhipu": {
        "label": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "protocol": "openai",
        "chat_path": "/chat/completions",
        "models_path": "/models",
    },
    "gemini": {"label": "Google Gemini（兼容端点）", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "protocol": "openai"},
    "anthropic": {"label": "Anthropic Claude", "base_url": "https://api.anthropic.com", "protocol": "anthropic"},
    "custom": {"label": "自定义（OpenAI 兼容）", "base_url": "", "protocol": "openai"},
}

AI_MODES = ("proxy", "official")


class AIChatError(RuntimeError):
    pass


def resolve_base_url(base_url: str) -> str:
    # 地址留空时回退默认端点，便于“只填 API Key”直连官方
    return (base_url or "").strip().rstrip("/") or DEFAULT_BASE_URL


def build_chat_completions_url(base_url: str) -> str:
    # 兼容三种填法：根地址、以 /v1 结尾、直接粘贴完整 chat/completions 端点
    base = resolve_base_url(base_url)
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def build_models_url(base_url: str) -> str:
    base = resolve_base_url(base_url)
    if base.endswith("/chat/completions"):
        base = base[: -len("/chat/completions")]
    if base.endswith("/v1"):
        return base + "/models"
    return base + "/v1/models"


def resolve_connection(mode: str, proxy_url: str, provider: str, custom_base_url: str) -> dict:
    # 按模式解析实际连接信息：{mode, provider, protocol, base_url, chat_url, models_url}
    if mode == "official" and provider and provider != "custom":
        info = PROVIDERS.get(provider)
        if info:
            base_url = info["base_url"]
            protocol = info.get("protocol", "openai")
            if protocol == "anthropic":
                chat_url = base_url + "/v1/messages"
                models_url = base_url + "/v1/models"
            else:
                chat_url = base_url + info["chat_path"] if info.get("chat_path") else build_chat_completions_url(base_url)
                models_url = base_url + info["models_path"] if info.get("models_path") else build_models_url(base_url)
            return {
                "mode": "official",
                "provider": provider,
                "protocol": protocol,
                "base_url": base_url,
                "chat_url": chat_url,
                "models_url": models_url,
            }
    # 代理模式，或官方模式下的自定义地址
    source = (custom_base_url or "") if mode == "official" else (proxy_url or "")
    base_url = resolve_base_url(source)
    return {
        "mode": mode,
        "provider": provider,
        "protocol": "openai",
        "base_url": base_url,
        "chat_url": build_chat_completions_url(base_url),
        "models_url": build_models_url(base_url),
    }


def _build_headers(protocol: str, api_key: str) -> dict:
    if protocol == "anthropic":
        headers = {"Content-Type": "application/json", "anthropic-version": _ANTHROPIC_VERSION}
        if api_key:
            headers["x-api-key"] = api_key
        return headers
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _post_json(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        snippet = ""
        try:
            snippet = e.read().decode("utf-8", "replace")[:500]
        except OSError:
            pass
        raise AIChatError(f"AI 服务返回 HTTP {e.code}: {snippet}") from e
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        raise AIChatError(f"无法连接 AI 服务 {url}：{reason}") from e
    except TimeoutError as e:
        raise AIChatError(f"AI 请求超时（超过 {timeout:g} 秒无响应）") from e
    try:
        return json.loads(raw)
    except ValueError as e:
        raise AIChatError(f"AI 服务返回了无法解析的内容：{raw[:200]}") from e


def _to_anthropic_tools(tools: list[dict] | None) -> list[dict]:
    converted = []
    for tool in tools or []:
        function = tool.get("function") or {}
        parameters = function.get("parameters") or {"type": "object", "properties": {}}
        converted.append({
            "name": function.get("name") or "",
            "description": function.get("description") or "",
            "input_schema": parameters,
        })
    return converted


def _to_anthropic_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    # OpenAI 格式消息 → Anthropic messages；连续的 tool 结果合并进同一条 user 消息
    system_parts: list[str] = []
    converted: list[dict] = []
    pending_tool_results: list[dict] = []

    def flush_tool_results():
        if pending_tool_results:
            converted.append({"role": "user", "content": list(pending_tool_results)})
            pending_tool_results.clear()

    for message in messages:
        role = message.get("role")
        if role == "system":
            system_parts.append(str(message.get("content") or ""))
            continue
        if role == "user":
            flush_tool_results()
            converted.append({"role": "user", "content": [{"type": "text", "text": str(message.get("content") or "")}]})
        elif role == "assistant":
            blocks = []
            text = _THINK_BLOCK_RE.sub("", str(message.get("content") or "")).strip()
            if text:
                blocks.append({"type": "text", "text": text})
            for call in message.get("tool_calls") or []:
                function = call.get("function") or {}
                try:
                    arguments = json.loads(function.get("arguments") or "{}")
                except ValueError:
                    arguments = {}
                blocks.append({
                    "type": "tool_use",
                    "id": call.get("id") or "",
                    "name": function.get("name") or "",
                    "input": arguments if isinstance(arguments, dict) else {},
                })
            flush_tool_results()
            converted.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            pending_tool_results.append({
                "type": "tool_result",
                "tool_use_id": message.get("tool_call_id") or "",
                "content": str(message.get("content") or ""),
            })
    flush_tool_results()
    return "\n".join(part for part in system_parts if part), converted


def _parse_anthropic_message(data: dict) -> dict:
    text_parts: list[str] = []
    tool_calls: list[dict] = []
    for block in data.get("content") or []:
        block_type = block.get("type")
        if block_type == "text":
            text_parts.append(block.get("text") or "")
        elif block_type == "thinking":
            text_parts.append(f"<think>{block.get('thinking') or ''}</think>")
        elif block_type == "tool_use":
            tool_calls.append({
                "id": block.get("id") or "",
                "type": "function",
                "function": {
                    "name": block.get("name") or "",
                    "arguments": json.dumps(block.get("input") or {}, ensure_ascii=False),
                },
            })
    message = {"role": "assistant", "content": "\n".join(part for part in text_parts if part)}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return message


def chat_completion(
    connection: dict,
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    model: str = "",
    api_key: str = "",
    timeout: float = 300.0,
) -> dict:
    """发送一次对话请求，统一返回 {"message": {role, content, tool_calls?}}。"""
    protocol = connection.get("protocol", "openai")
    headers = _build_headers(protocol, api_key)
    if protocol == "anthropic":
        if not model:
            raise AIChatError("Anthropic 官方模式需要在设置里指定模型名")
        system_text, anthropic_messages = _to_anthropic_messages(messages)
        payload: dict = {
            "model": model,
            "max_tokens": ANTHROPIC_MAX_TOKENS,
            "messages": anthropic_messages,
        }
        if system_text:
            payload["system"] = system_text
        if tools:
            payload["tools"] = _to_anthropic_tools(tools)
        data = _post_json(connection["chat_url"], payload, headers, timeout)
        return {"message": _parse_anthropic_message(data)}

    payload = {"messages": messages}
    if model:
        payload["model"] = model
    if tools:
        payload["tools"] = tools
        payload.setdefault("tool_choice", "auto")
    data = _post_json(connection["chat_url"], payload, headers, timeout)
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as e:
        raise AIChatError(f"AI 服务响应缺少 choices/message 字段：{str(data)[:300]}") from e
    return {"message": message}


def list_models(connection: dict, api_key: str = "", timeout: float = 10.0) -> list[str]:
    """查询可用模型 id 列表（OpenAI /v1/models 或 Anthropic /v1/models）。"""
    protocol = connection.get("protocol", "openai")
    headers = _build_headers(protocol, api_key)
    headers.pop("Content-Type", None)
    request = urllib.request.Request(connection["models_url"], headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise AIChatError(f"查询 AI 模型列表失败：HTTP {e.code}") from e
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        raise AIChatError(f"无法连接 AI 服务 {connection['models_url']}：{reason}") from e
    except TimeoutError as e:
        raise AIChatError(f"查询 AI 模型列表超时（{timeout:g} 秒）") from e
    try:
        data = json.loads(raw)
    except ValueError as e:
        raise AIChatError(f"AI 服务返回了无法解析的内容：{raw[:200]}") from e
    models = []
    for item in data.get("data") or []:
        model_id = item.get("id") if isinstance(item, dict) else None
        if model_id:
            models.append(str(model_id))
    return models
