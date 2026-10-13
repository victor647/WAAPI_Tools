import os
import sys
import io
import logging
import time
from libraries.singleton import Singleton


def _waapi_mcp_mode() -> bool:
    return os.environ.get("WAAPI_MCP") == "1"


# 运行日志文件：每次启动以 w 模式重写，放在应用目录（打包后为 exe 所在目录）
# GUI 与 MCP 分开写日志文件，均放在应用目录，每次启动以 w 模式重写
LOG_FILE_NAMES = {"gui": "gui_log.log", "mcp": "mcp_log.log"}


# 当前进程属于哪种运行模式（MCP 以 stdio 提供服务，与 GUI 分开记日志）
def log_mode() -> str:
    return "mcp" if _waapi_mcp_mode() else "gui"


def _log_dir() -> str:
    # 延迟导入 path_utils：该模块顶部依赖本模块，避免循环导入
    from libraries.utils import path_utils

    return path_utils.get_app_dir()


def _software_version() -> str:
    try:
        from globals.version import get_software_version

        return get_software_version()
    except Exception:
        return ""


# 把 print() / 第三方库写到 stdout、stderr 的内容一并收进日志文件；
# 原流仍照常输出（开发环境控制台不受影响），打包成无控制台的 exe 时只写文件
class _StreamTee(io.TextIOBase):

    def __init__(self, stream, prefix: str = ""):
        self._stream = stream
        self._prefix = prefix
        self._pending = ""

    @property
    def encoding(self):
        return getattr(self._stream, "encoding", None) or "utf-8"

    def write(self, text):
        if self._stream is not None:
            self._stream.write(text)
        self._pending += text
        while "\n" in self._pending:
            line, self._pending = self._pending.split("\n", 1)
            if line.strip():
                Logger().trace(f"{self._prefix}{line}", console=False)
        return len(text)

    def flush(self):
        if self._pending.strip():
            Logger().trace(f"{self._prefix}{self._pending.strip()}", console=False)
            self._pending = ""
        if self._stream is not None:
            self._stream.flush()

    def isatty(self):
        return False


# 安装输出捕获：MCP 的 stdout 走 JSON-RPC 协议，只接管 stderr
def install_output_capture() -> None:
    names = (("stderr", "[stderr] "),) if _waapi_mcp_mode() else (("stdout", ""), ("stderr", "[stderr] "))
    for name, prefix in names:
        stream = getattr(sys, name, None)
        if isinstance(stream, _StreamTee):
            continue
        setattr(sys, name, _StreamTee(stream, prefix))

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


# 默认不落盘的明细日志（批量逐对象处理、WAAPI 调用流水）最多积攒多少行/多久才 flush 一次
DETAIL_LOG_FLUSH_LINES = 200
DETAIL_LOG_FLUSH_SECONDS = 0.5


# 带缓冲的日志文件句柄：logging.FileHandler 默认每条记录都 flush（每条一次 write+flush 系统调用），
# 明细日志量大时开销可观；这里按行数与时间攒批落盘，退出前由 Logger().flush() 兜底
class _BufferedFileHandler(logging.FileHandler):

    def __init__(self, filename, flush_lines: int = DETAIL_LOG_FLUSH_LINES,
                 flush_seconds: float = DETAIL_LOG_FLUSH_SECONDS):
        super().__init__(filename, mode="w", encoding="utf-8")
        self._flush_lines = max(1, flush_lines)
        self._flush_seconds = max(0.0, flush_seconds)
        self._pending = 0
        self._last_flush = time.monotonic()

    def emit(self, record):
        with self.lock:
            try:
                message = self.format(record)
                self.stream.write(message + self.terminator)
                self._pending += 1
                if self._pending >= self._flush_lines or \
                        time.monotonic() - self._last_flush >= self._flush_seconds:
                    self.flush()
            except Exception:
                self.handleError(record)

    def flush(self):
        super().flush()
        self._pending = 0
        self._last_flush = time.monotonic()


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
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        self.console_handle = None

    # 控制台句柄：IDE 里用带 ANSI 颜色的 stderr，普通命令行用不带颜色码的 stdout；
    # MCP stdio 固定走 stderr（避免与 stdout 上的 JSON-RPC 混流），
    # 打包成无控制台的 exe 时两个流都是 None，此时不注册控制台句柄，只写日志文件
    def attach_console(self, use_color: bool) -> None:
        stream = sys.stderr if (_waapi_mcp_mode() or use_color) else sys.stdout
        if stream is None:
            return
        self.console_handle = logging.StreamHandler(stream)
        self.console_handle.setLevel(logging.DEBUG)
        formatter = CustomFormatter() if use_color else logging.Formatter("%(message)s")
        self.console_handle.setFormatter(formatter)
        self.logger.addHandler(self.console_handle)


