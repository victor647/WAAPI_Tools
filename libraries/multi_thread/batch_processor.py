from PySide6.QtCore import Signal, QThread
from libraries.multi_thread.progress_bar import ProgressBar
import globals.global_variables as gv
from typing import Callable
import traceback

from libraries.utils.log_utils import Logger

# 单线程批处理（适用于MCP模式）
def create_sync(objects: list, processor: Callable, title: str,
                on_finished: Callable = None, on_interrupted: Callable = None):
    gv.batch_processor = BatchProcessor(objects, processor, title, on_finished, on_interrupted)
    gv.batch_processor.execute()

# 多线程批处理（适用于GUI模式）
def create_async(objects: list, processor: Callable, title: str, obj_name: str = "",
                 on_finished: Callable = None, on_interrupted: Callable = None, on_item_processed: Callable = None):
    gv.batch_processor = BatchProcessorAsync(objects, processor, obj_name, on_finished, on_interrupted, on_item_processed)
    gv.progress_bar = ProgressBar(len(objects), title, gv.batch_processor)
    gv.progress_bar.show()
    gv.progress_bar.raise_()
    gv.progress_bar.activateWindow()
    gv.batch_processor.set_progress_bar(gv.progress_bar)
    gv.batch_processor.start()

# 同步批处理
class BatchProcessor:
    def __init__(self, objects: list, processor: Callable, title: str = "", on_finished: Callable = None, on_interrupted: Callable = None):
        self.objects = objects
        self.processor = processor
        self.title = title
        self.on_finished = on_finished
        self.on_interrupted = on_interrupted

    def execute(self):
        Logger().debug(f"同步批处理开始：{self.title}")
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
                 on_finished: Callable = None, on_interrupted: Callable = None, on_item_processed: Callable = None):
        BatchProcessor.__init__(self, objects, processor, on_finished=on_finished, on_interrupted=on_interrupted)
        QThread.__init__(self)
        self.name_attr = name_attr
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
        title = self.progress_bar.windowTitle()
        Logger().debug(f"异步批处理开始：{title}")
        for index, obj in enumerate(self.objects, 0):
            if not self.is_working:
                break
            if self.progress_bar:
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
