import sys
import ctypes
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QWidget


# 穿透操作系统前台锁定限制，将指定窗口激活并置于最前台
def bring_to_foreground(window: QWidget) -> None:
    if not window or not window.isVisible():
        return
    if window.isMinimized():
        window.showNormal()
    window.setWindowState((window.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive)
    window.raise_()
    window.activateWindow()

    # Windows 平台下穿透前台锁定机制（Foreground Lock Timeout）
    if sys.platform == "win32":
        try:
            hwnd = int(window.winId())
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            foreground_hwnd = user32.GetForegroundWindow()
            if foreground_hwnd != hwnd:
                current_thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
                foreground_thread_id = user32.GetWindowThreadProcessId(foreground_hwnd, None)
                if foreground_thread_id != current_thread_id:
                    user32.AttachThreadInput(foreground_thread_id, current_thread_id, True)
                    user32.SetForegroundWindow(hwnd)
                    user32.BringWindowToTop(hwnd)
                    user32.AttachThreadInput(foreground_thread_id, current_thread_id, False)
                else:
                    user32.SetForegroundWindow(hwnd)
                    user32.BringWindowToTop(hwnd)
            else:
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
        except Exception:
            pass


# 所有独立工具子窗口继承的通用基类：
# - 构造时自动识别并记录上一级窗口（父窗口 / 当前活动窗口 / 全局主窗口）；
# - 关闭时（右上角X / Esc / close() / reject() / accept() / done()）自动将上一级窗口切回最前台。
class BaseDialog(QDialog):

    def __init__(self, parent: QWidget | None = None, *args, **kwargs):
        # 未显式传递 parent 时，自动探测当前处于激活状态的窗口作为上一级，找不到时回退到主窗口
        if parent is None:
            active = QApplication.activeWindow()
            if active and active is not self:
                parent = active
            else:
                import globals.global_variables as gv
                parent = gv.main_window

        super().__init__(parent, *args, **kwargs)
        self._parent_window = parent
        self._has_restored_parent = False
        # 连接 finished 信号兜底所有结束路径
        self.finished.connect(lambda _r: self._bring_parent_to_foreground())

    # 将上一级窗口置于前台
    def _bring_parent_to_foreground(self) -> None:
        if self._has_restored_parent:
            return
        self._has_restored_parent = True

        target = self._parent_window
        if target is None or not target.isVisible():
            active = QApplication.activeWindow()
            if active and active is not self:
                target = active
            else:
                import globals.global_variables as gv
                target = gv.main_window

        if target and target.isVisible():
            # 通过 singleShot 确保在当前对话框隐藏完成后，主线程下一拍执行激活
            QTimer.singleShot(0, lambda: bring_to_foreground(target))

    def done(self, r: int) -> None:
        super().done(r)
        self._bring_parent_to_foreground()

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        if event.isAccepted():
            self._bring_parent_to_foreground()
