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
from libraries.utils import io_utils, user_config, wem_utils
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import (
    project_utils, soundbank_info_utils, waapi_utils, work_unit_parse_utils, wwise_compat,
)
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
]

CAUSE_CONVERSION = "conversion"
CAUSE_EDIT = "edit"
CAUSE_FADE = "fade"
CAUSE_LOOP = "loop"
CAUSE_RENDER = "render"
CAUSE_UNKNOWN = "unknown"
CAUSE_UNMATCHED = "unmatched"
CAUSE_PARTIAL_UNMATCHED = "partial_unmatched"
CAUSE_NOT_ANALYZED = "not_analyzed"

CAUSE_LABELS = {
    CAUSE_CONVERSION: "Conversion 不同",
    CAUSE_EDIT: "剪辑不同",
    CAUSE_FADE: "Fade 不同",
    CAUSE_LOOP: "循环设置不同",
    CAUSE_RENDER: "渲染效果不同",
    CAUSE_UNKNOWN: "未发现设置差异",
    CAUSE_UNMATCHED: "工程中未匹配",
    CAUSE_PARTIAL_UNMATCHED: "部分 wem 未匹配（SoundBanksInfo 可能过时）",
}

CAUSE_FILTER_OPTIONS = [
    ("全部原因", ""),
    (CAUSE_LABELS[CAUSE_CONVERSION], CAUSE_CONVERSION),
    (CAUSE_LABELS[CAUSE_EDIT], CAUSE_EDIT),
    (CAUSE_LABELS[CAUSE_FADE], CAUSE_FADE),
    (CAUSE_LABELS[CAUSE_LOOP], CAUSE_LOOP),
    (CAUSE_LABELS[CAUSE_RENDER], CAUSE_RENDER),
    (CAUSE_LABELS[CAUSE_UNKNOWN], CAUSE_UNKNOWN),
    (CAUSE_LABELS[CAUSE_UNMATCHED], CAUSE_UNMATCHED),
    ("部分 wem 未匹配", CAUSE_PARTIAL_UNMATCHED),
    ("未分析", CAUSE_NOT_ANALYZED),
]


@dataclass(frozen=True)
class MediaVariant:
    media_id: str
    owner_path: str
    conversion: str
    edit: work_unit_parse_utils.SourceEditSettings
    render_signature: str = ""
    conversion_key: str = ""
    looping: bool = False


