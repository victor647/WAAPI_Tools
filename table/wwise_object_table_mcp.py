"""MCP / 无界面场景：与 GUI 共用 `WwiseObjectTable`，构造时不传入 QTableView。"""
from __future__ import annotations

from libraries.multi_thread import batch_processor
from table.wwise_object_table import WwiseObjectTable


class WwiseTableImpl_MCP(WwiseObjectTable):
    def __init__(self):
        super().__init__(None)

    def _run_batch(
        self,
        objects: list,
        processor,
        title: str,
        obj_name: str = "",
        on_finished=None,
        on_interrupted=None,
        exclusive: bool = True,
        progress_text_func=None,
    ):
        # MCP 场景没有进度条，也不允许在批处理期间插队，progress_text_func / exclusive 只用于对齐 GUI 侧的签名
        batch_processor.create_sync(
            objects,
            processor,
            title,
            on_finished,
            on_interrupted,
        )
