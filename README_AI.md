# AI 助手（软件内对话）使用说明

主窗口底部「Console」日志区下方有一行 **AI 助手** 输入框：输入中文指令后，AI 会通过
`function calling` 调用内置工具，对**表格当前筛选可见的 Wwise 对象**执行批量操作，并把过程和结果
输出到日志区。请求在后台线程执行，不阻塞界面；AI 修改过对象后表格会自动刷新。

---

## 1. 配置（user_config.json / libraries/utils/user_config.py）

```json
"ai": {
  "proxy": "http://127.0.0.1:15721",
  "api_key": "",
  "model": "",
  "max_context_objects": 300,
  "max_turns": 20
}
```

- `mode`：连接模式，`proxy`（代理模式）或 `official`（官方 API 模式），在设置窗口的
  “AI 助手”Tab 里二选一。
- `proxy`：代理模式下的 API 地址（如 `http://127.0.0.1:15721`，可带 `/v1`，也可直接粘贴
  完整 `…/v1/chat/completions`）；留空时回退 `https://api.openai.com`。
- `provider`：官方 API 模式下的服务提供方，内置 OpenAI / DeepSeek / 通义千问（兼容模式）/
  Kimi / 智谱 GLM / Google Gemini（兼容端点）/ **Anthropic Claude（原生协议）** / 自定义。
  除 Claude 走 Anthropic `/v1/messages`（`x-api-key`，模型名必填）外，其余均为 OpenAI 兼容协议。
- `base_url`：官方模式选择“自定义”时填写的 OpenAI 兼容地址。
- `model`：界面 AI 输入栏左侧有模型下拉框：启动时会请求代理的 `/v1/models` 填充列表，
  选择后自动写回本配置（下次启动沿用）。也可手动输入模型名。留空时下拉框会默认选中
  列表第一个模型。
- `api_key`：代理要求鉴权时填写。
- `max_context_objects`：一次最多放进提示词的对象数，超出部分会提示用户先用筛选缩小范围。
- `max_turns`：允许的最大对话往返轮数，防止模型陷入工具循环。
- `enable_script_tool`：是否允许 AI 执行临时脚本（`run_wwise_script`），默认 `false`
  （IDE 调试器下可能不稳定）；在设置窗口的「AI 助手」页勾选开启。

---

## 2. 意图 → 工具 → 底层实现 对照表

模型理解需求依赖两点：工具自带的 `description`（随 function calling schema 下发），以及
系统提示词。**系统提示词全文维护在 `ai_assistant_prompt.md`**（仓库根目录）：每次对话开始时
`libraries/ai_assistant.py` 读取该文件并作为 system 消息原样发给模型，再动态附上本次表格
对象清单。因此：

- 想让 AI 更懂某类用户说法，直接改 `ai_assistant_prompt.md` 的「工具选择指南」表即可，
  无需改 Python；
- 打包 GUI 时需把 `ai_assistant_prompt.md` 加进 PyInstaller spec 的 `datas`
  （与 `material.css` 同级、解压到 bundle 根目录）；漏打时程序会退回到内置兜底提示词并在
  日志中报错，功能不会静默失效。

### 工具复用架构（AI / MCP / 手动工具同源）

**执行顺序（写在系统提示词里，模型每次都会读到）**：先判断需求能否用界面操作组合出来
（`gui_*`：取选中 / 查找上下级 / 筛选 / 打开窗口 / 触发菜单动作），能则走 GUI；
界面动作覆盖不了或需要数据结论时，才落到底层数据工具（`get_descendants_of_type` /
`find_objects_by_property` / `aggregate_tool_chain` / `group_tool_items` …）；
GUI 失败时明确说明并退回底层工具继续完成目标。不确定菜单功能时先 `gui_list_actions` 再用
`gui_run_action` 触发。

另外：模型上下文里的对象清单仍按 `max_context_objects` 截断（保护上下文），但**不限制可处理的对象数量**——
工具参数支持 `object_ids: ["@table"]`（当前表格全部对象）与 `"@selection"`（Wwise 当前选中），
聚合类工具（`find_objects_by_property` / `aggregate_tool_chain` / `count_tool_items` 等）在工具侧全量处理，
只把紧凑结果回传模型。

结果超过字符预算时，AI 助手会把**完整结果写入本次任务的临时目录**（`%TEMP%/waapi_ai_*/`），
只回传 `result_file` 路径 + 摘要 + 预览；模型用 `read_result_file`（分页）或 `group_result_file`
（分组统计）继续处理，任务结束（含异常/中止）时目录会被删除，异常残留的旧目录在下次任务开始时清理。