@dataclass
class DuplicateCause:
    kind: str = CAUSE_UNMATCHED
    conversions: list[str] = field(default_factory=list)
    edits: list[str] = field(default_factory=list)
    fades: list[str] = field(default_factory=list)
    loops: list[bool] = field(default_factory=list)
    renders: list[str] = field(default_factory=list)
    variant_count: int = 0
    expected_media_count: int = 0
    matched_media_count: int = 0
    original_duration_seconds: Optional[float] = None
    edit_total_seconds: Optional[float] = None
    edit_waste_seconds: Optional[float] = None

    @property
    def label(self) -> str:
        if self.kind == CAUSE_UNMATCHED:
            return CAUSE_LABELS[CAUSE_UNMATCHED]
        parts = self.kind.split("+")
        labels = [CAUSE_LABELS.get(part, part) for part in parts]
        if CAUSE_EDIT in parts and self.edit_total_seconds is not None:
            if (self.edit_waste_seconds or 0) <= 1e-9:
                labels[parts.index(CAUSE_EDIT)] = "剪辑不同（无重叠）"
            else:
                labels[parts.index(CAUSE_EDIT)] = (
                    f"剪辑不同（重叠 {self.edit_waste_seconds:.3f}s）"
                )
        if self.expected_media_count and self.matched_media_count < self.expected_media_count:
            note = (
                f"部分 wem 未匹配（{self.matched_media_count}/{self.expected_media_count}，"
                "SoundBanksInfo 可能过时）"
            )
            if self.kind == CAUSE_PARTIAL_UNMATCHED:
                return note
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
def classify_media_variants(variants: list[MediaVariant]) -> DuplicateCause:
    if not variants:
        return DuplicateCause(kind=CAUSE_UNMATCHED)

    conversions = sorted({variant.conversion for variant in variants if variant.conversion})
    conversion_keys = sorted({variant.conversion_key or variant.conversion for variant in variants})
    trim_edits = sorted({variant.edit.trim_signature for variant in variants})
    # 剪辑已经不同时，重复原因已明确，不再继续比较 Fade
    if len(trim_edits) > 1:
        edits = trim_edits
        fade_edits: list[str] = []
    else:
        edits = sorted({variant.edit.describe() for variant in variants})
        fade_edits = sorted({variant.edit.fade_signature for variant in variants})
    loop_values = sorted({variant.looping for variant in variants})
    renders = sorted({variant.render_signature for variant in variants if variant.render_signature})

    causes: list[str] = []
    if len(conversion_keys) > 1:
        causes.append(CAUSE_CONVERSION)
    if len(trim_edits) > 1:
        causes.append(CAUSE_EDIT)
    if len(renders) > 1:
        causes.append(CAUSE_RENDER)
    if len(loop_values) > 1:
        causes.append(CAUSE_LOOP)
    # Fade 仅在其它原因都无法解释重复时作为独立原因展示
    if not causes and len(fade_edits) > 1:
        causes.append(CAUSE_FADE)

    return DuplicateCause(
        kind="+".join(causes) if causes else CAUSE_UNKNOWN,
        conversions=conversions,
        edits=edits,
        fades=fade_edits if len(fade_edits) > 1 else [],
        loops=loop_values if len(loop_values) > 1 else [],
        renders=renders,
        variant_count=len(variants),
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
    if (cause is not None
            and CAUSE_EDIT in cause.kind.split("+")
            and cause.edit_total_seconds
            and cause.edit_waste_seconds is not None):
        denominator = cause.original_duration_seconds or cause.edit_total_seconds
        ratio = max(0.0, min(1.0, cause.edit_waste_seconds / denominator))
        group_extra *= ratio
    return group_extra


def _cause_category(cause: DuplicateCause) -> str:
    if cause is None:
        return "未分析"
    parts = set(cause.kind.split("+"))
    if CAUSE_UNMATCHED in parts:
        return "工程中未匹配"
    if CAUSE_PARTIAL_UNMATCHED in parts:
        return "部分 wem 未匹配"
    if CAUSE_UNKNOWN in parts:
        return "未发现设置差异"
    if parts == {CAUSE_EDIT}:
        return "剪辑不同"
    if len(parts) == 1:
        return CAUSE_LABELS.get(next(iter(parts)), next(iter(parts)))
    return "多个原因"


def build_media_variant_index(
    project_root: Path,
    platform: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> dict[str, list[MediaVariant]]:
    index = work_unit_parse_utils.build_work_unit_index(project_root, progress_callback)
    variants_by_media: dict[str, list[MediaVariant]] = {}
    for record in index.audio_sources:
        media_id = work_unit_parse_utils.media_id_for_platform(record.media_ids_by_platform, platform)
        if not media_id:
            continue
        conversion, conversion_id = index.effective_conversion_pair(record.owner_id)
        variant = MediaVariant(
            media_id=media_id,
            owner_path=index.path_of(record.owner_id),
            conversion=conversion,
            edit=record.edit,
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
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if column == 1:
                return Qt.AlignmentFlag.AlignCenter
            if column == 4:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        if role == Qt.ItemDataRole.ToolTipRole:
            value = self.__rows[row][column]
            return value if len(value) > 40 else None
        return None

    def search_text(self, row: int) -> str:
        return self.__search_texts[row]


class DuplicateMediaSortProxyModel(QSortFilterProxyModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__segments: list[str] = []
        self.__cause_kind = ""

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

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if model is None:
            return True
        if self.__cause_kind:
            kind_value = model.data(
                model.index(source_row, 3),
                Qt.ItemDataRole.UserRole,
            )
            if self.__cause_kind not in str(kind_value or "").split("+"):
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
    analysis_progress = Signal(int, int)
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
            soundbank_info_utils.fill_duplicate_sizes(result, self.__xml_path)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
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
        variants_by_media = build_media_variant_index(
            project_root,
            result.platform,
            self.analysis_progress.emit,
        )
        causes: dict[str, DuplicateCause] = {}
        duration_cache: dict[str, Optional[float]] = {}
        for group in result.duplicate_groups:
            variants: list[MediaVariant] = []
            intervals: list[tuple[float, float]] = []
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
            cause = classify_media_variants(variants)
            if duration and len(intervals) >= 2:
                total_seconds = sum(end - start for start, end in intervals)
                union_seconds = _merge_interval_length(intervals)
                cause.original_duration_seconds = duration
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
        header = self.tblDuplicates.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tblDuplicates.setColumnWidth(3, 320)
        self.load_user_settings()
        self.setup_triggers()
        QTimer.singleShot(0, self.restore_last_file)

    def setup_triggers(self):
        self.btnChooseFile.clicked.connect(self.choose_file)
        self.btnReparse.clicked.connect(self.reparse_current_file)
        self.btnExportCsv.clicked.connect(self.export_csv)
        self.btnExportJson.clicked.connect(self.export_json)
        self.tblDuplicates.doubleClicked.connect(self.open_detail_for_index)
        self.tblDuplicates.customContextMenuRequested.connect(self.show_context_menu)
        self.iptFilter.textChanged.connect(self.schedule_filter)
        self.cbbCauseFilter.currentIndexChanged.connect(self.apply_filter)
        self.__filter_timer.timeout.connect(self.apply_filter)

    def load_user_settings(self):
        settings = user_config.get_window_settings(WINDOW_SETTINGS_KEY)
        self.__last_file = str(settings.get("last_file", ""))
        self.__analysis_root_hint = str(settings.get("analysis_project_root", ""))
        self.iptFilter.setText(str(settings.get("filter", "")))
        cause_filter = str(settings.get("cause_filter", ""))
        cause_index = self.cbbCauseFilter.findData(cause_filter)
        if cause_index >= 0:
            self.cbbCauseFilter.setCurrentIndex(cause_index)

    def save_user_settings(self):
        user_config.set_window_settings(WINDOW_SETTINGS_KEY, {
            "last_file": self.__last_file,
            "analysis_project_root": self.__analysis_root_hint,
            "filter": self.iptFilter.text(),
            "cause_filter": self.cbbCauseFilter.currentData() or "",
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
        self.lblFilterResult.setText("显示 0 / 0 行")
        self.lblStatus.setText(f"正在解析：{path.name} …")
        self.lblPlatform.setText("平台：读取中…")
        self.btnExportCsv.setEnabled(False)
        self.btnExportJson.setEnabled(False)
        self.set_buttons_enabled(False)

        self.__worker = SoundBankInfoWorker(str(path), self.__analysis_root_hint, self)
        self.__worker.total_ready.connect(self.on_total_ready)
        self.__worker.progress.connect(self.on_parse_progress)
        self.__worker.analysis_progress.connect(self.on_analysis_progress)
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

    def on_analysis_progress(self, processed: int, total: int):
        if total <= 0:
            self.close_progress_bar()
            return
        if (self.__progress_bar is None
                or self.__progress_bar.total_count != total
                or self.__progress_bar.windowTitle() != "分析重复原因"):
            self.close_progress_bar()
            self.__progress_bar = ProgressBar(total, "分析重复原因", None)
            self.__progress_bar.show()
            self.__progress_bar.raise_()
            self.__progress_bar.activateWindow()
        self.__progress_bar.update_progress(
            processed,
            f"已扫描 {processed} / {total} 个 WorkUnit",
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
            ])
            sort_values.append([
                group.original_path.casefold(),
                wem_count,
                event_count,
                cause_kind,
                extra_size,
            ])
            search_texts.append(group.original_path.casefold())

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
                category = _cause_category(cause)
                stats = category_stats.setdefault(category, {
                    "count": 0,
                    "extra_size": 0.0,
                    "no_overlap": 0,
                })
                stats["count"] += 1
                stats["extra_size"] += _group_extra_size(group, cause)
                if (cause is not None
                        and CAUSE_EDIT in cause.kind.split("+")
                        and cause.edit_total_seconds is not None):
                    edit_waste_seconds += cause.edit_waste_seconds or 0
                    if category == "剪辑不同" and (cause.edit_waste_seconds or 0) <= 1e-9:
                        stats["no_overlap"] += 1
            summary_lines.append("原因分类：")
            order = [
                "Conversion 不同",
                "剪辑不同",
                "Fade 不同",
                "循环设置不同",
                "渲染效果不同",
                "多个原因",
                "部分 wem 未匹配",
                "工程中未匹配",
                "未发现设置差异",
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
                if category == "剪辑不同" and stats["no_overlap"]:
                    line += f"（其中无重叠 {stats['no_overlap']} 个）"
                summary_lines.append(line)
            if edit_waste_seconds > 0:
                summary_lines.append(
                    f"剪辑重叠浪费时长：{wem_utils.format_duration(edit_waste_seconds)}"
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
        detail = MediaDuplicateDetailWindow(
            group,
            self.detail_search_dirs(),
            self.__result.platform,
            original_audio_path,
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
        self.__proxy.set_filter(self.iptFilter.text())
        total = self.__model.rowCount()
        self.lblFilterResult.setText(f"显示 {self.__proxy.rowCount()} / {total} 行")
        has_visible_rows = self.__proxy.rowCount() > 0
        self.btnExportCsv.setEnabled(has_visible_rows)
        self.btnExportJson.setEnabled(has_visible_rows)
        if total:
            self.save_user_settings()

    # 导出当前筛选结果（保持当前排序）
    def export_csv(self):
        row_count = self.__proxy.rowCount()
        if row_count == 0:
            Logger().warning("表格为空，暂无可导出的查重结果")
            return
        headers = [
            self.__model.headerData(column, Qt.Orientation.Horizontal)
            for column in range(self.__model.columnCount())
        ]
        rows = [headers]
        for row in range(row_count):
            rows.append([
                self.__proxy.data(self.__proxy.index(row, column))
                for column in range(self.__model.columnCount())
            ])

        default_name = f"MediaDuplicates_{datetime.now():%Y%m%d_%H%M%S}.csv"
        default_dir = Path(self.__last_file).parent if self.__last_file else Path.cwd()
        file_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出媒体查重结果",
            str(default_dir / default_name),
            "CSV 文件 (*.csv)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path += ".csv"
        if not io_utils.export_to_csv_path(rows, file_path):
            QMessageBox.critical(self, "媒体查重", f"导出失败：\n{file_path}")
            return
        self.lblStatus.setText(f"已导出 {row_count} 行到：{file_path}")
        Logger().info(f"媒体查重结果已导出：{row_count} 行 -> {file_path}")

    # 导出当前筛选结果，保留每个 wem 与 SoundBank 的对应关系
    def export_json(self):
        groups = self.current_groups()
        if not groups:
            Logger().warning("表格为空，暂无可导出的查重结果")
            return
        result = self.__result
        payload = {
            "source_file": self.iptSoundBanksInfoPath.text(),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "platform": result.platform,
            "soundbank_count": result.soundbank_count,
            "media_file_count": result.media_file_count,
            "unique_original_count": result.unique_original_count,
            "duplicate_original_count": result.duplicate_original_count,
            "duplicate_wem_count": result.duplicate_wem_count,
            "duplicate_total_size_bytes": result.duplicate_total_size_bytes,
            "duplicate_extra_size_bytes": result.duplicate_extra_size_bytes,
            "missing_duplicate_size_count": result.missing_duplicate_size_count,
            "exported_group_count": len(groups),
            "exported_wem_count": sum(len(group.files) for group in groups),
            "duplicates": [
                {
                    "original_path": group.original_path,
                    "wem_count": len(group.files),
                    "event_count": len(group.event_names),
                    "extra_size_bytes": int(round(_group_extra_size(
                        group, self.__causes.get(group.original_path.casefold())
                    ))),
                    "cause": self.__cause_payload(group),
                    "wems": [
                        {
                            "wem_id": file_info.wem_id,
                            "packed_path": file_info.packed_path,
                            "size_bytes": file_info.size_bytes,
                            "soundbanks": list(file_info.soundbank_names),
                        }
                        for file_info in group.files
                    ],
                }
                for group in groups
            ],
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
        return {
            "kind": cause.kind,
            "label": cause.label,
            "conversions": list(cause.conversions),
            "edits": list(cause.edits),
            "fades": list(cause.fades),
            "loops": list(cause.loops),
            "renders": list(cause.renders),
            "variant_count": cause.variant_count,
            "expected_media_count": cause.expected_media_count,
            "matched_media_count": cause.matched_media_count,
            "edit_total_seconds": cause.edit_total_seconds,
            "edit_waste_seconds": cause.edit_waste_seconds,
        }

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