# Logger: 在console和QTextItem中输出
class Logger(object, metaclass=Singleton):
    def __new__(cls, *args, **kwargs):
        # 构造过程中会读配置，读配置又可能用到 Logger（如「用户配置已加载」），
        # 这里先登记实例，让递归调用复用同一个对象：否则会重复注册句柄（日志翻倍）
        # 并用 w 模式二次打开日志文件（把已写入的内容截断）
        Singleton._instances[cls] = super().__new__(cls)
        return Singleton._instances[cls]

    def __init__(self):
        self.to_cmdline = True
        self._console_logger = ColorfulCMDLogger()
        self.colorful_cmd_logger = self._console_logger.logger
        # 在Pycharm中的Console中执行：带颜色；在exe中执行：不带颜色
        self.enable_colorful_cmdline = True if os.getenv("PYCHARM_HOSTED") else False
        self._log_window_stream = None
        self._status_bar_stream = None
        self._debug_mode = False
        # 「记录明细日志」开关：默认关，关掉后批量逐对象、WAAPI 流水这类高频日志不再生成
        self._detail_enabled = False
        self.log_file_path = ""
        self._file_only_logger = logging.getLogger("FFSimpleTool.file")
        self._console_logger.attach_console(self.enable_colorful_cmdline)
        self._setup_file_log()
        self.refresh_detail_log_setting()

    # 运行日志文件：每次启动重写一份，便于只看本次运行的完整输出
    def _setup_file_log(self) -> None:
        mode = log_mode()
        path = os.path.join(_log_dir(), LOG_FILE_NAMES[mode])
        try:
            handler = _BufferedFileHandler(path)
        except OSError as e:
            self.info(f"无法写入日志文件 {path}：{e}")
            return
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        self.colorful_cmd_logger.addHandler(handler)
        # 第二个日志器只挂文件句柄：WAAPI 调用流水等只想进文件的内容走它
        self._file_only_logger = logging.getLogger("FFSimpleTool.file")
        self._file_only_logger.handlers.clear()
        self._file_only_logger.setLevel(logging.DEBUG)
        self._file_only_logger.propagate = False
        self._file_only_logger.addHandler(handler)
        self.log_file_path = path
        header = (
            f"===== WAAPI 工具集 {_software_version()} 启动 "
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} ({mode.upper()}) =====\n"
            f"Python {sys.version.split()[0]} | {'打包环境' if getattr(sys, 'frozen', False) else '开发环境'} "
            f"| 工作目录 {os.getcwd()}\n"
            f"日志文件 {path}\n"
        )
        handler.stream.write(header)
        handler.stream.flush()

    # 重新读取「记录明细日志」开关（设置窗口改动后由 user_config 调用，避免每次写日志都读配置）
    def refresh_detail_log_setting(self) -> None:
        try:
            from libraries.utils import user_config

            self._detail_enabled = user_config.get_tool_detail_log_enabled()
        except Exception:
            # 配置还没就绪（或导入期）时按关闭处理
            self._detail_enabled = False

    # 明细日志当前是否输出：总开关关闭、或「记录明细日志」未开启时为 False
    def detail_on(self) -> bool:
        return bool(self.to_cmdline and self._detail_enabled)

    # 把所有日志句柄的缓冲内容落盘（退出前调用，避免缓冲里的日志丢失）
    def flush(self) -> None:
        for logger in (self.colorful_cmd_logger, self._file_only_logger):
            for handler in list(logger.handlers):
                try:
                    handler.flush()
                except Exception:
                    continue

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

    # 控制台与日志文件统一由 logging 句柄输出：控制台句柄缺失（无控制台的 exe）时只落日志文件
    def _emit(self, log_info: str, level: int, exc_info: bool = False):
        if not self.to_cmdline:
            return
        self.colorful_cmd_logger.log(level, log_info, exc_info=exc_info)

    # 用户主动查询的信息（浅紫色）
    def query(self, text: str):
        log_info = self._get_log_info(text, logging.INFO)
        self._emit(log_info, logging.INFO)
        self.log_to_output_stream(log_info, "QUERY")

    # 提示日志（默认颜色）
    def info(self, text: str):
        log_info = self._get_log_info(text, logging.INFO)
        self._emit(log_info, logging.INFO)
        self.log_to_output_stream(log_info, "INFO")

    # 警告日志（黄色）
    def warning(self, text: str):
        log_info = self._get_log_info(text, logging.WARNING)
        self._emit(log_info, logging.WARNING)
        self.log_to_output_stream(log_info, "WARNING")

    # 错误日志（红色）
    def error(self, text: str):
        log_info = self._get_log_info(text, logging.ERROR)
        self._emit(log_info, logging.ERROR)
        self.log_to_output_stream(log_info, "ERROR")

    # 底层日志（深紫色）
    def debug(self, text: str):
        log_info = self._get_log_info(text, logging.DEBUG)
        self._emit(log_info, logging.DEBUG)
        # 仅Debug模式开启
        if self._debug_mode:
            self.log_to_output_stream(log_info, "DEBUG")

    # 明细日志：写日志文件（console=False 时只写文件），始终不显示在日志窗口
    # 用于批量逐对象处理记录、WAAPI 调用流水等排查用信息
    # detail=True 的调用受「设置 → 工具行为 → 记录明细日志」开关控制（默认关闭）
    def trace(self, text: str, console: bool = True, detail: bool = False):
        if detail and not self.detail_on():
            return
        log_info = self._get_log_info(text, logging.DEBUG)
        if not console:
            self._file_only_logger.debug(log_info)
            return
        self._emit(log_info, logging.DEBUG)

    # 故障日志（红色）
    def exception(self, text: str):
        log_info = self._get_log_info(text, logging.ERROR)
        self._emit(log_info, logging.ERROR, exc_info=True)
        self.log_to_output_stream(log_info, "EXCEPTION")

    # 状态栏日志
    def status(self, text: str):
        if self._status_bar_stream:
            self._status_bar_stream(text)
