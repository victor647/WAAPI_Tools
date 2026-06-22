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
    ):
        batch_processor.create_sync(
            objects,
            processor,
            title,
            on_finished,
            on_interrupted,
        )
