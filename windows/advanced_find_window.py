from libraries.base_dialog import BaseDialog
from PySide6.QtWidgets import QDialog, QWidget

from data import user_config
from ui.AdvancedFind_ui import Ui_AdvancedFind


# 高级查找窗口：按属性查找、按类型查找子对象、保留原始层级开关
class AdvancedFindWindow(BaseDialog, Ui_AdvancedFind):

    def __init__(self, main_window, parent: QWidget = None):
        super().__init__(parent)
        self.setupUi(self)
        self.__main = main_window
        # 先回填再连信号，避免回填过程触发一次保存
        self.__sync_from_main()
        self.setup_triggers()

    # 绑定控件信号槽
    def setup_triggers(self):
        self.cbxKeepSelf.toggled.connect(self._on_keep_self_toggled)
        self.cbbFindChildType.selectionChanged.connect(self._on_find_child_type_changed)
        self.btnFindChildType.clicked.connect(self._on_find_child_type)
        self.cbbFindProperty.currentTextChanged.connect(self._on_find_property_changed)
        self.btnFindProperty.clicked.connect(self._on_find_property)

    # 打开时从 user_config 恢复上次保存的选项
    def __sync_from_main(self):
        settings = user_config.get_advanced_find_settings()
        # 类型选项复用主窗口筛选里的类型列表（可复选，一个都没勾时按全部类型查找）
        self.cbbFindChildType.set_options(
            self.__main.get_filter_type_options(), settings["find_child_types"], all_text='全部类型')
        # 「找属性」下拉框恢复上次选择
        index = self.cbbFindProperty.findText(settings["find_property"])
        if index >= 0:
            self.cbbFindProperty.setCurrentIndex(index)
        # 「保留原始层级」由主窗口的那份隐藏控件持有状态（各类查找共用），这里只做同步
        self.cbxKeepSelf.blockSignals(True)
        self.cbxKeepSelf.setChecked(self.__main.cbxKeepSelf.isChecked())
        self.cbxKeepSelf.blockSignals(False)

    # 保留原始层级变化时同步主窗口（由主窗口负责写入 user_config）
    def _on_keep_self_toggled(self, checked: bool):
        self.__main.cbxKeepSelf.setChecked(checked)

    # 类型勾选变化时保存
    def _on_find_child_type_changed(self):
        user_config.save_advanced_find_settings({"find_child_types": self.cbbFindChildType.checked_options()})

    # 按所选类型查找表格对象的子对象
    def _on_find_child_type(self):
        type_names = self.cbbFindChildType.checked_options()
        user_config.save_advanced_find_settings({"find_child_types": type_names})
        self.__main.find_children_by_type(type_names)
        # 查找动作已经作用到主窗口，直接关闭本窗口
        self.accept()

    # 「找属性」下拉框选择变化时保存
    def _on_find_property_changed(self, text: str):
        user_config.save_advanced_find_settings({"find_property": text})

    # 按所选属性查找表格对象引用到的对象
    def _on_find_property(self):
        property_name = self.cbbFindProperty.currentText()
        user_config.save_advanced_find_settings({"find_property": property_name})
        self.__main.find_by_property(property_name)
        # 查找动作已经作用到主窗口，直接关闭本窗口
        self.accept()
