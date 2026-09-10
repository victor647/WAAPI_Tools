from PySide6.QtWidgets import QDialog, QWidget

from libraries.utils import user_config
from ui.AdvancedFind_ui import Ui_AdvancedFind


# 高级查找窗口：递归查找、保留原始层级
class AdvancedFindWindow(QDialog, Ui_AdvancedFind):

    def __init__(self, main_window, parent: QWidget = None):
        super().__init__(parent)
        self.setupUi(self)
        self.__main = main_window
        self.setup_triggers()
        self.__sync_from_main()

    # 绑定复选控件信号槽
    def setup_triggers(self):
        self.cbxRecursiveFind.toggled.connect(self._on_recursive_find_toggled)
        self.cbxKeepSelf.toggled.connect(self._on_keep_self_toggled)
        self.cbbFindChildType.currentIndexChanged.connect(self._on_find_child_type_changed)
        self.btnFindChildType.clicked.connect(self._on_find_child_type)
        self.btnClose.clicked.connect(self.accept)

    # 打开时从 user_config 恢复上次保存的选项，并同步主窗口隐藏的状态控件
    def __sync_from_main(self):
        settings = user_config.get_advanced_find_settings()
        # 类型选项复用主窗口筛选里的类型列表
        self.cbbFindChildType.clear()
        self.cbbFindChildType.addItems(self.__main.get_filter_type_options())
        saved_index = self.cbbFindChildType.findText(settings["find_child_type"])
        self.cbbFindChildType.setCurrentIndex(saved_index if saved_index >= 0 else 0)
        self.cbxRecursiveFind.blockSignals(True)
        self.cbxKeepSelf.blockSignals(True)
        self.cbxRecursiveFind.setChecked(settings["recursive_find"])
        self.cbxKeepSelf.setChecked(settings["keep_self"])
        self.cbxRecursiveFind.blockSignals(False)
        self.cbxKeepSelf.blockSignals(False)
        if self.__main.cbxRecursiveFind.isChecked() != settings["recursive_find"]:
            self.__main.cbxRecursiveFind.setChecked(settings["recursive_find"])
        if self.__main.cbxKeepSelf.isChecked() != settings["keep_self"]:
            self.__main.cbxKeepSelf.setChecked(settings["keep_self"])

    # 递归查找选项变化时同步主窗口并保存
    def _on_recursive_find_toggled(self, checked: bool):
        self.__main.cbxRecursiveFind.setChecked(checked)
        user_config.save_advanced_find_settings({"recursive_find": bool(checked)})

    # 保留原始层级选项变化时同步主窗口并保存
    def _on_keep_self_toggled(self, checked: bool):
        self.__main.cbxKeepSelf.setChecked(checked)
        user_config.save_advanced_find_settings({"keep_self": bool(checked)})

    # 类型选择变化时保存
    def _on_find_child_type_changed(self, index: int):
        user_config.save_advanced_find_settings({"find_child_type": self.cbbFindChildType.currentText()})

    # 按所选类型查找表格对象的子对象
    def _on_find_child_type(self):
        type_text = self.cbbFindChildType.currentText()
        user_config.save_advanced_find_settings({"find_child_type": type_text})
        self.__main.find_children_by_type(type_text)
