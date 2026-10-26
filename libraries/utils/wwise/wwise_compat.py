# Wwise 版本兼容：2025 起物理根目录改为 \Containers / \Busses，
# 2026 起 ActorMixer 对象类型改名为 PropertyContainer。
# 这里集中提供版本判断与名称映射，业务代码不要各自硬编码旧根目录。

from libraries.wwise_object import WwiseObjectType

LAYOUT_CHANGE_YEAR = 2025
PROPERTY_CONTAINER_YEAR = 2026

CONTAINERS_FOLDER = "Containers"
BUSSES_FOLDER = "Busses"
LEGACY_AUDIO_FOLDER = "Actor-Mixer Hierarchy"
LEGACY_MUSIC_FOLDER = "Interactive Music Hierarchy"
LEGACY_BUS_FOLDER = "Master-Mixer Hierarchy"

# 工程目录 / Work Unit 里可能出现的层级根名称（新旧版本）
HIERARCHY_FOLDER_NAMES = (
    LEGACY_AUDIO_FOLDER,
    LEGACY_MUSIC_FOLDER,
    LEGACY_BUS_FOLDER,
    CONTAINERS_FOLDER,
    BUSSES_FOLDER,
)

_MUSIC_TYPES = {
    WwiseObjectType.MusicSegment,
    WwiseObjectType.MusicTrack,
    WwiseObjectType.MusicPlaylistContainer,
    WwiseObjectType.MusicSwitchContainer,
    WwiseObjectType.MusicClip,
    WwiseObjectType.MusicClipMidi,
    WwiseObjectType.MusicPlaylistItem,
    WwiseObjectType.MusicStinger,
    WwiseObjectType.MusicTrackSequence,
}


def authoring_year() -> int:
    # 延迟导入：project_utils -> waapi_utils -> waapi_client，避免循环依赖
    try:
        from libraries.utils.wwise import project_utils

        return int(project_utils.get_project_version() or 0)
    except Exception:
        return 0


def uses_2025_layout(year: int = None) -> bool:
    value = authoring_year() if year is None else int(year)
    return value >= LAYOUT_CHANGE_YEAR


def uses_property_container(year: int = None) -> bool:
    value = authoring_year() if year is None else int(year)
    return value >= PROPERTY_CONTAINER_YEAR


def containers_root(year: int = None) -> str:
    folder = CONTAINERS_FOLDER if uses_2025_layout(year) else LEGACY_AUDIO_FOLDER
    return "\\" + folder


def music_root(year: int = None) -> str:
    folder = CONTAINERS_FOLDER if uses_2025_layout(year) else LEGACY_MUSIC_FOLDER
    return "\\" + folder


def busses_root(year: int = None) -> str:
    folder = BUSSES_FOLDER if uses_2025_layout(year) else LEGACY_BUS_FOLDER
    return "\\" + folder


def default_audio_work_unit(year: int = None) -> str:
    return containers_root(year) + "\\Default Work Unit"


def default_music_work_unit(year: int = None) -> str:
    return music_root(year) + "\\Default Work Unit"


def default_bus_path(year: int = None) -> str:
    if uses_2025_layout(year):
        return "\\Busses\\Default Work Unit\\Main Audio Bus"
    return "\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus"


def is_containers_path(path: str) -> bool:
    # 2025+ 音频与音乐都在 \Containers 下；旧版本按两个 Hierarchy 根判断
    if not path:
        return False
    prefixes = (
        "\\" + CONTAINERS_FOLDER,
        "\\" + LEGACY_AUDIO_FOLDER,
        "\\" + LEGACY_MUSIC_FOLDER,
    )
    return any(path.startswith(prefix) for prefix in prefixes)


def is_hierarchy_root_name(name: str) -> bool:
    normalized = (name or "").strip().lower()
    return any(normalized == folder.lower() for folder in HIERARCHY_FOLDER_NAMES)


def is_music_object(obj) -> bool:
    if obj is None:
        return False
    try:
        if obj.type in _MUSIC_TYPES:
            return True
    except Exception:
        pass
    path = getattr(obj, "path", "") or ""
    return path.startswith("\\" + LEGACY_MUSIC_FOLDER)


def property_container_type_names() -> tuple:
    # 查询时同时接受新旧类型名，避免升级/降级工程时漏对象
    return ("ActorMixer", "PropertyContainer")


def is_property_container_type(type_name: str) -> bool:
    return (type_name or "") in property_container_type_names()


def is_property_container(obj) -> bool:
    if obj is None:
        return False
    try:
        return is_property_container_type(obj.type.value)
    except Exception:
        return False


def default_property_container_type(year: int = None) -> str:
    return "PropertyContainer" if uses_property_container(year) else "ActorMixer"


def resolve_wrapper_type(type_name: str, year: int = None) -> str:
    # 用户/AI 仍可用 ActorMixer 这个旧名字；按当前工程版本映射到实际可创建的类型
    if type_name == "ActorMixer":
        return default_property_container_type(year)
    if type_name == "PropertyContainer" and not uses_property_container(year):
        return "ActorMixer"
    return type_name
