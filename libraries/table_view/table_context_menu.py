from dataclasses import dataclass, field
from enum import Flag, auto
from typing import Callable, Optional

import clipboard
from PySide6.QtCore import QObject, QPoint
from PySide6.QtWidgets import QMenu, QTableWidget, QTableWidgetItem

from libraries.utils.log_utils import Logger
from libraries.utils.wwise import transport_utils, waapi_utils
from libraries.wwise_object import WwiseObjectType
from libraries.table_view.table_path_item import full_path_from_item


class CellCapability(Flag):
    TEXT = auto()
    WWISE_OBJECT = auto()
    AUDIO_FILE_PATH = auto()
    WWISE_OBJECT_PATH = auto()
    EVENT_NAME = auto()


@dataclass
class CellPayload:
    text: str = ""
    wwise_object: object = None
    wwise_objects: list = field(default_factory=list)
    audio_file_path: str = ""
    wwise_path: str = ""
    event_name: str = ""
    event_object: object = None
    trim_begin_seconds: float = None
    trim_end_seconds: float = None


@dataclass(frozen=True)
class ColumnSpec:
    capabilities: CellCapability
    default_action: str = ""


class TableContextMenu(QObject):

    def __init__(
        self,
        table: QTableWidget,
        columns: dict[int, ColumnSpec],
        payload_resolver: Callable[[int, int], CellPayload],
        extra_actions: Optional[Callable] = None,
        parent=None,
    ):
        super().__init__(parent or table)
        self.__table = table
        self.__columns = dict(columns)
        self.__payload_resolver = payload_resolver
        self.__extra_actions = extra_actions
        self.__transport_id = -1

    def install(self):
        self.__table.customContextMenuRequested.connect(self.show_menu)
        self.__table.itemDoubleClicked.connect(self.on_double_click)

    def set_columns(self, columns: dict[int, ColumnSpec]):
        self.__columns = dict(columns)

    def spec_for(self, column: int) -> ColumnSpec:
        return self.__columns.get(column, ColumnSpec(CellCapability.TEXT))

    def payload_for(self, row: int, column: int) -> CellPayload:
        value = self.__payload_resolver(row, column)
        if isinstance(value, CellPayload):
            return value
        if isinstance(value, dict):
            return CellPayload(**value)
        return CellPayload(text=str(value or ""))

    def show_menu(self, position: QPoint):
        item = self.__table.itemAt(position)
        if item is None:
            return
        menu = QMenu(self.__table)
        added: set[str] = set()
        self.add_standard_actions(menu, item.row(), item.column(), added)
        if self.__extra_actions is not None:
            payload = self.payload_for(item.row(), item.column())
            self.__extra_actions(menu, item, payload)
        if menu.actions():
            menu.exec(self.__table.viewport().mapToGlobal(position))

    def on_double_click(self, item: QTableWidgetItem):
        spec = self.spec_for(item.column())
        if not spec.default_action:
            return
        payload = self.payload_for(item.row(), item.column())
        self.run_action(spec.default_action, payload)

    def add_standard_actions(self, menu: QMenu, row: int, column: int, added: set[str]):
        spec = self.spec_for(column)
        payload = self.payload_for(row, column)
        objects = self.objects_of(payload)
        has_path = CellCapability.WWISE_OBJECT_PATH in spec.capabilities and bool(payload.wwise_path)
        object_name = objects[0].name if objects else ""
        if has_path:
            self.add_action(menu, added, "copy", "复制", lambda: self.copy_path(payload))
        elif objects and payload.text and payload.text == object_name:
            self.add_action(menu, added, "copy", "复制", lambda: self.copy_name(payload))
        elif CellCapability.TEXT in spec.capabilities:
            self.add_action(menu, added, "copy", "复制", lambda: self.copy_text(payload))
        if CellCapability.WWISE_OBJECT in spec.capabilities and objects:
            self.add_action(menu, added, "select", "在Wwise中选中", lambda: self.select_object(payload))
        if CellCapability.AUDIO_FILE_PATH in spec.capabilities and payload.audio_file_path:
            self.add_action(menu, added, "preview", "音频预览", lambda: self.preview_audio(payload))
        if CellCapability.EVENT_NAME in spec.capabilities and payload.event_name:
            self.add_action(menu, added, "play", "WAAPI播放", lambda: self.play_event(payload))
            if self.__transport_id != -1:
                self.add_action(menu, added, "stop", "停止", self.stop_event)

    @staticmethod
    def add_action(menu: QMenu, added: set[str], key: str, label: str, callback):
        if key in added:
            return
        added.add(key)
        menu.addAction(label, callback)

    def run_action(self, key: str, payload: CellPayload):
        actions = {
            "copy": lambda: self.copy_text(payload),
            "copy_name": lambda: self.copy_name(payload),
            "select": lambda: self.select_object(payload),
            "copy_path": lambda: self.copy_path(payload),
            "preview": lambda: self.preview_audio(payload),
            "play": lambda: self.play_event(payload),
            "stop": self.stop_event,
        }
        action = actions.get(key)
        if action is not None:
            action()

    @staticmethod
    def objects_of(payload: CellPayload) -> list:
        objects = [obj for obj in (payload.wwise_objects or []) if obj and obj.is_valid]
        if objects:
            return objects
        if payload.wwise_object is not None and payload.wwise_object.is_valid:
            return [payload.wwise_object]
        return []

    @staticmethod
    def copy_text(payload: CellPayload):
        if payload.text:
            clipboard.copy(payload.text)

    @staticmethod
    def copy_path(payload: CellPayload):
        if payload.wwise_path:
            clipboard.copy(payload.wwise_path)

    @staticmethod
    def copy_name(payload: CellPayload):
        objects = [obj for obj in (payload.wwise_objects or []) if obj and obj.is_valid]
        if not objects and payload.wwise_object is not None and payload.wwise_object.is_valid:
            objects = [payload.wwise_object]
        if objects:
            clipboard.copy(objects[0].name)

    def select_object(self, payload: CellPayload):
        objects = self.objects_of(payload)
        if not objects:
            Logger().warning("该行没有对应的 Wwise 对象，无法选中")
            return
        waapi_utils.select_objects_in_wwise(objects)

    def preview_audio(self, payload: CellPayload):
        from windows.audio_preview_window import AudioPreviewWindow

        AudioPreviewWindow(
            payload.audio_file_path,
            self.__table,
            trim_begin_seconds=payload.trim_begin_seconds,
            trim_end_seconds=payload.trim_end_seconds,
        ).show()

    def play_event(self, payload: CellPayload):
        if not waapi_utils.is_connected():
            Logger().warning("Wwise 未连接，无法播放")
            return
        event = payload.event_object
        if event is None or not event.is_valid:
            event = waapi_utils.find_object_by_name_and_type(
                payload.event_name, WwiseObjectType.Event
            )
        if event is None or not event.is_valid:
            Logger().warning(f"未找到播放 Event：{payload.event_name}")
            return
        self.stop_event()
        self.__transport_id = transport_utils.play_sound(event)
        if self.__transport_id != -1:
            Logger().info(f"正在通过 Wwise 播放：{event.name}")

    def stop_event(self):
        if self.__transport_id == -1:
            return
        transport_utils.stop_sound(self.__transport_id)
        self.__transport_id = -1


