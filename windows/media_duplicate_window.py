from libraries.base_dialog import BaseDialog
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import clipboard
import soundfile
from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtWidgets import QDialog, QFileDialog, QHeaderView, QMenu, QMessageBox, QWidget

from libraries.multi_thread.progress_bar import ProgressBar
from libraries.multi_thread import batch_processor
from libraries.table_view.table_cell_data import CellSeverity
from libraries.table_view.table_severity_delegate import SeverityTableDelegate
from libraries.utils import io_utils
from data import user_config
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import (
    project_utils, soundbank_info_utils, waapi_utils, work_unit_parse_utils, wwise_compat, wem_utils,
)
from libraries.wwise_object import WwiseObject, WwiseObjectType
from ui.MediaDuplicate_ui import Ui_MediaDuplicate
from windows.audio_preview_window import AudioPreviewWindow
from windows.media_duplicate_detail_window import MediaDuplicateDetailWindow


WINDOW_SETTINGS_KEY = "media_duplicate"
HEADERS = [
    "原始音频路径",
    "同源 wem 数",
    "引用 Event 数",
    "重复原因（双击查看详情）",
    "额外包体大小",
    "当前状态",
]
STATUS_COLUMN = 5
STATUS_UNPROCESSED = "未处理"
STATUS_PROCESSED = "已处理"
STATUS_FAILED = "处理失败"

CAUSE_CONVERSION = "conversion"
CAUSE_EDIT = "edit"
CAUSE_DURATION = "duration"
CAUSE_FADE = "fade"
CAUSE_LOOP_FLAG = "loop_flag"
CAUSE_LOOP_REGION = "loop_region"
CAUSE_LOOP_OVERRIDE = "loop_override"
CAUSE_RENDER = "render"
CAUSE_UNKNOWN = "unknown"
CAUSE_UNMATCHED = "unmatched"
CAUSE_PARTIAL_UNMATCHED = "partial_unmatched"
CAUSE_NOT_ANALYZED = "not_analyzed"
CAUSE_MISSING_FILTER = "missing"
CAUSE_MISSING_KINDS = (CAUSE_UNMATCHED, CAUSE_PARTIAL_UNMATCHED)
DURATION_CAUSE_TOLERANCE = 0.01

CAUSE_LABELS = {
    CAUSE_CONVERSION: "压缩设置",
    CAUSE_EDIT: "样本剪辑",
    CAUSE_DURATION: "时长不等",
    CAUSE_FADE: "淡入淡出",
    CAUSE_LOOP_FLAG: "Sound循环",
    CAUSE_LOOP_REGION: "Loop区间",
    CAUSE_LOOP_OVERRIDE: "覆盖WAV循环",
    CAUSE_RENDER: "效果器渲染",
    CAUSE_UNKNOWN: "未知原因",
    CAUSE_UNMATCHED: "WorkUnit或wem不匹配",
    CAUSE_PARTIAL_UNMATCHED: "WorkUnit或wem不匹配",
}

CAUSE_FILTER_OPTIONS = [
    ("全部原因", ""),
    (CAUSE_LABELS[CAUSE_CONVERSION], CAUSE_CONVERSION),
    (CAUSE_LABELS[CAUSE_EDIT], CAUSE_EDIT),
    (CAUSE_LABELS[CAUSE_DURATION], CAUSE_DURATION),
    (CAUSE_LABELS[CAUSE_FADE], CAUSE_FADE),
    (CAUSE_LABELS[CAUSE_LOOP_FLAG], CAUSE_LOOP_FLAG),
    (CAUSE_LABELS[CAUSE_LOOP_REGION], CAUSE_LOOP_REGION),
    (CAUSE_LABELS[CAUSE_LOOP_OVERRIDE], CAUSE_LOOP_OVERRIDE),
    (CAUSE_LABELS[CAUSE_RENDER], CAUSE_RENDER),
    (CAUSE_LABELS[CAUSE_UNKNOWN], CAUSE_UNKNOWN),
    (CAUSE_LABELS[CAUSE_UNMATCHED], CAUSE_MISSING_FILTER),
]

CAUSE_DETAIL_FIELDS = {
    CAUSE_CONVERSION: ("conversion", "format", "sample_rate"),
    CAUSE_EDIT: ("trim_begin", "trim_end"),
    CAUSE_FADE: ("fade_in", "fade_out"),
    CAUSE_LOOP_FLAG: ("is_looping",),
    CAUSE_LOOP_REGION: ("loop_begin", "loop_end"),
    CAUSE_LOOP_OVERRIDE: ("override_wav_loop",),
    CAUSE_RENDER: ("render_effect",),
}


# 多原因取并集；未知/未匹配原因不带任何设置字段
def _cause_detail_fields(cause) -> set[str]:
    if cause is None:
        return set()
    fields: set[str] = set()
    for part in cause.kind.split("+"):
        fields.update(CAUSE_DETAIL_FIELDS.get(part, ()))
    return fields


def _is_default_loop_value(value) -> bool:
    try:
        return abs(float(value) - work_unit_parse_utils.DEFAULT_EDIT_VALUE) <= 1e-6
    except (TypeError, ValueError):
        return True


@dataclass(frozen=True)
class MediaVariant:
    media_id: str
    owner_id: str
    owner_path: str
    conversion: str
    edit: work_unit_parse_utils.SourceEditSettings
    source_id: str = ""
    source_name: str = ""
    source_path: str = ""
    audio_file: str = ""
    render_signature: str = ""
    conversion_key: str = ""
    looping: bool = False


AUTO_FIX_UNDO_GROUP = "媒体查重自动处理"
AUTO_FIX_ACTION_LABELS = {
    "loop": "Sound循环",
    "fade": "淡入淡出",
    "render": "效果器渲染",
}
LOOPABLE_CONTAINER_TYPES = {
    WwiseObjectType.RandomContainer,
    WwiseObjectType.SwitchContainer,
    WwiseObjectType.BlendContainer,
}


@dataclass
class AutoFixTask:
    action: str
    target_id: str
    target_name: str
    group_paths: list[str]
    success: bool = True
    changed: bool = False


@dataclass
class DuplicateCause:
    kind: str = CAUSE_UNMATCHED
    conversions: list[str] = field(default_factory=list)
    edits: list[str] = field(default_factory=list)
    durations: list[float] = field(default_factory=list)
    fades: list[str] = field(default_factory=list)
    loops: list[bool] = field(default_factory=list)
    loop_regions: list[str] = field(default_factory=list)
    loop_overrides: list[bool] = field(default_factory=list)
    renders: list[str] = field(default_factory=list)
    variant_count: int = 0
    expected_media_count: int = 0
    matched_media_count: int = 0
    original_duration_seconds: Optional[float] = None
    edit_total_seconds: Optional[float] = None
    edit_waste_seconds: Optional[float] = None
    file_intervals: dict[str, tuple[float, float]] = field(default_factory=dict)
    file_bytes_per_second: dict[str, float] = field(default_factory=dict)
    conversion_by_media: dict[str, str] = field(default_factory=dict)
    edit_by_media: dict[str, tuple] = field(default_factory=dict)
    looping_by_media: dict[str, bool] = field(default_factory=dict)
    render_by_media: dict[str, str] = field(default_factory=dict)
    sources_by_media: dict[str, list[dict]] = field(default_factory=dict)

    @property
    def label(self) -> str:
        if self.kind == CAUSE_UNMATCHED:
            return CAUSE_LABELS[CAUSE_UNMATCHED]
        if self.kind == CAUSE_PARTIAL_UNMATCHED:
            if self.expected_media_count:
                return (
                    f"{CAUSE_LABELS[CAUSE_PARTIAL_UNMATCHED]}"
                    f"（{self.matched_media_count}/{self.expected_media_count}）"
                )
            return CAUSE_LABELS[CAUSE_PARTIAL_UNMATCHED]
        parts = self.kind.split("+")
        labels = [CAUSE_LABELS.get(part, part) for part in parts]
        if CAUSE_EDIT in parts and self.edit_total_seconds is not None:
            if (self.edit_waste_seconds or 0) <= 1e-9:
                labels[parts.index(CAUSE_EDIT)] = f"{CAUSE_LABELS[CAUSE_EDIT]}（无重叠）"
            else:
                labels[parts.index(CAUSE_EDIT)] = (
                    f"{CAUSE_LABELS[CAUSE_EDIT]}（重叠 {self.edit_waste_seconds:.3f}s）"
                )
        if self.expected_media_count and self.matched_media_count < self.expected_media_count:
            note = (
                f"{CAUSE_LABELS[CAUSE_PARTIAL_UNMATCHED]}"
                f"（{self.matched_media_count}/{self.expected_media_count}，"
                "SoundBanksInfo 可能过时）"
            )
            labels.append(note)
        return "；".join(labels)

    @property
    def conversion_text(self) -> str:
        return " | ".join(self.conversions) if self.conversions else "-"

    @property
    def edit_text(self) -> str:
        return " | ".join(self.edits) if self.edits else "-"

    @property
    def fade_text(self) -> str:
        return " | ".join(self.fades) if self.fades else "-"

    @property
    def render_text(self) -> str:
        return " | ".join(self.renders) if self.renders else "-"


