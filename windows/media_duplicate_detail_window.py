from libraries.base_dialog import BaseDialog
from dataclasses import dataclass
from pathlib import Path

import clipboard
import soundfile
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QMenu, QMessageBox, QStyle, QTableWidgetItem, QWidget

from libraries.multi_thread import batch_processor
from libraries.table_view.table_path_item import create_path_item, full_path_from_item
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import (
    audio_source_utils, event_utils, transport_utils, waapi_utils, wem_utils,
)
from libraries.wwise_object import WwiseObject, WwiseObjectType
from ui.MediaDuplicateDetail_ui import Ui_MediaDuplicateDetail
from windows.audio_preview_window import AudioPreviewWindow


READ_ONLY_FLAGS = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
POST_EVENT_SOURCE_PLACEHOLDER = "PostEventAction间接引用"
REFERENCE_UNDO_GROUP = "媒体查重参考处理"


@dataclass
class ReferenceFixTask:
    source_id: str
    source_name: str
    target_rows: list[int]
    settings: dict
    copy_conversion: bool
    copy_edit: bool
    copy_fade: bool
    copy_loop_flag: bool
    copy_loop_region: bool
    copy_loop_override: bool
    copy_render: bool
    success: bool = True
    changed: bool = False


# 同源 wem 明细：打开时才逐个读取 wem 头，避免主分析阶段扫描大量文件
class MediaDuplicateDetailWindow(BaseDialog, Ui_MediaDuplicateDetail):

    def __init__(
        self,
        group,
        search_dirs: list[str | Path],
        platform: str = "",
        original_audio_path: str | Path = None,
        cause=None,
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
        self.__name_objects: dict[str, list] = {}
        self.__name_kind: dict[str, str] = {}
        self.__cause = cause
        self.__trims_loaded = False
        self.__transport_id = -1
        self.__reference_tasks: list[ReferenceFixTask] = []
        self.__reference_failed = False
        self.__reference_changed = False
        self.setup_triggers()
        self.configure_cause_columns()
        self.lblTitle.setText(f"原始音频：{group.original_path}")

        event_names = group.event_names
        if waapi_utils.is_connected():
            self.__event_source_info = self.load_event_source_info(event_names)
            self.__trims_loaded = True

        total_size = 0
        missing_count = 0
        wem_cache: dict[str, tuple] = {}
        for (file_info, event_name, source_name, source_id, source_path, owner_path,
             conversion_name, conversion_object, edit_pairs,
             is_looping) in self.build_detail_rows(event_names):
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
                source_name, source_id, source_path, owner_path,
                conversion_name, conversion_object, edit_pairs, is_looping,
            )

        original_size_text = self.original_audio_size_text(original_audio_path)
        original_duration_text = self.original_audio_duration_text(original_audio_path)
        summary = (
            f"平台：{platform or '未知'}；同源 wem {len(group.files)} 个；"
            f"引用 Event/SoundBank {len(event_names)} 个；"
            f"原始 wav 大小：{original_size_text}（时长 {original_duration_text}）；"
            f"合计 wem 大小：{wem_utils.format_file_size(total_size)}"
        )
        if missing_count:
            summary += f"；未找到 {missing_count} 个文件"
        if not self.__trims_loaded:
            summary += "；Wwise 未连接，Audio Source 属性未读取"
        self.lblSummary.setText(summary)
        self.adjust_columns_and_window()
        Logger().info(
            f"打开媒体查重详情：{group.original_path}，"
            f"{len(group.files)} 个 wem，{len(event_names)} 个 Event/SoundBank"
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
                    (file_info, event_name, missing_source_name, "", None, "", "-", None, [], False)
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
                override_wav_loop = source_info.get("override_wav_loop")
                if isinstance(override_wav_loop, str):
                    override_wav_loop = override_wav_loop.casefold() == "true"
                edit_pair = (
                    source_info.get("trim_begin"),
                    source_info.get("trim_end"),
                    source_info.get("fade_in"),
                    source_info.get("fade_out"),
                    source_info.get("loop_begin"),
                    source_info.get("loop_end"),
                    override_wav_loop,
                )
                # 按 wem + AudioSource + Conversion + 剪辑/淡入淡出/循环设置去重，
                # 避免把仅有 Trim/Fade/Loop 差异的行合并掉
                row_key = (
                    file_info.wem_id.casefold(),
                    source_info.get("source_name"),
                    conversion_name,
                    edit_pair,
                    source_info.get("is_looping", False),
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
                    source_info.get("owner_path"),
                    conversion_name,
                    source_info.get("conversion_object"),
                    [edit_pair],
                    source_info.get("is_looping", False),
                ))

            for file_info in related_wems:
                if file_info.wem_id.casefold() not in used_wem_ids:
                    rows.append((
                        file_info,
                        event_name,
                        missing_source_name,
                        "",
                        None,
                        "",
                        "-",
                        None,
                        [],
                        False,
                    ))
        return rows

    def setup_triggers(self):
        self.tblWemDetails.customContextMenuRequested.connect(self.show_context_menu)
        self.tblWemDetails.itemDoubleClicked.connect(self.on_item_double_clicked)

    # 只显示与当前重复原因相关的列；多原因取并集
    def configure_cause_columns(self):
        if self.__cause is None:
            return
        parts = set(self.__cause.kind.split("+"))
        visible = {
            3: "conversion" in parts,
            4: "conversion" in parts,
            5: "conversion" in parts,
            8: "loop_flag" in parts,
            9: "edit" in parts,
            10: "edit" in parts,
            11: "fade" in parts,
            12: "fade" in parts,
            13: "loop_region" in parts,
            14: "loop_region" in parts,
            15: "loop_override" in parts,
            16: "render" in parts,
        }
        for column, show in visible.items():
            self.tblWemDetails.setColumnHidden(column, not show)

    def set_text_cell(self, row: int, column: int, text: str, tooltip: str = ""):
        item = QTableWidgetItem(text)
        item.setFlags(READ_ONLY_FLAGS)
        item.setToolTip(tooltip)
        self.tblWemDetails.setItem(row, column, item)

    def adjust_columns_and_window(self):
        self.tblWemDetails.horizontalHeader().setStretchLastSection(False)
        metrics = self.tblWemDetails.fontMetrics()
        widths = {}
        for column in range(self.tblWemDetails.columnCount()):
            if self.tblWemDetails.isColumnHidden(column):
                continue
            header_item = self.tblWemDetails.horizontalHeaderItem(column)
            header_text = header_item.text() if header_item else ""
            width = metrics.horizontalAdvance(header_text) + 24
            for row in range(self.tblWemDetails.rowCount()):
                item = self.tblWemDetails.item(row, column)
                if item is None:
                    continue
                for text_line in item.text().splitlines() or [""]:
                    width = max(width, metrics.horizontalAdvance(text_line) + 24)
            widths[column] = width

        for column, width in widths.items():
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
        target_width = sum(widths.values()) + extra_width
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
        owner_path: str | None,
        conversion_name: str | None,
        conversion_object,
        edit_pairs: list[tuple],
        is_looping: bool,
    ):
        row = self.tblWemDetails.rowCount()
        self.tblWemDetails.insertRow(row)
        self.__row_event_names[row] = [event_name] if event_name else []
        edit = self.resolved_edit(file_info, edit_pairs)
        (
            trim_begin, trim_end, fade_in, fade_out,
            loop_begin, loop_end, override_wav_loop,
        ) = edit if edit else (None, None, None, None, None, None, None)
        if not self.__trims_loaded and file_info is not None and self.__cause is not None:
            is_looping = self.__cause.looping_by_media.get(
                file_info.wem_id.casefold(), is_looping
            )
        render_text = self.resolved_render_text(file_info)
        self.__row_sources[row] = {
            "name": source_name,
            "id": source_id,
            "path": source_path,
            "owner_path": owner_path,
            "wem_id": file_info.wem_id if file_info is not None else "",
            "trim_begin": trim_begin,
            "trim_end": trim_end,
            "fade_in": fade_in,
            "fade_out": fade_out,
            "loop_begin": loop_begin,
            "loop_end": loop_end,
            "override_wav_loop": override_wav_loop,
            "is_looping": is_looping,
            "render_text": render_text,
        }
        self.__row_conversions[row] = conversion_object
        wem_text = file_info.packed_path if file_info is not None else "-"
        wem_tooltip = str(wem_path) if wem_path is not None else ""
        self.set_text_cell(row, 0, wem_text, wem_tooltip)
        display_event_name = event_name or "-"
        event_tooltip = ""
        if event_name:
            kind = self.__name_kind.get(event_name)
            if kind == "soundbank":
                display_event_name = f"{event_name}（SoundBank）"
                event_tooltip = f"Wwise SoundBank：{event_name}"
            elif kind == "event":
                event_tooltip = f"Wwise Event：{event_name}"
            elif kind == "missing":
                event_tooltip = f"Wwise 中未找到：{event_name}"
        self.set_text_cell(row, 1, display_event_name, event_tooltip)
        if owner_path:
            owner_item = create_path_item(owner_path)
            owner_item.setFlags(READ_ONLY_FLAGS)
            self.tblWemDetails.setItem(row, 2, owner_item)
        else:
            self.set_text_cell(row, 2, source_name or "-")
        self.set_text_cell(row, 3, self.resolved_conversion_name(file_info, conversion_name))
        self.set_text_cell(row, 4, info.codec if info is not None else "-")
        sample_rate = f"{info.sample_rate} Hz" if info is not None and info.sample_rate else "-"
        self.set_text_cell(row, 5, sample_rate)
        duration = wem_utils.format_duration(info.duration_seconds) if info is not None else "-"
        self.set_text_cell(row, 6, duration)
        self.set_text_cell(row, 7, size_text, wem_tooltip)
        self.set_text_cell(row, 8, "True" if is_looping else "False")
        loop_tooltip = (
            f"OverrideWavLoop={override_wav_loop}"
            if override_wav_loop is not None else ""
        )
        self.set_text_cell(row, 9, self.format_edit_value(trim_begin))
        self.set_text_cell(row, 10, self.format_edit_value(trim_end))
        self.set_text_cell(row, 11, self.format_edit_value(fade_in))
        self.set_text_cell(row, 12, self.format_edit_value(fade_out))
        self.set_text_cell(row, 13, self.format_edit_value(loop_begin), loop_tooltip)
        self.set_text_cell(row, 14, self.format_edit_value(loop_end), loop_tooltip)
        if override_wav_loop is None:
            override_text = "-"
        else:
            override_text = "True" if override_wav_loop else "False"
        self.set_text_cell(row, 15, override_text, loop_tooltip)
        self.set_text_cell(row, 16, render_text)

    @staticmethod
    def format_edit_value(value) -> str:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return "-"
        if numeric < 0:
            return "-"
        return f"{numeric:.3f} s"

    def resolved_edit(self, file_info, edit_pairs: list[tuple]):
        mapped = None
        if file_info is not None and self.__cause is not None:
            mapped = self.__cause.edit_by_media.get(file_info.wem_id.casefold())
        if not edit_pairs:
            return mapped
        values = edit_pairs[0]
        if mapped is None:
            return values
        # WAAPI 未返回的字段用分析阶段的 WorkUnit 结果补全
        return tuple(
            mapped[index] if value is None else value
            for index, value in enumerate(values)
        )

    def resolved_conversion_name(self, file_info, conversion_name: str | None) -> str:
        if conversion_name and conversion_name != "-":
            return conversion_name
        if file_info is not None and self.__cause is not None:
            mapped = self.__cause.conversion_by_media.get(file_info.wem_id.casefold())
            if mapped:
                return mapped
        return conversion_name or "-"

    def resolved_render_text(self, file_info) -> str:
        if file_info is not None and self.__cause is not None:
            mapped = self.__cause.render_by_media.get(file_info.wem_id.casefold())
            if mapped:
                return mapped
        return "-"

    @staticmethod
    def unique_objects(objects) -> list:
        result = []
        seen: set[str] = set()
        for obj in objects:
            if obj and obj.is_valid and obj.id and obj.id not in seen:
                seen.add(obj.id)
                result.append(obj)
        return result

    # 先按 Event 查找；找不到时再按 SoundBank 查找，兼容 user-defined SoundBank
    def resolve_name_objects(self, name: str) -> tuple[list, str]:
        if name in self.__name_objects:
            return self.__name_objects[name], self.__name_kind.get(name, "missing")
        matches = waapi_utils.find_all_objects_by_name(name, exact_match=True)
        events = self.unique_objects(
            obj for obj in matches if obj.type == WwiseObjectType.Event
        )
        if events:
            objects, kind = events, "event"
        else:
            soundbanks = self.unique_objects(
                obj for obj in matches if obj.type == WwiseObjectType.SoundBank
            )
            if soundbanks:
                objects, kind = soundbanks, "soundbank"
            else:
                event = waapi_utils.find_object_by_name_and_type(
                    name, WwiseObjectType.Event
                )
                if event and event.is_valid:
                    objects, kind = [event], "event"
                else:
                    soundbank = waapi_utils.find_object_by_name_and_type(
                        name, WwiseObjectType.SoundBank
                    )
                    if soundbank and soundbank.is_valid:
                        objects, kind = [soundbank], "soundbank"
                    else:
                        objects, kind = [], "missing"
        self.__name_objects[name] = objects
        self.__name_kind[name] = kind
        return objects, kind

    def find_events(self, event_names: list[str]) -> list:
        objects = []
        seen_ids: set[str] = set()
        for event_name in event_names:
            matches, kind = self.resolve_name_objects(event_name)
            if kind != "event":
                continue
            for match in matches:
                if match.id not in seen_ids:
                    seen_ids.add(match.id)
                    objects.append(match)
        return objects

    def find_named_objects(self, names: list[str]) -> list:
        objects = []
        seen_ids: set[str] = set()
        for name in names:
            matches, _kind = self.resolve_name_objects(name)
            for match in matches:
                if match.id not in seen_ids:
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
            _objects, kind = self.resolve_name_objects(event_name)
            if kind != "event":
                self.__event_post_event[event_name] = False
                source_by_event[event_name] = []
                Logger().debug(
                    f"[{event_name}] 在 Wwise 中按 {kind} 处理，跳过 AudioSource 查找"
                )
                continue
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

        parents_by_source_id = {}
        unique_parents = {}
        for source in all_sources.values():
            parent = waapi_utils.get_parent_object(source)
            if parent and parent.is_valid:
                parents_by_source_id[source.id] = parent
                unique_parents[parent.id] = parent
        parent_properties = (
            waapi_utils.get_objects_properties(
                list(unique_parents.values()), ["IsLoopingEnabled"]
            )
            if unique_parents else {}
        )
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
                "LoopBegin",
                "LoopEnd",
                "OverrideWavLoop",
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
                parent = parents_by_source_id.get(source.id)
                is_looping = bool(
                    (parent_properties.get(parent.id) or {}).get("IsLoopingEnabled", False)
                ) if parent else False
                source_info = {
                    "source_name": source.name,
                    "source_id": source.id,
                    "source_path": original_path,
                    "owner_path": parent.path if parent and parent.is_valid else "",
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
                    "loop_begin": properties.get("LoopBegin"),
                    "loop_end": properties.get("LoopEnd"),
                    "override_wav_loop": properties.get("OverrideWavLoop"),
                    "is_looping": is_looping,
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
        row = item.row()
        menu = QMenu(self)
        if item.column() == 1:
            event_names = self.__row_event_names.get(row, [])
            if event_names:
                menu.addAction("复制", lambda: self.copy_event_names(row))
                menu.addAction("选中", lambda: self.select_events(row))
                if self.row_has_events(row):
                    menu.addAction("WAAPI播放", lambda: self.play_event_in_wwise(row))
                if self.__transport_id != -1:
                    menu.addAction("停止", self.stop_event_in_wwise)
        elif item.column() == 2:
            menu.addAction("复制", lambda: self.copy_source_path(row))
            source = self.__row_sources.get(row, {})
            if source.get("name") != POST_EVENT_SOURCE_PLACEHOLDER:
                menu.addAction("在Wwise中选中", lambda: self.select_source(row))
                menu.addAction("音频预览", lambda: self.preview_source_audio(row))
        elif item.column() == 3:
            if item.text():
                menu.addAction("复制", lambda: clipboard.copy(item.text()))
            menu.addAction("在Wwise中选中", lambda: self.select_conversion(row))
        elif item.text():
            menu.addAction("复制", lambda: clipboard.copy(item.text()))
        if menu.actions():
            menu.addSeparator()
        reference_action = menu.addAction(
            "以本条为参考处理",
            lambda: self.process_from_reference(row),
        )
        reference_action.setEnabled(self.can_use_reference(row))
        menu.exec(self.tblWemDetails.viewport().mapToGlobal(position))

    def row_has_events(self, row: int) -> bool:
        return any(
            self.__name_kind.get(name) == "event"
            for name in self.__row_event_names.get(row, [])
        )

    def can_use_reference(self, row: int) -> bool:
        if not waapi_utils.is_connected() or self.__cause is None:
            return False
        if not self.has_reference_settings():
            return False
        source = self.__row_sources.get(row, {})
        if not source.get("id") or source.get("name") == POST_EVENT_SOURCE_PLACEHOLDER:
            return False
        return self.has_reference_targets(row)

    def has_reference_settings(self) -> bool:
        return any((
            not self.tblWemDetails.isColumnHidden(3),
            not self.tblWemDetails.isColumnHidden(8),
            not self.tblWemDetails.isColumnHidden(9),
            not self.tblWemDetails.isColumnHidden(10),
            not self.tblWemDetails.isColumnHidden(11),
            not self.tblWemDetails.isColumnHidden(12),
            not self.tblWemDetails.isColumnHidden(13),
            not self.tblWemDetails.isColumnHidden(14),
            not self.tblWemDetails.isColumnHidden(15),
            not self.tblWemDetails.isColumnHidden(16),
        ))

    def has_reference_targets(self, row: int) -> bool:
        reference = self.__row_sources.get(row, {})
        reference_wem = str(reference.get("wem_id") or "")
        for other_row, other in self.__row_sources.items():
            if other_row == row:
                continue
            if not other.get("id") or other.get("name") == POST_EVENT_SOURCE_PLACEHOLDER:
                continue
            if reference_wem and str(other.get("wem_id") or "") == reference_wem:
                continue
            return True
        return False

    def process_from_reference(self, reference_row: int):
        if not waapi_utils.is_connected():
            QMessageBox.warning(self, "参考处理", "Wwise 未连接，无法执行参考处理。")
            return
        if batch_processor.is_busy():
            QMessageBox.warning(self, "参考处理", batch_processor.busy_message("参考处理"))
            return
        reference = self.__row_sources.get(reference_row, {})
        if not reference.get("id"):
            QMessageBox.information(self, "参考处理", "当前行没有可用的 Audio Source。")
            return

        settings = {
            "conversion_object": self.resolve_conversion_object(reference_row),
            "conversion_name": self.cell_text(reference_row, 3),
            "trim_begin": reference.get("trim_begin"),
            "trim_end": reference.get("trim_end"),
            "fade_in": reference.get("fade_in"),
            "fade_out": reference.get("fade_out"),
            "loop_begin": reference.get("loop_begin"),
            "loop_end": reference.get("loop_end"),
            "override_wav_loop": reference.get("override_wav_loop"),
            "is_looping": reference.get("is_looping"),
            "render_text": reference.get("render_text") or "-",
            "render_on": bool(
                reference.get("render_text")
                and reference.get("render_text") != "-"
            ),
        }
        copy_conversion = not self.tblWemDetails.isColumnHidden(3)
        copy_edit = (
            not self.tblWemDetails.isColumnHidden(9)
            or not self.tblWemDetails.isColumnHidden(10)
        )
        copy_fade = (
            not self.tblWemDetails.isColumnHidden(11)
            or not self.tblWemDetails.isColumnHidden(12)
        )
        copy_loop_flag = not self.tblWemDetails.isColumnHidden(8)
        copy_loop_region = (
            not self.tblWemDetails.isColumnHidden(13)
            or not self.tblWemDetails.isColumnHidden(14)
        )
        copy_loop_override = not self.tblWemDetails.isColumnHidden(15)
        copy_render = not self.tblWemDetails.isColumnHidden(16)
        if not any((
            copy_conversion, copy_edit, copy_fade,
            copy_loop_flag, copy_loop_region, copy_loop_override,
            copy_render,
        )):
            QMessageBox.information(
                self, "参考处理", "当前重复原因没有可参考复制的设置。"
            )
            return
        setting_labels = []
        if copy_conversion:
            setting_labels.append("压缩设置")
        if copy_edit:
            setting_labels.append("样本剪辑")
        if copy_fade:
            setting_labels.append("淡入淡出")
        if copy_loop_flag:
            setting_labels.append("Sound循环")
        skip_loop_region = (
            copy_loop_override and reference.get("override_wav_loop") is True
        )
        if copy_loop_region and not skip_loop_region:
            setting_labels.append("Loop区间")
        if copy_loop_override:
            setting_labels.append("覆盖WAV循环")
        if copy_render:
            setting_labels.append("效果器渲染")

        tasks = self.build_reference_tasks(
            reference_row, settings,
            copy_conversion, copy_edit, copy_fade,
            copy_loop_flag, copy_loop_region, copy_loop_override,
            copy_render,
        )
        if not tasks:
            QMessageBox.information(
                self, "参考处理",
                "没有其他使用不同 wem 的 Audio Source 可处理。",
            )
            return

        reference_name = str(reference.get("name") or "-")
        reply = QMessageBox.question(
            self,
            "参考处理",
            f"以「{reference_name}」为参考，修改 {len(tasks)} 个其他 Audio Source 的"
            f"{'、'.join(setting_labels)}？\n\n"
            "所有修改会合并为一个撤销组。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.__reference_tasks = tasks
        self.__reference_failed = False
        self.__reference_changed = False
        started = batch_processor.create_async(
            tasks,
            self.process_reference_task,
            "媒体查重参考处理",
            on_finished=self.on_reference_finished,
            on_interrupted=self.on_reference_interrupted,
            on_item_processed=self.on_reference_item_processed,
            progress_text_func=lambda index, task: f"参考处理：{task.source_name}",
            undo_group=REFERENCE_UNDO_GROUP,
        )
        if not started:
            QMessageBox.warning(self, "参考处理", batch_processor.busy_message("参考处理"))
            return
        Logger().info(
            f"开始媒体查重参考处理：{self.__group.original_path}，"
            f"参考 {reference_name}，目标 {len(tasks)} 个 Audio Source"
        )

    def cell_text(self, row: int, column: int) -> str:
        item = self.tblWemDetails.item(row, column)
        return item.text() if item is not None else ""

    def build_reference_tasks(
        self,
        reference_row: int,
        settings: dict,
        copy_conversion: bool,
        copy_edit: bool,
        copy_fade: bool,
        copy_loop_flag: bool,
        copy_loop_region: bool,
        copy_loop_override: bool,
        copy_render: bool,
    ) -> list[ReferenceFixTask]:
        reference = self.__row_sources.get(reference_row, {})
        reference_wem = str(reference.get("wem_id") or "")
        reference_source_id = str(reference.get("id") or "")
        tasks_by_source: dict[str, ReferenceFixTask] = {}
        for row, source in self.__row_sources.items():
            if row == reference_row:
                continue
            source_id = str(source.get("id") or "")
            if not source_id or source.get("name") == POST_EVENT_SOURCE_PLACEHOLDER:
                continue
            if source_id == reference_source_id:
                continue
            if reference_wem and str(source.get("wem_id") or "") == reference_wem:
                continue
            task = tasks_by_source.get(source_id)
            if task is None:
                task = ReferenceFixTask(
                    source_id=source_id,
                    source_name=str(source.get("name") or source_id),
                    target_rows=[],
                    settings=settings,
                    copy_conversion=copy_conversion,
                    copy_edit=copy_edit,
                    copy_fade=copy_fade,
                    copy_loop_flag=copy_loop_flag,
                    copy_loop_region=copy_loop_region,
                    copy_loop_override=copy_loop_override,
                    copy_render=copy_render,
                )
                tasks_by_source[source_id] = task
            if row not in task.target_rows:
                task.target_rows.append(row)
        return list(tasks_by_source.values())

    def process_reference_task(self, _index: int, task: ReferenceFixTask) -> bool:
        try:
            source = waapi_utils.get_full_info_from_obj_id(task.source_id)
            if source is None or source.type != WwiseObjectType.AudioSource:
                task.success = False
                return True
            owner = waapi_utils.get_parent_object(source)
            settings = task.settings
            if task.copy_conversion:
                conversion = settings.get("conversion_object")
                if (conversion is not None and conversion.is_valid
                        and owner is not None and owner.is_valid
                        and owner.has_property("Conversion")):
                    ok = waapi_utils.set_object_reference(owner, "Conversion", conversion)
                    task.success = task.success and ok
                    task.changed = True
            if task.copy_edit or task.copy_fade:
                current = audio_source_utils.get_source_edit_info(source)
                trim_begin = settings.get("trim_begin") if task.copy_edit else None
                trim_end = settings.get("trim_end") if task.copy_edit else None
                fade_in = settings.get("fade_in") if task.copy_fade else None
                fade_out = settings.get("fade_out") if task.copy_fade else None
                if any(value is not None for value in (trim_begin, trim_end, fade_in, fade_out)):
                    ok = audio_source_utils.set_source_trim_range(
                        source,
                        trim_begin=trim_begin,
                        trim_end=trim_end,
                        fade_in=fade_in,
                        fade_out=fade_out,
                        current=current,
                    )
                    task.success = task.success and ok
                    task.changed = True
            if task.copy_loop_flag:
                is_looping = settings.get("is_looping")
                if (is_looping is not None and owner is not None and owner.is_valid
                        and owner.has_property("IsLoopingEnabled")):
                    ok = waapi_utils.set_object_property(
                        owner, "IsLoopingEnabled", bool(is_looping)
                    )
                    task.success = task.success and ok
                    task.changed = True
            skip_loop_region = (
                task.copy_loop_override
                and settings.get("override_wav_loop") is True
            )
            # 覆盖WAV循环为 True 时 LoopBegin/End 不参与渲染，保持目标原值
            if task.copy_loop_region and not skip_loop_region:
                for property_name, key in (
                    ("LoopBegin", "loop_begin"),
                    ("LoopEnd", "loop_end"),
                ):
                    value = settings.get(key)
                    if value is None:
                        continue
                    ok = waapi_utils.set_object_property(source, property_name, value)
                    task.success = task.success and ok
                    task.changed = True
            if task.copy_loop_override:
                override = settings.get("override_wav_loop")
                if override is not None:
                    ok = waapi_utils.set_object_property(
                        source, "OverrideWavLoop", override
                    )
                    task.success = task.success and ok
                    task.changed = True
            if task.copy_render:
                ok, changed = self.set_render_state(owner, bool(settings.get("render_on")))
                task.success = task.success and ok
                task.changed = task.changed or changed
        except Exception:
            task.success = False
            Logger().exception(f"参考处理失败：{task.source_name}")
        return True

    def set_render_state(self, owner, enabled: bool) -> tuple[bool, bool]:
        if owner is None or not owner.is_valid:
            return True, False
        ok = True
        changed = False
        current = owner
        visited: set[str] = set()
        while current is not None and current.is_valid and current.id not in visited:
            visited.add(current.id)
            effect_slots = waapi_utils.get_object_property(current, "@Effects") or []
            for slot_dict in effect_slots:
                slot = WwiseObject(slot_dict)
                if not slot.is_valid:
                    continue
                if bool(waapi_utils.get_object_property(slot, "Render")) != enabled:
                    ok = waapi_utils.set_object_property(slot, "Render", enabled) and ok
                    changed = True
            current = waapi_utils.get_parent_object(current)
        return ok, changed

    def on_reference_item_processed(self, payload):
        _index, task = payload
        if not task.success:
            self.__reference_failed = True
        if task.changed:
            self.__reference_changed = True
        if not task.success:
            return
        for row in task.target_rows:
            self.apply_reference_display(row, task)

    def apply_reference_display(self, row: int, task: ReferenceFixTask):
        source = self.__row_sources.get(row, {})
        settings = task.settings
        if task.copy_conversion:
            self.__row_conversions[row] = settings.get("conversion_object")
            self.set_text_cell(row, 3, str(settings.get("conversion_name") or "-"))
        if task.copy_edit:
            source["trim_begin"] = settings.get("trim_begin")
            source["trim_end"] = settings.get("trim_end")
            self.set_text_cell(row, 9, self.format_edit_value(settings.get("trim_begin")))
            self.set_text_cell(row, 10, self.format_edit_value(settings.get("trim_end")))
        if task.copy_fade:
            source["fade_in"] = settings.get("fade_in")
            source["fade_out"] = settings.get("fade_out")
            self.set_text_cell(row, 11, self.format_edit_value(settings.get("fade_in")))
            self.set_text_cell(row, 12, self.format_edit_value(settings.get("fade_out")))
        if task.copy_loop_flag:
            source["is_looping"] = settings.get("is_looping")
            self.set_text_cell(
                row, 8, "True" if settings.get("is_looping") else "False"
            )
        skip_loop_region = (
            task.copy_loop_override
            and settings.get("override_wav_loop") is True
        )
        if task.copy_loop_region and not skip_loop_region:
            source["loop_begin"] = settings.get("loop_begin")
            source["loop_end"] = settings.get("loop_end")
            tooltip = f"OverrideWavLoop={settings.get('override_wav_loop')}"
            self.set_text_cell(row, 13, self.format_edit_value(settings.get("loop_begin")), tooltip)
            self.set_text_cell(row, 14, self.format_edit_value(settings.get("loop_end")), tooltip)
        if task.copy_loop_override:
            source["override_wav_loop"] = settings.get("override_wav_loop")
            override_value = settings.get("override_wav_loop")
            override_text = (
                "-" if override_value is None
                else "True" if override_value else "False"
            )
            self.set_text_cell(
                row, 15, override_text,
                f"OverrideWavLoop={settings.get('override_wav_loop')}",
            )
        if task.copy_render:
            source["render_text"] = settings.get("render_text") or "-"
            self.set_text_cell(row, 16, source["render_text"])

    def on_reference_finished(self):
        if self.__reference_failed:
            message = "参考处理完成，但有部分对象处理失败，请查看日志。"
            mark = getattr(self.parent(), "mark_group_failed", None)
            if callable(mark):
                mark(self.__group.original_path)
        else:
            message = f"参考处理完成，共处理 {len(self.__reference_tasks)} 个 Audio Source。"
            if self.__reference_changed:
                mark = getattr(self.parent(), "mark_group_processed", None)
                if callable(mark):
                    mark(self.__group.original_path)
        message += "\n\nwem 路径、格式和大小等结果可能已变化，请重新打开详情或重新解析刷新。"
        Logger().info(
            f"媒体查重参考处理结束：{self.__group.original_path}，"
            f"{len(self.__reference_tasks)} 个 Audio Source"
        )
        self.__reference_tasks = []
        self.__reference_failed = False
        self.__reference_changed = False
        QMessageBox.information(self, "参考处理", message)

    def on_reference_interrupted(self):
        mark = getattr(self.parent(), "mark_group_failed", None)
        if callable(mark):
            mark(self.__group.original_path)
        self.__reference_tasks = []
        self.__reference_failed = False
        self.__reference_changed = False
        Logger().warning("媒体查重参考处理中断")
        QMessageBox.warning(self, "参考处理", "参考处理中断，部分对象可能已修改。")

    def on_item_double_clicked(self, item: QTableWidgetItem):
        if item.column() == 1:
            self.select_events(item.row())
        elif item.column() == 2:
            self.select_source(item.row())
        elif item.column() == 3:
            self.select_conversion(item.row())

    def copy_source_path(self, row: int):
        item = self.tblWemDetails.item(row, 2)
        path = full_path_from_item(item)
        if not path or path == "-":
            source = self.__row_sources.get(row, {})
            path = str(source.get("owner_path") or source.get("name") or "")
        if not path:
            return
        clipboard.copy(path)
        Logger().info(f"已复制 Sound 路径：{path}")

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
        if isinstance(value, WwiseObject):
            return value if value.is_valid else None
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
        Logger().info(f"已复制 Event/SoundBank 名称：{'; '.join(event_names)}")

    def select_events(self, row: int):
        event_names = self.__row_event_names.get(row, [])
        if not event_names:
            return
        if not waapi_utils.is_connected():
            QMessageBox.warning(self, "选中 Event/SoundBank", "Wwise 未连接，无法选中 Event 或 SoundBank。")
            return
        objects = self.find_named_objects(event_names)
        if not objects:
            QMessageBox.warning(
                self,
                "选中 Event/SoundBank",
                "在 Wwise 中未找到对应的 Event 或 SoundBank：\n" + "\n".join(event_names),
            )
            return
        if waapi_utils.select_objects_in_wwise(objects):
            Logger().info(f"已在 Wwise 中选中 {len(objects)} 个 Event/SoundBank")
        else:
            Logger().error("在 Wwise 中选中 Event/SoundBank 失败")

    def closeEvent(self, event):
        self.stop_event_in_wwise()
        super().closeEvent(event)