# 行级 Wwise 对象表格的快捷接入：默认所有列可复制/选中对象，路径列复制完整路径
def install_row_object_context(
    table: QTableWidget,
    object_resolver: Callable[[int], object],
    path_columns: tuple[int, ...] = (),
    audio_path_resolver: Optional[Callable[[int], str]] = None,
    audio_columns: tuple[int, ...] = (),
    extra_actions: Optional[Callable] = None,
    default_action: str = "select",
    column_capabilities: Optional[dict[int, CellCapability]] = None,
) -> TableContextMenu:
    columns = {}
    for column in range(table.columnCount()):
        capabilities = CellCapability.TEXT | CellCapability.WWISE_OBJECT
        if column in path_columns:
            capabilities |= CellCapability.WWISE_OBJECT_PATH
        if column in audio_columns:
            capabilities |= CellCapability.AUDIO_FILE_PATH
        if column_capabilities and column in column_capabilities:
            capabilities = column_capabilities[column]
        columns[column] = ColumnSpec(
            capabilities,
            default_action=default_action if column not in audio_columns else "preview",
        )

    def resolve_payload(row: int, column: int) -> CellPayload:
        item = table.item(row, column)
        objects = object_resolver(row) or []
        if not isinstance(objects, (list, tuple)):
            objects = [objects]
        audio_path = ""
        if audio_path_resolver is not None and column in audio_columns:
            audio_path = audio_path_resolver(row) or ""
        return CellPayload(
            text=item.text() if item is not None else "",
            wwise_object=objects[0] if len(objects) == 1 else None,
            wwise_objects=list(objects),
            wwise_path=full_path_from_item(item) if column in path_columns else "",
            audio_file_path=audio_path,
        )

    controller = TableContextMenu(table, columns, resolve_payload, extra_actions)
    controller.install()
    return controller
