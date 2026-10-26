# UI 窗口开发流程（Qt Designer + pyuic）

新建任何 `windows/*_window.py` 窗口（对话框、主窗口等）时，必须遵循以下流程：

1. 先在 `ui/` 目录创建对应的 `<Name>.ui` 文件（用 Qt Designer 编辑布局）。
2. 用 pyuic 生成 Python 代码：
   ```text
   pyside6-uic ui/<Name>.ui -o ui/<Name>_ui.py
   ```
3. 窗口类继承生成的 UI 类并调用 `setupUi`：
   ```python
   from ui.<Name>_ui import Ui_<Name>

   class XxxWindow(QDialog, Ui_<Name>):
       def __init__(self, parent=None):
           super().__init__(parent)
           self.setupUi(self)
   ```
4. 不要在窗口的逻辑代码里手工添加控件、布局、菜单等 UI 结构；布局一律放进 `.ui`。
5. `_window.py` 里只保留：信号连接（setup triggers）、运行时数据填充/状态同步、业务逻辑。
6. 所有按钮 / action / 控件（复选、下拉、输入框等）的信号绑定统一放进 `setup_triggers` 方法，由 `__init__` 调用；不要在 `__init__` 或其它方法里散落 `connect`。

补充约定：
- 修改已有窗口的布局时同样只能改 `ui/<Name>.ui`，然后重新用 pyuic 生成 `ui/<Name>_ui.py`，不要直接在窗口逻辑代码里调整控件/布局。
- 自定义可复用控件（如波形图、表格编辑器）放在独立模块（例如 `libraries/widgets/`），在 `.ui` 中用 promoted widget 引用（`<customwidget>` header 指向该模块），避免 ui ↔ window 循环导入。
- 修改已有 `.ui` 后必须重新运行 pyuic 并保持 `ui/*_ui.py` 与 `.ui` 同步，不要手改生成的 `_ui.py`。

## 控件 objectName 命名前缀

`.ui` 中控件 objectName 统一使用“类型缩写 + 语义名（驼峰）”：

| Qt 类型 | 前缀 | 示例 |
| --- | --- | --- |
| QAction | `act` | actExportObjectList、actClearInclusions |
| QPushButton | `btn` | btnSave、btnFindChildren |
| QComboBox | `cbb` | cbbFilterType、cbbTableDisplayMode |
| QCheckBox | `cbx` | cbxTurboMode、cbxOnlyIncludedEnabled |
| QLabel | `lbl` | lblWwiseConnection、lblInfo |
| QRadioButton | `rbn` | rbnEventAll、rbnLangActive |
| QLineEdit | `ipt` | iptFindName、iptNetRole1P |
| QPlainTextEdit | `pte` | pteLanguages |
| QTextEdit | `txe` | txeOutputLogs |
| QSpinBox | `spb` | spbTrimHeadThreshold |
| QTableView / QTableWidget | `tbl` | tblWwiseObjects、tblMatrix |
| QGroupBox | `grp` | grpFindFilter、grpTableAction |
| QMenu | `mnu` | mnuFile、mnuAudioEdit |
| QTabWidget 页面 | `tab` | tabNaming、tabHabits |
| 自定义控件 / 容器 | 语义名 | waveform、categoryMap |

说明：
- 主窗口中的即时筛选/提示输入沿用历史 `led` 前缀（如 `ledFilterKeyword`、`ledAiPrompt`），不改名；新窗口普通单行输入统一用 `ipt`。
- `QTabWidget` 主容器本身可用通用名 `tabWidget`。
- 窗口逻辑代码中引用的属性名与 objectName 一致（由 `setupUi` 自动生成）。

## 表格路径列与右键菜单（强制）

任何显示 Wwise 对象路径的表格都必须使用同一套实现，禁止在窗口里各写一套：

### 路径单元格

```python
from libraries.table_view.table_path_item import create_path_item

path_item = create_path_item(obj.path)
self.tblResult.setItem(row, COL_PATH, path_item)
```

- `create_path_item` 内部调用 `path_utils.get_display_path`，统一遵循「路径隐藏根目录 / 路径显示简写」设置。
- 显示文本是缩写路径，完整路径保存在 Tooltip 和 `Qt.UserRole`。
- 不要直接 `QTableWidgetItem(obj.path)`，否则会显示原始长路径。
- 使用 `WwiseTableRowData` 的模型表格沿用 `get_path_text` / `set_path_cell`，它们已经接入了同一套路径显示逻辑。
- 路径列使用 `Stretch` 或 `Interactive`；名称列不要用 `ResizeToContents` 让长名称撑宽，避免把路径/指标列挤出窗口。

### 右键菜单与复制

```python
from table.wwise_table_context_menu import add_common_object_actions, connect_double_click_select

self.tblResult.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
self.tblResult.customContextMenuRequested.connect(self.show_context_menu)
connect_double_click_select(self.tblResult, self.objects_at_row)
```

- 行的通用动作统一用 `add_common_object_actions`（在 Wwise 中选中、复制名称、复制路径）。
- 若需要按列复制，路径列必须复制 `Qt.UserRole` 中的完整路径，不能复制缩写后的显示文本；名称列复制名称，其它列复制单元格文本。
- 窗口只追加自己的专属动作，不要重复实现通用动作。

### 提交前检查

- [ ] 路径单元格使用 `create_path_item`。
- [ ] 完整路径在 Tooltip / `UserRole` 中可取得，复制路径不复制缩写文本。
- [ ] 右键菜单使用 `add_common_object_actions`。
- [ ] 双击选中使用 `connect_double_click_select`。
- [ ] 名称/路径列宽度合理，路径列不会因长名称被挤出窗口。

## 窗口设置持久化

所有允许用户在界面上设置的选项（开关、数值、下拉选择、单选模式等）都必须保存到 `user_config`，并**以窗口为节点**管理：

- 使用 `user_config.get_window_settings(<window_key>)` 读取、`user_config.set_window_settings(<window_key>, {...})` 写入；数据保存在 `user_config.json` 的 `window_settings.<window_key>` 下。
- `<window_key>` 用窗口的语义名，例如裁剪工具用 `audio_silence_trim`。
- 打开窗口时在 `__init__` 里调用一次“读取并回填控件”的方法（如 `load_user_settings`）；关闭窗口（`closeEvent`）或选项变化时保存（如 `save_user_settings`）。
- 界面新增任何可设置项时，必须同步加入读取与保存逻辑，不要只存内存不落盘。
