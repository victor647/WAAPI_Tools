from data.design_info import DesignInfo
from data import project_conventions
from libraries.table_view.table_cell_data import CellSeverity
from libraries.table_view.table_row_data import TableRowData
from libraries.utils import path_utils
from libraries.utils import vcs_utils
from libraries.utils.wwise import common_utils, audio_source_utils, localization_utils, event_utils, soundbank_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType
from table.wwise_table_headers import *

# Wwise EventAction 的 ActionType 数值 → 展示名（已取官方显示名路径末尾的名称）
ACTION_TYPE_NAMES = {
    1: "Play",
    2: "Stop",
    3: "Stop All",
    4: "Mute",
    5: "UnMute",
    6: "UnMute All",
    7: "Pause",
    8: "Pause All",
    9: "Resume",
    10: "Resume All",
    11: "Set Bus Volume",
    12: "Set Voice Volume",
    13: "Set Voice Pitch",
    14: "Reset Bus Volume",
    15: "Reset Bus Volume All",
    16: "Reset Voice Volume",
    17: "Reset Voice Volume All",
    18: "Reset Pitch",
    19: "Reset Pitch All",
    20: "Enable State",
    21: "Disable State",
    22: "Set State",
    23: "Set Switch",
    26: "Set LPF",
    27: "Reset LPF",
    28: "Reset LPF All",
    29: "Set HPF",
    30: "Reset HPF",
    31: "Reset HPF All",
    34: "Break",
    35: "Trigger",
    36: "Seek",
    37: "Seek All",
    38: "Set Game Parameter",
    39: "Reset Game Parameter",
    40: "Release Envelope",
    41: "Post Event",
    42: "Reset Playlist",
    43: "Set Effect",
    44: "Reset Set Effect",
    45: "Reset Set Effect All",
    50: "Set - Bypass Effect Slot",
    51: "Reset - Bypass Effect Slot",
    52: "Reset - Bypass Effect Slot - All",
    53: "Set - Bypass All Effects",
    54: "Reset - Bypass All Effects",
    55: "Reset - Bypass All Effects - All",
    56: "Reset - All Effect Bypasses",
    57: "Reset - All Effect Bypasses - All",
}


