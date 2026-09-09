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
| QRadioButton | `rdo` | rdoEventAll、rdoLangActive |
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
