import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from qt_material import build_stylesheet

from libraries.utils import path_utils
from libraries.utils.log_utils import Logger
from windows.main_window import MainWindow


def run_app_loop():
    app = QApplication([])
    css_path = path_utils.get_resource_path("material.css")
    stylesheet = build_stylesheet(theme="dark_teal.xml", template=css_path)
    main_window = MainWindow(stylesheet)
    app.setStyleSheet(stylesheet)
    icon_path = path_utils.get_resource_path("icons/Icon.png")
    main_window.setWindowIcon(QIcon(icon_path))
    Logger().debug("Application started.")
    main_window.show()
    code = app.exec()
    Logger().debug(f"Application exiting with code: {code}")
    return code


if __name__ == '__main__':
    try:
        exit_code = run_app_loop()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        Logger().info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        Logger().exception(e)
        sys.exit(1)
