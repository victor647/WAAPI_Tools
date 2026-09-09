# 把 libraries/tool_registry.py 里的中立工具批量注册为 MCP tool：
# 与软件内 AI 助手、手动工具共享同一份「名称/描述/参数/handler」定义，避免各层重复实现。
from __future__ import annotations

from typing import Any

from libraries import tool_registry
from libraries.waapi_client import WAAPIClient
from waapi_mcp.mcp_instance import mcp

# JSON schema 类型 -> python 注解（FastMCP 依据真实函数签名生成自己的 JSON schema）
_ANNOTATION_BY_TYPE = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}


def _annotation_for(prop: dict) -> str:
    type_name = prop.get("type")
    if type_name == "array":
        items = prop.get("items") or {}
        inner = _ANNOTATION_BY_TYPE.get(items.get("type"), "object")
        return f"list[{inner}]"
    return _ANNOTATION_BY_TYPE.get(type_name, "object")


def _build_mcp_function(spec: tool_registry.ToolSpec):
    # 按注册表的 parameters 动态生成带类型注解的真实函数，供 FastMCP 推导工具 schema
    properties = spec.parameters.get("properties", {})
    required = set(spec.parameters.get("required") or [])
    param_defs = []
    for name, prop in properties.items():
        annotation = _annotation_for(prop)
        if name in required:
            param_defs.append(f"{name}: {annotation}")
        else:
            param_defs.append(f"{name}: {annotation} = None")
    signature = ", ".join(param_defs)
    namespace: dict[str, Any] = {
        "_handler": spec.handler,
        "WAAPIClient": WAAPIClient,
    }
    code = (
        f"def _tool({signature}):\n"
        "    _kwargs = {k: v for k, v in locals().items() if v is not None}\n"
        "    WAAPIClient().connect()\n"
        "    return _handler(_kwargs)\n"
    )
    exec(code, namespace)
    fn = namespace["_tool"]
    fn.__name__ = spec.name
    fn.__doc__ = spec.description
    return fn


for _spec in tool_registry.list_tools():
    mcp.tool(name=_spec.name, description=_spec.description)(_build_mcp_function(_spec))
