import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from libraries.utils.wwise import wem_utils


@dataclass
class DuplicateMediaFile:
    packed_path: str
    soundbank_names: list[str] = field(default_factory=list)
    size_bytes: int | None = None
    duration_seconds: float | None = None
    codec: str = ""
    sample_rate: int | None = None

    @property
    def wem_id(self) -> str:
        value = self.packed_path.replace("\\", "/")
        if value.casefold().startswith("media/"):
            value = value[len("media/"):]
        if value.casefold().endswith(".wem"):
            value = value[:-len(".wem")]
        return value


# 一个原始音频路径对应多个打包 wem 的查重结果
@dataclass
class DuplicateMediaGroup:
    original_path: str
    files: list[DuplicateMediaFile] = field(default_factory=list)

    @property
    def event_names(self) -> list[str]:
        names = []
        for file_info in self.files:
            for name in file_info.soundbank_names:
                if name and name not in names:
                    names.append(name)
        return names


@dataclass
class SoundBankInfoResult:
    platform: str = ""
    project_root: str = ""
    source_files_root: str = ""
    soundbanks_root: str = ""
    soundbank_count: int = 0
    media_file_count: int = 0
    unique_original_count: int = 0
    duplicate_total_size_bytes: int = 0
    duplicate_extra_size_bytes: int = 0
    missing_duplicate_size_count: int = 0
    duplicate_groups: list[DuplicateMediaGroup] = field(default_factory=list)

    @property
    def duplicate_original_count(self) -> int:
        return len(self.duplicate_groups)

    @property
    def duplicate_wem_count(self) -> int:
        return sum(len(group.files) for group in self.duplicate_groups)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(element: ET.Element, child_name: str) -> str:
    for child in element:
        if _local_name(child.tag) == child_name:
            return (child.text or "").strip()
    return ""


def _path_key(path: str) -> str:
    return path.replace("\\", "/").strip().casefold()


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


# 快速统计 SoundBank 起始节点，供解析进度条使用；不解析 XML 内容
def count_soundbanks(xml_path: str | Path) -> int:
    path = Path(xml_path)
    if not path.is_file():
        raise FileNotFoundError(f"文件不存在：{path}")
    count = 0
    prefix = b"<SoundBank"
    with path.open("rb") as file:
        for line in file:
            stripped = line.lstrip()
            if not stripped.startswith(prefix):
                continue
            next_char = stripped[len(prefix):len(prefix) + 1]
            if next_char in (b" ", b"\t", b">", b"/", b"\r", b"\n"):
                count += 1
    return count


# 只读 XML 根节点的 Platform，用于自动匹配 SoundBanksInfo.xml 与当前平台
def read_soundbanks_info_platform(xml_path: str | Path) -> str:
    try:
        for _event, element in ET.iterparse(str(xml_path), events=("start",)):
            if _local_name(element.tag) == "SoundBanksInfo":
                return element.get("Platform") or element.get("BasePlatform") or ""
            return ""
    except (ET.ParseError, OSError):
        return ""


def _resolve_soundbanks_root(xml_dir: Path, root_text: str) -> Path:
    if not root_text:
        return xml_dir
    root = Path(root_text)
    return root if root.is_absolute() else (xml_dir / root).resolve()


