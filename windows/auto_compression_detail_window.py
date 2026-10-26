from libraries.base_dialog import BaseDialog
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QTableWidgetItem

from libraries.utils.qt_utils import resize_table_and_window
from libraries.table_view.table_context_menu import install_row_object_context
from ui.AutoCompressionDetail_ui import Ui_AutoCompressionDetail


COL_NAME = 0
COL_DURATION = 1
COL_CATEGORY = 2


# 自动转码详情：列出某个节点包含的每个音频文件的时长与分档判定
# entries 为 [{'source': WwiseObject, 'duration': float, 'category_text': str}, ...]
class AutoCompressionDetailWindow(BaseDialog, Ui_AutoCompressionDetail):

    def __init__(self, entries: list, title: str = "音效详情", parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.__entries = list(entries)
        self.setWindowTitle(title)
        self.setup_triggers()
        self.__fill_rows()

    def setup_triggers(self):
        install_row_object_context(
            self.tblAudioDetails,
            self.__objects_at_row,
            default_action="select",
        )

    # 某一行对应的 Wwise 对象（供双击在 Wwise 中选中使用）
    def __objects_at_row(self, row: int) -> list:
        if 0 <= row < len(self.__entries):
            return [self.__entries[row]["source"]]
        return []

    # 填入每个音频文件的名称、路径、时长与分类
    def __fill_rows(self):
        self.tblAudioDetails.setSortingEnabled(False)
        self.tblAudioDetails.setRowCount(len(self.__entries))
        for row, entry in enumerate(self.__entries):
            source = entry["source"]
            name_item = QTableWidgetItem(source.name)
            name_item.setData(Qt.ItemDataRole.UserRole, source.id)
            name_item.setToolTip(source.path)
            self.tblAudioDetails.setItem(row, COL_NAME, name_item)
            duration_item = QTableWidgetItem()
            duration = entry["duration"]
            duration_item.setData(
                Qt.ItemDataRole.DisplayRole, "-" if duration is None else round(float(duration), 3)
            )
            self.tblAudioDetails.setItem(row, COL_DURATION, duration_item)
            self.tblAudioDetails.setItem(row, COL_CATEGORY, QTableWidgetItem(entry["category_text"]))
        self.tblAudioDetails.setSortingEnabled(True)
        resize_table_and_window(self.tblAudioDetails, self)