# 比较同一原始音频的多个媒体变体，判定重复来自 conversion、剪辑还是渲染效果
def classify_media_variants(
    variants: list[MediaVariant],
    durations: list[float] | None = None,
) -> DuplicateCause:
    if not variants:
        return DuplicateCause(kind=CAUSE_UNMATCHED)

    conversions = sorted({variant.conversion for variant in variants if variant.conversion})
    conversion_keys = sorted({variant.conversion_key or variant.conversion for variant in variants})
    trim_edits = sorted({variant.edit.trim_signature for variant in variants})
    loop_ranges = sorted({
        f"loop {variant.edit.loop_begin:.3f}~{variant.edit.loop_end:.3f}s"
        for variant in variants
    })
    # 剪辑已经不同时，重复原因已明确，不再继续比较 Fade
    if len(trim_edits) > 1:
        edits = trim_edits
        fade_edits: list[str] = []
    else:
        edits = sorted({variant.edit.describe() for variant in variants})
        fade_edits = sorted({variant.edit.fade_signature for variant in variants})
    loop_values = sorted({variant.looping for variant in variants})
    loop_overrides = sorted({variant.edit.override_wav_loop for variant in variants})
    # Trim 编辑会让 Wwise 自动打开 OverrideWavLoop；剪辑已不同时不再把
    # OverrideWavLoop 的连带变化单独算成循环原因。
    loop_flag_cause = len(loop_values) > 1
    loop_region_cause = len(loop_ranges) > 1
    loop_override_cause = len(loop_overrides) > 1 and len(trim_edits) <= 1
    duration_values = sorted({
        round(float(value), 3) for value in (durations or [])
        if value is not None and float(value) > 0
    })
    duration_cause = (
        len(duration_values) >= 2
        and duration_values[-1] - duration_values[0] > DURATION_CAUSE_TOLERANCE
        and len(trim_edits) <= 1
    )
    renders = sorted({variant.render_signature for variant in variants if variant.render_signature})

    conversion_by_media: dict[str, str] = {}
    edit_by_media: dict[str, tuple] = {}
    looping_by_media: dict[str, bool] = {}
    render_by_media: dict[str, str] = {}
    sources_by_media: dict[str, list[dict]] = {}
    for variant in variants:
        media_key = variant.media_id.casefold()
        if variant.conversion:
            conversion_by_media.setdefault(media_key, variant.conversion)
        edit = variant.edit
        edit_by_media.setdefault(media_key, (
            edit.trim_begin,
            edit.trim_end,
            edit.fade_in,
            edit.fade_out,
            edit.loop_begin,
            edit.loop_end,
            edit.override_wav_loop,
        ))
        looping_by_media.setdefault(media_key, variant.looping)
        if variant.render_signature:
            render_by_media.setdefault(media_key, variant.render_signature)
        source_entry = {
            "audio_source_id": variant.source_id,
            "audio_source_name": variant.source_name,
            "audio_source_path": variant.source_path,
            "audio_file": variant.audio_file,
            "owner_object_id": variant.owner_id,
            "owner_object_path": variant.owner_path,
            "conversion": variant.conversion,
            "is_looping": variant.looping,
            "render_effect": variant.render_signature,
            "trim_begin": edit.trim_begin,
            "trim_end": edit.trim_end,
            "fade_in": edit.fade_in,
            "fade_out": edit.fade_out,
            "loop_begin": edit.loop_begin,
            "loop_end": edit.loop_end,
            "override_wav_loop": edit.override_wav_loop,
        }
        entries = sources_by_media.setdefault(media_key, [])
        if source_entry not in entries:
            entries.append(source_entry)

    causes: list[str] = []
    if len(conversion_keys) > 1:
        causes.append(CAUSE_CONVERSION)
    if len(trim_edits) > 1:
        causes.append(CAUSE_EDIT)
    if duration_cause:
        causes.append(CAUSE_DURATION)
    if loop_flag_cause:
        causes.append(CAUSE_LOOP_FLAG)
    if loop_region_cause:
        causes.append(CAUSE_LOOP_REGION)
    if loop_override_cause:
        causes.append(CAUSE_LOOP_OVERRIDE)
    if len(fade_edits) > 1:
        causes.append(CAUSE_FADE)
    if len(renders) > 1:
        causes.append(CAUSE_RENDER)

    return DuplicateCause(
        kind="+".join(causes) if causes else CAUSE_UNKNOWN,
        conversions=conversions,
        edits=edits,
        durations=duration_values if duration_cause else [],
        fades=fade_edits if len(fade_edits) > 1 else [],
        loops=loop_values if loop_flag_cause else [],
        loop_regions=loop_ranges if loop_region_cause else [],
        loop_overrides=loop_overrides if loop_override_cause else [],
        renders=renders,
        variant_count=len(variants),
        conversion_by_media=conversion_by_media,
        edit_by_media=edit_by_media,
        looping_by_media=looping_by_media,
        render_by_media=render_by_media,
        sources_by_media=sources_by_media,
    )


def _merge_interval_length(intervals: list[tuple[float, float]]) -> float:
    if not intervals:
        return 0.0
    intervals = sorted(intervals)
    merged_start, merged_end = intervals[0]
    union_length = 0.0
    for start, end in intervals[1:]:
        if start <= merged_end:
            merged_end = max(merged_end, end)
        else:
            union_length += merged_end - merged_start
            merged_start, merged_end = start, end
    union_length += merged_end - merged_start
    return max(0.0, union_length)


def _variant_interval(variant: MediaVariant, duration: float) -> tuple[float, float] | None:
    if duration <= 0:
        return None
    trim_begin = variant.edit.trim_begin if variant.edit.trim_begin >= 0 else 0.0
    trim_end = variant.edit.trim_end if variant.edit.trim_end >= 0 else 0.0
    start = max(0.0, min(float(trim_begin), duration))
    end = max(start, min(duration, duration - float(trim_end)))
    return (start, end) if end > start else None


def _resolve_original_duration(project_root: Path, original_path: str) -> Optional[float]:
    relative_path = Path(original_path)
    candidates = [
        project_root / "Originals" / "SFX" / relative_path,
        project_root / "Originals" / relative_path,
    ]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            with soundfile.SoundFile(str(candidate)) as sound_file:
                return sound_file.frames / sound_file.samplerate if sound_file.samplerate else None
        except (OSError, RuntimeError):
            return None
    return None


def _overlap_extra_size(group, cause: DuplicateCause) -> Optional[float]:
    file_data: list[tuple[float, float, float]] = []
    for file_info in group.files:
        key = file_info.wem_id.casefold()
        interval = cause.file_intervals.get(key)
        bytes_per_second = cause.file_bytes_per_second.get(key)
        if interval is None or not bytes_per_second or bytes_per_second <= 0:
            return None
        start, end = interval
        if end <= start:
            return None
        file_data.append((start, end, bytes_per_second))
    if len(file_data) < 2:
        return None

    points = sorted({point for start, end, _bps in file_data for point in (start, end)})
    extra_size = 0.0
    for start, end in zip(points, points[1:]):
        if end <= start:
            continue
        covering = [
            bytes_per_second
            for file_start, file_end, bytes_per_second in file_data
            if file_start <= start + 1e-9 and file_end >= end - 1e-9
        ]
        if len(covering) <= 1:
            continue
        # 同一时间段保留码率最低的一份，其余份数都算额外包体
        covering.sort()
        extra_size += (end - start) * sum(covering[1:])
    return max(0.0, extra_size)


