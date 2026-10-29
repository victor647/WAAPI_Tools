# WAAPI 模块补充说明

## 底层 WAAPI 调用摘要

本文件是对 `libraries/waapi_client.py` 中 `WAAPIClient` 实现细节的速记，便于排查“实际调了哪条 waapi”。

| 区域 | 典型 `client.call` |
|------|---------------------|
| 连接 | `WaapiClient(url='ws://127.0.0.1:8080/waapi')` |
| 信息 | `ak.wwise.core.getInfo`, `getProjectInfo` |
| 对象读写 | `ak.wwise.core.object.get` / `set` / `create` / `move` / `copy` / `delete` / `setName` / `setProperty` / `setReference` / `setNotes` / `pasteProperties` |
| UI | `ak.wwise.ui.getSelectedObjects`, `ak.wwise.ui.commands.execute`, `ak.wwise.ui.bringToForeground` |
| Switch | `ak.wwise.core.switchContainer.getAssignments` / `addAssignment` / `removeAssignment` |
| 音频 | `ak.wwise.core.audio.import` |
| SoundBank | `ak.wwise.core.soundbank.getInclusions` / `setInclusions` |
| Transport | `ak.wwise.core.transport.create` / `executeAction` / `destroy` |
| 撤销 | `ak.wwise.core.undo.beginGroup` / `endGroup` |
| 源码管理 | `ak.wwise.core.sourceControl.add` |

## 返回值注意

- 多数查询在失败时返回空 `WwiseObject`、`[]` 或 `None`，并写日志。
- `get_object_from_path` 与部分路径 API 在成功分支可能返回原始 dict 列表元素，与 `find_object_by_path` 包装方式不完全一致；以当前源码为准。

## 并发与序列化

- `WAAPIClient.connect()` 会给底层 client 的 `call` 包一层 `RLock`：界面线程、批处理线程、AI 线程
  共用同一条 websocket 时串行执行，避免并发调用导致的原生崩溃。批量操作会因此略慢，属预期行为。

## MCP 工具来源

- MCP（`WaapiMCP.exe`）暴露的工具全部来自 `libraries/tool_registry.py`，由
  `waapi_mcp/registry_mcp_tools.py` 批量注册（同名同参数）；`run_wwise_script` 默认不注册，
  需 `ai.enable_script_tool=true`。软件内 AI 另有一批专用工具（表格、结果文件、`gui_*`），MCP 不可用。

## RETURN_FIELDS

默认对象查询返回字段：`id`, `name`, `type`, `path`（模块常量 `RETURN_FIELDS`）。

## 属性名预判（本地表）

- `libraries/wwise_object_properties.py` 由 Wwise SDK 帮助文档 "Wwise Objects Reference" 生成：
  `TYPE_PROPERTIES` 是「对象类型 -> 该类型可用的属性/引用/列表名」，`BUILTIN_ACCESSORS` 是
  `ak.wwise.core.object.get` 的内置访问器；表对应文档版本 `SOURCE_VERSION`（2023.1.18.8899）。
- `WwiseObject.has_property(name)` 本地判定该名称在此对象类型上是否可用：不区分大小写，
  `@` / `@@` 前缀与 `A.B` 只取第一段；`Effect` / `SourcePlugin` 已并入同族插件的全部属性；
  表里没有的对象类型一律返回 `True`，不拦截。
- `waapi_utils.get_object_property` / `get_object_properties` 已内置该过滤：类型上不存在的
  名称直接返回 `None` / `{}`，不再发一次必然拿不到值的 WAAPI 请求。
- 换 Wwise 版本后重新生成：
  `python .agents/skills/wwise-waapi/scripts/gen_object_properties.py`
  （默认读 `G:\H74\Sound\Wwise_2023.1.18.8899\SDK\Help\WwiseSDK-Windows.chm`，可用 `--chm` 指定）。

## 常用属性 / 引用 / 列表（筛选与 RTPC 时参考）

属性读取用 `@PropertyName`（对象上的直接值）或 `PropertyName`（带 override 解析），大小写不敏感。

