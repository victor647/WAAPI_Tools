import argparse
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from qt_material import build_stylesheet

from libraries.utils import path_utils
from libraries.utils.log_utils import Logger
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
    app = QApplication([])
    css_path = path_utils.get_resource_path("material.css")
    stylesheet = build_stylesheet(theme="dark_teal.xml", template=css_path)
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


if __name__ == '__main__':
    try:
        object_ids, from_wwise = parse_args(sys.argv[1:])
        exit_code = run_app_loop(object_ids, from_wwise)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        Logger().info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        Logger().exception(e)
        sys.exit(1)
