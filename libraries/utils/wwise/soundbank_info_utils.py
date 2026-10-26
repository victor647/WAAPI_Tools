import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class DuplicateMediaFile:
    packed_path: str
    soundbank_names: list[str] = field(default_factory=list)
    size_bytes: int | None = None

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


# 只对重复组里的 wem 做 stat，用于统计重复总量和额外包体体积
def fill_duplicate_sizes(result: SoundBankInfoResult, xml_path: str | Path) -> None:
    xml_dir = Path(xml_path).parent
    roots = [Path(result.soundbanks_root)] if result.soundbanks_root else []
    roots.append(xml_dir)
    size_cache: dict[str, int | None] = {}
    total_size = 0
    extra_size = 0
    missing_count = 0
    for group in result.duplicate_groups:
        group_sizes = []
        for file_info in group.files:
            cache_key = _path_key(file_info.packed_path)
            if cache_key not in size_cache:
                size_cache[cache_key] = _read_file_size(file_info.packed_path, roots)
            size = size_cache[cache_key]
            file_info.size_bytes = size
            if size is None:
                missing_count += 1
            else:
                group_sizes.append(size)
        if group_sizes:
            group_total = sum(group_sizes)
            total_size += group_total
            extra_size += max(0, group_total - min(group_sizes))
    result.duplicate_total_size_bytes = total_size
    result.duplicate_extra_size_bytes = extra_size
    result.missing_duplicate_size_count = missing_count


def _read_file_size(packed_path: str, roots: list[Path]) -> int | None:
    relative_path = Path(packed_path)
    for root in roots:
        try:
            return (root / relative_path).stat().st_size
        except OSError:
            continue
    return None
