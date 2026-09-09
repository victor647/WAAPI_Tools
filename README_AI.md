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

- `proxy`：OpenAI 兼容代理根地址，代码会拼接 `/v1/chat/completions`。
- `model`：界面 AI 输入栏左侧有模型下拉框：启动时会请求代理的 `/v1/models` 填充列表，
  选择后自动写回本配置（下次启动沿用）。也可手动输入模型名。留空时下拉框会默认选中
  列表第一个模型。
- `api_key`：代理要求鉴权时填写。
- `max_context_objects`：一次最多放进提示词的对象数，超出部分会提示用户先用筛选缩小范围。
- `max_turns`：允许的最大对话往返轮数，防止模型陷入工具循环。

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

工具本体只定义一份，各消费方生成自己的协议层：

- `libraries/tool_registry.py`：中立注册表（不得 import fastmcp / PySide6 / Qt /
  `waapi_mcp`），每项包含 `name / description / parameters(JSON schema) / handler /
  mutating`，handler 返回 JSON 兼容值。
- AI 助手：`build_tool_schemas()` 先取注册表工具，再拼本地过渡工具；执行时优先走
  `tool_registry.execute_tool()`，结构化结果统一转文本回传模型。
- MCP：`waapi_mcp/registry_mcp_tools.py` 按注册表批量生成 `@mcp.tool`（同源同名），
  在 `waapi_mcp/server.py` 中随服务启动注册。
- 手动工具（GUI 菜单/表格操作）：仍直接调用 `*_utils`，注册表 handler 内部复用的就是
  同一批封装，无需改动。

过渡期说明：AI 助手当前已把 `get_objects_info` / `get_audio_sources` /
`calculate_audio_source_size` 迁入注册表；其余 14 个工具仍是 `libraries/ai_assistant.py`
里的本地定义，后续按同样方式逐个迁移（迁移后 MCP 侧同步获得）。

下表面向开发者，列明每个工具最终复用了哪个 `waapi_utils` / `common_utils` /
`event_utils` 函数：

| 用户说法示例 | AI 工具 | 底层复用（waapi_utils / *_utils） |
| --- | --- | --- |
| 查一下这些对象的备注 / 是否启用 | `get_objects_info` | `WwiseObject.from_id` → `waapi_utils.get_full_info_from_obj_id`；`common_utils.get_object_notes`；`common_utils.is_object_included` |
| 查看对象下有哪些音频源 / 源文件路径 | `get_audio_sources` | `waapi_utils.get_descendants_of_type(..., AudioSource)`（Event 用 `event_utils.get_event_targets` 展开）+ `audio_source_utils.get_source_file_path` |
| 统计这些对象的音频资源总大小 | `calculate_audio_source_size` | `waapi_utils.get_descendants_of_type(..., AudioSource)`（Event 展开播放目标）+ `audio_source_utils.get_source_file_path` + `os.path.getsize`（按路径去重） |
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
3. 在 `ai_assistant_prompt.md` 的「工具选择指南」表加一行“用户说法 → 工具”，并同步更新
   本文件对照表。
4. 若会修改工程内容，把 `mutating=True` 传给 `register_tool`（AI 任务结束后据此刷新表格）。

旧式本地工具仍在过渡期保留，新增功能请优先走注册表，避免再次出现三层重复定义。

---

## 4. 当前边界与注意事项

- AI 只能操作**发送时表格里可见的对象**（`get_visible_objects()`）；隐藏行不会交给 AI。
- `convert_type` / `delete_objects` 会改变或移除 GUID：任务结束后表格会自动刷新，
  被删除或转换的对象会从列表移除，必要时重新在 Wwise 中获取。
- 当前只暴露了表格批量操作所需的一批工具；`waapi_utils` 中查询父级/子级/引用、
  语言、SoundBank 等大量函数尚未对 AI 开放。若希望 AI 能回答“这个被谁引用 / 它的子级有哪些”
  这类查询，需要先补充对应工具并登记到对照表。