| 属性 | 类型 | 说明 |
|------|------|------|
| `Volume` | dB | 声音/容器音量，-96 ~ +12 |
| `Pitch` | cents | 音高，1200 = 2 倍速 |
| `Lowpass` / `Highpass` | 0-100 | 递归低通/高通 |
| `BusVolume` | dB | 总线音量 |
| `MakeUpGain` | dB | 最终补偿增益 |
| `InitialDelay` | s | 播放前延迟 |
| `PlaybackSpeed` | 倍率 | 播放速度 |
| `Inclusion` | bool | 是否进 SoundBank |
| `IsStreamingEnabled` / `IsLoopingEnabled` / `IsLoopingInfinite` / `LoopCount` | bool/int | 流式与循环 |
| `NormalOrShuffle` / `RandomAvoidRepeating` | int/bool | Random 容器行为 |
| `SwitchBehavior` / `BlendBehavior` | int | Switch/Blend 行为 |
| `Tempo` / `TimeSignatureUpper` / `TimeSignatureLower` | 数值 | 音乐节拍 |

Override 开关：`OverrideOutput`、`OverrideGameAuxSends`、`OverrideUserAuxSends`、
`OverrideEffect`、`OverrideColor`。

常用引用：`OutputBus`、`UserAuxSend0..3`、`Attenuation`、`Conversion`、`AudioDevice`、
`SwitchGroupOrStateGroup`、`DefaultSwitchOrState`、`Target`（Action）、`Effect`（EffectSlot）。

- Effects 是 `EffectSlot` 列表：`effects.at(0).Effect` 才是插件本身；
  `where effects.any(effect.pluginname : "EQ")` 可筛选带 EQ 的总线。
- RTPC 是列表：`rtpc.any(propertyname = "Volume")`、`@RTPC.{propertyName, controlInput}`。
- 层级规则：Sound 可挂在 PropertyContainer / Random / Switch / Blend / WorkUnit / Folder 下；
  MusicTrack 只能挂在 MusicSegment 下；MusicSegment 可挂在 MusicSwitch/MusicPlaylist/WorkUnit/Folder 下。

## MCP 工具分组与发现

- MCP 侧仍一次暴露全部工具；AI 侧只常驻 `core`，其余分组用 `load_tools(group=...)` 加载。
- 分组：`auto_compression`、`soundbank`、`localization`、`rtpc_effects`、`source_files`、`advanced`。
- 发现工具：`get_guidelines`、`list_tool_groups`、`load_tools`、`get_tool_examples`、
  `get_tool_schema`、`get_tool_reference`；重点工具带 `output_schema` 与 `examples`。

## Wwise 2025 / 2026 兼容

- 2025+ 根目录：`\Containers`（音频+音乐）、`\Busses`；旧版为三个 `* Hierarchy`。
- 2026+ 类型：`ActorMixer` → `PropertyContainer`。
- 统一走 `libraries/utils/wwise/wwise_compat.py` 的 `containers_root()` / `busses_root()` /
  `is_property_container_type()` / `resolve_wrapper_type()`；不要新增硬编码。

## WWU 离线解析（work_unit_parse_utils）

- `find_work_unit_files(project_root)`：按新旧层级根收集 `.wwu`。
- `build_work_unit_index(project_root)` / `build_work_unit_index_for_files(files)` /
  `read_work_unit_file(file_path)` → `WorkUnitIndex`。
- `WorkUnitIndex`：`object_count`、`audio_sources`（`AudioSourceRecord(owner_id, media_ids_by_platform, edit)`）、
  `effective_conversion_pair(node_id)`、`effective_looping(node_id)`、`effective_render_signature(node_id)`、
  `path_of(node_id)`。
- `media_id_for_platform(media_ids, platform)`：平台优先，其次无平台共享项、唯一项、大小写匹配。
- 工具 `read_work_unit` 包装以上逻辑；`needs_waapi=False`，MCP 调用时不会先连接 Wwise。
