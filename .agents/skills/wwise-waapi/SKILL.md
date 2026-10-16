---
name: wwise-waapi
description: Use for WAAPI_Tools tasks that automate Wwise — in the software's AI assistant, through MCP tools, or by editing libraries/utils/wwise code. Covers object queries, children/descendants, references, property filtering, counting/aggregation, SoundBank, Switch, RTPC, transport, undo groups, GUI actions, and GUID-based operations.
---

# Wwise WAAPI（本工程）

## 架构：工具只定义一份

- `libraries/tool_registry.py`：中立工具注册表（`name / description / parameters / handler / mutating`），
  不依赖 Qt 与 fastmcp；`libraries/wwise_tool_catalog.py` 是原 MCP 薄封装迁入的实现。
  两者合计约 110 个后台工具，AI 助手与 MCP **同源同名**。
- `waapi_mcp/registry_mcp_tools.py`：把注册表工具批量注册为 MCP tool（`WaapiMCP.exe`）；
  `run_wwise_script` 受 `ai.enable_script_tool` 控制，默认不注册。
- 软件内 AI 助手：注册表工具 + AI 专用工具（表格 / 大结果文件 / `gui_*` / 脚本）。
- GUI 手动工具：直接调用 `libraries/utils/wwise/*_utils.py`。
- 业务代码优先 `from libraries.utils.wwise import waapi_utils`（传 `WwiseObject` / `WwiseObjectType`）；
  只有 MCP 薄封装或底层改动才直接用 `WAAPIClient`（`libraries/waapi_client.py`，dict 层）。
- `WAAPIClient` 内部用锁串行化 `call`（界面/批处理/AI 共用一条 websocket），不要依赖并发调用。

## 参数与结果约定（AI 与 MCP 通用）

- 对象一律用 GUID；批量传 `object_ids` 数组。AI 侧可用 `["@table"]`（当前表格对象）与
  `["@selection"]`（Wwise 当前选中）代替罗列大量 id。
- 列表型工具有 `limit`（`0` = 不限量）。默认上限：子级 500 / 后代 1000 / 引用 500 /
  属性筛选扫描 20000。
- 结果过大时 AI 侧会落盘：返回 `result_file`，用 `read_result_file(result_file, offset, limit)`
  分页、`group_result_file(result_file, group_by, min_count)` 分组；任务结束自动删除。
- 结果带 `truncated: true` 时不要下钻重查，改用统计类工具让工具侧完成。
- 多步任务一次把 id 批量传给下一步；跨层级统计用 `aggregate_tool_chain`（自动注入上一步 id）。

## 意图 → 工具（后台/数据，AI 与 MCP 都可调用）

| 需求 | 工具 | 说明 |
|------|------|------|
| 对象详情 / 备注 / 启用状态 | `get_objects_info` | 备注、Inclusion 等 |
| 子级或全部后代 | `get_children(object_ids, recursive, limit)` | `recursive=true` 一次取全量 |
| 指定类型的后代 | `get_descendants_of_type(object_ids, child_type, include_path, limit)` | Wwise 侧按类型过滤，最省数据 |
| 谁引用了对象 | `get_references(object_ids)` | Event 通过 EventAction(Action) 引用 |
| 被 Event 引用计数 | `check_event_references(object_ids)` | 已按 Action 口径封装 |
| 按属性筛选（Volume/Pitch…） | `find_objects_by_property(object_ids, property_name, op, value, child_type?, scan_limit?)` | 与「属性查询」窗口同口径：逐对象 `get_object_properties`，某类型首次读不到即视为该类型无此属性，结果含 `types_without_property` |
| 列表计数 / 分组 | `count_tool_items` / `group_tool_items` | 包裹任意返回列表的工具 |
| 多步链式统计 | `aggregate_tool_chain(steps, group_by, min_count)` | 例：统计含 >1 个 MusicTrack 的 MusicSegment |
| 音频源与体积 | `get_audio_sources` / `calculate_audio_source_size` | 源文件路径、磁盘占用 |
| 自动转码（长短音效分开转码） | `auto_compression_plan`（只读出方案）→ `auto_compression_apply`（改工程，需 `confirmed=true`） | 按 AudioFileSource 播放时长分短/中/长档，改节点的 OverrideConversion + Conversion |
| 改名 / 备注 / 启用 / 颜色 | `rename_object` / `set_object_notes` / `set_object_inclusion` / `set_object_color` | |
| 结构操作 | `create_parent` / `convert_to_type` / `split_underscore_to_folder` / `create_play_event` | |
| 删除 | `delete_object`（MCP 侧需 `confirmed=true`） | AI 侧对应 `delete_objects`，由软件按修改策略弹窗确认 |
| 试听 | `play_sound` / `stop_sound` | 返回 `transport_id` |
| 撤销 | `begin_undo_group` / `end_undo_group` / `undo` / `redo` | AI 批量任务会自动包撤销组 |

