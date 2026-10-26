import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


DEFAULT_CONVERSION_NAME = "Default Conversion Settings"
DEFAULT_EDIT_VALUE = -0.001
DEFAULT_FADE_VALUE = 0.0
HIERARCHY_FOLDERS = (
    "Actor-Mixer Hierarchy",
    "Interactive Music Hierarchy",
    "Master-Mixer Hierarchy",
    "Containers",
    "Busses",
)
OBJECT_TAGS = {
    "Sound",
    "ActorMixer",
    "PropertyContainer",
    "RandomSequenceContainer",
    "SwitchContainer",
    "BlendContainer",
    "Folder",
    "MusicSegment",
    "MusicTrack",
    "MusicPlaylistContainer",
    "MusicSwitchContainer",
    "MusicClip",
    "WorkUnit",
    "VirtualFolder",
}


@dataclass(frozen=True)
class SourceEditSettings:
    trim_begin: float = DEFAULT_EDIT_VALUE
    trim_end: float = DEFAULT_EDIT_VALUE
    loop_begin: float = DEFAULT_EDIT_VALUE
    loop_end: float = DEFAULT_EDIT_VALUE
    fade_in: float = DEFAULT_FADE_VALUE
    fade_out: float = DEFAULT_FADE_VALUE

    @property
    def is_default(self) -> bool:
        return (
            self.trim_begin == DEFAULT_EDIT_VALUE
            and self.trim_end == DEFAULT_EDIT_VALUE
            and self.loop_begin == DEFAULT_EDIT_VALUE
            and self.loop_end == DEFAULT_EDIT_VALUE
            and self.fade_in == DEFAULT_FADE_VALUE
            and self.fade_out == DEFAULT_FADE_VALUE
        )

    @property
    def trim_signature(self) -> str:
        return (
            f"trim {self.trim_begin:.3f}~{self.trim_end:.3f}s, "
            f"loop {self.loop_begin:.3f}~{self.loop_end:.3f}s"
        )

    @property
    def fade_signature(self) -> str:
        return f"fade in {self.fade_in:.3f}s, out {self.fade_out:.3f}s"

    def describe(self) -> str:
        if self.is_default:
            return "默认剪辑"
        return f"{self.trim_signature}, {self.fade_signature}"


@dataclass(frozen=True)
class AudioSourceRecord:
    owner_id: str
    media_ids_by_platform: dict[str, str]
    edit: SourceEditSettings


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _float_property(
    properties: dict[str, str],
    name: str,
    default: float = DEFAULT_EDIT_VALUE,
) -> float:
    try:
        return float(properties.get(name, default))
    except (TypeError, ValueError):
        return default


def _read_edit_settings(properties: dict[str, str]) -> SourceEditSettings:
    return SourceEditSettings(
        trim_begin=_float_property(properties, "TrimBegin"),
        trim_end=_float_property(properties, "TrimEnd"),
        loop_begin=_float_property(properties, "LoopBegin"),
        loop_end=_float_property(properties, "LoopEnd"),
        fade_in=_float_property(properties, "FadeInDuration", DEFAULT_FADE_VALUE),
        fade_out=_float_property(properties, "FadeOutDuration", DEFAULT_FADE_VALUE),
    )


def _render_signature(slot: ET.Element) -> str:
    effect = next(iter(slot.iter("Effect")), None)
    if effect is not None:
        properties = "&".join(sorted(
            f"{prop.get('Name')}={prop.get('Value')}"
            for prop in effect.iter("Property")
        ))
        return f"{effect.get('Name')}[{effect.get('PluginName')}]{{{properties}}}"
    object_ref = next(iter(slot.iter("ObjectRef")), None)
    return object_ref.get("Name") if object_ref is not None else "?"


# 多个平台共享同一份媒体时只写一条无 Platform 的 MediaID
def media_id_for_platform(media_ids: dict[str, str], platform: str) -> str:
    if platform and platform in media_ids:
        return media_ids[platform]
    if "" in media_ids:
        return media_ids[""]
    if len(media_ids) == 1:
        return next(iter(media_ids.values()))
    if platform:
        casefold_platform = platform.casefold()
        for name, value in media_ids.items():
            if name.casefold() == casefold_platform:
                return value
    return ""


