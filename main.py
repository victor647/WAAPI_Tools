import argparse
import os
import sys
import threading
import traceback

from PySide6.QtGui import QIcon
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication
from qt_material import build_stylesheet, list_themes

from libraries.utils import path_utils, user_config
from libraries.utils.log_utils import Logger, set_log_theme
from windows.main_window import MainWindow

# 关闭 QtMultimedia ffmpeg 后端的媒体信息输出，避免打开音频时在控制台打印冗余日志
os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.*=false")


# Wwise 右键菜单「Open in WAAPI Tools」有两种传入方式：
#   1) 不带参数启动（--from-wwise）：窗口打开后自动读取 Wwise 当前选中对象（推荐，规避 Wwise 参数引号展开问题）
#   2) 直接传入对象 GUID：适用于需要精确定位对象的场景
def parse_args(argv: list[str]) -> tuple[list[str], bool]:
    parser = argparse.ArgumentParser(
        prog="WAAPI_Tools",
        description="Wwise WAAPI 工具集主程序",
    )
    parser.add_argument(
        "--from-wwise",
        action="store_true",
        help="由 Wwise 右键菜单启动：窗口打开后自动读取当前选中的对象",
    )
    parser.add_argument(
        "object_ids",
        nargs="*",
        metavar="OBJECT_ID",
        help="直接传入的 Wwise 对象 GUID，可多个（可选）",
    )
    args = parser.parse_args(argv)
    return args.object_ids, args.from_wwise


def run_app_loop(object_ids: list[str] | None = None, from_wwise: bool = False):
    apply_ui_scale_setting()
    app = QApplication([])
    css_path = path_utils.get_resource_path("material.css")
    theme = user_config.get_appearance_theme()
    if theme not in list_themes():
        theme = user_config.DEFAULT_CONFIG["appearance"]["theme"]
    set_log_theme(theme)
    stylesheet = build_stylesheet(theme=theme, template=css_path)
    main_window = MainWindow(stylesheet)
    app.setStyleSheet(stylesheet)
    icon_path = path_utils.get_resource_path("icons/Icon.png")
    main_window.setWindowIcon(QIcon(icon_path))
    Logger().debug("Application started.")
    main_window.show()
    if object_ids:
        main_window.load_external_objects(object_ids)
    elif from_wwise:
        main_window.load_current_wwise_selection()
    code = app.exec()
    Logger().debug(f"Application exiting with code: {code}")
    return code


# 界面缩放：设置-外观里选择具体百分比时用 QT_SCALE_FACTOR 固定缩放（必须在 QApplication 之前设置）
def apply_ui_scale_setting() -> str:
    scale = user_config.get_appearance_ui_scale()
    if scale == "auto":
        return ""
    os.environ["QT_SCALE_FACTOR"] = f"{int(scale) / 100:g}"
    return scale

# 退出前记录仍然存活的非守护线程（如 waapi 客户端的回调线程），便于排查退出卡住的问题
def log_leftover_threads() -> None:
    leftovers = [
        thread.name for thread in threading.enumerate()
        if thread is not threading.main_thread() and not thread.daemon
    ]
    if leftovers:
        Logger().debug("退出时仍有非守护线程：" + ", ".join(leftovers))


# 打包成无控制台的 exe 后，未捕获异常只会写到 stderr（为 None）而丢失，这里统一记入日志文件
def install_exception_logging() -> None:
    def log_uncaught(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            return
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb)).rstrip()
        # 这里已经带上完整堆栈，用 error 输出避免 logging 再追加一次当前异常堆栈
        Logger().error(f"未捕获异常：\n{detail}")

    sys.excepthook = log_uncaught
    threading.excepthook = lambda args: log_uncaught(args.exc_type, args.exc_value, args.exc_traceback)


# 冲刷输出流后强制结束进程：Qt 关闭后仍可能残留第三方库的非守护线程，
# 走 sys.exit 会卡在解释器退出阶段，留下没有窗口的 python.exe
def exit_process(code: int) -> None:
    log_leftover_threads()
    # 日志句柄是攒批落盘的，退出前先冲一遍，避免缓冲里的最后几行丢失
    try:
        from libraries.utils.log_utils import Logger

        Logger().flush()
    except Exception:
        pass
    for stream in (sys.stdout, sys.stderr):
        # 打包成无控制台的 exe 时这两个流是 None，直接跳过
        if stream is None or not hasattr(stream, "flush"):
            continue
        try:
            stream.flush()
        except (ValueError, OSError):
            pass
    os._exit(code)


if __name__ == '__main__':
    install_exception_logging()
    # 把 print()/第三方库的输出也收进日志文件（控制台仍可见）
    from libraries.utils.log_utils import install_output_capture
    install_output_capture()
    try:
        object_ids, from_wwise = parse_args(sys.argv[1:])
        exit_code = run_app_loop(object_ids, from_wwise)
    except KeyboardInterrupt:
        Logger().info("Application interrupted by user")
        exit_code = 0
    except Exception as e:
        Logger().exception(e)
        exit_code = 1
    exit_process(exit_code)
