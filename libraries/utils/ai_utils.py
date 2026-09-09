# OpenAI 兼容 chat/completions 客户端：软件内的 AI 助手通过本地代理访问大模型。
# 仅使用标准库，避免为 GUI 增加 requests/openai 等额外依赖。
from __future__ import annotations

import json
import urllib.error
import urllib.request

# 代理根地址之后拼接的 OpenAI 兼容端点
CHAT_COMPLETIONS_PATH = "/v1/chat/completions"
MODELS_PATH = "/v1/models"


class AIChatError(RuntimeError):
    pass


def build_chat_completions_url(proxy_url: str) -> str:
    # 统一拼接代理地址与 chat/completions 路径，容忍末尾斜杠
    return proxy_url.rstrip("/") + CHAT_COMPLETIONS_PATH


def list_models(proxy_url: str, api_key: str = "", timeout: float = 10.0) -> list[str]:
    """查询代理支持的模型 id 列表（GET /v1/models）。"""
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        proxy_url.rstrip("/") + MODELS_PATH, headers=headers, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise AIChatError(f"查询 AI 模型列表失败：HTTP {e.code}") from e
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        raise AIChatError(f"无法连接 AI 代理 {proxy_url}：{reason}") from e
    except TimeoutError as e:
        raise AIChatError(f"查询 AI 模型列表超时（{timeout:g} 秒）") from e
    try:
        data = json.loads(raw)
    except ValueError as e:
        raise AIChatError(f"AI 代理返回了无法解析的内容：{raw[:200]}") from e
    models = []
    for item in data.get("data") or []:
        model_id = item.get("id") if isinstance(item, dict) else None
        if model_id:
            models.append(str(model_id))
    return models


def chat_completion(
    proxy_url: str,
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    model: str = "",
    api_key: str = "",
    timeout: float = 300.0,
) -> dict:
    """发送一次 chat/completions 请求并返回解析后的 JSON 响应。"""
    payload: dict = {"messages": messages}
    if model:
        payload["model"] = model
    if tools:
        payload["tools"] = tools
        payload.setdefault("tool_choice", "auto")

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        build_chat_completions_url(proxy_url), data=body, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        snippet = ""
        try:
            snippet = e.read().decode("utf-8", "replace")[:500]
        except OSError:
            pass
        raise AIChatError(f"AI 代理返回 HTTP {e.code}: {snippet}") from e
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        raise AIChatError(f"无法连接 AI 代理 {proxy_url}：{reason}") from e
    except TimeoutError as e:
        raise AIChatError(f"AI 请求超时（超过 {timeout:g} 秒无响应）") from e

    try:
        return json.loads(raw)
    except ValueError as e:
        raise AIChatError(f"AI 代理返回了无法解析的内容：{raw[:200]}") from e
