---
name: wwise-waapi
description: Use for WAAPI_Tools tasks that automate Wwise via Python or MCP, especially object queries, children/parents, SoundBank, Switch, import, RTPC, transport, UI commands, undo groups, or GUID-to-Wwise operations.
---

# Wwise WAAPI（本工程）

## 架构

- 底层 WAAPI 客户端：`libraries/waapi_client.py` 中的 `WAAPIClient`，入参出参为 dict 或原生值。
- Wwise 对象门面：`libraries/utils/wwise/waapi_utils.py`，负责 `WwiseObject` / `WwiseObjectType` 与 `WAAPIClient` 所需 dict / type string 的转换。
- 业务工具：`libraries/utils/wwise/*_utils.py` 基于 `waapi_utils` 组合更高层操作。
- 对象模型：`libraries/wwise_object.py` 中的 `WwiseObject` 和 `WwiseObjectType`。
- 连接：`WAAPIClient().connect()` 使用 `ws://127.0.0.1:8080/waapi`；结束时可 `WAAPIClient().disconnect()` 或通过 `waapi_utils.close_client()` 关闭。
- 编辑业务代码时优先使用 `from libraries.utils.wwise import waapi_utils`。只有 MCP GUID/dict 薄封装或底层客户端改动才直接使用 `WAAPIClient`。

## MCP 与自然语言任务

- **工具名**：在 Codex 里调用的 MCP 工具名，与 `waapi_mcp/waapi_mcp_tools.py`、`waapi_mcp/utils_mcp_tools.py` 中带 `@mcp.tool()` 的**函数名一致**。
- **典型链**：先**查询** → 在助手侧根据返回 JSON 里的 `type`、`name`、`path` **筛选** → 再**写入**（`set_object_property` 等）。批量修改建议用 `begin_undo_group` / `end_undo_group` 包一层，失败时可 `undo`。
- **名称 + 类型**：若用户同时给出精确名与类型，优先 `find_object_by_name_and_type`；若只给类型或只给名称片段，用 `find_all_objects_by_type` 或 `find_all_objects_by_name`，再在结果上筛选。
- **`find_all_objects_by_name(obj_name, exact_match)`**（对应 `waapi_utils.find_all_objects_by_name` / `WAAPIClient.find_all_objects_by_name`）：工程版本大于 2020 时走 WAQL `search`；`exact_match=False` 时返回搜索命中的一批对象，**未必**已按「前缀」过滤，常需在客户端保留 `type == 某值` 且 `name` 以某前缀开头等条件。
- **示例**（用户话：「所有以 Weapon 开头的 ActorMixer 音量设为 -3」）：调用 `find_all_objects_by_name`，参数如 `obj_name="Weapon"`、`exact_match=false` → 在结果中只保留 `type` 为 `ActorMixer` 且 `name` 以 `Weapon` 开头 → 对每个对象的 `id` 调用 `set_object_property`，`property_name` 为 `Volume`，`value` 为 `-3`。
- **优先 utils**：若 `libraries/utils/wwise` 里已有对应业务封装，优先使用 MCP 中的高层工具；没有时再组合底层 WAAPI 薄封装。

## 意图 → 函数速查

按用户需求优先选择 `waapi_utils` 或已有 MCP tool 中的函数。

### 连接

| 函数 | 用途 |
|------|------|
| `WAAPIClient().connect()` | 获取/懒建 `WaapiClient` |
| `close_client()` | 断开并清理客户端 |

### 查询（Query）

| 函数 | 用途 |
|------|------|
| `get_authoring_info(property_name)` | Wwise 编辑器信息（`ak.wwise.core.getInfo`） |
| `get_project_info(property_name)` | 工程信息（`getProjectInfo`） |
| `get_project_property(property_name)` | 工程根对象上的单个属性 |
| `get_object_property(obj, property_name)` | 指定对象的单个属性 |
| `paste_object_property(source_obj, target_objects, property_name)` | 从源对象复制某属性到多个目标 |
| `get_selected_objects()` | 当前在 Wwise 中选中的对象 |
| `get_object_from_path(path)` | 按路径解析对象（与 `find_object_by_path` 类似场景，注意返回值形态） |
| `get_object_references(obj)` | 引用该对象的所有对象 |
| `get_parent_object(obj)` | 直接父级 |
| `get_ancestor_objects(obj)` | 自底向上祖先链 |
| `get_child_objects(obj, include_descendants=False)` | **直属子级**；`include_descendants=True` 时取全部后代（分页拉取） |
| `get_descendants_of_type(obj, child_type)` | 某类型后代（`WwiseObjectType`） |
| `get_global_objects()` | 聚合多类型的“全工程对象”列表（内部多次 `find_all_objects_by_type`） |
| `get_full_info_from_obj_id(obj_id)` | 用 id 取完整 `RETURN_FIELDS` 信息 |
| `find_object_by_path(path)` | 路径查找单个对象 |
| `find_object_by_name_and_type(obj_name, obj_type, exact_match=True)` | 按名+类型查找 |
| `find_all_objects_by_name(obj_name, exact_match)` | 工程内按名称搜索 |
| `find_all_objects_by_type(obj_type)` | 某类型的全部对象 |