class WorkUnitIndex:
    def __init__(
        self,
        parent_by_id: dict[str, Optional[str]],
        name_by_id: dict[str, str],
        conversion_by_id: dict[str, Optional[str]],
        conversion_id_by_id: dict[str, Optional[str]],
        override_conversion_by_id: dict[str, bool],
        loop_by_id: dict[str, bool],
        render_by_id: dict[str, list[str]],
        audio_sources: list[AudioSourceRecord],
    ):
        self.__parent_by_id = parent_by_id
        self.__name_by_id = name_by_id
        self.__conversion_by_id = conversion_by_id
        self.__conversion_id_by_id = conversion_id_by_id
        self.__override_conversion_by_id = override_conversion_by_id
        self.__loop_by_id = loop_by_id
        self.__render_by_id = render_by_id
        self.__conversion_cache: dict[str, tuple[str, str]] = {}
        self.__loop_cache: dict[str, bool] = {}
        self.__render_cache: dict[str, str] = {}
        self.audio_sources = audio_sources

    @property
    def object_count(self) -> int:
        return len(self.__parent_by_id)

    # 有效 Conversion：优先取最近的 OverrideConversion；没有覆盖时退回最近的 Conversion 引用
    def effective_conversion_pair(self, node_id: str) -> tuple[str, str]:
        if node_id in self.__conversion_cache:
            return self.__conversion_cache[node_id]
        current: Optional[str] = node_id
        visited: set[str] = set()
        fallback: Optional[tuple[str, str]] = None
        while current and current not in visited:
            visited.add(current)
            conversion = self.__conversion_by_id.get(current)
            if conversion and conversion != DEFAULT_CONVERSION_NAME and fallback is None:
                fallback = (conversion, self.__conversion_id_by_id.get(current) or "")
            if self.__override_conversion_by_id.get(current):
                resolved = (
                    conversion
                    if conversion and conversion != DEFAULT_CONVERSION_NAME
                    else DEFAULT_CONVERSION_NAME
                )
                pair = (resolved, self.__conversion_id_by_id.get(current) or "")
                self.__conversion_cache[node_id] = pair
                return pair
            current = self.__parent_by_id.get(current)
        if fallback is not None:
            self.__conversion_cache[node_id] = fallback
            return fallback
        pair = (DEFAULT_CONVERSION_NAME, "")
        self.__conversion_cache[node_id] = pair
        return pair

    def effective_conversion(self, node_id: str) -> str:
        return self.effective_conversion_pair(node_id)[0]

    # 循环开关会继承：取最近一个显式设置了 IsLoopingEnabled 的祖先
    def effective_looping(self, node_id: str) -> bool:
        if node_id in self.__loop_cache:
            return self.__loop_cache[node_id]
        current: Optional[str] = node_id
        visited: set[str] = set()
        while current and current not in visited:
            visited.add(current)
            if current in self.__loop_by_id:
                value = self.__loop_by_id[current]
                self.__loop_cache[node_id] = value
                return value
            current = self.__parent_by_id.get(current)
        self.__loop_cache[node_id] = False
        return False

    def path_of(self, node_id: str) -> str:
        parts: list[str] = []
        current: Optional[str] = node_id
        visited: set[str] = set()
        while current and current not in visited:
            visited.add(current)
            parts.append(self.__name_by_id.get(current) or "?")
            current = self.__parent_by_id.get(current)
        return "/".join(reversed(parts))

    # 渲染效果会继承，向上收集所有可影响该源媒体的 Render 效果
    def effective_render_signature(self, node_id: str) -> str:
        if node_id in self.__render_cache:
            return self.__render_cache[node_id]
        current: Optional[str] = node_id
        visited: set[str] = set()
        signatures: list[str] = []
        while current and current not in visited:
            visited.add(current)
            for signature in self.__render_by_id.get(current, []):
                if signature not in signatures:
                    signatures.append(signature)
            current = self.__parent_by_id.get(current)
        value = " | ".join(signatures)
        self.__render_cache[node_id] = value
        return value