def _group_extra_size(group, cause: DuplicateCause) -> float:
    sizes = [
        file_info.size_bytes
        for file_info in group.files
        if file_info.size_bytes is not None
    ]
    if not sizes:
        return 0.0
    group_total = sum(sizes)
    group_extra = max(0, group_total - min(sizes))
    if cause is not None:
        parts = cause.kind.split("+")
        # 剪辑/Fade：按时间轴重叠部分计算真正冗余的那几份，而不是整份 wem 扣最小
        if CAUSE_EDIT in parts or CAUSE_FADE in parts:
            overlap_extra = _overlap_extra_size(group, cause)
            if overlap_extra is not None:
                return overlap_extra
    return group_extra


# 多种原因时分别归入各自分类，便于查看每种原因各占多少重复体积
def _cause_categories(cause: DuplicateCause) -> list[str]:
    if cause is None:
        return ["未分析"]
    parts = cause.kind.split("+")
    if CAUSE_UNMATCHED in parts or CAUSE_PARTIAL_UNMATCHED in parts:
        return [CAUSE_LABELS[CAUSE_UNMATCHED]]
    if CAUSE_UNKNOWN in parts:
        return [CAUSE_LABELS[CAUSE_UNKNOWN]]
    categories = []
    for part in parts:
        label = CAUSE_LABELS.get(part)
        if label and label not in categories:
            categories.append(label)
    return categories or ["未分析"]


