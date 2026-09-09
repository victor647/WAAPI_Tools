# MCP 工具入口
# - 所有工具统一定义在 libraries/tool_registry.py（含 wwise_tool_catalog.py 迁移实现），
#   由 registry_mcp_tools 批量注册为 MCP tool；与软件内 AI 助手共用同一份定义。

from __future__ import annotations

from waapi_mcp.bootstrap import ensure_project_root

ensure_project_root()
# 须先于 serialize / wwise_object 完成加载，避免 libraries 内 WAAPI ↔ wwise_object 循环 import
# 也先于 waapi_client 链路加载 waapi_utils，解开 waapi_client ↔ project_utils 的循环导入
from libraries.utils.wwise import waapi_utils  # noqa: F401, E402

# 注册顺序：libraries/tool_registry.py 先加载（含 wwise_tool_catalog 迁移的全部工具），
# 再由 registry_mcp_tools 统一注册为 MCP tool
from waapi_mcp import registry_mcp_tools  # noqa: F401
from waapi_mcp.mcp_instance import mcp


def run_stdio() -> None:
    # 启动 FastMCP，使用标准输入输出传输 MCP 协议（阻塞直至进程结束）
    mcp.run(transport="stdio")
