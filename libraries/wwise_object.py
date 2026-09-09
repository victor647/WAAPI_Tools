from enum import Enum


class WwiseObjectType(Enum):
    Folder = "Folder"
    WorkUnit = "WorkUnit"
    ActorMixer = "ActorMixer"
    Sound = "Sound"
    AudioSource = "AudioFileSource"
    ExternalSource = "ExternalSource"
    Event = "Event"
    EventAction = "Action"
    SoundBank = "SoundBank"
    RandomContainer = "RandomSequenceContainer"
    BlendContainer = "BlendContainer"
    SwitchContainer = "SwitchContainer"
    MusicPlaylistContainer = "MusicPlaylistContainer"
    MusicSwitchContainer = "MusicSwitchContainer"
    MusicSegment = "MusicSegment"
    MusicTrack = "MusicTrack"
    RTPC = "GameParameter"
    SwitchGroup = "SwitchGroup"
    SwitchValue = "Switch"
    StateGroup = "StateGroup"
    StateValue = "State"
    SourcePlugin = "SourcePlugin"
    Bus = "Bus"
    AuxBus = "AuxBus"
    Effect = "Effect"
    EffectSlot = "EffectSlot"
    Conversion = "Conversion"
    Attenuation = "Attenuation"
    AudioDevice = "AudioDevice"
    # 其余 Wwise 对象类型（左侧为显示名，右侧为 Wwise 实际 type）
    AcousticTexture = "AcousticTexture"
    ActionException = "ActionException"
    ArgumentsSlot = "ArgumentsSlot"
    BlendTrack = "BlendTrack"
    ControlSurfaceBinding = "ControlSurfaceBinding"
    ControlSurfaceBindingGroup = "ControlSurfaceBindingGroup"
    ControlSurfaceSession = "ControlSurfaceSession"
    Curve = "Curve"
    CustomState = "CustomState"
    DialogueEvent = "DialogueEvent"
    EntryPathSlot = "EntryPathSlot"
    ExternalSourceFile = "ExternalSourceFile"
    Language = "Language"
    Marker = "Marker"
    MediaPoolDatabase = "MediaPoolDatabase"
    MediaPoolDatabasePath = "MediaPoolDatabasePath"
    MediaPoolFilter = "MediaPoolFilter"
    MediaPoolQuery = "MediaPoolQuery"
    Metadata = "Metadata"
    MetadataSlot = "MetadataSlot"
    MidiFileSource = "MidiFileSource"
    MidiParameter = "MidiParameter"
    MixingSession = "MixingSession"
    Modifier = "Modifier"
    ModulatorEnvelope = "ModulatorEnvelope"
    ModulatorLfo = "ModulatorLfo"
    ModulatorTime = "ModulatorTime"
    MultiSwitchEntry = "MultiSwitchEntry"
    MusicArgumentsSlot = "MusicArgumentsSlot"
    MusicClip = "MusicClip"
    MusicClipMidi = "MusicClipMidi"
    MusicCue = "MusicCue"
    MusicEventCue = "MusicEventCue"
    MusicFade = "MusicFade"
    MusicPlaylistItem = "MusicPlaylistItem"
    MusicStinger = "MusicStinger"
    MusicTrackSequence = "MusicTrackSequence"
    MusicTransition = "MusicTransition"
    ObjectSettingAssoc = "ObjectSettingAssoc"
    Panner = "Panner"
    Path2D = "Path2D"
    Platform = "Platform"
    PlaylistSlot = "PlaylistSlot"
    PluginDataSource = "PluginDataSource"
    Position = "Position"
    Project = "Project"
    PropertyContainer = "PropertyContainer"
    Query = "Query"
    SearchCriteria = "SearchCriteria"
    SidechainMix = "SidechainMix"
    SoundCaster = "SoundcasterSession"
    StateGroupInfo = "StateGroupInfo"
    Trigger = "Trigger"
    UserProjectSettings = "UserProjectSettings"


# Wwise对象封装
class WwiseObject(object):
    def __init__(self, wwise_dict: dict = None):
        self.wwise_dict = wwise_dict

    @staticmethod
    def dict_from_id(object_id: str) -> dict:
        """由 GUID 拉取 WAAPI 返回的对象字典（JSON 层入参）。"""
        from libraries.waapi_client import WAAPIClient

        raw = WAAPIClient().get_full_info_from_obj_id(object_id)
        if isinstance(raw, dict) and raw.get("id"):
            return raw
        raise ValueError(f"Object not found for id: {object_id!r}")

    @classmethod
    def from_id(cls, object_id: str) -> "WwiseObject":
        """由 GUID 构造封装对象（内部使用 ``dict_from_id``）。"""
        return cls(cls.dict_from_id(object_id))

    def __bool__(self):
        return bool(self.wwise_dict)

    @property
    def is_valid(self) -> bool:
        return self.id != "" and self.name != ""

    @property
    def is_designable(self) -> bool:
        if not "-Mixer" in self.path:
            return False
        return self.type != WwiseObjectType.Folder and self.type != WwiseObjectType.WorkUnit

    @property
    def is_container(self) -> bool:
        return "Container" in self.type.value

    @property
    def id(self) -> str:
        return self.wwise_dict.get("id", "")

    @property
    def type(self) -> WwiseObjectType:
        type_str = self.wwise_dict.get("type", "")
        return WwiseObjectType(type_str)

    @property
    def name(self) -> str:
        return self.wwise_dict.get("name", "")

    @property
    def path(self) -> str:
        return self.wwise_dict.get("path", "")

    @property
    def parent(self):
        from libraries.utils.wwise import waapi_utils

        return waapi_utils.get_parent_object(self)

    @property
    def children(self) -> list:
        from libraries.utils.wwise import waapi_utils

        return waapi_utils.get_child_objects(self)
