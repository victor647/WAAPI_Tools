import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from libraries.ai_assistant import AIAgentStopped, run_assistant

# 尚未发请求时即中止 → 应抛 AIAgentStopped 而不是发网络请求
try:
    run_assistant("hi", [], should_stop=lambda: True)
    raise AssertionError("应当被中止")
except AIAgentStopped:
    print("提前中止 ok")

# UI：停止按钮初始禁用，忙碌时可用
from libraries import waapi_client as wc


class _FakeClient:
    def __init__(self, *args, **kwargs):
        self.client = None

    def is_connected(self):
        return False

    def disconnect(self):
        pass


wc.WAAPIClient = _FakeClient

from PySide6.QtWidgets import QApplication

from windows.main_window import MainWindow

app = QApplication([])
window = MainWindow(None)
assert hasattr(window, "btnAiStop")
assert not window.btnAiStop.isEnabled()
window._set_ai_busy(True)
assert window.btnAiStop.isEnabled() and not window.btnAiSend.isEnabled()
window._set_ai_busy(False)
assert not window.btnAiStop.isEnabled() and window.btnAiSend.isEnabled()
print("停止按钮状态切换 ok")
window.close()