## AI 专用（无界面环境不可用）

- 表格：`set_table_objects(object_ids, append=false)`（默认**替换**表格内容，`append=true` 追加）
- 大结果文件：`read_result_file` / `group_result_file`
- 界面操作（等价于点按钮/菜单）：`gui_get_wwise_selection`、`gui_find_children`、`gui_find_parent`、
  `gui_set_filter`、`gui_open_window`、`gui_list_actions`、`gui_run_action`
- 脚本：`run_wwise_script`（需设置里开启 `ai.enable_script_tool`；MCP 侧还要传 `confirmed=true`，AI 侧由修改策略处理；
  受限命名空间：可用 `tools_api` / `api_names` / `help()`，禁止 `import os/sys/subprocess/inspect`，
  循环与超时预算由 AST 注入）

## 代码侧函数速查（waapi_utils / *_utils）

| 区域 | 函数 |
|------|------|
| 查询 | `get_object_property` / `get_object_properties` / `get_property_and_reference_names`、`get_selected_objects`、`get_parent_object`、`get_ancestor_objects`、`get_child_objects`、`get_descendants_of_type`、`get_object_references`、`find_object_by_path`、`find_object_by_name_and_type`、`find_all_objects_by_name` / `find_all_objects_by_type`、`get_full_info_from_obj_id`、`get_authoring_info` / `get_project_info` / `get_project_property` |
| 通用写 | `create_child_object`、`create_object_by_path`、`create_object_at_default_location`、`move_object`、`copy_object`、`rename_object`、`set_object_property`、`set_object_reference`、`set_object_notes`、`delete_object` |
| 容器 | `set_sequence_container_playlist`、`get_switch_mappings`、`assign_switch_mapping`、`remove_switch_mappings` |
| 音频源 | `import_audio_file`、`add_silence`、`get_default_audio_source` |
| SoundBank | `get_bank_inclusions`、`clear_bank_inclusions`、`set_bank_inclusion` |
| GameSync / 混音 | `add_rtpc`、`clear_slots`、`add_effect` |
| 本地化 | `get_language_list` |
| 播放 | `play_sound_in_transport`、`stop_sound_in_transport`、`destroy_transport` |
| UI / 撤销 / 源码管理 | `execute_ui_command`、`select_objects_in_wwise`、`bring_wwise_to_foreground`、`begin_undo_group` / `end_undo_group`、`undo` / `redo`、`add_to_source_control` |

## 约定与坑

- **禁止逐层展开**：一次 `get_descendants_of_type` / `get_children(recursive=true)` 取到位，
  不要对每个对象重复查询。
- 属性读取用 `get_object_property(s)`；`options.return` 中属性名带不带 `@` 都可（返回 key 相应变化）。
- 属性名是否存在于某对象类型，可先用 `WwiseObject.has_property(name)` 本地判定（表见
  `libraries/wwise_object_properties.py`）；`get_object_property(s)` 已内置该过滤，文档里没有的类型不拦截。
- 版本差异：工程 >2020 走 WAQL，旧版走 `from` / `transform`；新增逻辑需与
  `project_utils.get_project_version()` 分支一致。
- 多数查询失败时返回空 `WwiseObject` / `[]` / `None` 并写日志，不要假设会抛异常。
- 未对 AI/MCP 开放：迁移类导入（FMOD/截图）与全工程破坏性操作（如删除多余 .akd）。

更多细节与边缘行为见 [reference.md](reference.md)。