class _WorkUnitParser:
    def __init__(self):
        self.parent_by_id: dict[str, Optional[str]] = {}
        self.name_by_id: dict[str, str] = {}
        self.conversion_by_id: dict[str, Optional[str]] = {}
        self.conversion_id_by_id: dict[str, Optional[str]] = {}
        self.override_conversion_by_id: dict[str, bool] = {}
        self.loop_by_id: dict[str, bool] = {}
        self.render_by_id: dict[str, list[str]] = {}
        self.audio_sources: list[AudioSourceRecord] = []

    def parse_file(self, file_path: Path) -> None:
        try:
            root = ET.parse(str(file_path)).getroot()
        except (ET.ParseError, OSError):
            return

        stack: list[str] = []

        def walk(element: ET.Element) -> None:
            local_name = _local_name(element.tag)
            pushed = local_name in OBJECT_TAGS and element.get("ID")
            if pushed:
                node_id = element.get("ID")
                # work unit 引用会重复出现同一 ID：优先保留带父级的引用关系
                new_parent = stack[-1] if stack else None
                if node_id not in self.parent_by_id:
                    self.parent_by_id[node_id] = new_parent
                elif self.parent_by_id[node_id] is None and new_parent is not None:
                    self.parent_by_id[node_id] = new_parent
                self.name_by_id.setdefault(node_id, element.get("Name") or "")

                reference_list = None
                for child in element:
                    if _local_name(child.tag) == "ReferenceList":
                        reference_list = child
                        break
                if reference_list is not None:
                    for reference in reference_list:
                        if _local_name(reference.tag) != "Reference":
                            continue
                        if reference.get("Name") != "Conversion":
                            continue
                        for object_ref in reference:
                            target_name = _local_name(object_ref.tag)
                            if target_name == "ObjectRef":
                                self.conversion_by_id[node_id] = object_ref.get("Name")
                                self.conversion_id_by_id[node_id] = object_ref.get("ID")
                            elif target_name == "Custom":
                                custom = next(
                                    (
                                        item for item in object_ref.iter()
                                        if _local_name(item.tag) == "Conversion"
                                    ),
                                    None,
                                )
                                if custom is not None:
                                    self.conversion_by_id[node_id] = custom.get("Name")
                                    self.conversion_id_by_id[node_id] = custom.get("ID")
                for property_list in element.findall("PropertyList"):
                    for prop in property_list:
                        if _local_name(prop.tag) != "Property":
                            continue
                        if prop.get("Name") == "OverrideConversion":
                            self.override_conversion_by_id[node_id] = (
                                (prop.get("Value") or "").casefold() == "true"
                            )
                        elif prop.get("Name") == "IsLoopingEnabled":
                            self.loop_by_id[node_id] = (
                                (prop.get("Value") or "").casefold() == "true"
                            )

                signatures: list[str] = []
                for object_lists in element.findall("ObjectLists"):
                    for object_list in object_lists.findall("ObjectList"):
                        if object_list.get("Name") != "Effects":
                            continue
                        for slot in object_list.iter("EffectSlot"):
                            render_values = [
                                prop.get("Value")
                                for prop in slot.iter("Property")
                                if prop.get("Name") == "Render"
                            ]
                            if not render_values or render_values[0] != "True":
                                continue
                            signatures.append(_render_signature(slot))
                if signatures:
                    self.render_by_id[node_id] = signatures
                stack.append(node_id)

            if local_name == "AudioFileSource" and stack:
                media_ids: dict[str, str] = {}
                has_audio = False
                properties: dict[str, str] = {}
                for child in element:
                    child_name = _local_name(child.tag)
                    if child_name == "AudioFile" and (child.text or "").strip():
                        has_audio = True
                    elif child_name == "MediaIDList":
                        for media_id in child:
                            if _local_name(media_id.tag) != "MediaID":
                                continue
                            value = media_id.get("ID")
                            if value:
                                media_ids[media_id.get("Platform") or ""] = value
                    elif child_name == "PropertyList":
                        for prop in child:
                            if _local_name(prop.tag) != "Property":
                                continue
                            name = prop.get("Name") or ""
                            if prop.get("Value") is not None:
                                properties[name] = prop.get("Value")
                if has_audio and media_ids:
                    self.audio_sources.append(
                        AudioSourceRecord(
                            owner_id=stack[-1],
                            media_ids_by_platform=media_ids,
                            edit=_read_edit_settings(properties),
                        )
                    )

            for child in element:
                walk(child)
            if pushed:
                stack.pop()

        walk(root)


def build_work_unit_index(
    project_root: str | Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> WorkUnitIndex:
    root_path = Path(project_root)
    files: list[Path] = []
    for folder_name in HIERARCHY_FOLDERS:
        folder = root_path / folder_name
        if folder.is_dir():
            files.extend(folder.rglob("*.wwu"))

    parser = _WorkUnitParser()
    total = len(files)
    if progress_callback is not None:
        progress_callback(0, total)
    for index, file_path in enumerate(files, start=1):
        parser.parse_file(file_path)
        if progress_callback is not None and index % 100 == 0:
            progress_callback(index, total)
    if progress_callback is not None:
        progress_callback(total, total)

    return WorkUnitIndex(
        parent_by_id=parser.parent_by_id,
        name_by_id=parser.name_by_id,
        conversion_by_id=parser.conversion_by_id,
        conversion_id_by_id=parser.conversion_id_by_id,
        override_conversion_by_id=parser.override_conversion_by_id,
        loop_by_id=parser.loop_by_id,
        render_by_id=parser.render_by_id,
        audio_sources=parser.audio_sources,
    )
