import os
import sys
import logging
import time
from libraries.singleton import Singleton


def _waapi_mcp_mode() -> bool:
    return os.environ.get("WAAPI_MCP") == "1"


def _console_print(line: str) -> None:
    print(line, file=sys.stderr if _waapi_mcp_mode() else sys.stdout)

# 日志窗口字体颜色：[颜色, 字号, 字重]
_DARK_FONT_STYLES = {
        "INFO": ["#1DE9B6", 10.5, 400],
        "QUERY": ["#C7B8E2", 10.5, 400],
        "WARNING": ["#FFD700", 10.5, 400],
        "ERROR": ["#EE2C2C", 10.5, 400],
        "DEBUG": ["#8A71BF", 10.5, 400],
        "EXCEPTION": ["#FF0015", 10.5, 400],
    }

# 浅色主题下改用深色系文字，保证在浅色背景上可读
_LIGHT_FONT_STYLES = {
        "INFO": ["#00796B", 10.5, 400],
        "QUERY": ["#6A1B9A", 10.5, 400],
        "WARNING": ["#B26A00", 10.5, 400],
        "ERROR": ["#C62828", 10.5, 400],
        "DEBUG": ["#5E35B1", 10.5, 400],
        "EXCEPTION": ["#B71C1C", 10.5, 400],
    }

FONT_STYLE_DICT = dict(_DARK_FONT_STYLES)


# 取主题主色（qt_material 的 primaryColor）；浅色主题下过亮时压暗，保证可读
def _theme_primary_color(theme_name: str) -> str | None:
    try:
        from qt_material import get_theme

        color = get_theme(theme_name).get("primaryColor")
    except Exception:
        return None
    if not color or not str(color).startswith("#") or len(color) != 7:
        return None
    if str(theme_name).startswith("light"):
        red, green, blue = (int(color[i:i + 2], 16) for i in (1, 3, 5))
        if 0.299 * red + 0.587 * green + 0.114 * blue > 160:
            red, green, blue = int(red * 0.6), int(green * 0.6), int(blue * 0.6)
            return f"#{red:02x}{green:02x}{blue:02x}"
    return color


# 按 qt_material 主题切换日志窗口配色（dark_*.xml 用亮色、light_*.xml 用深色）
def set_log_theme(theme_name: str) -> None:
    is_dark = not str(theme_name).startswith("light")
    FONT_STYLE_DICT.update(_DARK_FONT_STYLES if is_dark else _LIGHT_FONT_STYLES)
    info_color = _theme_primary_color(theme_name)
    if info_color:
        FONT_STYLE_DICT["INFO"] = [info_color, 10.5, 400]


# Format used for log colored text in cmd
class CustomFormatter(logging.Formatter):
    reset = "\x1b[0m"
    red = "\x1b[31m"  # aa,0,0
    green = "\x1b[32m"  # 0,aa,0
    yellow = "\x1b[33m"  # aa,55,0
    purple = "\x1b[35m"  # aa,0,aa
    cyan = "\x1b[36m"  # 0,aa,aa
    white = "\x1b[37m"
    grey = "\x1b[90m"  # 55,55,55
    blue = '\x1b[38;5;39m'
    format = "%(message)s" # "%(asctime)s - %(levelname)s - %(message)s "

    COLORFUL_FORMATS = {
        logging.INFO: cyan + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.DEBUG: purple + format + reset,
    }

    def format(self, record):
        log_fmt = self.COLORFUL_FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# 在IDE Console中使用的带颜色的Logger，但不支持CMD
class ColorfulCMDLogger(object):
    def __init__(self):
        self.logger = logging.getLogger("FFSimpleTool")
        # MCP stdio：仅 stderr，避免与 stdout 上的 JSON-RPC 混流
        stream = sys.stderr if _waapi_mcp_mode() else None
        self.console_handle = logging.StreamHandler(stream)
        self.set_format_for_cmd()

    def set_format_for_cmd(self):
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        self.console_handle.setLevel(logging.DEBUG)
        self.console_handle.setFormatter(CustomFormatter())
        if not self.logger.handlers:
            self.logger.addHandler(self.console_handle)


