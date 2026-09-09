# FastMCP 单例：供 waapi_full_tools / utils_mcp_tools 注册 tool，避免循环 import
# 新环境使用独立 fastmcp 包（from fastmcp import FastMCP）；
# 旧环境（mcp SDK <2.0）仍可用 mcp.server.fastmcp，保留兜底导入。
try:
    from fastmcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Wwise WAAPI")
