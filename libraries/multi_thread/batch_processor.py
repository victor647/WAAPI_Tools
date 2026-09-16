from PySide6.QtCore import Signal, QThread
from libraries.multi_thread.progress_bar import ProgressBar
import globals.global_variables as gv
from typing import Callable
import traceback

from libraries.utils.log_utils import Logger
from libraries.utils.wwise import waapi_utils

# 单线程批处理（适用于MCP模式）
def create_sync(objects: list, processor: Callable, title: str,
                on_finished: Callable = None, on_interrupted: Callable = None, undo_group: str = ""):
    gv.batch_processor = BatchProcessor(objects, processor, title, on_finished, on_interrupted, undo_group)
    gv.batch_processor.execute()

# 多线程批处理（适用于GUI模式）
def create_async(objects: list, processor: Callable, title: str, obj_name: str = "",
                 on_finished: Callable = None, on_interrupted: Callable = None, on_item_processed: Callable = None,
                 progress_text_func: Callable = None, undo_group: str = ""):
    gv.batch_processor = BatchProcessorAsync(objects, processor, obj_name, on_finished, on_interrupted,
                                             on_item_processed, progress_text_func, undo_group)
    gv.progress_bar = ProgressBar(len(objects), title, gv.batch_processor)
    gv.progress_bar.show()
    gv.progress_bar.raise_()
    gv.progress_bar.activateWindow()
    gv.batch_processor.set_progress_bar(gv.progress_bar)
    gv.batch_processor.start()

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

    def execute(self):
        Logger().debug(f"同步批处理开始：{self.title}")
        self.begin_undo_group()
        try:
            self.run_objects()
        finally:
            self.end_undo_group()

    # 整个批量操作 = 一个撤销组；已有外层撤销组或没有目标对象时不开组
    def begin_undo_group(self):
        if not self.undo_group or not self.objects or waapi_utils.is_undo_group_open():
            return
        self.undo_group_opened = waapi_utils.begin_undo_group(self.undo_group)

    def end_undo_group(self):
        if self.undo_group_opened:
            waapi_utils.end_undo_group(self.undo_group)
            self.undo_group_opened = False

    def run_objects(self):
        for index, obj in enumerate(self.objects, 0):
            try:
                should_continue = self.processor(index, obj)
            except Exception:
                Logger().exception(f"同步批处理异常：{self.title}\n{traceback.format_exc()}")
                if self.on_interrupted:
                    self.on_interrupted()
                return
            if self.on_interrupted and not should_continue:
                Logger().debug(f"同步批处理中断：{self.title}")
                self.on_interrupted()
                return
        Logger().debug(f"同步批处理完成：{self.title}")
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
                 progress_text_func: Callable = None, undo_group: str = ""):
        BatchProcessor.__init__(self, objects, processor, on_finished=on_finished, on_interrupted=on_interrupted,
                                undo_group=undo_group)
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
        title = self.progress_bar.windowTitle() if self.progress_bar else self.title
        Logger().debug(f"异步批处理开始：{title}")
        # 整个批量操作 = 一个撤销组，结束（含异常/中断）后统一关闭
        self.begin_undo_group()
        try:
            self.run_objects(title)
        finally:
            self.end_undo_group()

    def run_objects(self, title: str):
        for index, obj in enumerate(self.objects, 0):
            if not self.is_working:
                break
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
                Logger().exception(f"异步批处理异常：{title}\n{traceback.format_exc()}")
                self.interrupted_signal.emit()
                return
            # 单条处理完成后通知主线程（用于实时刷新进度信息，不触碰 UI 之外的状态）
            self.item_processed_signal.emit((index, obj))
            if self.progress_bar and self.progress_text_func:
                # 自定义进度文本（如“已找到 N 条”）：处理完当前对象后再刷新，避免被默认文本覆盖
                self.progress_bar_signal.emit(index, self.progress_text_func(index, obj))
            if self._interrupt_enabled and not should_continue:
                Logger().debug(f"异步批处理中断：{title}")
                self.interrupted_signal.emit()
                return
        Logger().debug(f"异步批处理完成：{title}")
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