# Logger: 在console和QTextItem中输出
class Logger(object, metaclass=Singleton):
    def __init__(self):
        self.to_cmdline = True
        self.colorful_cmd_logger = ColorfulCMDLogger().logger
        # 在Pycharm中的Console中执行：带颜色；在exe中执行：不带颜色
        self.enable_colorful_cmdline = True if os.getenv("PYCHARM_HOSTED") else False
        self._log_window_stream = None
        self._status_bar_stream = None
        self._debug_mode = False

    # 在文本框中显示日志
    def set_log_window_stream(self, output_stream):
        self._log_window_stream = output_stream

    # 在状态栏显示日志
    def set_status_bar_stream(self, status_stream):
        self._status_bar_stream = status_stream

    # 开关Debug模式，开启时才显示Debug类型的信息
    def toggle_debug_mode(self, debug_on: bool):
        self._debug_mode = debug_on

    # 根据text获取待时间戳的log info
    @staticmethod
    def _get_log_info(text: str, log_level) -> str:
        now = time.localtime()
        if log_level == logging.DEBUG:
            ms = int((time.time() - int(time.time())) * 1000)
            timestamp = "[%s.%03d]" % (time.strftime("%H:%M:%S", now), ms)
        else:
            timestamp = "[%s]" % (time.strftime("%H:%M:%S", now))
        log_info = f"{timestamp} - {text}"
        return log_info

    # 输出至文本框
    def log_to_output_stream(self, log_info: str, level_name: str):
        font_style = FONT_STYLE_DICT[level_name]
        color = font_style[0]
        font_size = font_style[1]
        font_weight = font_style[2]

        if self._log_window_stream is not None:
            colored_text = f"<span style=\" font-size:{font_size}pt; " \
                           f"font-weight:{font_weight}; " \
                           f"color:{color};\" >" + log_info + "</span>"
            self._log_window_stream(colored_text)

    # 用户主动查询的信息（浅紫色）
    def query(self, text: str):
        log_info = self._get_log_info(text, logging.INFO)
        if self.to_cmdline:
            if self.enable_colorful_cmdline:
                self.colorful_cmd_logger.info(log_info)
            else:
                _console_print(log_info)
        self.log_to_output_stream(log_info, "QUERY")

    # 提示日志（默认颜色）
    def info(self, text: str):
        log_info = self._get_log_info(text, logging.INFO)
        if self.to_cmdline:
            if self.enable_colorful_cmdline:
                self.colorful_cmd_logger.info(log_info)
            else:
                _console_print(log_info)
        self.log_to_output_stream(log_info, "INFO")

    # 警告日志（黄色）
    def warning(self, text: str):
        log_info = self._get_log_info(text, logging.WARNING)
        if self.to_cmdline:
            if self.enable_colorful_cmdline:
                self.colorful_cmd_logger.warning(log_info)
            else:
                _console_print(log_info)
        self.log_to_output_stream(log_info, "WARNING")

    # 错误日志（红色）
    def error(self, text: str):
        log_info = self._get_log_info(text, logging.ERROR)
        if self.to_cmdline:
            if self.enable_colorful_cmdline:
                self.colorful_cmd_logger.error(log_info)
            else:
                _console_print(log_info)
        self.log_to_output_stream(log_info, "ERROR")

    # 底层日志（深紫色）
    def debug(self, text: str):
        log_info = self._get_log_info(text, logging.DEBUG)
        if self.to_cmdline:
            if self.enable_colorful_cmdline:
                self.colorful_cmd_logger.debug(log_info)
            else:
                _console_print(log_info)
        # 仅Debug模式开启
        if self._debug_mode:
            self.log_to_output_stream(log_info, "DEBUG")

    # 故障日志（红色）
    def exception(self, text: str):
        log_info = self._get_log_info(text, logging.ERROR)
        if self.to_cmdline:
            if self.enable_colorful_cmdline:
                self.colorful_cmd_logger.exception(log_info)
            else:
                _console_print(log_info)
        self.log_to_output_stream(log_info, "EXCEPTION")

    # 状态栏日志
    def status(self, text: str):
        self._status_bar_stream(text)
