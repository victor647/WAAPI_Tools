from PySide6.QtWidgets import QDialog, QWidget
from PySide6.QtWidgets import QButtonGroup
from qt_material import list_themes

from data import project_conventions
from libraries.utils import ai_utils, audio_utils, user_config, vcs_utils
from libraries.utils.log_utils import Logger
from ui.ProjectSettings_ui import Ui_ProjectSettings

AI_MODE_KEYS = ("proxy", "official")
AI_MODE_LABELS = ("代理模式", "官方 API 模式")

# AI 修改策略下拉框：键与 user_config.MUTATION_POLICIES 对应
AI_MUTATION_POLICY_KEYS = user_config.MUTATION_POLICIES
AI_MUTATION_POLICY_LABELS = ("只读（不改工程）", "改动前弹窗确认", "直接执行（不询问）")

# 响度标准下拉项（顺序与 .ui 一致）
LOUDNESS_STANDARDS = (audio_utils.LoudnessStandard.RMS, audio_utils.LoudnessStandard.LUFS)

# 版本控制类型下拉项（顺序与 project_conventions.VCS_MODES 一致）
VCS_MODE_LABELS = ("Perforce (P4)", "Subversion (SVN)")

# 界面缩放下拉项：键与 user_config.appearance.ui_scale 一致（auto=跟随系统）
UI_SCALE_KEYS = ("auto", "100", "125", "150", "175", "200")
UI_SCALE_LABELS = ("跟随系统", "100%", "125%", "150%", "175%", "200%")

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
        self.cbxDetailLog.setChecked(user_config.get_tool_detail_log_enabled())
        self.spbPageSize.setValue(user_config.get_tool_page_size())
        self.spbConversionDominance.setValue(
            int(round(user_config.get_tool_conversion_dominance_ratio() * 100))
        )
        self.spbLoudnessBuffer.setValue(user_config.get_tool_loudness_buffer_samples())
        self.cbxPathDisplayCompact.setChecked(user_config.get_tool_path_display_compact())
        self.cbxPathHideRoot.setChecked(user_config.get_tool_path_hide_root())
        self.cbbAiMode.addItems(list(AI_MODE_LABELS))
        self.cbbAiMutationPolicy.addItems(list(AI_MUTATION_POLICY_LABELS))
        self.cbbAiProvider.addItems([info["label"] for info in ai_utils.PROVIDERS.values()])
        self.cbbVcsMode.addItems(list(VCS_MODE_LABELS))
        self.cbbUiScale.addItems(list(UI_SCALE_LABELS))
        self.setup_triggers()
        self.__load_values()
        self.__load_ai_values()
        self.__load_theme_values()
        self.__load_ui_scale_value()
        self.__load_window_settings()
        self.__load_vcs_values()

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
        self.cbxDetailLog.toggled.connect(user_config.set_tool_detail_log_enabled)
        self.spbPageSize.valueChanged.connect(user_config.set_tool_page_size)
        self.spbConversionDominance.valueChanged.connect(self._on_conversion_dominance_changed)
        self.spbLoudnessBuffer.valueChanged.connect(user_config.set_tool_loudness_buffer_samples)
        self.cbxPathDisplayCompact.toggled.connect(user_config.set_tool_path_display_compact)
        self.cbxPathHideRoot.toggled.connect(user_config.set_tool_path_hide_root)
        self.cbbAiMode.currentIndexChanged.connect(self.__update_ai_controls_state)
        self.cbbAiProvider.currentIndexChanged.connect(self.__update_ai_controls_state)
        self.cbbTheme.currentTextChanged.connect(self._on_theme_changed)
        self.cbbUiScale.currentIndexChanged.connect(self._on_ui_scale_changed)
        self.cbbVcsMode.currentIndexChanged.connect(self.__update_vcs_controls_state)
        self.btnVcsTest.clicked.connect(self._on_vcs_test_clicked)
        # 工具窗口设置（统一编辑入口）
        self.__grp_event = QButtonGroup(self)
        self.__grp_event.addButton(self.rbnEventAll)
        self.__grp_event.addButton(self.rbnEventHas)
        self.__grp_event.addButton(self.rbnEventNo)

        self.__grp_lang = QButtonGroup(self)
        self.__grp_lang.addButton(self.rbnLangAll)
        self.__grp_lang.addButton(self.rbnLangActive)

        self.cbxKeepSelf.toggled.connect(self._on_keep_self_toggled)
        self.cbxCaseSensitive.toggled.connect(self._on_case_sensitive_toggled)
        self.cbxOnlyIncluded.toggled.connect(self._on_only_included_toggled)
        self.cbxOnlyInUse.toggled.connect(self._on_only_in_use_toggled)
        self.rbnEventAll.toggled.connect(self._on_event_filter_toggled)
        self.rbnEventHas.toggled.connect(self._on_event_filter_toggled)
        self.rbnEventNo.toggled.connect(self._on_event_filter_toggled)
        self.rbnLangAll.toggled.connect(self._on_lang_filter_toggled)
        self.rbnLangActive.toggled.connect(self._on_lang_filter_toggled)

        self.cbbLoudnessStandard.currentIndexChanged.connect(self._save_loudness_settings)
        self.spbTargetLoudness.valueChanged.connect(self._save_loudness_settings)
        self.spbLoudnessTolerance.valueChanged.connect(self._save_loudness_settings)
        self.cbbPreviewDisplayMode.currentIndexChanged.connect(self._save_preview_settings)
        self.cbxUseDefaultReferenceLanguage.toggled.connect(self._on_use_default_reference_language_toggled)
        self.ledReferenceLanguage.textChanged.connect(self._save_reference_language)

    # 自动转码占优比例：界面用百分数，配置里存 0~1 的比例
    def _on_conversion_dominance_changed(self, percent: int):
        user_config.set_tool_conversion_dominance_ratio(percent / 100)

    # 各工具窗口持久化的设置（统一在这里编辑，工具窗口内的入口保持不变）
    def __load_window_settings(self):
        loudness = user_config.get_window_settings('loudness_adjustment')
        standard_name = str(loudness.get('loudness_standard', audio_utils.LoudnessStandard.RMS.value))
        index = next((i for i, item in enumerate(LOUDNESS_STANDARDS) if item.value == standard_name), 0)
        self.cbbLoudnessStandard.setCurrentIndex(index)
        self.spbTargetLoudness.setValue(int(loudness.get('target_loudness_db', self.spbTargetLoudness.value())))
        self.spbLoudnessTolerance.setValue(
            float(loudness.get('tolerance_db', self.spbLoudnessTolerance.value())))

        preview = user_config.get_window_settings('audio_preview')
        self.cbbPreviewDisplayMode.setCurrentIndex(
            1 if preview.get('display_mode') == 'spectrum' else 0)

        self.cbxUseDefaultReferenceLanguage.setChecked(user_config.get_reference_language_use_default())
        self.ledReferenceLanguage.setText(user_config.get_configured_reference_language())
        self.__sync_reference_language_state()

        find_settings = user_config.get_advanced_find_settings()
        self.cbxKeepSelf.setChecked(bool(find_settings.get("keep_self", False)))

        filter_settings = user_config.get_advanced_filter_settings()
        self.cbxCaseSensitive.setChecked(bool(filter_settings.get("case_sensitive", False)))
        self.cbxOnlyIncluded.setChecked(bool(filter_settings.get("only_included", False)))
        self.cbxOnlyInUse.setChecked(bool(filter_settings.get("only_in_use", False)))

        ev_val = filter_settings.get("event_filter", "all")
        self.rbnEventAll.setChecked(ev_val == "all")
        self.rbnEventHas.setChecked(ev_val == "with_ref")
        self.rbnEventNo.setChecked(ev_val == "without_ref")

        lang_val = filter_settings.get("language_filter", "all")
        self.rbnLangAll.setChecked(lang_val == "all")
        self.rbnLangActive.setChecked(lang_val == "active")

    # 合并写入某个窗口节点（保留该节点里的其它键）
    @staticmethod
    def __save_window_settings(node: str, patch: dict):
        current = dict(user_config.get_window_settings(node))
        current.update(patch)
        user_config.set_window_settings(node, current)

    # 版本控制设置：读入类型与对应客户端字段（存在工程规范文件的 VersionControl 节点，随工程走）
    def __load_vcs_values(self):
        mode = project_conventions.get_version_control_mode()
        index = project_conventions.VCS_MODES.index(mode) if mode in project_conventions.VCS_MODES else 0
        self.cbbVcsMode.blockSignals(True)
        self.cbbVcsMode.setCurrentIndex(index)
        self.cbbVcsMode.blockSignals(False)
        self.iptP4Server.setText(project_conventions.get_p4_server())
        self.iptP4Charset.setText(project_conventions.get_p4_charset())
        self.iptP4ChangelistDescription.setText(project_conventions.get_p4_changelist_description())
        self.iptSvnExecutable.setText(project_conventions.get_svn_executable())
        self.iptSvnUsername.setText(project_conventions.get_svn_username())
        self.iptSvnPassword.setText(project_conventions.get_svn_password())
        self.iptSvnCommitMessage.setText(project_conventions.get_svn_commit_message())
        self.__update_vcs_controls_state()

    # 只显示当前版本控制类型对应的字段
    def __set_vcs_row_visible(self, row: int, label: QWidget, field: QWidget, visible: bool):
        if hasattr(self.vcsForm, "setRowVisible"):
            self.vcsForm.setRowVisible(row, visible)
        else:
            label.setVisible(visible)
            field.setVisible(visible)

    def __update_vcs_controls_state(self, *_args):
        is_p4 = self.cbbVcsMode.currentIndex() != 1
        for row, (label, field) in enumerate((
                (self.lblP4Server, self.iptP4Server),
                (self.lblP4Charset, self.iptP4Charset),
                (self.lblP4ChangelistDescription, self.iptP4ChangelistDescription)), start=1):
            self.__set_vcs_row_visible(row, label, field, is_p4)
        for row, (label, field) in enumerate((
                (self.lblSvnExecutable, self.iptSvnExecutable),
                (self.lblSvnUsername, self.iptSvnUsername),
                (self.lblSvnPassword, self.iptSvnPassword),
                (self.lblSvnCommitMessage, self.iptSvnCommitMessage)), start=4):
            self.__set_vcs_row_visible(row, label, field, not is_p4)

    # 把「版本控制」Tab 的内容写进内存里的工程规范（保存规范文件时一并落盘）
    def __apply_vcs_to_conventions(self):
        index = self.cbbVcsMode.currentIndex()
        mode = (project_conventions.VCS_MODES[index]
                if 0 <= index < len(project_conventions.VCS_MODES)
                else project_conventions.DEFAULT_VCS_MODE)
        self.__conventions["VersionControl"] = {
            "Mode": mode,
            "P4": {
                "Server": self.iptP4Server.text().strip(),
                "Charset": self.iptP4Charset.text().strip() or project_conventions.DEFAULT_P4_CHARSET,
                "ChangelistDescription": self.iptP4ChangelistDescription.text().strip()
                                          or project_conventions.DEFAULT_P4_CHANGELIST_DESCRIPTION,
            },
            "SVN": {
                "Executable": self.iptSvnExecutable.text().strip() or project_conventions.DEFAULT_SVN_EXECUTABLE,
                "Username": self.iptSvnUsername.text().strip(),
                "Password": self.iptSvnPassword.text(),
                "CommitMessage": self.iptSvnCommitMessage.text().strip()
                                 or project_conventions.DEFAULT_SVN_COMMIT_MESSAGE,
            },
        }
        # 设置变了，之前的可用性与作者缓存作废
        vcs_utils.clear_cache()

    # 测试版本控制连接：先把当前填写内容写进规范文件（不关窗口），再探测一次
    def _on_vcs_test_clicked(self):
        self.__apply_vcs_to_conventions()
        if not project_conventions.save_conventions(dict(self.__conventions)):
            Logger().error("版本控制设置保存失败，无法测试连接")
            return
        mode_label = self.cbbVcsMode.currentText()
        if vcs_utils.is_available():
            Logger().info(f"版本控制连接正常：{mode_label}")
        else:
            Logger().error(f"版本控制连接失败：{mode_label}，请检查上面的设置（上面日志里有具体原因）")

    def _save_loudness_settings(self, *_args):
        self.__save_window_settings('loudness_adjustment', {
            'loudness_standard': LOUDNESS_STANDARDS[self.cbbLoudnessStandard.currentIndex()].value,
            'target_loudness_db': self.spbTargetLoudness.value(),
            'tolerance_db': self.spbLoudnessTolerance.value(),
        })

    def _save_preview_settings(self, *_args):
        self.__save_window_settings('audio_preview', {
            'display_mode': 'spectrum' if self.cbbPreviewDisplayMode.currentIndex() == 1 else 'wave',
        })

    # 勾选「使用工程默认」时禁用手填输入框
    def __sync_reference_language_state(self):
        use_default = self.cbxUseDefaultReferenceLanguage.isChecked()
        self.ledReferenceLanguage.setEnabled(not use_default)

    def _on_keep_self_toggled(self, checked: bool):
        user_config.save_advanced_find_settings({"keep_self": bool(checked)})
        main = self.parent()
        if main and hasattr(main, "cbxKeepSelf"):
            main.cbxKeepSelf.setChecked(checked)

    def _on_case_sensitive_toggled(self, checked: bool):
        user_config.save_advanced_filter_settings({"case_sensitive": bool(checked)})
        main = self.parent()
        if main and hasattr(main, "cbxCaseSensitive"):
            main.cbxCaseSensitive.setChecked(checked)

    def _on_only_included_toggled(self, checked: bool):
        user_config.save_advanced_filter_settings({"only_included": bool(checked)})
        main = self.parent()
        if main and hasattr(main, "cbxOnlyIncludedEnabled"):
            main.cbxOnlyIncludedEnabled.setChecked(checked)

    def _on_only_in_use_toggled(self, checked: bool):
        user_config.save_advanced_filter_settings({"only_in_use": bool(checked)})
        main = self.parent()
        if main:
            if checked and hasattr(main, "apply_in_use_filter"):
                main.apply_in_use_filter()
            elif hasattr(main, "apply_table_filter"):
                main.apply_table_filter(True)

    def _on_event_filter_toggled(self, checked: bool):
        if not checked:
            return
        val = "all"
        if self.rbnEventHas.isChecked():
            val = "with_ref"
        elif self.rbnEventNo.isChecked():
            val = "without_ref"
        user_config.save_advanced_filter_settings({"event_filter": val})
        main = self.parent()
        if main:
            if val == "with_ref" and hasattr(main, "filter_by_event_reference"):
                main.filter_by_event_reference(True)
            elif val == "without_ref" and hasattr(main, "filter_by_event_reference"):
                main.filter_by_event_reference(False)
            elif hasattr(main, "reset_event_reference_filter"):
                main.reset_event_reference_filter()

    def _on_lang_filter_toggled(self, checked: bool):
        if not checked:
            return
        val = "active" if self.rbnLangActive.isChecked() else "all"
        user_config.save_advanced_filter_settings({"language_filter": val})
        main = self.parent()
        if main:
            if val == "active" and hasattr(main, "filter_by_active_language"):
                main.filter_by_active_language()
            elif hasattr(main, "reset_active_language_filter"):
                main.reset_active_language_filter()

    def _on_use_default_reference_language_toggled(self, checked: bool):
        user_config.set_reference_language_use_default(bool(checked))
        self.__sync_reference_language_state()

    def _save_reference_language(self, _text: str = ''):
        user_config.set_configured_reference_language(self.ledReferenceLanguage.text())

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

    # 填充界面缩放下拉框（QT_SCALE_FACTOR 只在启动时生效，改完提示重启）
    def __load_ui_scale_value(self):
        scale = user_config.get_appearance_ui_scale()
        index = UI_SCALE_KEYS.index(scale) if scale in UI_SCALE_KEYS else 0
        self.cbbUiScale.blockSignals(True)
        self.cbbUiScale.setCurrentIndex(index)
        self.cbbUiScale.blockSignals(False)

    def _on_ui_scale_changed(self, index: int):
        if not 0 <= index < len(UI_SCALE_KEYS):
            return
        scale = UI_SCALE_KEYS[index]
        user_config.save_appearance_ui_scale(scale)
        if scale != "auto":
            Logger().info(f"界面缩放已设为 {scale}%，重启软件后生效")

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
        self.__apply_vcs_to_conventions()
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
