from PySide6.QtCore import Signal, QThread
from libraries.multi_thread.progress_bar import ProgressBar
import globals.global_variables as gv
from typing import Callable
import traceback

from libraries.utils.log_utils import Logger
from libraries.utils.wwise import waapi_utils


# 同一时间只允许一个批处理：并发跑批处理会抢 gv.progress_bar、交错改动工程、日志也会串在一起
def is_busy() -> bool:
    processor = gv.batch_processor
    if processor is None:
        return False
    if isinstance(processor, QThread):
        return processor.isRunning()
    return bool(getattr(processor, "running", False))


# 正在运行的批处理标题（没有任务时返回空串）
def running_title() -> str:
    if not is_busy():
        return ""
    return str(getattr(gv.batch_processor, "title", "") or "")


# 统一的「有任务正在运行」提示，供各入口告知用户
def busy_message(action: str = "") -> str:
    title = running_title()
    running = f"「{title}」" if title else "其他任务"
    prefix = f"「{action}」未执行：" if action else ""
    return f"{prefix}{running}正在运行，请等它结束后再试"


# 单线程批处理（适用于MCP模式）
def create_sync(objects: list, processor: Callable, title: str,
                on_finished: Callable = None, on_interrupted: Callable = None, undo_group: str = "",
                exclusive: bool = True):
    if exclusive and is_busy():
        Logger().warning(busy_message(title))
        return False
    gv.batch_processor = BatchProcessor(objects, processor, title, on_finished, on_interrupted, undo_group)
    gv.batch_processor.execute()
    return True

# 多线程批处理（适用于GUI模式）
def create_async(objects: list, processor: Callable, title: str, obj_name: str = "",
                 on_finished: Callable = None, on_interrupted: Callable = None, on_item_processed: Callable = None,
                 progress_text_func: Callable = None, undo_group: str = "", exclusive: bool = True):
    # exclusive=False 的调用（如表格自身刷新）允许与工具并行，其余一律拒绝，避免并发改动工程
    if exclusive and is_busy():
        Logger().warning(busy_message(title))
        return False
    gv.batch_processor = BatchProcessorAsync(objects, processor, obj_name, on_finished, on_interrupted,
                                             on_item_processed, progress_text_func, undo_group, title)
    gv.progress_bar = ProgressBar(len(objects), title, gv.batch_processor)
    gv.progress_bar.show()
    gv.progress_bar.raise_()
    gv.progress_bar.activateWindow()
    gv.batch_processor.set_progress_bar(gv.progress_bar)
    gv.batch_processor.start()
    return True

# 同步批处理
class BatchProcessor:
    def __init__(self, objects: list, processor: Callable, title: str = "", on_finished: Callable = None,
                 on_interrupted: Callable = None, undo_group: str = ""):
        self.objects = objects
        self.processor = processor
        self.title = title
        self.on_finished = on_finished
        self.on_interrupted = on_interrupted
        # 非空时把整批操作包进一个撤销组，Wwise 里可一步撤销，名字用于主窗口「撤销/重做」显示
        self.undo_group = undo_group
        self.undo_group_opened = False
        # 同步批处理是否正在执行（供 is_busy 判断；异步侧用 QThread.isRunning）
        self.running = False

    def execute(self):
        Logger().debug(f"同步批处理开始：{self.title}（{len(self.objects)} 个对象）")
        self.running = True
        try:
            self.begin_undo_group()
            self.run_objects(self.title)
        finally:
            self.end_undo_group()
            self.running = False

    # 整个批量操作 = 一个撤销组；已有外层撤销组或没有目标对象时不开组
    def begin_undo_group(self):
        if not self.undo_group or not self.objects or waapi_utils.is_undo_group_open():
            return
        self.undo_group_opened = waapi_utils.begin_undo_group(self.undo_group)

    def end_undo_group(self):
        if self.undo_group_opened:
            waapi_utils.end_undo_group(self.undo_group)
            self.undo_group_opened = False

    # 每处理一个对象记一条明细日志：只进日志文件与控制台，不显示在日志窗口
    @staticmethod
    def object_label(obj) -> str:
        if not isinstance(obj, str):
            path = getattr(obj, "path", "")
            if path:
                return path
            name = getattr(obj, "name", "")
            if name:
                return name
            obj = str(obj)
        # 表格行 / CSV 行这类内容可能很长，截断避免日志爆长
        return obj if len(obj) <= 120 else obj[:100] + f"...({len(obj)}字符)"

    def run_objects(self, title: str = ""):
        total = len(self.objects)
        # 明细日志关闭时不生成逐对象日志（也省掉 object_label 的路径拼装）
        detail = Logger().detail_on()
        for index, obj in enumerate(self.objects, 0):
            if detail:
                Logger().trace(f"{title} [{index + 1}/{total}] {self.object_label(obj)}",
                               console=False, detail=True)
            try:
                should_continue = self.processor(index, obj)
            except Exception:
                Logger().exception(
                    f"同步批处理异常：{self.title} [{index + 1}/{total}] {self.object_label(obj)}\n"
                    f"{traceback.format_exc()}")
                if self.on_interrupted:
                    self.on_interrupted()
                return
            if self.on_interrupted and not should_continue:
                Logger().debug(f"同步批处理中断：{self.title}")
                self.on_interrupted()
                return
        Logger().debug(f"同步批处理完成：{self.title}（{total} 个对象）")
        if self.on_finished:
            self.on_finished()

