from PyQt6.QtWidgets import QMessageBox, QTableWidget


# 弹出消息框
def show_message_box(title: str, text: str):
    message = QMessageBox()
    message.setWindowTitle(title)
    message.setText(text)
    message.exec()