工具本体只定义一份，各消费方生成自己的协议层：

- `libraries/tool_registry.py`：中立注册表（不得 import fastmcp / PySide6 / Qt /
  `waapi_mcp`），每项包含 `name / description / parameters(JSON schema) / handler /
  mutating`，handler 返回 JSON 兼容值。
- `libraries/wwise_tool_catalog.py`：MCP legacy 工具迁移后的中立实现（98 个，自动生成），
  随 `tool_registry` 一并注册；删除工具/改参数直接在注册表与其 schema 上维护。
- AI 助手：`build_tool_schemas()` 先取注册表工具，再拼本地过渡工具；执行时优先走
  `tool_registry.execute_tool()`，结构化结果统一转文本回传模型。因此 **MCP 能用的工具
  AI 助手全部能用**（注册表全部工具 + 少量 AI 专用封装与界面桥工具）。
- MCP：`waapi_mcp/registry_mcp_tools.py` 按注册表批量生成 `@mcp.tool`（同源同名），
  在 `waapi_mcp/server.py` 中随服务启动注册。
- 手动工具（GUI 菜单/表格操作）：仍直接调用 `*_utils`，注册表 handler 内部复用的就是
  同一批封装，无需改动。

说明：旧的两份手写 MCP 工具文件已删除并迁入注册表；AI 侧只保留注册表未覆盖的少量封装
（如 `rename_case`、`set_table_objects`、`read_result_file`）与界面桥工具（`gui_*`），不参与 MCP。

下表面向开发者，列明每个工具最终复用了哪个 `waapi_utils` / `common_utils` /
`event_utils` 函数：

| 用户说法示例 | AI 工具 | 底层复用（waapi_utils / *_utils） |
| --- | --- | --- |
| 查一下这些对象的备注 / 是否启用 | `get_objects_info` | `WwiseObject.from_id` → `waapi_utils.get_full_info_from_obj_id`；`common_utils.get_object_notes`；`common_utils.is_object_included` |
| 查看对象下有哪些音频源 / 源文件路径 | `get_audio_sources` | `waapi_utils.get_descendants_of_type(..., AudioSource)`（Event 用 `event_utils.get_event_targets` 展开）+ `audio_source_utils.get_source_file_path` |
| 统计这些对象的音频资源总大小 | `calculate_audio_source_size` | `waapi_utils.get_descendants_of_type(..., AudioSource)`（Event 展开播放目标）+ `audio_source_utils.get_source_file_path` + `os.path.getsize`（按路径去重） |
| 列出对象下有哪些子级 / 后代 | `get_children` | `waapi_utils.get_child_objects(..., include_descendants)` |
| 查找对象下某类型的全部后代（如所有 Sound / Event） | `get_descendants_of_type` | `waapi_utils.get_descendants_of_type`（Wwise 侧 WAQL 按类型过滤） |
| 统计任意列表工具返回的条数 | `count_tool_items` | 调用目标工具后对结果列表计数（自动识别 items/objects/data 等） |
| 按列表项字段分组计数 / 有多少分组超过 N 个 | `group_tool_items` | 调用目标工具 + 按字段分组计数，`min_count` 返回 matched_count |
| 多步链式统计（先取 A，再统计每个 A 下 B 的数量） | `aggregate_tool_chain` | 顺序执行 `steps`，自动把上一步 id 注入下一步 `object_ids`，末步按 `group_by` 分组（`min_count` 返回 matched_count） |
| 复杂组合逻辑（多级遍历 / 聚合统计 / 批量改） | `run_wwise_script` | 进程内 `exec` 受限脚本（注入 `waapi_utils` 等模块 + `tools_api`/`help()` 清单，循环/超时预算用 AST 注入，不与 IDE 调试器冲突），需 `confirmed=true`，由 AI 层包撤销组 |
| 把结果发送到主界面表格 | `set_table_objects` | AI 助手专用：通过 sink 回调**替换** `gv.active_objects`（`append=true` 时追加）并刷新表格（MCP 环境不可用） |
| 用界面按钮/菜单完成操作 | `gui_*` 系列 | AI 助手专用：通过主线程 GUI 桥调用 `MainWindow` 上与按钮/菜单相同的方法（`get_selected_objects` / `find_children` / `find_parent` / `apply_table_filter` / `open_property_query_window` / 任意 QAction），不模拟鼠标点击 |
| 发现并使用菜单功能 | `gui_list_actions` / `gui_run_action` | 遍历 `QAction` 返回 `objectName/名称/是否可用/使用说明`（说明取自 `data/action_help.py`），再用 `gui_run_action` 按 objectName 触发；无需为每个菜单项单独写工具 |
| 按属性筛选子对象（如 Volume ≠ 0） | `find_objects_by_property` | `waapi_utils.get_child_objects(..., include_descendants=True)`（或 `get_descendants_of_type`）+ `waapi_utils.get_object_properties(obj, [属性])`，与 `windows/property_query_window.py` 同口径：某类型首次读不到该属性即跳过该类型，并在 `types_without_property` 中汇报 |
| 查询哪些对象引用它 / 被谁使用 | `get_references` | `waapi_utils.get_object_references` |
| 统计其中有多少被 Event 引用 | `check_event_references` | `event_utils.has_event_reference`（引用含 EventAction 即算） |
| 全部改成小写 / 大写 / 首字母大写 | `rename_case` | `common_utils.rename_to_lower_case` / `rename_to_upper_case` / `rename_to_title_case`（内部走 `waapi_utils.rename_object`） |
| 前缀换成缩写 / 按工程缩写重命名 | `rename_with_acronym` | `common_utils.rename_with_acronym` |
| 把这个改名为 xxx | `rename_object` | `waapi_utils.rename_object` |
| 去掉开头 / 前缀 `XX_` | `remove_name_prefix` | `common_utils.remove_name_prefix` |
| 去掉末尾 / 后缀 `_XX` | `remove_name_suffix` | `common_utils.remove_name_suffix` |
| 给对象写备注 | `set_notes` | `waapi_utils.set_object_notes` |
| 启用 / 停用这些对象 | `set_inclusion` | `common_utils.set_object_inclusion`（内部走 `waapi_utils.set_object_property(..., 'Inclusion')`） |
| 包一层 ActorMixer / 建个父级 | `create_parent` | `common_utils.create_parent`（内部走 `waapi_utils.create_child_object` / `move_object` / `rename_object`） |
| 转成别的容器类型 | `convert_type` | `common_utils.convert_to_type` |
| 把下划线分段拆成子文件夹 | `split_underscore_to_folder` | `common_utils.split_underscore_to_folder` |
| 按规范更新备注和颜色 | `update_notes_and_color` | `common_utils.update_notes_and_color` |
| 创建 / 更新 Play Event | `create_play_event` | `event_utils.create_play_event` |
| 删除对象（需明确确认） | `delete_objects` | `waapi_utils.delete_object` |
| 在 Wwise 里选中查看 | `select_objects_in_wwise` | `waapi_utils.select_objects_in_wwise` |