# 流式读取 SoundBanksInfo.xml，按原始音频路径汇总所有出现过的打包 wem（Wwise 工具）
def find_duplicate_media(
    xml_path: str | Path,
    progress_callback: Callable[[int], None] | None = None,
) -> SoundBankInfoResult:
    path = Path(xml_path)
    if not path.is_file():
        raise FileNotFoundError(f"文件不存在：{path}")

    result = SoundBankInfoResult()
    # 原始路径 key -> 展示用原始路径
    original_paths: dict[str, str] = {}
    # 原始路径 key -> 打包路径 key -> 打包文件信息
    packed_files: dict[str, dict[str, DuplicateMediaFile]] = {}
    project_root_text = ""
    source_files_root_text = ""
    soundbanks_root_text = ""

    try:
        context = ET.iterparse(str(path), events=("start", "end"))
        for event, element in context:
            local_name = _local_name(element.tag)
            if event == "start" and local_name == "SoundBanksInfo":
                result.platform = element.get("Platform") or element.get("BasePlatform") or ""
                continue
            if event == "end" and local_name == "SoundBanksRoot":
                soundbanks_root_text = (element.text or "").strip()
                continue
            if event == "end" and local_name == "ProjectRoot":
                project_root_text = (element.text or "").strip()
                continue
            if event == "end" and local_name == "SourceFilesRoot":
                source_files_root_text = (element.text or "").strip()
                continue
            if event != "end" or local_name != "SoundBank":
                continue

            result.soundbank_count += 1
            if progress_callback is not None and result.soundbank_count % 500 == 0:
                progress_callback(result.soundbank_count)
            soundbank_name = _child_text(element, "ShortName")
            media_element = None
            for child in element:
                if _local_name(child.tag) == "Media":
                    media_element = child
                    break
            if media_element is not None:
                for file_element in media_element:
                    if _local_name(file_element.tag) != "File":
                        continue
                    # 本地化样本在不同语言下天然对应不同 wem，不纳入同源查重
                    language = file_element.get("Language") or element.get("Language") or "SFX"
                    if language.casefold() != "sfx":
                        continue
                    original_path = _child_text(file_element, "ShortName")
                    packed_path = _child_text(file_element, "Path")
                    if not original_path or not packed_path:
                        continue
                    result.media_file_count += 1

                    original_key = _path_key(original_path)
                    packed_key = _path_key(packed_path)
                    original_paths.setdefault(original_key, original_path)
                    file_info = packed_files.setdefault(original_key, {}).setdefault(
                        packed_key, DuplicateMediaFile(packed_path=packed_path)
                    )
                    _append_unique(file_info.soundbank_names, soundbank_name)
            element.clear()
    except ET.ParseError as exc:
        raise ValueError(f"SoundBanksInfo.xml 解析失败：{exc}") from exc

    if progress_callback is not None:
        progress_callback(result.soundbank_count)
    result.unique_original_count = len(original_paths)
    for original_key, files_by_path in packed_files.items():
        if len(files_by_path) <= 1:
            continue
        result.duplicate_groups.append(
            DuplicateMediaGroup(
                original_path=original_paths[original_key],
                files=list(files_by_path.values()),
            )
        )
    result.duplicate_groups.sort(key=lambda group: group.original_path.casefold())
    soundbanks_root = _resolve_soundbanks_root(path.parent, soundbanks_root_text)
    result.soundbanks_root = str(soundbanks_root)
    if project_root_text:
        result.project_root = str(_resolve_soundbanks_root(path.parent, project_root_text))
    if source_files_root_text:
        result.source_files_root = str(_resolve_soundbanks_root(path.parent, source_files_root_text))
    return result