def build_media_variant_index(
    project_root: Path,
    platform: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> dict[str, list[MediaVariant]]:
    index = work_unit_parse_utils.build_work_unit_index(
        project_root, file_progress_callback=progress_callback
    )
    variants_by_media: dict[str, list[MediaVariant]] = {}
    for record in index.audio_sources:
        media_id = work_unit_parse_utils.media_id_for_platform(record.media_ids_by_platform, platform)
        if not media_id:
            continue
        conversion, conversion_id = index.effective_conversion_pair(record.owner_id)
        owner_path = index.path_of(record.owner_id)
        if record.hierarchy_root:
            owner_path = f"{record.hierarchy_root}/{owner_path}"
        source_path = (
            f"{owner_path}/{record.audio_source_name}"
            if record.audio_source_name else owner_path
        )
        variant = MediaVariant(
            media_id=media_id,
            owner_id=record.owner_id,
            owner_path=owner_path,
            conversion=conversion,
            edit=record.edit,
            source_id=record.audio_source_id,
            source_name=record.audio_source_name,
            source_path=source_path,
            audio_file=record.audio_file,
            render_signature=index.effective_render_signature(record.owner_id),
            conversion_key=conversion_id or conversion,
            looping=index.effective_looping(record.owner_id),
        )
        variants_by_media.setdefault(media_id, []).append(variant)
    return variants_by_media


class DuplicateMediaTableModel(QAbstractTableModel):

    def __init__(self, headers: list[str], parent=None):
        super().__init__(parent)
        self.__headers = list(headers)
        self.__rows: list[list[str]] = []
        self.__sort_values: list[list] = []
        self.__search_texts: list[str] = []
        self.__status_severities: list[CellSeverity] = []

    def replace_rows(
        self,
        rows: list[list[str]],
        sort_values: list[list],
        search_texts: list[str] | None = None,
    ):
        self.beginResetModel()
        self.__rows = rows
        self.__sort_values = sort_values
        self.__search_texts = (
            search_texts if search_texts is not None
            else [" ".join(row).casefold() for row in rows]
        )
        self.__status_severities = [CellSeverity.Normal] * len(rows)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.__rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.__headers)

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        role_value = getattr(role, "value", role)
        orientation_value = getattr(orientation, "value", orientation)
        if (role_value != Qt.ItemDataRole.DisplayRole.value
                or orientation_value != Qt.Orientation.Horizontal.value):
            return None
        if 0 <= section < len(self.__headers):
            return self.__headers[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        column = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return self.__rows[row][column]
        if role == Qt.ItemDataRole.UserRole:
            return self.__sort_values[row][column]
        if role == Qt.ItemDataRole.BackgroundRole and column == STATUS_COLUMN:
            return self.__status_severities[row]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if column == 1:
                return Qt.AlignmentFlag.AlignCenter
            if column == 4:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            if column == STATUS_COLUMN:
                return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.ToolTipRole:
            value = self.__rows[row][column]
            return value if len(value) > 40 else None
        return None

    def search_text(self, row: int) -> str:
        return self.__search_texts[row]

    def set_status(self, row: int, text: str, severity: CellSeverity = CellSeverity.Normal):
        if not 0 <= row < len(self.__rows):
            return
        self.__rows[row][STATUS_COLUMN] = text
        self.__sort_values[row][STATUS_COLUMN] = (
            1 if severity == CellSeverity.Success
            else 2 if severity == CellSeverity.Danger
            else 0
        )
        self.__status_severities[row] = severity
        index = self.index(row, STATUS_COLUMN)
        self.dataChanged.emit(index, index, [
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.UserRole,
            Qt.ItemDataRole.BackgroundRole,
        ])


class DuplicateMediaSortProxyModel(QSortFilterProxyModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__segments: list[str] = []
        self.__cause_kind = ""
        self.__single_cause_only = False

    def set_filter(self, keyword: str):
        self.__segments = [
            segment.strip().casefold()
            for segment in keyword.split(";")
            if segment.strip()
        ]
        self.invalidateFilter()

    def set_cause_filter(self, kind: str):
        self.__cause_kind = kind
        self.invalidateFilter()

    def set_single_cause_only(self, enabled: bool):
        self.__single_cause_only = enabled
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if model is None:
            return True
        kind_value = ""
        if self.__cause_kind or self.__single_cause_only:
            kind_value = str(
                model.data(
                    model.index(source_row, 3),
                    Qt.ItemDataRole.UserRole,
                ) or ""
            )
        if self.__cause_kind:
            kind_parts = kind_value.split("+")
            if self.__cause_kind == CAUSE_MISSING_FILTER:
                if not any(kind in kind_parts for kind in CAUSE_MISSING_KINDS):
                    return False
            elif self.__cause_kind not in kind_parts:
                return False
        if self.__single_cause_only:
            reason_parts = [part for part in kind_value.split("+") if part]
            if len(reason_parts) > 1:
                return False
        if not self.__segments:
            return True
        search_text = model.search_text(source_row)
        for segment in self.__segments:
            exclude = segment.startswith("-")
            word = segment[1:].strip() if exclude else segment
            if not word:
                continue
            matched = word in search_text
            if exclude and matched:
                return False
            if not exclude and not matched:
                return False
        return True

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        left_value = left.data(Qt.ItemDataRole.UserRole)
        right_value = right.data(Qt.ItemDataRole.UserRole)
        if isinstance(left_value, int) and isinstance(right_value, int):
            return left_value < right_value
        return str(left_value or "").casefold() < str(right_value or "").casefold()


class SoundBankInfoWorker(QThread):
    total_ready = Signal(int)
    progress = Signal(int, int)
    size_progress = Signal(int, int)
    analysis_progress = Signal(int, int, str)
    stage_status = Signal(str)
    parsed = Signal(object)
    failed = Signal(str)
    analysis_status = Signal(str)

    def __init__(self, xml_path: str, project_root_hint: str = "", parent=None):
        super().__init__(parent)
        self.__xml_path = xml_path
        self.__project_root_hint = project_root_hint

    def run(self):
        try:
            total = soundbank_info_utils.count_soundbanks(self.__xml_path)
            self.total_ready.emit(total)
            result = soundbank_info_utils.find_duplicate_media(
                self.__xml_path,
                lambda processed: self.progress.emit(processed, total),
            )
            self.stage_status.emit("正在读取 wem 头信息…")
            soundbank_info_utils.fill_duplicate_sizes(
                result, self.__xml_path, self.size_progress.emit
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.stage_status.emit("正在定位 Wwise 工程…")
        project_root = self.resolve_project_root(result)
        if project_root is None:
            self.analysis_status.emit("未找到 Wwise 工程目录，跳过重复原因分析")
            self.parsed.emit((result, {}, ""))
            return
        try:
            causes = self.analyse_causes(result, project_root)
        except Exception as exc:
            Logger().error(f"分析重复原因失败：{exc}")
            causes = {}
        self.apply_edit_aware_extra_sizes(result, causes)
        self.parsed.emit((result, causes, str(project_root)))

    # 解析工程 XML，判定每个重复组是 conversion 差异还是剪辑差异造成
    def analyse_causes(self, result, project_root: Path) -> dict[str, DuplicateCause]:
        self.analysis_status.emit(f"正在分析重复原因：{project_root}")
        self.stage_status.emit("正在扫描 WorkUnit 文件…")
        variants_by_media = build_media_variant_index(
            project_root,
            result.platform,
            self.analysis_progress.emit,
        )
        self.stage_status.emit("正在统计重复原因…")
        causes: dict[str, DuplicateCause] = {}
        duration_cache: dict[str, Optional[float]] = {}
        for group in result.duplicate_groups:
            variants: list[MediaVariant] = []
            intervals: list[tuple[float, float]] = []
            file_intervals: dict[str, tuple[float, float]] = {}
            file_bytes_per_second: dict[str, float] = {}
            duration = duration_cache.get(group.original_path)
            if group.original_path not in duration_cache:
                duration = _resolve_original_duration(project_root, group.original_path)
                duration_cache[group.original_path] = duration
            for file_info in group.files:
                media_variants = variants_by_media.get(file_info.wem_id, [])
                variants.extend(media_variants)
                if media_variants and duration:
                    interval = _variant_interval(media_variants[0], duration)
                    if interval is not None:
                        intervals.append(interval)
                        key = file_info.wem_id.casefold()
                        file_intervals[key] = interval
                        interval_seconds = interval[1] - interval[0]
                        base_seconds = (
                            file_info.duration_seconds
                            if file_info.duration_seconds and file_info.duration_seconds > 0
                            else interval_seconds
                        )
                        if file_info.size_bytes is not None and base_seconds > 0:
                            file_bytes_per_second[key] = file_info.size_bytes / base_seconds
            durations = sorted(
                file_info.duration_seconds
                for file_info in group.files
                if file_info.duration_seconds is not None
                and file_info.duration_seconds > 0
            )
            cause = classify_media_variants(variants, durations)
            cause.file_intervals = file_intervals
            cause.file_bytes_per_second = file_bytes_per_second
            if duration and len(intervals) >= 2:
                total_seconds = sum(end - start for start, end in intervals)
                union_seconds = _merge_interval_length(intervals)
                cause.original_duration_seconds = duration
                if CAUSE_EDIT in cause.kind.split("+"):
                    cause.edit_total_seconds = total_seconds
                    cause.edit_waste_seconds = max(0.0, total_seconds - union_seconds)
            cause.expected_media_count = len(group.files)
            cause.matched_media_count = sum(
                1 for file_info in group.files
                if variants_by_media.get(file_info.wem_id)
            )
            if (cause.kind == CAUSE_UNKNOWN
                    and cause.matched_media_count < cause.expected_media_count):
                cause.kind = CAUSE_PARTIAL_UNMATCHED
            causes[group.original_path.casefold()] = cause
        return causes

    @staticmethod
    def apply_edit_aware_extra_sizes(result, causes: dict[str, DuplicateCause]) -> None:
        result.duplicate_extra_size_bytes = int(round(sum(
            _group_extra_size(group, causes.get(group.original_path.casefold()))
            for group in result.duplicate_groups
        )))

    def resolve_project_root(self, result) -> Optional[Path]:
        candidates: list[Path] = []
        # 工具本身连着 Wwise，优先使用当前打开的工程目录
        try:
            project_directory = project_utils.get_project_directory()
            if project_directory:
                candidates.append(Path(project_directory))
        except Exception:
            Logger().debug("未能从 Wwise 读取当前工程目录，继续尝试其它来源")
        if result.project_root:
            candidates.append(Path(result.project_root))
        xml_path = Path(self.__xml_path).resolve()
        if len(xml_path.parents) >= 3:
            candidates.append(xml_path.parents[2])
        if self.__project_root_hint:
            candidates.append(Path(self.__project_root_hint))
        for candidate in candidates:
            if any((candidate / folder).is_dir() for folder in wwise_compat.HIERARCHY_FOLDER_NAMES):
                return candidate
        return None


# 媒体查重窗口：从 SoundBanksInfo.xml 找出同一原始音频对应的多个打包 wem
class MediaDuplicateWindow(BaseDialog, Ui_MediaDuplicate):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setupUi(self)
        for label, kind in CAUSE_FILTER_OPTIONS:
            self.cbbCauseFilter.addItem(label, kind)
        self.__worker: Optional[SoundBankInfoWorker] = None
        self.__progress_bar: Optional[ProgressBar] = None
        self.__detail_windows: set[MediaDuplicateDetailWindow] = set()
        self.__result = None
        self.__causes: dict[str, DuplicateCause] = {}
        self.__row_by_group_path: dict[str, int] = {}
        self.__auto_fix_pending: dict[str, int] = {}
        self.__auto_fix_failed: set[str] = set()
        self.__auto_fix_changed: set[str] = set()
        self.__auto_fix_counts: dict[str, int] = {}
        self.__auto_fix_render_checked: set[str] = set()
        self.__analysis_root_hint = ""
        self.__last_file = ""
        self.__closing = False
        self.__filter_timer = QTimer(self)
        self.__filter_timer.setSingleShot(True)
        self.__filter_timer.setInterval(250)
        self.__model = DuplicateMediaTableModel(HEADERS, self)
        self.__proxy = DuplicateMediaSortProxyModel(self)
        self.__proxy.setSourceModel(self.__model)
        self.tblDuplicates.setModel(self.__proxy)
        self.tblDuplicates.setItemDelegateForColumn(
            STATUS_COLUMN, SeverityTableDelegate(self.tblDuplicates)
        )
        header = self.tblDuplicates.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self.tblDuplicates.setColumnWidth(0, 450)
        self.tblDuplicates.setColumnWidth(1, 90)
        self.tblDuplicates.setColumnWidth(2, 100)
        self.tblDuplicates.setColumnWidth(3, 320)
        self.tblDuplicates.setColumnWidth(4, 110)
        self.tblDuplicates.setColumnWidth(5, 90)
        self.load_user_settings()
        self.setup_triggers()
        QTimer.singleShot(0, self.restore_last_file)

    def setup_triggers(self):
        self.btnChooseFile.clicked.connect(self.choose_file)
        self.btnReparse.clicked.connect(self.reparse_current_file)
        self.btnAutoFix.clicked.connect(self.auto_fix_duplicates)
        self.btnExportJson.clicked.connect(self.export_json)
        self.tblDuplicates.doubleClicked.connect(self.open_detail_for_index)
        self.tblDuplicates.customContextMenuRequested.connect(self.show_context_menu)
        self.iptFilter.textChanged.connect(self.schedule_filter)
        self.cbbCauseFilter.currentIndexChanged.connect(self.apply_filter)
        self.cbxSingleCauseOnly.toggled.connect(self.apply_filter)
        self.__filter_timer.timeout.connect(self.apply_filter)

    def load_user_settings(self):
        settings = user_config.get_window_settings(WINDOW_SETTINGS_KEY)
        self.__last_file = str(settings.get("last_file", ""))
        self.__analysis_root_hint = str(settings.get("analysis_project_root", ""))
        self.iptFilter.setText(str(settings.get("filter", "")))
        column_widths = settings.get("column_widths")
        if (isinstance(column_widths, list)
                and len(column_widths) == self.__model.columnCount()):
            for column, width in enumerate(column_widths):
                if isinstance(width, (int, float)) and width > 0:
                    self.tblDuplicates.setColumnWidth(column, int(width))

    def save_user_settings(self):
        user_config.set_window_settings(WINDOW_SETTINGS_KEY, {
            "last_file": self.__last_file,
            "analysis_project_root": self.__analysis_root_hint,
            "filter": self.iptFilter.text(),
            "column_widths": [
                self.tblDuplicates.columnWidth(column)
                for column in range(self.__model.columnCount())
            ],
        })

    def choose_file(self):
        if self.__worker is not None and self.__worker.isRunning():
            return
        start_path = self.__last_file if self.__last_file and Path(self.__last_file).is_file() else ""
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择 SoundBanksInfo.xml",
            start_path,
            "SoundBanksInfo.xml (SoundBanksInfo.xml);;XML 文件 (*.xml);;所有文件 (*.*)",
        )
        if not file_path:
            self.lblStatus.setText("未选择文件。可点击「选择文件…」重新选择。")
            return
        self.__last_file = file_path
        self.save_user_settings()
        self.start_parsing(file_path)

    def restore_last_file(self):
        if self.__last_file and Path(self.__last_file).is_file():
            if self.confirm_use_last_file():
                self.start_parsing(self.__last_file)
            else:
                self.choose_file()
            return
        if self.__last_file:
            self.lblStatus.setText("上次打开的 SoundBanksInfo.xml 不存在，请重新选择。")
        self.choose_file()

    def confirm_use_last_file(self) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle("媒体查重")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText("是否使用上一次打开的 SoundBanksInfo.xml？")
        box.setInformativeText(f"XML 路径：\n{self.__last_file}")
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        yes_button = box.button(QMessageBox.StandardButton.Yes)
        no_button = box.button(QMessageBox.StandardButton.No)
        if yes_button is not None:
            yes_button.setText("是，使用上次")
        if no_button is not None:
            no_button.setText("否，重新选择")
        return box.exec() == QMessageBox.StandardButton.Yes

    def reparse_current_file(self):
        file_path = self.iptSoundBanksInfoPath.text().strip()
        if not file_path:
            self.choose_file()
            return
        self.start_parsing(file_path)

    def start_parsing(self, file_path: str):
        if self.__worker is not None and self.__worker.isRunning():
            return
        path = Path(file_path)
        if not path.is_file():
            message = f"文件不存在：{path}"
            self.lblStatus.setText(message)
            Logger().error(message)
            QMessageBox.critical(self, "媒体查重", message)
            return

        self.iptSoundBanksInfoPath.setText(str(path))
        self.__model.replace_rows([], [])
        self.__result = None
        self.__causes = {}
        self.__row_by_group_path = {}
        self.lblFilterResult.setText("显示 0 / 0 行")
        self.lblStatus.setText(f"正在解析：{path.name} …")
        self.lblPlatform.setText("平台：读取中…")
        self.btnExportJson.setEnabled(False)
        self.btnAutoFix.setEnabled(False)
        self.set_buttons_enabled(False)

        self.__worker = SoundBankInfoWorker(str(path), self.__analysis_root_hint, self)
        self.__worker.total_ready.connect(self.on_total_ready)
        self.__worker.progress.connect(self.on_parse_progress)
        self.__worker.size_progress.connect(self.on_size_progress)
        self.__worker.analysis_progress.connect(self.on_analysis_progress)
        self.__worker.stage_status.connect(self.on_stage_status)
        self.__worker.parsed.connect(self.on_parsed)
        self.__worker.failed.connect(self.on_parse_failed)
        self.__worker.finished.connect(self.on_worker_finished)
        self.__worker.analysis_status.connect(self.lblStatus.setText)
        self.__worker.start()

    def set_buttons_enabled(self, enabled: bool):
        self.btnChooseFile.setEnabled(enabled)
        self.btnReparse.setEnabled(enabled)

    def on_total_ready(self, total: int):
        if total <= 0:
            return
        self.close_progress_bar()
        self.__progress_bar = ProgressBar(total, "解析 SoundBanksInfo.xml", None)
        self.__progress_bar.update_progress(0, f"已解析 0 / {total} 个 SoundBank")
        self.__progress_bar.show()
        self.__progress_bar.raise_()
        self.__progress_bar.activateWindow()

    def on_parse_progress(self, processed: int, total: int):
        if self.__progress_bar is not None and total > 0:
            self.__progress_bar.update_progress(
                processed,
                f"已解析 {processed} / {total} 个 SoundBank",
            )

    def ensure_progress_bar(self, total: int, title: str):
        if (self.__progress_bar is None
                or self.__progress_bar.total_count != total
                or self.__progress_bar.windowTitle() != title):
            self.close_progress_bar()
            self.__progress_bar = ProgressBar(total, title, None)
            self.__progress_bar.show()
            self.__progress_bar.raise_()
            self.__progress_bar.activateWindow()

    def on_size_progress(self, processed: int, total: int):
        if total <= 0:
            self.close_progress_bar()
            return
        self.ensure_progress_bar(total, "读取 wem 头信息")
        self.__progress_bar.update_progress(processed, "读取 wem 头信息")

    def on_stage_status(self, text: str):
        if self.__progress_bar is not None:
            self.__progress_bar.set_status(text)
        self.lblStatus.setText(text)

    def on_analysis_progress(self, processed: int, total: int, work_unit_path: str):
        if total <= 0:
            self.close_progress_bar()
            return
        self.ensure_progress_bar(total, "分析重复原因")
        work_unit_name = Path(work_unit_path).stem if work_unit_path else "准备中"
        self.__progress_bar.update_progress(
            processed,
            f"正在读取WorkUnit：{work_unit_name}",
        )

    def close_progress_bar(self):
        if self.__progress_bar is None:
            return
        self.__progress_bar.processor = None
        self.__progress_bar.close()
        self.__progress_bar = None

    def on_parsed(self, payload):
        if self.__closing:
            return
        result, causes, analysis_root = payload
        self.__result = result
        self.__causes = causes
        if analysis_root:
            self.__analysis_root_hint = analysis_root
        rows: list[list[str]] = []
        sort_values: list[list] = []
        search_texts: list[str] = []

        for group in result.duplicate_groups:
            wem_count = len(group.files)
            event_count = len(group.event_names)
            cause = causes.get(group.original_path.casefold())
            cause_label = cause.label if cause else "未分析"
            extra_size = int(round(_group_extra_size(group, cause)))
            cause_kind = cause.kind if cause else CAUSE_NOT_ANALYZED
            if (cause is not None
                    and cause.expected_media_count
                    and cause.matched_media_count < cause.expected_media_count
                    and CAUSE_UNMATCHED not in cause_kind.split("+")
                    and CAUSE_PARTIAL_UNMATCHED not in cause_kind.split("+")):
                cause_kind += "+" + CAUSE_PARTIAL_UNMATCHED
            rows.append([
                group.original_path,
                str(wem_count),
                str(event_count),
                cause_label,
                wem_utils.format_file_size(extra_size),
                STATUS_UNPROCESSED,
            ])
            sort_values.append([
                group.original_path.casefold(),
                wem_count,
                event_count,
                cause_kind,
                extra_size,
                0,
            ])
            search_texts.append(group.original_path.casefold())

        self.__row_by_group_path = {
            group.original_path.casefold(): row
            for row, group in enumerate(result.duplicate_groups)
        }
        self.__model.replace_rows(rows, sort_values, search_texts)
        self.apply_filter()
        platform = result.platform or "未知"
        self.lblPlatform.setText(f"平台：{platform}")
        summary_lines = [
            f"SoundBank {result.soundbank_count} 个，SFX 媒体条目 {result.media_file_count} 条，"
            f"原始音频 {result.unique_original_count} 个。",
            f"重复原始音频 {result.duplicate_original_count} 个，重复 wem {result.duplicate_wem_count} 条；"
            f"合计大小 {wem_utils.format_file_size(result.duplicate_total_size_bytes)}，"
            f"额外包体 {wem_utils.format_file_size(result.duplicate_extra_size_bytes)}。",
        ]
        if result.missing_duplicate_size_count:
            summary_lines.append(
                f"有 {result.missing_duplicate_size_count} 个重复 wem 大小未读取。"
            )
        if causes:
            category_stats: dict[str, dict] = {}
            edit_waste_seconds = 0.0
            for group in result.duplicate_groups:
                cause = causes.get(group.original_path.casefold())
                group_extra_size = _group_extra_size(group, cause)
                has_edit_waste = (
                    cause is not None
                    and CAUSE_EDIT in cause.kind.split("+")
                    and cause.edit_total_seconds is not None
                )
                if has_edit_waste:
                    edit_waste_seconds += cause.edit_waste_seconds or 0
                for category in _cause_categories(cause):
                    stats = category_stats.setdefault(category, {
                        "count": 0,
                        "extra_size": 0.0,
                        "no_overlap": 0,
                    })
                    stats["count"] += 1
                    stats["extra_size"] += group_extra_size
                    if (category == CAUSE_LABELS[CAUSE_EDIT]
                            and has_edit_waste
                            and (cause.edit_waste_seconds or 0) <= 1e-9):
                        stats["no_overlap"] += 1
            summary_lines.append("原因分类：")
            order = [
                CAUSE_LABELS[CAUSE_CONVERSION],
                CAUSE_LABELS[CAUSE_EDIT],
                CAUSE_LABELS[CAUSE_DURATION],
                CAUSE_LABELS[CAUSE_LOOP_FLAG],
                CAUSE_LABELS[CAUSE_LOOP_REGION],
                CAUSE_LABELS[CAUSE_LOOP_OVERRIDE],
                CAUSE_LABELS[CAUSE_FADE],
                CAUSE_LABELS[CAUSE_RENDER],
                CAUSE_LABELS[CAUSE_UNMATCHED],
                CAUSE_LABELS[CAUSE_UNKNOWN],
                "未分析",
            ]
            order.extend(category for category in category_stats if category not in order)
            for category in order:
                stats = category_stats.get(category)
                if stats is None:
                    continue
                line = (
                    f"{category}：{stats['count']} 个，"
                    f"额外 {wem_utils.format_file_size(int(round(stats['extra_size'])))}"
                )
                if category == CAUSE_LABELS[CAUSE_EDIT] and stats["no_overlap"]:
                    line += f"（其中无重叠 {stats['no_overlap']} 个）"
                summary_lines.append(line)
                if category == CAUSE_LABELS[CAUSE_EDIT] and edit_waste_seconds > 0:
                    summary_lines.append(
                        f"{CAUSE_LABELS[CAUSE_EDIT]}重叠浪费时长："
                        f"{wem_utils.format_duration(edit_waste_seconds)}"
                    )
        else:
            summary_lines.append(
                "未分析重复原因：未找到 Wwise 工程目录。"
            )
        summary = "\n".join(summary_lines)
        result_box = QMessageBox(self)
        result_box.setWindowTitle("媒体查重解析结果")
        result_box.setIcon(QMessageBox.Icon.Information)
        result_box.setText("解析完成")
        result_box.setInformativeText(summary)
        result_box.setTextFormat(Qt.TextFormat.PlainText)
        result_box.exec()
        self.lblStatus.setText("" if causes else "重复原因未分析：未找到 Wwise 工程目录。")
        self.close_progress_bar()
        Logger().info(summary.replace("\n", "；") + f"；分析工程：{analysis_root}")

    def on_parse_failed(self, message: str):
        if self.__closing:
            return
        self.close_progress_bar()
        self.lblPlatform.setText("平台：-")
        self.lblStatus.setText(f"解析失败：{message}")
        self.btnAutoFix.setEnabled(False)
        Logger().error(f"解析 SoundBanksInfo.xml 失败：{message}")
        QMessageBox.critical(self, "媒体查重", f"解析失败：\n{message}")

    def on_worker_finished(self):
        self.close_progress_bar()
        self.__worker = None
        self.set_buttons_enabled(True)
        if self.__closing:
            self.reject()

    def schedule_filter(self):
        self.__filter_timer.start()

    # 双击或右键查看某个原始音频对应的 wem 明细
    def open_detail_for_index(self, index: QModelIndex):
        if self.__result is None or not index.isValid():
            return
        source_index = self.__proxy.mapToSource(index)
        source_row = source_index.row()
        if not 0 <= source_row < len(self.__result.duplicate_groups):
            return
        group = self.__result.duplicate_groups[source_row]
        original_audio_path = self.resolve_original_audio_path(group.original_path)
        cause = self.__causes.get(group.original_path.casefold())
        detail = MediaDuplicateDetailWindow(
            group,
            self.detail_search_dirs(),
            self.__result.platform,
            original_audio_path,
            cause,
            self,
        )
        detail.setWindowModality(Qt.WindowModality.NonModal)
        detail.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        detail.destroyed.connect(
            lambda _obj=None, window=detail: self.__detail_windows.discard(window)
        )
        self.__detail_windows.add(detail)
        detail.show()
        detail.raise_()
        detail.activateWindow()

    def show_context_menu(self, position):
        index = self.tblDuplicates.indexAt(position)
        if not index.isValid():
            return
        menu = QMenu(self)
        text = self.__proxy.data(index, Qt.ItemDataRole.DisplayRole)
        if text:
            menu.addAction("复制", lambda: clipboard.copy(str(text)))
        menu.addAction("查看详情", lambda: self.open_detail_for_index(index))
        source_index = self.__proxy.mapToSource(index)
        source_row = source_index.row()
        if self.__result is not None and 0 <= source_row < len(self.__result.duplicate_groups):
            group = self.__result.duplicate_groups[source_row]
            fix_action = menu.addAction(
                "一键处理",
                lambda: self.auto_fix_group(group),
            )
            fix_action.setEnabled(
                bool(self.build_auto_fix_tasks([group]))
                and waapi_utils.is_connected()
            )
        if index.column() == 0:
            menu.addAction("音频预览", lambda: self.preview_original_audio(index))
        menu.exec(self.tblDuplicates.viewport().mapToGlobal(position))

    def preview_original_audio(self, index: QModelIndex):
        if self.__result is None or not index.isValid():
            return
        source_index = self.__proxy.mapToSource(index)
        source_row = source_index.row()
        if not 0 <= source_row < len(self.__result.duplicate_groups):
            return
        group = self.__result.duplicate_groups[source_row]
        file_path = self.resolve_original_audio_path(group.original_path)
        if file_path is None or not file_path.is_file():
            message = f"未找到原始音频文件：\n{file_path or group.original_path}"
            Logger().warning(message)
            QMessageBox.warning(self, "音频预览", message)
            return
        AudioPreviewWindow(str(file_path), self).show()

    def resolve_original_audio_path(self, original_path: str) -> Path | None:
        if self.__result is None:
            return None
        relative_path = Path(original_path)
        candidates = []
        originals_folder = ""
        if waapi_utils.is_connected():
            try:
                originals_folder = project_utils.get_originals_folder()
            except Exception:
                Logger().debug("未能从 Wwise 工程读取 Originals 目录，改用 SoundBanksInfo.xml 中的工程路径")
        if originals_folder:
            originals_root = Path(originals_folder)
        elif self.__result.project_root:
            originals_root = Path(self.__result.project_root) / "Originals"
        else:
            originals_root = None
        if originals_root is not None:
            candidates.extend([
                originals_root / "SFX" / relative_path,
                originals_root / relative_path,
            ])
        if self.__result.source_files_root:
            candidates.append(Path(self.__result.source_files_root) / relative_path)
        xml_path = self.iptSoundBanksInfoPath.text().strip()
        if xml_path:
            xml_dir = Path(xml_path).parent
            candidates.extend([
                xml_dir / relative_path,
                xml_dir / "Originals" / "SFX" / relative_path,
            ])
        candidates = list(dict.fromkeys(candidates))
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return candidates[0] if candidates else None

    def detail_search_dirs(self) -> list[str]:
        search_dirs = []
        if self.__result is not None and self.__result.soundbanks_root:
            search_dirs.append(self.__result.soundbanks_root)
        xml_path = self.iptSoundBanksInfoPath.text().strip()
        if xml_path:
            search_dirs.append(str(Path(xml_path).parent))
        return list(dict.fromkeys(search_dirs))

    # 只显示同时满足所有关键词的行；以 - 开头的关键词表示排除
    def apply_filter(self):
        self.__proxy.set_cause_filter(self.cbbCauseFilter.currentData() or "")
        self.__proxy.set_single_cause_only(self.cbxSingleCauseOnly.isChecked())
        self.__proxy.set_filter(self.iptFilter.text())
        total = self.__model.rowCount()
        self.lblFilterResult.setText(f"显示 {self.__proxy.rowCount()} / {total} 行")
        has_visible_rows = self.__proxy.rowCount() > 0
        self.btnExportJson.setEnabled(has_visible_rows)
        self.btnAutoFix.setEnabled(bool(self.__causes) and has_visible_rows)
        if total:
            self.save_user_settings()

    # 当前筛选结果里可自动处理的对象：循环设置按 Sound 去重，Fade 按 AudioSource 去重
    def build_auto_fix_tasks(self, groups=None) -> list[AutoFixTask]:
        tasks: list[AutoFixTask] = []
        tasks_by_key: dict[tuple[str, str], AutoFixTask] = {}
        for group in (groups if groups is not None else self.current_groups()):
            cause = self.__causes.get(group.original_path.casefold())
            if cause is None:
                continue
            parts = set(cause.kind.split("+"))
            for file_info in group.files:
                for source in cause.sources_by_media.get(file_info.wem_id.casefold(), []):
                    owner_id = str(source.get("owner_object_id") or "")
                    source_id = str(source.get("audio_source_id") or "")
                    owner_label = str(
                        source.get("owner_object_path")
                        or source.get("audio_source_path")
                        or source.get("audio_source_name")
                        or group.original_path
                    )
                    if CAUSE_LOOP_FLAG in parts and owner_id:
                        self.add_auto_fix_task(
                            tasks, tasks_by_key, "loop", owner_id,
                            owner_label, group.original_path,
                        )
                    if CAUSE_FADE in parts and source_id:
                        self.add_auto_fix_task(
                            tasks, tasks_by_key, "fade", source_id,
                            str(source.get("audio_source_name") or owner_label),
                            group.original_path,
                        )
                    if CAUSE_RENDER in parts and owner_id:
                        self.add_auto_fix_task(
                            tasks, tasks_by_key, "render", owner_id,
                            owner_label, group.original_path,
                        )
        return tasks

    @staticmethod
    def add_auto_fix_task(tasks, tasks_by_key, action, target_id, target_name, group_path):
        key = (action, target_id)
        task = tasks_by_key.get(key)
        if task is None:
            task = AutoFixTask(action, target_id, target_name, [group_path])
            tasks_by_key[key] = task
            tasks.append(task)
        elif group_path not in task.group_paths:
            task.group_paths.append(group_path)

    def auto_fix_duplicates(self):
        self.start_auto_fix(self.build_auto_fix_tasks(), "当前筛选结果")

    def auto_fix_group(self, group):
        self.start_auto_fix(self.build_auto_fix_tasks([group]), group.original_path)

    def start_auto_fix(self, tasks: list[AutoFixTask], scope_text: str):
        if not waapi_utils.is_connected():
            QMessageBox.warning(self, "自动处理", "Wwise 未连接，无法执行自动处理。")
            return
        if batch_processor.is_busy():
            QMessageBox.warning(self, "自动处理", batch_processor.busy_message("自动处理"))
            return
        if not tasks:
            QMessageBox.information(
                self,
                "自动处理",
                f"{scope_text} 中没有可自动处理的重复原因。\n"
                "仅支持循环设置、淡入淡出和效果器渲染。",
            )
            return

        counts: dict[str, int] = {}
        for task in tasks:
            counts[task.action] = counts.get(task.action, 0) + 1
        summary = "\n".join(
            f"- {AUTO_FIX_ACTION_LABELS.get(action, action)}：{count} 项"
            for action, count in counts.items()
        )
        reply = QMessageBox.question(
            self,
            "自动处理",
            f"将对 {scope_text} 执行以下修改：\n{summary}\n\n"
            "所有修改会合并为一个撤销组，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.__auto_fix_counts = counts
        self.__auto_fix_failed = set()
        self.__auto_fix_changed = set()
        self.__auto_fix_pending = {}
        self.__auto_fix_render_checked = set()
        for task in tasks:
            for group_path in task.group_paths:
                key = group_path.casefold()
                self.__auto_fix_pending[key] = self.__auto_fix_pending.get(key, 0) + 1
        for key in self.__auto_fix_pending:
            self.set_group_status(key, STATUS_UNPROCESSED, CellSeverity.Normal)

        started = batch_processor.create_async(
            tasks,
            self.process_auto_fix_task,
            "媒体查重自动处理",
            on_finished=self.on_auto_fix_finished,
            on_interrupted=self.on_auto_fix_interrupted,
            on_item_processed=self.on_auto_fix_item_processed,
            progress_text_func=lambda index, task: (
                f"{AUTO_FIX_ACTION_LABELS.get(task.action, task.action)}：{task.target_name}"
            ),
            undo_group=AUTO_FIX_UNDO_GROUP,
        )
        if not started:
            QMessageBox.warning(self, "自动处理", batch_processor.busy_message("自动处理"))
            return
        Logger().info(f"开始媒体查重自动处理：{summary.replace(chr(10), '；')}")
        self.set_buttons_enabled(False)
        self.btnAutoFix.setEnabled(False)
        self.lblStatus.setText("正在自动处理重复媒体…")

    def process_auto_fix_task(self, _index: int, task: AutoFixTask) -> bool:
        try:
            obj = waapi_utils.get_full_info_from_obj_id(task.target_id)
            if obj is None or not obj.is_valid:
                task.success = False
                Logger().warning(f"自动处理：未找到对象 {task.target_id}")
                return True
            if task.action == "loop":
                task.success, task.changed = self.apply_loop_fix(obj)
            elif task.action == "fade":
                task.success, task.changed = self.apply_fade_fix(obj)
            elif task.action == "render":
                task.success, task.changed = self.apply_render_fix(obj)
        except Exception:
            task.success = False
            Logger().exception(f"自动处理失败：{task.action} {task.target_name}")
        return True

    # 只在父容器是唯一 active 子对象的 Sound 上，把循环上移到容器
    def apply_loop_fix(self, sound: WwiseObject) -> tuple[bool, bool]:
        if sound.type != WwiseObjectType.Sound:
            return True, False
        parent = waapi_utils.get_parent_object(sound)
        if (parent is None or not parent.is_valid
                or parent.type not in LOOPABLE_CONTAINER_TYPES):
            return True, False
        children = waapi_utils.get_child_objects(parent)
        active_children = self.active_children(children)
        if len(active_children) != 1 or active_children[0].id != sound.id:
            return True, False

        ok = True
        changed = False
        parent_looping = waapi_utils.get_object_property(parent, "PlayMechanismLoop")
        if not parent_looping:
            ok = waapi_utils.set_object_property(
                parent, "PlayMechanismLoop", True
            ) and ok
            changed = True
        sound_looping = waapi_utils.get_object_property(sound, "IsLoopingEnabled")
        if sound_looping:
            ok = waapi_utils.set_object_property(
                sound, "IsLoopingEnabled", False
            ) and ok
            changed = True
        return ok, changed

    @staticmethod
    def active_children(children: list) -> list:
        if not children:
            return []
        properties = waapi_utils.get_objects_properties(children, ["IsPlayable"])
        active = []
        for child in children:
            value = (properties.get(child.id) or {}).get("IsPlayable")
            if value is None or bool(value):
                active.append(child)
        return active

    @staticmethod
    def apply_fade_fix(source: WwiseObject) -> tuple[bool, bool]:
        if source.type != WwiseObjectType.AudioSource:
            return True, False
        properties = waapi_utils.get_object_properties(
            source, ["FadeInDuration", "FadeOutDuration"]
        )
        updates = {}
        for name in ("FadeInDuration", "FadeOutDuration"):
            value = properties.get(name)
            if isinstance(value, (int, float)) and 0 < value < 0.1:
                updates[name] = 0
        if not updates:
            return True, False
        return waapi_utils.set_object_property_values(source, updates), True

    # 关闭对象及其所有上级的 Render 效果槽
    def apply_render_fix(self, owner: WwiseObject) -> tuple[bool, bool]:
        ok = True
        changed = False
        current = owner
        visited: set[str] = set()
        while current is not None and current.is_valid and current.id not in visited:
            if current.id in self.__auto_fix_render_checked:
                break
            visited.add(current.id)
            self.__auto_fix_render_checked.add(current.id)
            slots_ok, slots_changed = self.disable_render_slots(current)
            ok = ok and slots_ok
            changed = changed or slots_changed
            current = waapi_utils.get_parent_object(current)
        return ok, changed

    @staticmethod
    def disable_render_slots(obj: WwiseObject) -> tuple[bool, bool]:
        effect_slots = waapi_utils.get_object_property(obj, "@Effects")
        if not effect_slots:
            return True, False
        ok = True
        changed = False
        for slot_dict in effect_slots:
            slot = WwiseObject(slot_dict)
            if not slot.is_valid:
                continue
            if waapi_utils.get_object_property(slot, "Render"):
                ok = waapi_utils.set_object_property(slot, "Render", False) and ok
                changed = True
        return ok, changed

    def on_auto_fix_item_processed(self, payload):
        _index, task = payload
        for group_path in task.group_paths:
            key = group_path.casefold()
            if not task.success:
                self.__auto_fix_failed.add(key)
            if task.changed:
                self.__auto_fix_changed.add(key)
            remaining = self.__auto_fix_pending.get(key, 1) - 1
            self.__auto_fix_pending[key] = max(0, remaining)
            if remaining <= 0:
                if key in self.__auto_fix_failed:
                    self.set_group_status(key, STATUS_FAILED, CellSeverity.Danger)
                elif key in self.__auto_fix_changed:
                    self.set_group_status(key, STATUS_PROCESSED, CellSeverity.Success)

    def set_group_status(self, group_path: str, text: str, severity: CellSeverity):
        row = self.__row_by_group_path.get(group_path.casefold())
        if row is not None:
            self.__model.set_status(row, text, severity)

    def mark_group_processed(self, group_path: str):
        self.set_group_status(group_path, STATUS_PROCESSED, CellSeverity.Success)

    def mark_group_failed(self, group_path: str):
        self.set_group_status(group_path, STATUS_FAILED, CellSeverity.Danger)

    def on_auto_fix_finished(self):
        failed_count = len(self.__auto_fix_failed)
        summary = "，".join(
            f"{AUTO_FIX_ACTION_LABELS.get(action, action)} {count} 项"
            for action, count in self.__auto_fix_counts.items()
        )
        self.lblStatus.setText(f"自动处理完成：{summary}。请重新解析以刷新查重结果。")
        message = f"自动处理完成：\n{summary}"
        if failed_count:
            message += f"\n有 {failed_count} 个原始音频处理失败，请查看日志。"
        message += "\n\n请重新解析 SoundBanksInfo.xml 以刷新查重结果。"
        self.__auto_fix_counts = {}
        self.__auto_fix_failed = set()
        self.__auto_fix_changed = set()
        self.__auto_fix_pending = {}
        self.__auto_fix_render_checked = set()
        self.set_buttons_enabled(True)
        self.apply_filter()
        Logger().info(f"媒体查重自动处理完成：{summary}")
        QMessageBox.information(self, "自动处理", message)

    def on_auto_fix_interrupted(self):
        for key, remaining in self.__auto_fix_pending.items():
            if remaining > 0:
                self.set_group_status(key, STATUS_FAILED, CellSeverity.Danger)
        self.__auto_fix_counts = {}
        self.__auto_fix_failed = set()
        self.__auto_fix_changed = set()
        self.__auto_fix_pending = {}
        self.__auto_fix_render_checked = set()
        self.set_buttons_enabled(True)
        self.apply_filter()
        self.lblStatus.setText("自动处理中断，部分对象可能已修改。")
        Logger().warning("媒体查重自动处理中断")
        QMessageBox.warning(self, "自动处理", "自动处理中断，部分对象可能已修改。")

    # 每个 wem 按实际引用它的 AudioFileSource 展开；只保留当前重复原因相关的设置字段
    def export_group_details(self, group, cause) -> list[dict]:
        sources_by_media = cause.sources_by_media if cause is not None else {}
        visible_fields = _cause_detail_fields(cause)
        details = []
        for file_info in group.files:
            sources = sources_by_media.get(file_info.wem_id.casefold(), [])
            for source in sources or [{}]:
                detail = {
                    "wem_path": file_info.packed_path,
                    "audio_source_name": source.get("audio_source_name", ""),
                    "audio_source_path": source.get("audio_source_path", ""),
                }
                cause_values = {
                    "conversion": source.get("conversion", ""),
                    "trim_begin": source.get("trim_begin"),
                    "trim_end": source.get("trim_end"),
                    "fade_in": source.get("fade_in"),
                    "fade_out": source.get("fade_out"),
                    "is_looping": source.get("is_looping"),
                    "loop_begin": source.get("loop_begin"),
                    "loop_end": source.get("loop_end"),
                    "override_wav_loop": source.get("override_wav_loop"),
                    "render_effect": source.get("render_effect", ""),
                }
                for field, value in cause_values.items():
                    if field not in visible_fields or value is None:
                        continue
                    if (field in ("loop_begin", "loop_end")
                            and _is_default_loop_value(value)):
                        continue
                    detail[field] = value
                details.append(detail)
        return details

    def export_duplicate_group(self, group) -> dict:
        cause = self.__causes.get(group.original_path.casefold())
        visible_fields = _cause_detail_fields(cause)
        wems = []
        for file_info in group.files:
            entry = {
                "packed_path": file_info.packed_path,
                "size_bytes": file_info.size_bytes,
                "duration_seconds": file_info.duration_seconds,
                "soundbanks": list(file_info.soundbank_names),
            }
            if "format" in visible_fields:
                entry["format"] = file_info.codec or "-"
            if "sample_rate" in visible_fields:
                entry["sample_rate"] = file_info.sample_rate
            wems.append(entry)
        return {
            "original_path": group.original_path,
            "wem_count": len(group.files),
            "event_count": len(group.event_names),
            "extra_size_bytes": int(round(_group_extra_size(group, cause))),
            "cause": self.__cause_payload(group),
            "wems": wems,
            "details": self.export_group_details(group, cause),
        }

    # 导出当前筛选结果，保留每个 wem 与 SoundBank 的对应关系及 AudioFileSource 明细
    def export_json(self):
        self.apply_filter()
        groups = self.current_groups()
        if not groups:
            Logger().warning("表格为空，暂无可导出的查重结果")
            return
        result = self.__result
        exported_wem_count = sum(len(group.files) for group in groups)
        exported_total_size_bytes = sum(
            file_info.size_bytes or 0
            for group in groups
            for file_info in group.files
        )
        exported_missing_size_count = sum(
            1
            for group in groups
            for file_info in group.files
            if file_info.size_bytes is None
        )
        exported_extra_size_bytes = int(round(sum(
            _group_extra_size(group, self.__causes.get(group.original_path.casefold()))
            for group in groups
        )))
        payload = {
            "source_file": self.iptSoundBanksInfoPath.text(),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "platform": result.platform,
            "soundbank_count": result.soundbank_count,
            "media_file_count": result.media_file_count,
            "unique_original_count": result.unique_original_count,
            "duplicate_original_count": len(groups),
            "duplicate_wem_count": exported_wem_count,
            "duplicate_total_size_bytes": exported_total_size_bytes,
            "duplicate_extra_size_bytes": exported_extra_size_bytes,
            "missing_duplicate_size_count": exported_missing_size_count,
            "exported_group_count": len(groups),
            "exported_wem_count": exported_wem_count,
            "duplicates": [self.export_duplicate_group(group) for group in groups],
        }

        default_name = f"MediaDuplicates_{datetime.now():%Y%m%d_%H%M%S}.json"
        default_dir = Path(self.__last_file).parent if self.__last_file else Path.cwd()
        file_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出媒体查重结果",
            str(default_dir / default_name),
            "JSON 文件 (*.json)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".json"):
            file_path += ".json"
        if not io_utils.export_to_json_path(payload, file_path):
            QMessageBox.critical(self, "媒体查重", f"导出失败：\n{file_path}")
            return
        self.lblStatus.setText(f"已导出 {len(groups)} 组到：{file_path}")
        Logger().info(f"媒体查重结果已导出：{len(groups)} 组 -> {file_path}")

    # 按当前排序/筛选后的视图顺序取查重分组
    def current_groups(self) -> list:
        if self.__result is None:
            return []
        groups = []
        for proxy_row in range(self.__proxy.rowCount()):
            source_index = self.__proxy.mapToSource(self.__proxy.index(proxy_row, 0))
            source_row = source_index.row()
            if 0 <= source_row < len(self.__result.duplicate_groups):
                groups.append(self.__result.duplicate_groups[source_row])
        return groups

    def __cause_payload(self, group) -> dict:
        cause = self.__causes.get(group.original_path.casefold())
        if cause is None:
            return {"kind": "not_analyzed", "label": "未分析"}
        parts = set(cause.kind.split("+"))
        payload = {
            "kind": cause.kind,
            "label": cause.label,
            "variant_count": cause.variant_count,
            "expected_media_count": cause.expected_media_count,
            "matched_media_count": cause.matched_media_count,
        }
        if CAUSE_CONVERSION in parts:
            payload["conversions"] = list(cause.conversions)
        if CAUSE_EDIT in parts:
            payload["edits"] = list(cause.edits)
            payload["edit_total_seconds"] = cause.edit_total_seconds
            payload["edit_waste_seconds"] = cause.edit_waste_seconds
        if CAUSE_DURATION in parts:
            payload["durations"] = list(cause.durations)
        if CAUSE_FADE in parts:
            payload["fades"] = list(cause.fades)
        if CAUSE_LOOP_FLAG in parts:
            payload["loops"] = list(cause.loops)
        if CAUSE_LOOP_REGION in parts:
            payload["loop_regions"] = list(cause.loop_regions)
        if CAUSE_LOOP_OVERRIDE in parts:
            payload["loop_overrides"] = list(cause.loop_overrides)
        if CAUSE_RENDER in parts:
            payload["renders"] = list(cause.renders)
        return payload

    def closeEvent(self, event):
        self.save_user_settings()
        if self.__worker is not None and self.__worker.isRunning():
            self.__closing = True
            self.lblStatus.setText("正在等待解析结束…")
            event.ignore()
            return
        super().closeEvent(event)

    # Esc 也会走 reject；解析线程未结束时先等它结束，避免窗口销毁时线程仍在运行
    def reject(self):
        if self.__worker is not None and self.__worker.isRunning():
            self.__closing = True
            self.lblStatus.setText("正在等待解析结束…")
            return
        super().reject()
