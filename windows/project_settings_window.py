from PySide6.QtWidgets import QDialog, QWidget

from data import project_conventions
from libraries.utils import user_config
from libraries.utils.log_utils import Logger
from ui.ProjectSettings_ui import Ui_ProjectSettings


# 工程规范设置窗口：把 project_conventions.json 的分段配置做成可视化 Tab 编辑
class ProjectSettingsWindow(QDialog, Ui_ProjectSettings):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setupUi(self)
        self.__conventions = dict(project_conventions.conventions or {})
        self.categoryMap.set_headers(["分类名", "缩写", "颜色值"])
        self.containerSuffix.set_headers(["容器类型", "后缀"])
        self.netRoleValues.set_headers(["角色", "Switch 名称"])
        self.cbxAutoFetchChildren.setChecked(user_config.get_tool_auto_fetch_children())
        self.setup_triggers()
        self.__load_values()

    # 绑定按钮与复选框信号槽
    def setup_triggers(self):
        self.btnSave.clicked.connect(self.save_settings)
        self.btnCancel.clicked.connect(self.reject)
        self.cbxAutoFetchChildren.toggled.connect(user_config.set_tool_auto_fetch_children)

    # 从当前规范数据填充控件
    def __load_values(self):
        conventions = self.__conventions
        acronym_map = conventions.get("AcronymMap", {}) or {}
        color_map = conventions.get("ColorMap", {}) or {}
        container_suffix = conventions.get("ContainerSuffix", {}) or {}
        net_role = conventions.get("NetRole") or {}
        net_role_suffix = net_role.get("Suffix") or {}
        net_role_values = net_role.get("SwitchValues") or {}

        category_keys = sorted(set(acronym_map) | set(color_map))
        category_rows = [
            (key, acronym_map.get(key, ""), str(color_map.get(key, "")))
            for key in category_keys
        ]
        self.categoryMap.set_data(category_rows)
        self.containerSuffix.set_data(list(container_suffix.items()))
        default_suffixes = {"1P": "_1P", "2P": "_2P", "3P": "_3P"}
        suffixes = {key: net_role_suffix.get(key, default_suffixes[key]) for key in default_suffixes}
        self.iptNetRole1P.setText(suffixes["1P"])
        self.iptNetRole2P.setText(suffixes["2P"])
        self.iptNetRole3P.setText(suffixes["3P"])
        self.iptNetRoleGroup.setText(str(net_role.get("SwitchGroup", "Net_Role")))
        self.netRoleValues.set_data(
            list(net_role_values.items()) or [("1P", "1P"), ("2P", "2P"), ("3P", "3P")]
        )
        languages = conventions.get("ImplementedLanguages", ["Chinese", "English"])
        self.pteLanguages.setPlainText("\n".join(str(item) for item in languages))
        self.cbxFullNameInSound.setChecked(bool(conventions.get("FullNameInSound", True)))
        self.cbxPlayPrefixInEvent.setChecked(bool(conventions.get("PlayPrefixInEvent", False)))

    # 收集并保存
    def save_settings(self):
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
        new_conventions["AcronymMap"] = acronym_map
        new_conventions["ColorMap"] = color_map
        new_conventions["ContainerSuffix"] = dict(self.containerSuffix.rows())

        value_rows = self.netRoleValues.rows()
        default_suffixes = {"1P": "_1P", "2P": "_2P", "3P": "_3P"}
        suffixes = {
            "1P": self.iptNetRole1P.text().strip() or default_suffixes["1P"],
            "2P": self.iptNetRole2P.text().strip() or default_suffixes["2P"],
            "3P": self.iptNetRole3P.text().strip() or default_suffixes["3P"],
        }
        new_conventions["NetRole"] = {
            "Suffix": suffixes,
            "SwitchGroup": self.iptNetRoleGroup.text().strip() or "Net_Role",
            "SwitchValues": dict(value_rows) if value_rows else {"1P": "1P", "2P": "2P", "3P": "3P"},
        }
        languages = [
            line.strip()
            for line in self.pteLanguages.toPlainText().splitlines()
            if line.strip()
        ]
        new_conventions["ImplementedLanguages"] = languages
        new_conventions["FullNameInSound"] = self.cbxFullNameInSound.isChecked()
        new_conventions["PlayPrefixInEvent"] = self.cbxPlayPrefixInEvent.isChecked()

        if project_conventions.save_conventions(new_conventions):
            Logger().info("工程规范设置已保存")
            self.accept()