# 表格中每行的数据封装
class WwiseTableRowData(TableRowData):

    def __init__(self, row: int, max_column: int, wwise_object: WwiseObject):
        super().__init__(row, max_column)
        # 对应的Wwise对象
        self.wwise_object = wwise_object
        self._design_info: DesignInfo | None = None

    def replace_wwise_object(self, obj: WwiseObject):
        # 重命名等操作后替换对象引用，并在需要时重新读取 DesignInfo。
        self.wwise_object = obj
        self._design_info = None

    @property
    def design_info(self) -> DesignInfo:
        if self._design_info is None:
            self._design_info = DesignInfo(self.wwise_object)
        return self._design_info

    @property
    def id(self) -> str:
        return self.wwise_object.id

    @property
    def name(self) -> str:
        return self.wwise_object.name

    @property
    def type(self) -> WwiseObjectType:
        return self.wwise_object.type

    @property
    def path(self) -> str:
        return self.wwise_object.path

    @property
    def notes(self) -> str:
        return waapi_utils.get_object_property(self.wwise_object, "notes")

    # 当前对象被多少个对象直接引用（WAAPI: referencesTo）
    @property
    def reference_count(self) -> int:
        return len(waapi_utils.get_object_references(self.wwise_object))

    # 缩写路径（实现统一放在 libraries/utils/path_utils.compact_path，窗口显示不要另写一套）
    @staticmethod
    def get_path_compact_text(path: str) -> str:
        return path_utils.compact_path(path)

    def set_path_cell(self, column: int, path: str):
        self.set_cell_value(column, self.get_path_text(path), path)

    # 按「路径显示简写」设置返回路径显示文本（关闭时显示完整路径）
    @staticmethod
    def get_path_text(path: str) -> str:
        return path_utils.get_display_path(path)

    # 筛选时决定需要筛选的条目
    def get_searched_properties(self) -> list[str]:
        # 关键字筛选：对名称与路径做子串匹配（见 TableFacade.filter_results）
        n = self.name or ""
        p = self.path or ""
        return [str(n), str(p)]

    # 读取所有显示模式共有的信息；read_optional=False 时为极速模式，
    # 只填充基础属性与启用状态，避免逐个对象查询备注、引用计数等
    # properties 传批量预取的列属性（waapi_utils.get_objects_properties），未传则逐行查询
    def read_common_data(self, inclusion_cache: dict[str, bool] | None = None, read_optional: bool = True,
                         properties: dict = None, property_values_by_id: dict = None):
        self[CHECK_BOX_COL] = True
        self[NAME_COL] = self.name
        self[TYPE_COL] = self.type.name
        self.set_path_cell(PATH_COL, self.path)
        # 启用状态始终读取，默认轻量模式也允许直接勾选启用
        can_set_inclusion = common_utils.can_set_object_inclusion(self.wwise_object)
        if not can_set_inclusion:
            # Wwise 不支持单独启用的对象（如 EventAction、AudioSource、State 等）留空置灰
            self.cells[ENABLE_COL].display_value = ""
            self.cells[ENABLE_COL].is_enabled = False
            self.set_cell_severity(ENABLE_COL, CellSeverity.Ignored)
        else:
            is_included = common_utils.is_object_included(
                self.wwise_object,
                inclusion_cache=inclusion_cache,
                property_values_by_id=property_values_by_id,
            )
            self[ENABLE_COL] = is_included
        if not read_optional:
            return
        self[DESCRIPTION_COL] = self.notes if properties is None else properties.get('notes')
        self[REFERENCE_COUNT_COL] = self.reference_count
        self.apply_inclusion_text_style()

    def apply_inclusion_text_style(self):
        if self[ENABLE_COL] or not self.cells[ENABLE_COL].is_enabled:
            return
        for column in range(NAME_COL, len(self.cells)):
            self.set_cell_severity(column, CellSeverity.Ignored)

    def read_design_info(self, properties: dict = None):
        # 用批量预取的属性构造 DesignInfo，避免逐行逐属性查询
        self._design_info = DesignInfo(self.wwise_object, properties)
        self.read_volume()
        self.read_output_bus()
        self.read_attenuation()
        self.read_conversion()
        self.read_playback_limit()
        self.read_wwise_original_path(properties)
        self.apply_inclusion_text_style()

    # 属性在对象上不存在时统一显示「不适用」并置灰
    def set_not_applicable(self, column: int):
        self[column] = "不适用"
        self.set_cell_severity(column, CellSeverity.Ignored)

    # 读取音量
    def read_volume(self):
        if not self.design_info.has_property("Volume"):
            self.set_not_applicable(VOLUME_COL)
            return
        self[VOLUME_COL] = self.design_info.volume

    def read_integration_info(self, event_bank_map: dict | None = None, properties: dict = None):
        self.read_event_action_types()
        self.read_wwise_target_info()
        self.read_wwise_localization()
        self.read_soundbank(event_bank_map)
        self.read_vcs_author(properties)
        self.apply_inclusion_text_style()

    # 读取对象所在 WorkUnit 文件的版本控制作者（未配置/不可用时显示不适用）
    def read_vcs_author(self, properties: dict = None):
        if not vcs_utils.is_available():
            self.set_not_applicable(VCS_AUTHOR_COL)
            return
        workunit_path = properties.get('workUnit.filePath') if properties is not None \
            else waapi_utils.get_object_property(self.wwise_object, 'workUnit.filePath')
        if not workunit_path:
            self.set_not_applicable(VCS_AUTHOR_COL)
            return
        author = vcs_utils.get_file_author(workunit_path)
        if not author:
            self[VCS_AUTHOR_COL] = "无记录"
            self.set_cell_severity(VCS_AUTHOR_COL, CellSeverity.Warning)
            return
        self[VCS_AUTHOR_COL] = author

    # 读取 Event 下所有 Action 的类型（集成视图「动作」列）；非 Event 显示不适用
    def read_event_action_types(self):
        if self.type != WwiseObjectType.Event:
            self[ACTION_COL] = "不适用"
            return
        action_names = []
        actions = [
            action for action in waapi_utils.get_child_objects(self.wwise_object)
            if action.type == WwiseObjectType.EventAction
        ]
        action_properties = waapi_utils.get_objects_properties(actions, ['ActionType'])
        for action in actions:
            action_type = action_properties.get(action.id, {}).get('ActionType')
            action_names.append(str(ACTION_TYPE_NAMES.get(action_type, action_type)))
        self[ACTION_COL] = "/".join(action_names)

    # 读取总线
    def read_output_bus(self):
        if not self.design_info.has_property("OutputBus"):
            self.set_not_applicable(OUTPUT_BUS_COL)
            return
        bus = self.design_info.output_bus
        if bus and bus.name != "Master Audio Bus":
            self[OUTPUT_BUS_COL] = bus.name
        else:
            self[OUTPUT_BUS_COL] = "默认"

    # 读取衰减
    def read_attenuation(self):
        if not self.design_info.has_property("Attenuation"):
            self.set_not_applicable(ATTENUATION_COL)
            return
        setting = self.design_info.attenuation
        if setting and setting.is_valid:
            self[ATTENUATION_COL] = setting.name
        else:
            # 没有衰减曲线即 2D 声音
            self[ATTENUATION_COL] = "2D"

    # 读取音质
    def read_conversion(self):
        if not self.design_info.has_property("Conversion"):
            self.set_not_applicable(CONVERSION_COL)
            return
        setting = self.design_info.conversion_setting
        if setting:
            self[CONVERSION_COL] = setting.name
        else:
            self[CONVERSION_COL] = "默认"

    # 读取最大发声数
    def read_playback_limit(self):
        if not self.design_info.has_property("MaxSoundPerInstance"):
            self.set_not_applicable(PLAYBACK_LIMIT_COL)
            return
        limit = self.design_info.playback_limit
        if not limit:
            self[PLAYBACK_LIMIT_COL] = "不限"
        else:
            self[PLAYBACK_LIMIT_COL] = limit

    # 读取播放对象的类型和路径
    def read_wwise_target_info(self):
        if self.type != WwiseObjectType.Event:
            for column in (TARGET_TYPE_COL, TARGET_PATH_COL):
                self[column] = "不适用"
                self.set_cell_severity(column, CellSeverity.Ignored)
            return
        targets = event_utils.get_event_targets(self.wwise_object)
        target_count = len(targets)
        if target_count == 0:
            for column in range(TARGET_TYPE_COL, len(self.cells)):
                self[column] = "空事件"
                self.set_cell_severity(column, CellSeverity.Warning)
        elif target_count > 1:
            self[TARGET_TYPE_COL] = self[TARGET_PATH_COL] = f"共{target_count}个对象"
        else:
            target = targets[0]
            if target and target.is_valid:
                self[TARGET_TYPE_COL] = target.type.name
                self.set_path_cell(TARGET_PATH_COL, target.path)
            else:
                self[TARGET_TYPE_COL] = "对象已失效"
                self.set_cell_severity(TARGET_TYPE_COL, CellSeverity.Warning)

    # 读取对象自身的源文件路径（不递归子对象，取不到时显示不适用）
    def read_wwise_original_path(self, properties: dict = None):
        if self.type not in (WwiseObjectType.Sound, WwiseObjectType.AudioSource, WwiseObjectType.MusicTrack):
            self.set_not_applicable(ORIGINAL_PATH_COL)
            return
        source_path = properties.get('originalFilePath') if properties is not None \
            else audio_source_utils.get_source_absolute_path(self.wwise_object)
        if not source_path:
            self.set_not_applicable(ORIGINAL_PATH_COL)
            return
        self[ORIGINAL_PATH_COL] = source_path

    # 读取事件是否包含本地化内容
    def read_wwise_localization(self):
        is_localized = localization_utils.is_localized(self.wwise_object)
        self[LOCALIZATION_COL] = "是" if is_localized else "否"

    # 读取所属 SoundBank（集成视图）；拆分 Event/Media 的工程不显示 _Event / _Media 后缀
    def read_soundbank(self, event_bank_map: dict | None):
        if self.type != WwiseObjectType.Event:
            self[SOUNDBANK_COL] = "不适用"
            self.set_cell_severity(SOUNDBANK_COL, CellSeverity.Ignored)
            return
        bank_names = (event_bank_map or {}).get(self.id, [])
        if not bank_names:
            self[SOUNDBANK_COL] = "未包含"
            self.set_cell_severity(SOUNDBANK_COL, CellSeverity.Warning)
            return
        if project_conventions.split_bank_event_media():
            bank_names = list(dict.fromkeys(soundbank_utils.get_bank_display_name(name) for name in bank_names))
        self[SOUNDBANK_COL] = "/".join(bank_names)
