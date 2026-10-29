import argparse
import ctypes
import os
import sys
import threading
import traceback
from datetime import datetime

# 无控制台打包（windowed exe）时 sys.stdout / sys.stderr 为 None，而部分第三方库（如 waapi 内部
# 的 autobahn 封装）在导入时就用 from sys import stderr 抓取了该流，连接失败时会写进去：
# 抓到 None 会抛 AttributeError，使后台线程静默终止、主线程永远等不到连接结果（窗口打不开）。
# 因此必须在导入这些库之前把两个流兜底掉；后续 install_output_capture 会再套一层写日志。
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from PySide6.QtGui import QIcon
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication
from qt_material import build_stylesheet, list_themes

from libraries.utils import path_utils, single_instance
from data import user_config
from libraries.utils.log_utils import Logger, set_log_theme
from windows.main_window import MainWindow

# 关闭 QtMultimedia ffmpeg 后端的媒体信息输出，避免打开音频时在控制台打印冗余日志
os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.*=false")

# 本机单实例标识：Wwise 右键反复打开时，把对象转发给这个端点对应的已有窗口
SINGLE_INSTANCE_KEY = "netease.waapi_tools.gui"


# Wwise 右键菜单「Open in WAAPI Tools」的对象来源：
#   1) 菜单宏 ${id} 直接传入右键对象 GUID（可多选，空格分隔）：副窗口（Contents Editor 等）里右键
#      也能拿到对象，不依赖主窗口的选中状态
#   2) 只带 --from-wwise（${id} 为空时）：窗口打开后再用 WAAPI 读 Wwise 当前选中对象，作为兜底
def parse_args(argv: list[str]) -> tuple[list[str], bool, bool]:
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
    parser.add_argument(
        "--new-instance",
        action="store_true",
        help="强制另起一个进程（默认会把对象转发给已运行的工具窗口）",
    )
    args = parser.parse_args(argv)
    return args.object_ids, args.from_wwise, args.new_instance


def run_app_loop(object_ids: list[str] | None = None, from_wwise: bool = False, new_instance: bool = False):
    set_windows_app_id()
    apply_ui_scale_setting()
    app = QApplication([])
    # 已有工具窗口在运行时：把本次要打开的对象转发过去，随即退出，不再起第二个进程
    if not new_instance and single_instance.forward_to_running_instance(
        SINGLE_INSTANCE_KEY, single_instance.encode_payload(object_ids or [], from_wwise)
    ):
        Logger().info("检测到已运行的工具窗口，已把对象转发过去")
        return 0
    icon_path = path_utils.get_resource_path("icons/Icon.png")
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    css_path = path_utils.get_resource_path("material.css")
    theme = user_config.get_appearance_theme()
    if theme not in list_themes():
        theme = user_config.DEFAULT_CONFIG["appearance"]["theme"]
    set_log_theme(theme)
    stylesheet = build_stylesheet(theme=theme, template=css_path)
    main_window = MainWindow(stylesheet)
    app.setStyleSheet(stylesheet)
    main_window.setWindowIcon(app_icon)
    Logger().debug("Application started.")
    main_window.show()
    # 菜单传入的 GUID 优先；没传（或传入为空）时才回头读 Wwise 当前选中对象
    if object_ids or from_wwise:
        main_window.load_objects_by_request(object_ids or [], from_wwise)
    # 注册本地监听，后续从 Wwise 右键再次打开时由本实例接收
    instance_server = single_instance.SingleInstanceServer(SINGLE_INSTANCE_KEY)
    instance_server.start(main_window.apply_single_instance_payload)
    code = app.exec()
    Logger().debug(f"Application exiting with code: {code}")
    return code


# 显式声明 Windows AppUserModelID：避免任务栏把窗口归到 python.exe 默认图标下
def set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(SINGLE_INSTANCE_KEY)
    except Exception:
        pass


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
        # 先单独落一份崩溃日志：日志管线本身出问题（例如异常发生在日志写入过程中）时也能拿到堆栈
        try:
            with open(path_utils.get_app_data_path("crash.log"), "a", encoding="utf-8") as f:
                f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n{detail}\n")
        except Exception:
            pass
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
        object_ids, from_wwise, new_instance = parse_args(sys.argv[1:])
        exit_code = run_app_loop(object_ids, from_wwise, new_instance)
    except KeyboardInterrupt:
        Logger().info("Application interrupted by user")
        exit_code = 0
    except Exception as e:
        Logger().exception(e)
        exit_code = 1
    exit_process(exit_code)
