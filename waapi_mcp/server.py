# MCP 工具入口
# - 业务操作：优先使用 utils_mcp_tools 中映射的 libraries.wwise.*_utils（工具名前缀 wwise_），与 WAAPI 工具集 GUI 共用同一套封装逻辑
# - 底层 WAAPI：waapi_mcp_tools 为 WAAPI 的薄封装（工具名无 waapi_ 前缀）；需要对外暴露的函数使用 @mcp.tool(description=...)

from __future__ import annotations

from waapi_mcp.bootstrap import ensure_project_root

ensure_project_root()
# 须先于 serialize / wwise_object 完成加载，避免 libraries 内 WAAPI ↔ wwise_object 循环 import

# 注册顺序：先核心 WAAPI，再各 *_utils 封装
from waapi_mcp import utils_mcp_tools  # noqa: F401
from waapi_mcp import waapi_mcp_tools  # noqa: F401
from waapi_mcp.mcp_instance import mcp


def run_stdio() -> None:
    # 启动 FastMCP，使用标准输入输出传输 MCP 协议（阻塞直至进程结束）
    mcp.run(transport="stdio")
