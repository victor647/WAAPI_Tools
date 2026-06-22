# MCP 服务进程入口：使用标准输入输出（stdio）与宿主（如 Cursor）通信
# 启动顺序很重要：先修正 import 路径，再建立 Wwise 连接，最后阻塞在 MCP 协议循环上

from __future__ import annotations

import os

from waapi_mcp.bootstrap import ensure_project_root

# 第一步：保证能 import libraries.*（开发环境为仓库根目录，PyInstaller 为 _MEIPASS）
ensure_project_root()

# MCP stdio：日志仅 stderr，避免 print 污染 stdout（JSON-RPC）
os.environ.setdefault("WAAPI_MCP", "1")


def main() -> None:
    # 进程主入口：创建全局 WaapiClient，然后启动 FastMCP 的 stdio 传输
    # 第二步：与 Wwise 建立 WebSocket（WAAPI 模块内 WaapiClient）

    WAAPI.connect()
    # 第三步：加载并注册所有 MCP tool，然后进入 mcp.run()（阻塞）
    from waapi_mcp.server import run_stdio

    run_stdio()


if __name__ == "__main__":
    main()
