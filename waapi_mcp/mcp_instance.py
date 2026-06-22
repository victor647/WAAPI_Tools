# FastMCP 单例：供 waapi_full_tools / utils_mcp_tools 注册 tool，避免循环 import
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Wwise WAAPI")
