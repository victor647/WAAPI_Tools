from PySide6.QtWidgets import QDialog, QWidget
from qt_material import list_themes

from data import project_conventions
from libraries.utils import ai_utils, user_config
from libraries.utils.log_utils import Logger
from ui.ProjectSettings_ui import Ui_ProjectSettings

AI_MODE_KEYS = ("proxy", "official")
AI_MODE_LABELS = ("代理模式", "官方 API 模式")

# AI 修改策略下拉框：键与 user_config.MUTATION_POLICIES 对应
AI_MUTATION_POLICY_KEYS = user_config.MUTATION_POLICIES
AI_MUTATION_POLICY_LABELS = ("只读（不改工程）", "改动前弹窗确认", "直接执行（不询问）")

# 角色表首列显示文案，内部键仍是 1P/2P/3P
NET_ROLE_LABELS = {"1P": "1P（主角）", "2P": "2P（队友）", "3P": "3P（敌人）"}


# 把表格里的角色文案还原成内部键；自定义角色原样返回
def net_role_key(text: str) -> str:
    for key, label in NET_ROLE_LABELS.items():
        if text == label:
            return key
    return text.strip()


# 工程规范设置窗口：把 project_conventions.json 的分段配置做成可视化 Tab 编辑
class ProjectSettingsWindow(QDialog, Ui_ProjectSettings):

    def __init__(self, parent: QWidget = None, on_ai_saved=None, on_theme_applied=None):
        super().__init__(parent)
        self.setupUi(self)
        self._on_ai_saved = on_ai_saved
        self._on_theme_applied = on_theme_applied
        # 内存里还没有规范数据时先兜底加载，避免表格空白被当成空配置保存回去
        if not project_conventions.conventions:
            project_conventions.init()
        self.__conventions = dict(project_conventions.conventions or {})
        self.categoryMap.set_headers(["分类名", "缩写", "颜色值"])
        self.containerSuffix.set_headers(["容器类型", "后缀"])
        self.netRoleValues.set_headers(["角色", "Switch 名称", "对象名后缀", "Bus后缀"])
        # 容器后缀与角色映射不允许增删行，只可编辑单元格；键列（首列）只读
        self.containerSuffix.set_fixed_rows(True)
        self.containerSuffix.set_first_column_readonly(True)
        self.netRoleValues.set_fixed_rows(True)
        self.netRoleValues.set_first_column_readonly(True)
        # 角色表只有 1P/2P/3P 三行，固定成刚好三行的高度
        self.netRoleValues.set_fixed_row_count(3)
        self.cbxAutoFetchChildren.setChecked(user_config.get_tool_auto_fetch_children())
        self.spbPageSize.setValue(user_config.get_tool_page_size())
        self.spbLoudnessBuffer.setValue(user_config.get_tool_loudness_buffer_samples())
        self.cbxPathDisplayCompact.setChecked(user_config.get_tool_path_display_compact())
        self.cbbAiMode.addItems(list(AI_MODE_LABELS))
        self.cbbAiMutationPolicy.addItems(list(AI_MUTATION_POLICY_LABELS))
        self.cbbAiProvider.addItems([info["label"] for info in ai_utils.PROVIDERS.values()])
        self.setup_triggers()
        self.__load_values()
        self.__load_ai_values()
        self.__load_theme_values()

    # 绑定按钮与复选框信号槽
    def setup_triggers(self):
        self.btnSave.clicked.connect(self.save_settings)
        self.btnCancel.clicked.connect(self.reject)
        self.cbxEnableAcronym.toggled.connect(self._on_regulation_switch_toggled)
        self.cbxEnableColor.toggled.connect(self._on_regulation_switch_toggled)
        self.cbxEnableNameCase.toggled.connect(self._on_regulation_switch_toggled)
        self.cbxEnablePathLength.toggled.connect(self._on_regulation_switch_toggled)
        self.cbxAutoDefinedBank.toggled.connect(self._on_bank_switch_toggled)
        self.cbxAutoFetchChildren.toggled.connect(user_config.set_tool_auto_fetch_children)
        self.spbPageSize.valueChanged.connect(user_config.set_tool_page_size)
        self.spbLoudnessBuffer.valueChanged.connect(user_config.set_tool_loudness_buffer_samples)
        self.cbxPathDisplayCompact.toggled.connect(user_config.set_tool_path_display_compact)
        self.cbbAiMode.currentIndexChanged.connect(self.__update_ai_controls_state)
        self.cbbAiProvider.currentIndexChanged.connect(self.__update_ai_controls_state)
        self.cbbTheme.currentTextChanged.connect(self._on_theme_changed)

    # 缩写/颜色规范开关：仅禁用分类表中对应列（缩写 / 颜色值）
    def _on_regulation_switch_toggled(self, _checked: bool):
        self.__update_naming_columns_enabled()

    # Bank 设置开关：未使用自动定义的 Bank 时才允许选择是否拆分 Event/Media
    def _on_bank_switch_toggled(self, _checked: bool):
        self.__update_bank_controls_enabled()

    def __update_bank_controls_enabled(self):
        self.cbxSplitEventMedia.setEnabled(not self.cbxAutoDefinedBank.isChecked())

    def __update_naming_columns_enabled(self):
        self.categoryMap.set_column_readonly(1, not self.cbxEnableAcronym.isChecked())
        self.categoryMap.set_column_readonly(2, not self.cbxEnableColor.isChecked())
        # 深浅色标记隶属颜色规范，规范关闭时该开关不可用
        self.cbxEventRefDarkColor.setEnabled(self.cbxEnableColor.isChecked())
        # 大小写方式隶属名称大小写规范，规范关闭时下拉框不可用
        self.cbbNameCase.setEnabled(self.cbxEnableNameCase.isChecked())
        # 「Sound 节点使用完整名称」隶属路径长度规范，规范关闭时该开关不可用
        self.cbxFullNameInSound.setEnabled(self.cbxEnablePathLength.isChecked())

    # 填充 qt_material 主题列表并选中当前配置主题
    def __load_theme_values(self):
        themes = sorted(list_themes())
        self.cbbTheme.blockSignals(True)
        self.cbbTheme.clear()
        self.cbbTheme.addItems(themes)
        default_theme = user_config.DEFAULT_CONFIG["appearance"]["theme"]
        index = self.cbbTheme.findText(user_config.get_appearance_theme())
        if index < 0:
            index = self.cbbTheme.findText(default_theme)
        if index < 0 and themes:
            index = 0
        if index >= 0:
            self.cbbTheme.setCurrentIndex(index)
        self.cbbTheme.blockSignals(False)

    # 主题切换：保存配置并通知主窗口立即应用
    def _on_theme_changed(self, theme: str):
        if not theme:
            return
        user_config.save_appearance_theme(theme)
        if self._on_theme_applied:
            self._on_theme_applied(theme)

    # 从当前规范数据填充控件
    def __load_values(self):
        conventions = self.__conventions
        self.cbxEnableAcronym.setChecked(project_conventions.is_acronym_enabled())
        self.cbxEnableColor.setChecked(project_conventions.is_color_enabled())
        self.cbxEventRefDarkColor.setChecked(project_conventions.use_dark_color_for_event_ref())
        self.cbxEnableNameCase.setChecked(project_conventions.is_name_case_enabled())
        self.cbxEnablePathLength.setChecked(project_conventions.is_path_length_enabled())
        self.cbxAutoDefinedBank.setChecked(project_conventions.use_auto_defined_bank())
        self.cbxSplitEventMedia.setChecked(project_conventions.get_split_event_media_setting())
        mode = project_conventions.get_name_case_mode()
        self.cbbNameCase.setCurrentIndex(project_conventions.NAME_CASE_MODES.index(mode))
        self.__update_naming_columns_enabled()
        self.__update_bank_controls_enabled()
        acronym_map = project_conventions.get_acronym_map()
        color_map = project_conventions.get_color_map()
        container_suffix = conventions.get("ContainerSuffix", {}) or {}
        net_role = conventions.get("NetRole") or {}
        net_role_suffix = net_role.get("Suffix") or {}
        net_role_bus_suffix = net_role.get("BusSuffix") or {}
        net_role_values = net_role.get("SwitchValues") or {}

        category_keys = sorted(set(acronym_map) | set(color_map))
        category_rows = [
            (key, acronym_map.get(key, ""), str(color_map.get(key, "")))
            for key in category_keys
        ]
        self.categoryMap.set_data(category_rows)
        self.containerSuffix.set_data(list(container_suffix.items()))
        default_suffixes = {"1P": "_1P", "2P": "_2P", "3P": "_3P"}
        name_suffixes = {key: net_role_suffix.get(key, default_suffixes[key]) for key in default_suffixes}
        # Bus 后缀未配置时默认跟随对象名后缀
        bus_suffixes = {key: net_role_bus_suffix.get(key) or name_suffixes[key] for key in default_suffixes}
        self.iptNetRoleGroup.setText(str(net_role.get("SwitchGroup", "Net_Role")))
        role_rows = [
            (NET_ROLE_LABELS.get(role, role), net_role_values.get(role, ""),
             name_suffixes.get(role, default_suffixes.get(role, "")),
             bus_suffixes.get(role, default_suffixes.get(role, "")))
            for role in sorted(set(net_role_values) | set(net_role_suffix) | set(net_role_bus_suffix))
        ] or [
            (NET_ROLE_LABELS[role], role, default_suffixes[role], default_suffixes[role])
            for role in ("1P", "2P", "3P")
        ]
        self.netRoleValues.set_data(role_rows)
        languages = conventions.get("UnimplementedLanguages", [])
        self.iptLanguages.setText(";".join(str(item) for item in languages))
        self.cbxFullNameInSound.setChecked(project_conventions.use_full_name_in_sound())
        self.cbxPlayPrefixInEvent.setChecked(project_conventions.has_event_play_prefix())
        self.cbxEventRefNotes.setChecked(project_conventions.use_event_ref_notes())

    # 从 user_config.json 的 ai 节填充 AI 设置
    def __load_ai_values(self):
        ai = user_config.get_ai_config()
        mode = ai.get("mode") if ai.get("mode") in AI_MODE_KEYS else AI_MODE_KEYS[0]
        self.cbbAiMode.setCurrentIndex(AI_MODE_KEYS.index(mode))
        policy = ai.get("mutation_policy")
        if policy not in AI_MUTATION_POLICY_KEYS:
            policy = user_config.DEFAULT_CONFIG["ai"]["mutation_policy"]
        self.cbbAiMutationPolicy.setCurrentIndex(AI_MUTATION_POLICY_KEYS.index(policy))
        provider_keys = list(ai_utils.PROVIDERS)
        provider = ai.get("provider") if ai.get("provider") in provider_keys else provider_keys[0]
        self.cbbAiProvider.setCurrentIndex(provider_keys.index(provider))
        self.iptAiProxy.setText(ai.get("proxy", ""))
        self.iptAiBaseUrl.setText(ai.get("base_url", ""))
        self.iptAiApiKey.setText(ai.get("api_key", ""))
        self.iptAiModel.setText(ai.get("model", ""))
        self.cbxAiEnableScript.setChecked(bool(ai.get("enable_script_tool", False)))
        self.spnAiMaxContext.setValue(int(ai.get("max_context_objects") or 300))
        self.spnAiMaxTurns.setValue(int(ai.get("max_turns") or 20))
        self.__update_ai_controls_state()

    # 隐藏当前模式下不适用的行：代理模式只显示代理地址；官方模式只在“自定义”时显示自定义地址
    def __set_ai_row_visible(self, row: int, label: QWidget, field: QWidget, visible: bool):
        if hasattr(self.aiForm, "setRowVisible"):
            self.aiForm.setRowVisible(row, visible)
        else:
            label.setVisible(visible)
            field.setVisible(visible)

    def __update_ai_controls_state(self):
        provider_keys = list(ai_utils.PROVIDERS)
        mode = AI_MODE_KEYS[self.cbbAiMode.currentIndex()] if self.cbbAiMode.currentIndex() >= 0 else "proxy"
        provider = provider_keys[self.cbbAiProvider.currentIndex()] if self.cbbAiProvider.currentIndex() >= 0 else "openai"
        is_official = mode == "official"
        self.__set_ai_row_visible(1, self.lblAiProvider, self.cbbAiProvider, is_official)
        self.__set_ai_row_visible(2, self.lblAiProxy, self.iptAiProxy, not is_official)
        self.__set_ai_row_visible(3, self.lblAiBaseUrl, self.iptAiBaseUrl, is_official and provider == "custom")

    # 保存 AI 设置到 user_config.json，并通知主窗口同步模型下拉框
    def save_ai_settings(self):
        defaults = user_config.DEFAULT_CONFIG["ai"]
        provider_keys = list(ai_utils.PROVIDERS)
        patch = {
            "mode": AI_MODE_KEYS[self.cbbAiMode.currentIndex()] if self.cbbAiMode.currentIndex() >= 0 else defaults["mode"],
            "provider": provider_keys[self.cbbAiProvider.currentIndex()] if self.cbbAiProvider.currentIndex() >= 0 else defaults["provider"],
            "proxy": self.iptAiProxy.text().strip() or defaults["proxy"],
            "base_url": self.iptAiBaseUrl.text().strip(),
            "api_key": self.iptAiApiKey.text(),
            "model": self.iptAiModel.text().strip(),
            "enable_script_tool": bool(self.cbxAiEnableScript.isChecked()),
            "mutation_policy": (
                AI_MUTATION_POLICY_KEYS[self.cbbAiMutationPolicy.currentIndex()]
                if self.cbbAiMutationPolicy.currentIndex() >= 0
                else defaults["mutation_policy"]
            ),
            "max_context_objects": int(self.spnAiMaxContext.value()),
            "max_turns": int(self.spnAiMaxTurns.value()),
        }
        if patch["mode"] == "official" and patch["provider"] == "anthropic" and not patch["model"]:
            Logger().warning("Anthropic 官方模式必须填写模型名，否则发送时会报错")
        user_config.save_ai_config(patch)
        if self._on_ai_saved:
            self._on_ai_saved()

    # 收集并保存
    def save_settings(self):
        self.save_ai_settings()
        new_conventions = dict(self.__conventions)
        acronym_map = {}
        color_map = {}
        for category, acronym, color_text in self.categoryMap.rows():
            if acronym:
                acronym_map[category] = acronym
            if color_text:
                try:
                    color_map[category] = int(color_text)
                except ValueError:
                    Logger().warning(f"颜色值「{color_text}」不是整数，已跳过 {category}")
        # 每个规范独立成一个节点：Enabled 开关 + 对应数据表
        new_conventions["AcronymConvention"] = {
            "Enabled": self.cbxEnableAcronym.isChecked(),
            "AcronymMap": acronym_map,
        }
        new_conventions["ColorConvention"] = {
            "Enabled": self.cbxEnableColor.isChecked(),
            "ColorMap": color_map,
        }
        case_index = self.cbbNameCase.currentIndex()
        case_mode = (project_conventions.NAME_CASE_MODES[case_index]
                     if 0 <= case_index < len(project_conventions.NAME_CASE_MODES)
                     else project_conventions.DEFAULT_NAME_CASE_MODE)
        new_conventions["NameCaseConvention"] = {
            "Enabled": self.cbxEnableNameCase.isChecked(),
            "Mode": case_mode,
        }
        # 「Sound 节点使用完整名称」隶属路径长度规范
        new_conventions["PathLengthConvention"] = {
            "Enabled": self.cbxEnablePathLength.isChecked(),
            "FullNameInSound": self.cbxFullNameInSound.isChecked(),
        }
        new_conventions["BankConvention"] = {
            "UseAutoDefinedBank": self.cbxAutoDefinedBank.isChecked(),
            "SplitEventMedia": self.cbxSplitEventMedia.isChecked(),
        }
        # 清理旧的顶层平铺字段
        for legacy_key in ("AcronymMap", "ColorMap", "EnableAcronym", "EnableColor",
                           "EnableNameCase", "EnablePathLength", "EnableAcronymColor",
                           "FullNameInSound", "PlayPrefixInEvent", "EventRefNotes"):
            new_conventions.pop(legacy_key, None)
        new_conventions["ContainerSuffix"] = dict(self.containerSuffix.rows())

        value_rows = self.netRoleValues.rows()
        default_suffixes = {"1P": "_1P", "2P": "_2P", "3P": "_3P"}
        roles = {"1P", "2P", "3P"}
        for row in value_rows:
            if row and row[0]:
                roles.add(net_role_key(row[0]))
        switch_values = {}
        suffixes = {}
        bus_suffixes = {}
        for role in sorted(roles):
            row = next((r for r in value_rows if r and net_role_key(r[0]) == role), None)
            if row and len(row) > 1 and row[1]:
                switch_values[role] = row[1]
            if row and len(row) > 2 and row[2]:
                suffixes[role] = row[2]
            else:
                suffixes[role] = default_suffixes.get(role, "_" + role)
            if row and len(row) > 3 and row[3]:
                bus_suffixes[role] = row[3]
            else:
                bus_suffixes[role] = suffixes[role]
        if not switch_values:
            switch_values = {"1P": "1P", "2P": "2P", "3P": "3P"}
        new_conventions["NetRole"] = {
            "Suffix": suffixes,
            "BusSuffix": bus_suffixes,
            "SwitchGroup": self.iptNetRoleGroup.text().strip() or "Net_Role",
            "SwitchValues": switch_values,
        }
        languages = [
            item.strip()
            for line in self.iptLanguages.text().splitlines()
            for item in line.split(";")
            if item.strip()
        ]
        new_conventions.pop("ImplementedLanguages", None)
        new_conventions["UnimplementedLanguages"] = languages
        # Event 设置：事件命名前缀、引用对象深色、引用备注
        new_conventions["EventConvention"] = {
            "PlayPrefix": self.cbxPlayPrefixInEvent.isChecked(),
            "RefDarkColor": self.cbxEventRefDarkColor.isChecked(),
            "RefNotes": self.cbxEventRefNotes.isChecked(),
        }

        if project_conventions.save_conventions(new_conventions):
            Logger().info("工程规范设置已保存")
            self.accept()