> 说明：AI 层不直接触碰 `WAAPIClient`；所有对象操作都通过 `libraries.utils.wwise`
> 下与 GUI 相同的封装执行，符合 AGENTS.md 的分层约定。

---

## 3. 新增工具（推荐：注册表方式，三方共用）

1. 在 `libraries/tool_registry.py` 写 handler（返回 JSON 兼容值，不要直接调
   `WAAPIClient`，优先复用 `*_utils`），并用 `register_tool(...)` 注册
   `name / description / parameters / mutating`。
2. AI 与 MCP 会自动获得该工具，无需再写第二遍；如只希望 AI 内部临时使用（不走注册表），
   才按旧方式在 `libraries/ai_assistant.py` 本地追加。
3. 在 `ai_assistant_prompt.md` 的「常用工具（意图 → 工具）」表加一行，并同步更新
   本文件对照表。
4. 若会修改工程内容，把 `mutating=True` 传给 `register_tool`（AI 任务结束后据此刷新表格）。

新增功能一律走注册表（AI 与 MCP 自动同源）；只有界面/表格相关能力才加在 `ai_assistant` 本地。

---

## 4. 当前边界与注意事项

- AI 只能操作**发送时表格里可见的对象**（`get_visible_objects()`）；隐藏行不会交给 AI。
- `convert_type` / `delete_objects` 会改变或移除 GUID：任务结束后表格会自动刷新，
  被删除或转换的对象会从列表移除，必要时重新在 Wwise 中获取。
- 已开放：对象查询（子级/后代/引用/属性）、统计与分组、属性筛选、批量修改、结果落盘读写、
  界面操作（`gui_*`）。尚未开放的主要是迁移类导入（FMOD / 截图）与全工程破坏性操作
  （如删除多余 .akd），需要时可单独评估再加。
