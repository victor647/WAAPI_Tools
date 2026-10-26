from libraries.base_dialog import BaseDialog
from PySide6.QtWidgets import QCheckBox, QDialog

from ui.ExportObjectList_ui import Ui_ExportObjectList


# 选择导出属性的对话框：勾选当前视图中的列作为CSV导出字段
class ExportObjectListWindow(BaseDialog, Ui_ExportObjectList):

    def __init__(self, headers: list[str]):
        super().__init__()
        self.setupUi(self)
        self._checkboxes: list[QCheckBox] = []
        for header in headers:
            checkbox = QCheckBox(header)
            checkbox.setChecked(True)
            self.layCheckboxes.addWidget(checkbox)
            self._checkboxes.append(checkbox)
        self.layCheckboxes.addStretch()
        self.setup_triggers()

    # 绑定按钮信号槽
    def setup_triggers(self):
        self.btnSelectAll.clicked.connect(self.select_all)
        self.btnSelectNone.clicked.connect(self.select_none)
        self.btnExport.clicked.connect(self.accept)
        self.btnCancel.clicked.connect(self.reject)

    def select_all(self):
        for checkbox in self._checkboxes:
            checkbox.setChecked(True)

    def select_none(self):
        for checkbox in self._checkboxes:
            checkbox.setChecked(False)

    def get_selected_headers(self) -> list[str]:
        return [checkbox.text() for checkbox in self._checkboxes if checkbox.isChecked()]
