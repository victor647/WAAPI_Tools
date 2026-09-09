from PySide6.QtWidgets import QDialog, QWidget

from libraries.utils import user_config
from ui.AdvancedFilter_ui import Ui_AdvancedFilter


# 高级筛选窗口：区分大小写、仅显示启用对象、Event 引用筛选、语言筛选
class AdvancedFilterWindow(QDialog, Ui_AdvancedFilter):

    def __init__(self, main_window, parent: QWidget = None):
        super().__init__(parent)
        self.setupUi(self)
        self.__main = main_window
        self.setup_triggers()
        self.__sync_from_main()

    # 绑定复选/单选控件信号槽
    def setup_triggers(self):
        self.cbxCaseSensitive.toggled.connect(self._on_case_sensitive_toggled)
        self.cbxOnlyIncluded.toggled.connect(self._on_only_included_toggled)
        self.rdoEventAll.toggled.connect(self._on_event_ref_changed)
        self.rdoEventHas.toggled.connect(self._on_event_ref_changed)
        self.rdoEventNo.toggled.connect(self._on_event_ref_changed)
        self.rdoLangAll.toggled.connect(self._on_language_changed)
        self.rdoLangActive.toggled.connect(self._on_language_changed)
        self.btnClose.clicked.connect(self.accept)

    # 打开时从 user_config 恢复上次保存的选项，并让复选框设置即时生效于主窗口
    def __sync_from_main(self):
        settings = user_config.get_advanced_filter_settings()
        widgets = (
            self.cbxCaseSensitive,
            self.cbxOnlyIncluded,
            self.rdoEventAll,
            self.rdoEventHas,
            self.rdoEventNo,
            self.rdoLangAll,
            self.rdoLangActive,
        )
        for widget in widgets:
            widget.blockSignals(True)
        self.cbxCaseSensitive.setChecked(settings["case_sensitive"])
        self.cbxOnlyIncluded.setChecked(settings["only_included"])
        event_value = settings["event_filter"]
        if event_value not in ("all", "with_ref", "without_ref"):
            event_value = "all"
        self.rdoEventAll.setChecked(event_value == "all")
        self.rdoEventHas.setChecked(event_value == "with_ref")
        self.rdoEventNo.setChecked(event_value == "without_ref")
        language_value = settings["language_filter"]
        if language_value not in ("all", "active"):
            language_value = "all"
        self.rdoLangAll.setChecked(language_value == "all")
        self.rdoLangActive.setChecked(language_value == "active")
        for widget in widgets:
            widget.blockSignals(False)
        if self.__main.cbxCaseSensitive.isChecked() != settings["case_sensitive"]:
            self.__main.cbxCaseSensitive.setChecked(settings["case_sensitive"])
        if self.__main.cbxOnlyIncludedEnabled.isChecked() != settings["only_included"]:
            self.__main.cbxOnlyIncludedEnabled.setChecked(settings["only_included"])

    # 区分大小写选项变化时同步主窗口并保存
    def _on_case_sensitive_toggled(self, checked: bool):
        self.__main.cbxCaseSensitive.setChecked(checked)
        user_config.save_advanced_filter_settings({"case_sensitive": bool(checked)})

    # 仅显示启用对象选项变化时同步主窗口并保存
    def _on_only_included_toggled(self, checked: bool):
        self.__main.cbxOnlyIncludedEnabled.setChecked(checked)
        user_config.save_advanced_filter_settings({"only_included": bool(checked)})

    # Event 引用选项变化时立即筛选
    def _on_event_ref_changed(self, checked: bool):
        if not checked:
            return
        if self.rdoEventHas.isChecked():
            self.__main.filter_by_event_reference(True)
            user_config.save_advanced_filter_settings({"event_filter": "with_ref"})
        elif self.rdoEventNo.isChecked():
            self.__main.filter_by_event_reference(False)
            user_config.save_advanced_filter_settings({"event_filter": "without_ref"})
        else:
            self.__main.reset_event_reference_filter()
            user_config.save_advanced_filter_settings({"event_filter": "all"})

    # 语言筛选选项变化时立即筛选
    def _on_language_changed(self, checked: bool):
        if not checked:
            return
        if self.rdoLangActive.isChecked():
            self.__main.filter_by_active_language()
            user_config.save_advanced_filter_settings({"language_filter": "active"})
        else:
            self.__main.reset_active_language_filter()
            user_config.save_advanced_filter_settings({"language_filter": "all"})
