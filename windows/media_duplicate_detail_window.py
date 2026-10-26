from libraries.base_dialog import BaseDialog
from pathlib import Path

import clipboard
import soundfile
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QMenu, QMessageBox, QStyle, QTableWidgetItem, QWidget

from libraries.utils import wem_utils
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import event_utils, transport_utils, waapi_utils
from libraries.wwise_object import WwiseObjectType
from ui.MediaDuplicateDetail_ui import Ui_MediaDuplicateDetail
from windows.audio_preview_window import AudioPreviewWindow


READ_ONLY_FLAGS = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
POST_EVENT_SOURCE_PLACEHOLDER = "PostEventAction间接引用"


# 同源 wem 明细：打开时才逐个读取 wem 头，避免主分析阶段扫描大量文件
class MediaDuplicateDetailWindow(BaseDialog, Ui_MediaDuplicateDetail):

    def __init__(
        self,
        group,
        search_dirs: list[str | Path],
        platform: str = "",
        original_audio_path: str | Path = None,
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.__group = group
        self.__search_dirs = [Path(path) for path in search_dirs]
        self.__row_event_names: dict[int, list[str]] = {}
        self.__row_sources: dict[int, dict] = {}
        self.__row_conversions: dict[int, object] = {}
        self.__event_source_info: dict[str, list[dict]] = {}
        self.__event_post_event: dict[str, bool] = {}
        self.__trims_loaded = False
        self.__transport_id = -1
        self.setup_triggers()
        self.lblTitle.setText(f"原始音频：{group.original_path}")

        event_names = group.event_names
        if waapi_utils.is_connected():
            self.__event_source_info = self.load_event_source_info(event_names)
            self.__trims_loaded = True

        total_size = 0
        missing_count = 0
        wem_cache: dict[str, tuple] = {}
        for (file_info, event_name, source_name, source_id, source_path,
             conversion_name, conversion_object, edit_pairs) in self.build_detail_rows(event_names):
            info = None
            wem_path = None
            size_text = "-"
            if file_info is not None:
                cache_key = file_info.wem_id.casefold()
                if cache_key not in wem_cache:
                    resolved_path = self.resolve_wem_path(file_info.packed_path)
                    resolved_info = wem_utils.read_wem_info(resolved_path)
                    if resolved_info.size_bytes is None:
                        resolved_size_text = "未找到"
                        missing_count += 1
                    else:
                        resolved_size_text = wem_utils.format_file_size(resolved_info.size_bytes)
                        total_size += resolved_info.size_bytes
                    wem_cache[cache_key] = (resolved_info, resolved_path, resolved_size_text)
                info, wem_path, size_text = wem_cache[cache_key]
            self.append_detail_row(
                file_info, info, wem_path, size_text, event_name,
                source_name, source_id, source_path,
                conversion_name, conversion_object, edit_pairs,
            )

        original_size_text = self.original_audio_size_text(original_audio_path)
        original_duration_text = self.original_audio_duration_text(original_audio_path)
        summary = (
            f"平台：{platform or '未知'}；同源 wem {len(group.files)} 个；"
            f"引用 Event {len(event_names)} 个；"
            f"原始 wav 大小：{original_size_text}（时长 {original_duration_text}）；"
            f"合计 wem 大小：{wem_utils.format_file_size(total_size)}"
        )
        if missing_count:
            summary += f"；未找到 {missing_count} 个文件"
        if not self.__trims_loaded:
            summary += "；Wwise 未连接，Audio Source、Trim 与 Fade 未读取"
        self.lblSummary.setText(summary)
        self.adjust_columns_and_window()
        Logger().info(
            f"打开媒体查重详情：{group.original_path}，"
            f"{len(group.files)} 个 wem，{len(event_names)} 个 Event"
        )

    def resolve_wem_path(self, packed_path: str) -> Path:
        relative_path = Path(packed_path)
        candidates = [directory / relative_path for directory in self.__search_dirs]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return candidates[0] if candidates else relative_path

    @staticmethod
    def original_audio_size_text(original_audio_path: str | Path | None) -> str:
        if not original_audio_path:
            return "未找到"
        try:
            return wem_utils.format_file_size(Path(original_audio_path).stat().st_size)
        except OSError:
            return "未找到"

    @staticmethod
    def original_audio_duration_text(original_audio_path: str | Path | None) -> str:
        if not original_audio_path:
            return "-"
        try:
            with soundfile.SoundFile(str(original_audio_path)) as sound_file:
                duration = sound_file.frames / sound_file.samplerate if sound_file.samplerate else None
        except (OSError, RuntimeError):
            return "-"
        return wem_utils.format_duration(duration)

    def build_detail_rows(self, event_names: list[str]) -> list[tuple]:
        rows = []
        for event_name in event_names:
            related_wems = [
                file_info for file_info in self.__group.files
                if event_name in file_info.soundbank_names
            ]
            if not related_wems:
                continue
            source_infos = self.__event_source_info.get(event_name, [])
            missing_source_name = (
                POST_EVENT_SOURCE_PLACEHOLDER
                if self.__event_post_event.get(event_name)
                else "-"
            )
            if not source_infos:
                rows.extend(
                    (file_info, event_name, missing_source_name, "", None, "-", None, [])
                    for file_info in related_wems
                )
                continue

            used_wem_ids: set[str] = set()
            seen_rows: set[tuple] = set()
            for source_info in source_infos:
                wem_id = str(source_info.get("wem_id") or "").casefold()
                # 同一个 wem 可能被多个 AudioSource 引用，匹配时允许复用
                file_info = next(
                    (
                        item for item in related_wems
                        if item.wem_id.casefold() == wem_id
                    ),
                    None,
                )
                # convertedWemFilePath 取不到时，优先按 Event 下的 wem 与 Source 顺序配对
                if file_info is None:
                    file_info = next(
                        (
                            item for item in related_wems
                            if item.wem_id.casefold() not in used_wem_ids
                        ),
                        related_wems[0],
                    )
                used_wem_ids.add(file_info.wem_id.casefold())
                conversion_name = source_info.get("conversion_name") or "-"
                edit_pair = (
                    source_info.get("trim_begin"),
                    source_info.get("trim_end"),
                    source_info.get("fade_in"),
                    source_info.get("fade_out"),
                )
                # 多个 AudioSource 可能共享同一个 wem 和相同编辑参数，避免展示完全重复的行
                row_key = (
                    file_info.wem_id.casefold(),
                    source_info.get("source_name"),
                    conversion_name,
                    edit_pair,
                )
                if row_key in seen_rows:
                    continue
                seen_rows.add(row_key)
                rows.append((
                    file_info,
                    event_name,
                    source_info.get("source_name") or "-",
                    source_info.get("source_id") or "",
                    source_info.get("source_path"),
                    conversion_name,
                    source_info.get("conversion_object"),
                    [edit_pair],
                ))

            for file_info in related_wems:
                if file_info.wem_id.casefold() not in used_wem_ids:
                    rows.append((
                        file_info,
                        event_name,
                        missing_source_name,
                        "",
                        None,
                        "-",
                        None,
                        [],
                    ))
        return rows

    def setup_triggers(self):
        self.tblWemDetails.customContextMenuRequested.connect(self.show_context_menu)
        self.tblWemDetails.itemDoubleClicked.connect(self.on_item_double_clicked)

    def set_text_cell(self, row: int, column: int, text: str, tooltip: str = ""):
        item = QTableWidgetItem(text)
        item.setFlags(READ_ONLY_FLAGS)
        item.setToolTip(tooltip)
        self.tblWemDetails.setItem(row, column, item)

    def adjust_columns_and_window(self):
        self.tblWemDetails.horizontalHeader().setStretchLastSection(False)
        metrics = self.tblWemDetails.fontMetrics()
        widths = []
        for column in range(self.tblWemDetails.columnCount()):
            header_item = self.tblWemDetails.horizontalHeaderItem(column)
            header_text = header_item.text() if header_item else ""
            width = metrics.horizontalAdvance(header_text) + 24
            for row in range(self.tblWemDetails.rowCount()):
                item = self.tblWemDetails.item(row, column)
                if item is None:
                    continue
                for text_line in item.text().splitlines() or [""]:
                    width = max(width, metrics.horizontalAdvance(text_line) + 24)
            widths.append(width)

        for column, width in enumerate(widths):
            self.tblWemDetails.setColumnWidth(column, width)

        margins = self.layout().contentsMargins()
        scrollbar_width = self.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent)
        extra_width = (
            self.tblWemDetails.frameWidth() * 2
            + scrollbar_width
            + margins.left()
            + margins.right()
            + 12
        )
        target_width = sum(widths) + extra_width
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is not None:
            target_width = min(target_width, int(screen.availableGeometry().width() * 0.95))
        self.resize(max(self.minimumWidth(), target_width), self.height())

    def append_detail_row(
        self,
        file_info,
        info: wem_utils.WemInfo | None,
        wem_path: Path | None,
        size_text: str,
        event_name: str | None,
        source_name: str | None,
        source_id: str | None,
        source_path: str | None,
        conversion_name: str | None,
        conversion_object,
        edit_pairs: list[tuple],
    ):
        row = self.tblWemDetails.rowCount()
        self.tblWemDetails.insertRow(row)
        self.__row_event_names[row] = [event_name] if event_name else []
        self.__row_sources[row] = {
            "name": source_name,
            "id": source_id,
            "path": source_path,
            "trim_begin": edit_pairs[0][0] if edit_pairs else None,
            "trim_end": edit_pairs[0][1] if edit_pairs else None,
            "fade_in": edit_pairs[0][2] if edit_pairs else None,
            "fade_out": edit_pairs[0][3] if edit_pairs else None,
        }
        self.__row_conversions[row] = conversion_object
        wem_text = file_info.packed_path if file_info is not None else "-"
        wem_tooltip = str(wem_path) if wem_path is not None else ""
        self.set_text_cell(row, 0, wem_text, wem_tooltip)
        self.set_text_cell(row, 1, event_name or "-")
        self.set_text_cell(row, 2, source_name or "-")
        self.set_text_cell(row, 3, conversion_name or "-")
        self.set_text_cell(row, 4, info.codec if info is not None else "-")
        sample_rate = f"{info.sample_rate} Hz" if info is not None and info.sample_rate else "-"
        self.set_text_cell(row, 5, sample_rate)
        duration = wem_utils.format_duration(info.duration_seconds) if info is not None else "-"
        self.set_text_cell(row, 6, duration)
        self.set_text_cell(row, 7, size_text, wem_tooltip)
        self.set_text_cell(row, 8, self.format_edit_values(edit_pairs, 0))
        self.set_text_cell(row, 9, self.format_edit_values(edit_pairs, 1))
        self.set_text_cell(row, 10, self.format_edit_values(edit_pairs, 2))
        self.set_text_cell(row, 11, self.format_edit_values(edit_pairs, 3))

    @staticmethod
    def format_edit_value(value: float | None) -> str:
        if value is None or value < 0:
            return "-"
        return f"{value:.3f} s"

    def format_edit_values(self, edit_pairs: list[tuple], index: int) -> str:
        if not edit_pairs:
            return "-"
        return "; ".join(self.format_edit_value(pair[index]) for pair in edit_pairs)

    def find_events(self, event_names: list[str]) -> list:
        objects = []
        seen_ids: set[str] = set()
        for event_name in event_names:
            matches = [
                obj for obj in waapi_utils.find_all_objects_by_name(event_name, exact_match=True)
                if obj.type == WwiseObjectType.Event
            ]
            if not matches:
                match = waapi_utils.find_object_by_name_and_type(event_name, WwiseObjectType.Event)
                if match and match.id:
                    matches = [match]
            for match in matches:
                if match.id and match.id not in seen_ids:
                    seen_ids.add(match.id)
                    objects.append(match)
        return objects

    def collect_audio_sources(self, root) -> list:
        sources = []
        visited: set[str] = set()

        def visit(obj):
            if not obj or not obj.id or obj.id in visited:
                return
            visited.add(obj.id)
            if obj.type == WwiseObjectType.AudioSource:
                sources.append(obj)
                return
            for child in waapi_utils.get_child_objects(obj):
                visit(child)

        visit(root)
        return sources

    def find_event_sources(self, event_name: str) -> tuple[list, bool]:
        sources = []
        seen_ids: set[str] = set()
        has_post_event = False
        for event in self.find_events([event_name]):
            for target in event_utils.get_event_targets(event):
                if target.type == WwiseObjectType.Event:
                    has_post_event = True
                    continue
                for source in self.collect_audio_sources(target):
                    if source.id and source.id not in seen_ids:
                        seen_ids.add(source.id)
                        sources.append(source)
        return sources, has_post_event

    def load_event_source_info(self, event_names: list[str]) -> dict[str, list[dict]]:
        source_by_event: dict[str, list] = {}
        all_sources: dict[str, object] = {}
        for event_name in event_names:
            sources, has_post_event = self.find_event_sources(event_name)
            self.__event_post_event[event_name] = has_post_event
            Logger().debug(
                f"Event [{event_name}] 下找到 {len(sources)} 个 AudioSource，"
                f"PostEvent={has_post_event}"
            )
            source_by_event[event_name] = sources
            for source in sources:
                all_sources[source.id] = source
        if not all_sources:
            return {}

        properties_by_id = waapi_utils.get_objects_properties(
            list(all_sources.values()),
            [
                "originalFilePath",
                "convertedWemFilePath",
                "Conversion",
                "TrimBegin",
                "TrimEnd",
                "FadeInDuration",
                "FadeOutDuration",
            ],
        )
        original_key = self.__group.original_path.replace("\\", "/").casefold()
        source_info_by_event: dict[str, list[dict]] = {}
        for event_name, sources in source_by_event.items():
            source_infos = []
            for source in sources:
                properties = properties_by_id.get(source.id, {})
                original_path = str(properties.get("originalFilePath") or "")
                original_key_in_source = original_path.replace("\\", "/").casefold()
                if original_key_in_source and not original_key_in_source.endswith(original_key):
                    continue
                source_info = {
                    "source_name": source.name,
                    "source_id": source.id,
                    "source_path": original_path,
                    "wem_id": self.wem_id_from_path(properties.get("convertedWemFilePath")),
                    "conversion_object": (
                        properties.get("Conversion") or properties.get("conversion")
                    ),
                    "conversion_name": self.conversion_name(
                        properties.get("Conversion")
                        or properties.get("conversion")
                    ),
                    "trim_begin": properties.get("TrimBegin"),
                    "trim_end": properties.get("TrimEnd"),
                    "fade_in": properties.get("FadeInDuration"),
                    "fade_out": properties.get("FadeOutDuration"),
                }
                if source_info not in source_infos:
                    source_infos.append(source_info)
            if sources and not source_infos:
                Logger().debug(f"Event [{event_name}] 的 AudioSource 未匹配当前原始音频路径")
            source_info_by_event[event_name] = source_infos
        return source_info_by_event

    @staticmethod
    def wem_id_from_path(wem_path: str | None) -> str:
        if not wem_path:
            return ""
        name = str(wem_path).replace("\\", "/").rsplit("/", 1)[-1]
        if name.casefold().endswith(".wem"):
            name = name[:-len(".wem")]
        return name

    @staticmethod
    def conversion_name(value) -> str:
        if isinstance(value, list):
            value = value[0] if value else None
        if isinstance(value, dict):
            return str(value.get("name") or value.get("path") or value.get("id") or "-")
        return str(value) if value else "-"

    # Event 列：复制/选中/WAAPI 播放；Audio Source 列：复制/选中/预览；Conversion 列：选中
    def show_context_menu(self, position):
        item = self.tblWemDetails.itemAt(position)
        if item is None:
            return
        menu = QMenu(self)
        if item.column() == 1:
            event_names = self.__row_event_names.get(item.row(), [])
            if not event_names:
                return
            menu.addAction("复制", lambda: self.copy_event_names(item.row()))
            menu.addAction("选中", lambda: self.select_events(item.row()))
            menu.addAction("WAAPI播放", lambda: self.play_event_in_wwise(item.row()))
            if self.__transport_id != -1:
                menu.addAction("停止", self.stop_event_in_wwise)
        elif item.column() == 2:
            menu.addAction("复制", lambda: self.copy_source_name(item.row()))
            source = self.__row_sources.get(item.row(), {})
            if source.get("name") != POST_EVENT_SOURCE_PLACEHOLDER:
                menu.addAction("在Wwise中选中", lambda: self.select_source(item.row()))
                menu.addAction("音频预览", lambda: self.preview_source_audio(item.row()))
        elif item.column() == 3:
            if item.text():
                menu.addAction("复制", lambda: clipboard.copy(item.text()))
            menu.addAction("在Wwise中选中", lambda: self.select_conversion(item.row()))
        elif item.text():
            menu.addAction("复制", lambda: clipboard.copy(item.text()))
        if not menu.actions():
            return
        menu.exec(self.tblWemDetails.viewport().mapToGlobal(position))

    def on_item_double_clicked(self, item: QTableWidgetItem):
        if item.column() == 1:
            self.select_events(item.row())
        elif item.column() == 2:
            self.select_source(item.row())
        elif item.column() == 3:
            self.select_conversion(item.row())

    def copy_source_name(self, row: int):
        source = self.__row_sources.get(row, {})
        name = source.get("name")
        if not name or name == "-":
            return
        clipboard.copy(name)
        Logger().info(f"已复制 Audio Source 名称：{name}")

    def select_source(self, row: int):
        if not waapi_utils.is_connected():
            QMessageBox.warning(self, "选中 Audio Source", "Wwise 未连接，无法选中 Audio Source。")
            return
        source = self.__row_sources.get(row, {})
        if source.get("name") == POST_EVENT_SOURCE_PLACEHOLDER:
            return
        source_id = source.get("id")
        obj = (
            waapi_utils.get_full_info_from_obj_id(source_id)
            if source_id else None
        )
        if obj is None or not obj.is_valid:
            name = source.get("name")
            obj = (
                waapi_utils.find_object_by_name_and_type(name, WwiseObjectType.AudioSource)
                if name and name != "-" else None
            )
        if obj is None or not obj.is_valid:
            QMessageBox.warning(self, "选中 Audio Source", "在 Wwise 中未找到对应的 Audio Source。")
            return
        if waapi_utils.select_objects_in_wwise([obj]):
            Logger().info(f"已在 Wwise 中选中 Audio Source：{obj.name}")
        else:
            Logger().error(f"在 Wwise 中选中 Audio Source 失败：{obj.name}")

    def select_conversion(self, row: int):
        if not waapi_utils.is_connected():
            QMessageBox.warning(self, "选中 Conversion", "Wwise 未连接，无法选中 Conversion。")
            return
        conversion = self.resolve_conversion_object(row)
        if conversion is None or not conversion.is_valid:
            QMessageBox.warning(self, "选中 Conversion", "在 Wwise 中未找到对应的 Conversion。")
            return
        if waapi_utils.select_objects_in_wwise([conversion]):
            Logger().info(f"已在 Wwise 中选中 Conversion：{conversion.name}")
        else:
            Logger().error(f"在 Wwise 中选中 Conversion 失败：{conversion.name}")

    def resolve_conversion_object(self, row: int):
        value = self.__row_conversions.get(row)
        if isinstance(value, list):
            value = value[0] if value else None
        if isinstance(value, dict):
            object_id = value.get("id")
            if object_id:
                obj = waapi_utils.get_full_info_from_obj_id(object_id)
                if obj and obj.is_valid:
                    return obj
            path = value.get("path")
            if path:
                obj = waapi_utils.find_object_by_path(path)
                if obj and obj.is_valid:
                    return obj
            name = value.get("name")
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                obj = waapi_utils.get_full_info_from_obj_id(stripped)
                if obj and obj.is_valid:
                    return obj
            name = stripped
        else:
            name = ""
        if not name:
            item = self.tblWemDetails.item(row, 3)
            name = item.text() if item is not None else ""
        if not name or name == "-":
            return None
        return waapi_utils.find_object_by_name_and_type(name, WwiseObjectType.Conversion)

    def preview_source_audio(self, row: int):
        source = self.__row_sources.get(row, {})
        if source.get("name") == POST_EVENT_SOURCE_PLACEHOLDER:
            return
        source_path = source.get("path")
        if not source_path or not Path(source_path).is_file():
            QMessageBox.warning(self, "音频预览", f"未找到 Audio Source 文件：\n{source_path or '-'}")
            return
        trim_begin = source.get("trim_begin")
        trim_end = source.get("trim_end")
        AudioPreviewWindow(
            source_path,
            self,
            trim_begin_seconds=trim_begin if trim_begin is not None and trim_begin >= 0 else None,
            trim_end_seconds=trim_end if trim_end is not None and trim_end >= 0 else None,
        ).show()

    def play_event_in_wwise(self, row: int):
        event_names = self.__row_event_names.get(row, [])
        if not event_names:
            return
        if not waapi_utils.is_connected():
            QMessageBox.warning(self, "WAAPI 播放", "Wwise 未连接，无法播放。")
            return
        events = self.find_events(event_names)
        if not events:
            QMessageBox.warning(
                self,
                "WAAPI 播放",
                "在 Wwise 中未找到对应的 Event：\n" + "\n".join(event_names),
            )
            return
        self.stop_event_in_wwise()
        event = events[0]
        self.__transport_id = transport_utils.play_sound(event)
        if self.__transport_id == -1:
            Logger().error(f"Wwise 播放失败：{event.name}")
            return
        Logger().info(f"正在通过 Wwise 播放：{event.name}")

    def stop_event_in_wwise(self):
        if self.__transport_id == -1:
            return
        transport_utils.stop_sound(self.__transport_id)
        self.__transport_id = -1

    def copy_event_names(self, row: int):
        event_names = self.__row_event_names.get(row, [])
        if not event_names:
            return
        clipboard.copy("\n".join(event_names))
        Logger().info(f"已复制 Event 名称：{'; '.join(event_names)}")

    def select_events(self, row: int):
        event_names = self.__row_event_names.get(row, [])
        if not event_names:
            return
        if not waapi_utils.is_connected():
            QMessageBox.warning(self, "选中 Event", "Wwise 未连接，无法选中 Event。")
            return
        objects = self.find_events(event_names)
        if not objects:
            QMessageBox.warning(
                self,
                "选中 Event",
                "在 Wwise 中未找到对应的 Event：\n" + "\n".join(event_names),
            )
            return
        if waapi_utils.select_objects_in_wwise(objects):
            Logger().info(f"已在 Wwise 中选中 {len(objects)} 个 Event")
        else:
            Logger().error("在 Wwise 中选中 Event 失败")

    def closeEvent(self, event):
        self.stop_event_in_wwise()
        super().closeEvent(event)