# 只读取重复组里的 wem 头和大小，用于统计重复总量、时长和额外包体体积
def fill_duplicate_sizes(
    result: SoundBankInfoResult,
    xml_path: str | Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> None:
    xml_dir = Path(xml_path).parent
    roots = [Path(result.soundbanks_root)] if result.soundbanks_root else []
    roots.append(xml_dir)
    info_cache: dict[str, wem_utils.WemInfo] = {}
    total = sum(len(group.files) for group in result.duplicate_groups)
    processed = 0
    if progress_callback is not None:
        progress_callback(0, total)
    total_size = 0
    extra_size = 0
    missing_count = 0
    for group in result.duplicate_groups:
        group_sizes = []
        for file_info in group.files:
            cache_key = _path_key(file_info.packed_path)
            if cache_key not in info_cache:
                info_cache[cache_key] = wem_utils.read_wem_info(
                    _resolve_wem_path(file_info.packed_path, roots)
                )
            info = info_cache[cache_key]
            file_info.size_bytes = info.size_bytes
            file_info.duration_seconds = info.duration_seconds
            file_info.codec = info.codec
            file_info.sample_rate = info.sample_rate
            processed += 1
            if progress_callback is not None:
                progress_callback(processed, total)
            if info.size_bytes is None:
                missing_count += 1
            else:
                group_sizes.append(info.size_bytes)
        if group_sizes:
            group_total = sum(group_sizes)
            total_size += group_total
            extra_size += max(0, group_total - min(group_sizes))
    result.duplicate_total_size_bytes = total_size
    result.duplicate_extra_size_bytes = extra_size
    result.missing_duplicate_size_count = missing_count


def _resolve_wem_path(packed_path: str, roots: list[Path]) -> Path:
    relative_path = Path(packed_path)
    for root in roots:
        candidate = root / relative_path
        if candidate.is_file():
            return candidate
    return roots[0] / relative_path if roots else relative_path


@dataclass
class SoundBankInfoMediaEntry:
    original_path: str
    wem_id: str
    packed_path: str
    cache_path: str
    language: str
    streaming: bool
    location: str


# SoundBanksInfo.xml 不记录 wem 字节大小，只记录打包路径/CachePath。
# 这里建立“原始音频路径 -> 打包 wem”索引，按需 stat 实际文件，供本地未生成 Bank 时补大小。
class SoundBankInfoSizeIndex:

    def __init__(self, xml_path: str | Path, project_root: str | Path = "", platform: str = ""):
        self.xml_path = Path(xml_path)
        self.xml_dir = self.xml_path.parent
        self.project_root = Path(project_root) if project_root else None
        self.platform = platform
        self.platform_name = ""
        self.xml_project_root: Path | None = None
        self.soundbanks_root = self.xml_dir
        self.source_files_root: Path | None = None
        self.entries_by_original: dict[str, list[SoundBankInfoMediaEntry]] = {}
        self.entry_count = 0
        self._size_cache: dict[str, int | None] = {}
        self._parse()

    def _parse(self):
        project_root_text = ""
        source_files_root_text = ""
        soundbanks_root_text = ""
        media_depth = 0
        seen_entries: set[tuple] = set()
        try:
            context = ET.iterparse(str(self.xml_path), events=("start", "end"))
            for event, element in context:
                local_name = _local_name(element.tag)
                if event == "start":
                    if local_name == "SoundBanksInfo":
                        self.platform_name = (
                            element.get("Platform") or element.get("BasePlatform") or ""
                        )
                    elif local_name == "Media":
                        media_depth += 1
                    continue

                if local_name == "Media":
                    media_depth = max(0, media_depth - 1)
                    element.clear()
                elif local_name == "ProjectRoot":
                    project_root_text = (element.text or "").strip()
                elif local_name == "SourceFilesRoot":
                    source_files_root_text = (element.text or "").strip()
                elif local_name == "SoundBanksRoot":
                    soundbanks_root_text = (element.text or "").strip()
                elif local_name == "File" and media_depth > 0:
                    original_path = _child_text(element, "ShortName")
                    packed_path = _child_text(element, "Path")
                    cache_path = _child_text(element, "CachePath")
                    if original_path and (packed_path or cache_path):
                        wem_id = element.get("Id") or ""
                        language = element.get("Language") or ""
                        location = element.get("Location") or ""
                        streaming = (
                            (element.get("Streaming") or "").casefold() == "true"
                            or location.casefold() == "streaming"
                        )
                        key = _path_key(original_path)
                        entry_key = (key, wem_id, packed_path, cache_path, streaming)
                        if entry_key not in seen_entries:
                            seen_entries.add(entry_key)
                            self.entries_by_original.setdefault(key, []).append(
                                SoundBankInfoMediaEntry(
                                    original_path=original_path,
                                    wem_id=wem_id,
                                    packed_path=packed_path,
                                    cache_path=cache_path,
                                    language=language,
                                    streaming=streaming,
                                    location=location,
                                )
                            )
                            self.entry_count += 1
                    element.clear()
                elif local_name == "SoundBank":
                    element.clear()
                if local_name == "SoundBanks":
                    break
        except ET.ParseError as exc:
            raise ValueError(f"SoundBanksInfo.xml 解析失败：{exc}") from exc

        if soundbanks_root_text:
            self.soundbanks_root = _resolve_soundbanks_root(self.xml_dir, soundbanks_root_text)
        if project_root_text:
            self.xml_project_root = _resolve_soundbanks_root(self.xml_dir, project_root_text)
        if source_files_root_text:
            self.source_files_root = _resolve_soundbanks_root(
                self.xml_dir, source_files_root_text
            )

    def lookup(self, original_paths: list[str], language: str = "") -> list[tuple[int, bool, str]]:
        keys: list[str] = []
        for original_path in original_paths:
            if not original_path:
                continue
            key = _path_key(original_path)
            keys.append(key)
            keys.append(key.lstrip("/"))
            # wav 绝对路径里通常包含 Originals\SFX，补一个相对路径候选
            for marker in ("/originals/sfx/", "/originals/", "originals/sfx/", "originals/"):
                marker_index = key.find(marker)
                if marker_index >= 0:
                    keys.append(key[marker_index + len(marker):])

        found: list[tuple[int, bool, str]] = []
        seen: set[str] = set()
        for key in dict.fromkeys(keys):
            for entry in self.entries_by_original.get(key, []):
                if language and entry.language and entry.language.casefold() not in (
                    "sfx", language.casefold()
                ):
                    continue
                resolved_path = self._resolve_entry_path(entry)
                if resolved_path is None:
                    continue
                resolved_key = str(resolved_path).casefold()
                if resolved_key in seen:
                    continue
                seen.add(resolved_key)
                size = self._size(resolved_path)
                if size is not None:
                    found.append((size, entry.streaming, str(resolved_path)))
        return found

    def _resolve_entry_path(self, entry: SoundBankInfoMediaEntry) -> Path | None:
        for candidate in self._candidate_paths(entry.packed_path, cache=False):
            if candidate.is_file():
                return candidate
        for candidate in self._candidate_paths(entry.cache_path, cache=True):
            if candidate.is_file():
                return candidate
        return None

    def _candidate_paths(self, value: str, cache: bool) -> list[Path]:
        if not value:
            return []
        path = Path(value)
        if path.is_absolute():
            return [path]

        candidates: list[Path] = []
        # 打包工程的 Android/iOS 额外音频常在 Package\ExtraSounds\<platform> 下
        if self.platform and self.xml_dir.name.casefold() == "sounds":
            candidates.append(self.xml_dir.parent / "ExtraSounds" / self.platform / path)
        candidates.extend([self.xml_dir / path, self.soundbanks_root / path])
        if self.platform:
            if self.project_root is not None:
                candidates.append(
                    self.project_root / "GeneratedSoundBanks" / self.platform / path
                )
            candidates.append(self.xml_dir.parent / "ExtraSounds" / self.platform / path)
        if cache:
            if self.source_files_root is not None:
                candidates.append(self.source_files_root / path)
            if self.project_root is not None and self.platform:
                candidates.append(
                    self.project_root / ".cache" / self.platform / path
                )
        if self.xml_project_root is not None:
            candidates.append(self.xml_project_root / path)
        return list(dict.fromkeys(candidates))

    def _size(self, path: Path) -> int | None:
        key = str(path).casefold()
        if key not in self._size_cache:
            try:
                self._size_cache[key] = path.stat().st_size
            except OSError:
                self._size_cache[key] = None
        return self._size_cache[key]