### 通用操作（CommonOperation）

| 函数 | 用途 |
|------|------|
| `create_object_at_default_location(obj_name, obj_type)` | 在各类默认 Work Unit 下创建 |
| `create_child_object(obj_name, obj_type, parent_obj, on_name_conflict='fail')` | 在指定父对象下创建子对象 |
| `create_object_by_path(obj_path, obj_type, on_name_conflict='fail')` | 按完整路径创建（>2020 用 `object.set`） |
| `move_object(obj, new_parent)` | 移动到新的父对象下 |
| `copy_object(obj, parent)` | 复制到某父下 |
| `rename_object(obj, new_name)` | 重命名 |
| `set_object_property(obj, property_name, value, platform=None)` | 设置属性；可选平台 |
| `set_object_reference(obj, reference_type, value)` | 设置引用类字段 |
| `set_object_notes(obj, notes)` | 备注 |
| `delete_object(obj)` | 删除对象 |

### 逻辑容器（LogicContainer）

| 函数 | 用途 |
|------|------|
| `set_sequence_container_playlist(container, playlist)` | 顺序容器播放列表 |
| `get_switch_mappings(container)` | Switch 容器当前分配 |
| `assign_switch_mapping(target, switch_obj)` | 为子对象分配 switch/state |
| `remove_switch_mappings(obj)` | 移除该 Switch 容器下全部分配 |

### 音频源（AudioSource）

| 函数 | 用途 |
|------|------|
| `import_audio_file(wave_path, sound, language='SFX')` | 导入波形到 Sound 下 |
| `add_silence(obj, length, language='SFX')` | 添加静音 SourcePlugin |
| `get_audio_source_from_sound(sound)` | Sound 下第一个子级（常见为 AudioSource） |

### SoundBank

| 函数 | 用途 |
|------|------|
| `get_bank_inclusions(bank)` | Bank 包含项 |
| `clear_bank_inclusions(bank)` | 清空 Bank 包含 |
| `set_bank_inclusion(bank, inclusion, replace, inclusion_type=None)` | 设置/追加包含 |

### GameSync / Mixing

| 函数 | 用途 |
|------|------|
| `add_rtpc(target_obj, rtpc_obj, target_property, points)` | 为目标对象添加 RTPC 曲线 |
| `clear_slots(obj, slot_name)` | 清空列表型属性（如 `@RTPC`、`@Effects` 等，参数为 WAAPI 中的槽位名） |
| `add_effect(obj, share_set_name)` | 追加 EffectSlot（引用 ShareSet 名） |

### 本地化（Localization）

| 函数 | 用途 |
|------|------|
| `get_language_list()` | 工程内所有 Language 对象（返回含 `name`） |

### 播放（Playback）

| 函数 | 用途 |
|------|------|
| `play_sound_in_transport(obj)` | 创建 transport 并 play，**返回 transport_id** |
| `stop_sound_in_transport(transport_id)` | stop 并 `destroy_transport` |
| `destroy_transport(transport_id)` | 销毁 transport |

### UI / 撤销 / 源码管理（UICommand）

| 函数 | 用途 |
|------|------|
| `execute_ui_command(objects, command)` | 执行 Wwise UI 命令名 |
| `select_objects_in_wwise(objects)` | 在工程浏览器中选中并 Inspect |
| `bring_wwise_to_foreground()` | 将 Wwise 窗口置前 |
| `begin_undo_group(action)` / `end_undo_group(action)` | 撤销分组 |
| `undo()` / `redo()` | 撤销/重做 |
| `add_to_source_control(file_path)` | 源码管理 add |

## 使用约定

- **子级**：直属子对象用 `get_child_objects(obj, include_descendants=False)`；整棵子树用 `include_descendants=True`。
- **按类型过滤后代**：`get_descendants_of_type(obj, child_type)`。
- **优先复用 utils**：若 `libraries/utils/wwise` 已有封装，先读现有工具函数再决定是否直接调 `WAAPIClient`。
- **版本差异**：工程版本 &gt; 2020 时多处使用 WAQL；旧版使用 `from`/`transform`。新增逻辑需与 `project_utils.get_project_version()` 分支一致。

更多细节与边缘行为见 [reference.md](reference.md)。
