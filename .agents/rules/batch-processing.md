# 批量处理必须走 BatchProcessor

工具 / 功能需要对多个对象（Wwise 对象、文件、行数据等）做重复处理时，一律使用批处理机制，禁止在界面线程里跑长循环让主窗口卡死等待。

- 使用 `libraries/multi_thread/batch_processor.py`：
  - GUI 侧用 `batch_processor.create_async(objects, processor, title, obj_name, on_finished=..., on_interrupted=...)`（带进度条、后台线程）。
  - MCP / 无界面场景用对应同步入口（如 `create_sync` 或批量帮助函数）。
- 工作线程的 `processor(index, obj)` 内：
  - 只做耗时操作（WAAPI 查询/写入、文件读写等），**不要直接操作 UI 控件**。
  - 需要展示的结果先收集起来，在 `on_finished`（主线程回调）里一次性更新表格/日志/控件。
- 批量任务尽量可中断：需要时提供 `on_interrupted` 清理逻辑。
- 不要把整批处理塞进信号槽同步执行；涉及 UI 反馈的长任务都必须异步化。
