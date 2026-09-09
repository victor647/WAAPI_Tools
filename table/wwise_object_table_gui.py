import os
from functools import partial

import clipboard
import globals.global_variables as gv
import libraries.multi_thread.batch_processor as batch_processor
from PySide6.QtWidgets import QTableView, QMenu, QAbstractItemView
from PySide6.QtCore import QModelIndex, Qt

from libraries.utils import path_utils
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import common_utils, transport_utils, waapi_utils
from libraries.wwise_object import WwiseObjectType
from table.wwise_table_context_menu import add_common_object_actions
from table.wwise_object_table import WwiseObjectTable, WwiseTableDisplayMode
from table.wwise_table_headers import *


class WwiseTableImpl_GUI(WwiseObjectTable):
    def __init__(self, table_view: QTableView):
        super().__init__(table_view)

    def _run_batch(
        self,
        objects: list,
        processor,
        title: str,
        obj_name: str = "",
        on_finished=None,
        on_interrupted=None,
    ):
        batch_processor.create_async(
            objects,
            processor,
            title,
            obj_name,
            on_finished=on_finished,
            on_interrupted=on_interrupted,
        )

    def init_table_view(self):
        super().init_table_view()
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def show_context_menu(self, position):
        index = self.table_view.indexAt(position)
        if not index.isValid():
            return
        column = index.column()
        row_data = self.data[self.get_source_row(index)]
        obj = row_data.wwise_object
        selection = self.table_view.selectionModel().selectedIndexes()
        items = [item for item in selection if item.column() == column]
        menu = QMenu()
        if column in (NAME_COL, PATH_COL):
            menu.addAction('复制', lambda: self.copy_cell_text(index))
        # 通用对象动作（在Wwise中选中、AudioSource 预览）
        add_common_object_actions(menu, obj, self.table_view)
        if column == NAME_COL:
            menu.addAction("WAAPI播放", lambda: self.play_in_wwise(index))
            if self.wwise_transport_id != -1:
                menu.addAction("停止", self.stop_in_wwise)
        elif column == TYPE_COL:
            sub = menu.addMenu("改变类型为")
            sub.addAction(
                "Actor Mixer",
                partial(self._convert_selection_to_type, items, WwiseObjectType.ActorMixer),
            )
            sub.addAction(
                "Blend Container",
                partial(self._convert_selection_to_type, items, WwiseObjectType.BlendContainer),
            )
            sub.addAction(
                "Random/Sequence Container",
                partial(self._convert_selection_to_type, items, WwiseObjectType.RandomContainer),
            )
            sub.addAction(
                "Switch Container",
                partial(self._convert_selection_to_type, items, WwiseObjectType.SwitchContainer),
            )
            sub.addAction(
                "Virtual Folder",
                partial(self._convert_selection_to_type, items, WwiseObjectType.Folder),
            )
            sub.addAction(
                "Work Unit",
                partial(self._convert_selection_to_type, items, WwiseObjectType.WorkUnit),
            )
        if self.display_mode == WwiseTableDisplayMode.Integration:
            if column == TARGET_PATH_COL:
                menu.addAction("选中", lambda: self.select_in_wwise(items))
        menu.exec(self.table_view.viewport().mapToGlobal(position))

    def refresh_rows_after_type_change(self, rows: list[int], paths: list[str]) -> None:
        for row, path in zip(rows, paths):
            if row < 0 or row >= len(self.data):
                continue
            rd = self.data[row]
            updated = waapi_utils.find_object_by_path(path)
            if not updated or not updated.is_valid:
                Logger().warning(f"改变类型后无法按路径刷新：{path}")
                continue
            rd.replace_wwise_object(updated)
            if row < len(gv.active_objects):
                gv.active_objects[row] = updated
            rd.read_common_data(self._inclusion_cache, read_optional=not self.light_mode)
            self.read_data_by_display_mode(rd)

    def _convert_selection_to_type(self, items: list[QModelIndex], target_type: WwiseObjectType):
        if not items:
            return
        seen: set[int] = set()
        objs = []
        rows_ordered: list[int] = []
        paths_before: list[str] = []
        for item in items:
            row = self.get_source_row(item)
            if row in seen:
                continue
            seen.add(row)
            rows_ordered.append(row)
            paths_before.append(self.data[row].path)
            objs.append(self.data[row].wwise_object)
        if not objs:
            return

        def proc(index: int, obj):
            common_utils.convert_to_type(obj, target_type)
            return True

        def finished():
            self.refresh_rows_after_type_change(rows_ordered, paths_before)

        self._run_batch(objs, proc, "改变类型", "name", on_finished=finished)

    def play_in_wwise(self, item: QModelIndex):
        row_data = self.data[self.get_source_row(item)]
        event = row_data.wwise_info.event_obj
        if event:
            Logger().info(f"正在通过Wwise播放：{event.name}")
            self.stop_in_wwise()
            self.wwise_transport_id = transport_utils.play_sound(event)
        else:
            Logger().error(f"AudioEvent不存在：{row_data.wwise_info.event_name}，播放失败！")

    def stop_in_wwise(self):
        if self.wwise_transport_id != -1:
            transport_utils.stop_sound(self.wwise_transport_id)
            self.wwise_transport_id = -1

    def on_transport_state_changed(self, args):
        transport_id = args["transport"]
        state = args["state"]
        if transport_id == self.wwise_transport_id and state == "Stopped":
            Logger().info("Wwise音效播放完毕")
            waapi_utils.destroy_transport(transport_id)
            self.wwise_transport_id = -1

    def show_in_explorer(self, item: QModelIndex):
        row_data = self.data[self.get_source_row(item)]
        wave_info = row_data.get_current_wave_info()
        if not wave_info:
            Logger().error(f"语音资源不存在，请检查当前语言和性别！")
            return
        file_path = wave_info.file_path
        path_utils.open_file_in_explorer(file_path)

    def open_meta_file(self, item: QModelIndex):
        row_data = self.data[self.get_source_row(item)]
        unity_info = row_data.get_current_unity_info()
        if not unity_info:
            Logger().error(f"语音资源不存在，请检查当前语言和性别！")
            return
        file_path = unity_info.meta_path
        if os.path.exists(file_path):
            Logger().info(f"正在打开Meta文件：{file_path}")
            os.startfile(file_path)
        else:
            Logger().error(f"Meta文件不存在：{file_path}，打开失败！")

    def select_in_wwise(self, items: list[QModelIndex]):
        wwise_objects = []
        for item in items:
            row_data = self.data[self.get_source_row(item)]
            wwise_objects.append(row_data.wwise_object)
        waapi_utils.select_objects_in_wwise(wwise_objects)

    @staticmethod
    def copy_cell_text(item: QModelIndex):
        text = item.data(Qt.ItemDataRole.UserRole)
        Logger().info(f"已复制到剪贴板：{text}")
        clipboard.copy(text)

# 主窗口等历史入口
WwiseTableImpl = WwiseTableImpl_GUI
