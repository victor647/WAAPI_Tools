from libraries.multi_thread.ProgressBar_ui import Ui_ProgressBar
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog


# 进度条显示
class ProgressBar(QDialog, Ui_ProgressBar):

    def __init__(self, total: int, title: str, processor):
        super().__init__()
        self.setupUi(self)
        # 进度条始终置顶，避免被工具窗口挡住
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.total_count = total
        self.setWindowTitle(title)
        self.processor = processor

    def update_progress(self, index: int, obj_name: str):
        # 更新进度条显示
        self.pgbSearching.setValue(int(index / self.total_count * 100))
        # 更新底部文字显示
        self.lblCurrentWorking.setText(f"{obj_name}({index}/{self.total_count})")

    def closeEvent(self, event):
        if self.processor:
            self.processor.stop()
        event.accept()




