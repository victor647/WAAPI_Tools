# WAAPI MCP server

通过 MCP（stdio）调用本工程里的 `libraries/wwise/WAAPI.py`，与 GUI 一样连接 Wwise（`ws://127.0.0.1:8080/waapi`）。

---

## 在 Cursor 里启用（推荐，无需 Python / 环境变量）

1. **先开 Wwise**，并保证 WAAPI 已开启（默认端口 8080）。
2. 在本机找到 **`WaapiMCP.exe`**（例如用 `package.py` 打包并复制后：`…/WaapiMCP/WaapiMCP.exe`），记下**完整路径**。
3. 打开 Cursor 的 MCP 配置文件（二选一即可）：
   - **用户级**：`%USERPROFILE%\.cursor\mcp.json`
   - **项目级**：仓库内 `.cursor/mcp.json`
4. 把下面 JSON **整段合并进**文件里的 `mcpServers`（若已有其它 MCP，只增加 `wwise-waapi` 这一项，注意逗号）。
5. 把 **`command`** 改成你电脑上 `WaapiMCP.exe` 的绝对路径（建议用正斜杠 `/`）。
6. **保存文件**，然后重开 Cursor 或执行一次 MCP 重载；无需配置 PATH、无需安装 Python。

```json
{
  "mcpServers": {
    "wwise-waapi": {
      "command": "D:/Audio_P4/Tools/WAAPI_Tools/WaapiMCP/WaapiMCP.exe",
      "args": []
    }
  }
}
```

说明：

- 上面 `D:/Audio_P4/...` 仅为示例，请换成你的真实路径。
- 若启动异常，可尝试为同一项增加 `"cwd": "D:/Audio_P4/Tools/WAAPI_Tools/WaapiMCP"`（与 `WaapiMCP.exe` 所在目录一致）。

工具参数中的 Wwise 对象请使用 **GUID 字符串**（`id`）。

---

## 开发者：从源码运行（需本机已安装 Python）

```bash
cd WAAPI_Tools
pip install -e .
```

开发调试时可：

```bash
python -m waapi_mcp
```

进程使用 **stdio** 与 MCP 宿主通信，一般不要在无 MCP 托管时手动长期运行。

---

## 开发者：打包装箱（PyInstaller）

在已安装 `pyinstaller` 与项目依赖的环境中，于仓库根目录执行：

```bash
python package.py
```

或只打 MCP：`python package.py --mcp-only`。

产物先出现在本仓库 **`dist/WaapiMCP/`**，再按 `package.py` 逻辑复制到默认上传目录（可用 `--upload-root`、`--no-copy` 调整）。最终把 **`WaapiMCP.exe` 的绝对路径** 填进上一节的 Cursor JSON 即可。

---

## Tools

每个 `libraries/wwise/WAAPI.py` 中的对外接口对应一个 `waapi_*` 工具（见 `waapi_mcp/server.py`）。可先调用 **`waapi_get_client_status`** 确认已与 Wwise 建立连接。