# 异步批处理
class BatchProcessorAsync(BatchProcessor, QThread):
    progress_bar_signal = Signal(int, str)
    item_processed_signal = Signal(object)
    finished_signal = Signal()
    interrupted_signal = Signal()

    def __init__(self, objects: list, processor: Callable, name_attr: str = "",
                 on_finished: Callable = None, on_interrupted: Callable = None, on_item_processed: Callable = None,
                 progress_text_func: Callable = None, undo_group: str = "", title: str = ""):
        BatchProcessor.__init__(self, objects, processor, title, on_finished=on_finished,
                                on_interrupted=on_interrupted, undo_group=undo_group)
        QThread.__init__(self)
        self.name_attr = name_attr
        self.progress_text_func = progress_text_func
        self.is_working = True
        self.progress_bar: ProgressBar = None
        self._interrupt_enabled = on_interrupted is not None
        self.finished_signal.connect(self._on_finished)
        self.interrupted_signal.connect(self._on_interrupted)
        if on_item_processed:
            self.item_processed_signal.connect(on_item_processed)

    # 绑定进度条窗口
    def set_progress_bar(self, progress_bar: ProgressBar):
        self.progress_bar = progress_bar
        self.progress_bar_signal.connect(progress_bar.update_progress)

    def run(self):
        title = self.title or (self.progress_bar.windowTitle() if self.progress_bar else "")
        Logger().debug(f"异步批处理开始：{title}（{len(self.objects)} 个对象）")
        # 整个批量操作 = 一个撤销组，结束（含异常/中断）后统一关闭
        self.begin_undo_group()
        try:
            self.run_objects(title)
        finally:
            self.end_undo_group()

    def run_objects(self, title: str):
        total = len(self.objects)
        done = 0
        # 明细日志关闭时不生成逐对象日志（也省掉 object_label 的路径拼装）
        detail = Logger().detail_on()
        for index, obj in enumerate(self.objects, 0):
            if not self.is_working:
                break
            if detail:
                Logger().trace(f"{title} [{index + 1}/{total}] {self.object_label(obj)}",
                               console=False, detail=True)
            if self.progress_bar and not self.progress_text_func:
                # 遍历字符串的话直接显示对象名称
                if isinstance(obj, str):
                    text = obj
                else:
                    text = getattr(obj, self.name_attr, "") if self.name_attr else ""
                self.progress_bar_signal.emit(index, text)
            try:
                should_continue = self.processor(index, obj)
            except Exception:
                Logger().exception(
                    f"异步批处理异常：{title} [{index + 1}/{total}] {self.object_label(obj)}\n"
                    f"{traceback.format_exc()}")
                self.interrupted_signal.emit()
                return
            done += 1
            # 单条处理完成后通知主线程（用于实时刷新进度信息，不触碰 UI 之外的状态）
            self.item_processed_signal.emit((index, obj))
            if self.progress_bar and self.progress_text_func:
                # 自定义进度文本（如“已找到 N 条”）：处理完当前对象后再刷新，避免被默认文本覆盖
                self.progress_bar_signal.emit(index, self.progress_text_func(index, obj))
            if self._interrupt_enabled and not should_continue:
                Logger().debug(f"异步批处理中断：{title}")
                self.interrupted_signal.emit()
                return
        if done < total:
            Logger().debug(f"异步批处理中断：{title}（已处理 {done}/{total} 个对象）")
        else:
            Logger().debug(f"异步批处理完成：{title}（{total} 个对象）")
        self.finished_signal.emit()

    def stop(self):
        self.is_working = False

    # 正常执行结束
    def _on_finished(self):
        if self.progress_bar:
            self.progress_bar.close()
        if self.on_finished:
            self.on_finished()

    # 中途打断
    def _on_interrupted(self):
        if self.progress_bar:
            self.progress_bar.close()
        if self.on_interrupted:
            self.on_interrupted()
