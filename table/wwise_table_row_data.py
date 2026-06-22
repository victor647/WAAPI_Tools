from data.design_info import DesignInfo
from libraries.table_view.table_cell_data import CellSeverity
from libraries.table_view.table_row_data import TableRowData
from libraries.utils.wwise import common_utils, audio_source_utils, localization_utils, event_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType
from table.wwise_table_headers import *


PATH_DISPLAY_LIMIT = 64


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

    @staticmethod
    def get_path_display_text(path: str) -> str:
        if not isinstance(path, str) or len(path) <= PATH_DISPLAY_LIMIT:
            return path
        separator = "\\" if "\\" in path else "/"
        parts = []
        for part in path.split(separator):
            suffix = part.rsplit("_", 1)[-1]
            parts.append(f"...{suffix}" if suffix != part else part)
        return separator.join(parts)

    def set_path_cell(self, column: int, path: str):
        self.set_cell_value(column, self.get_path_display_text(path), path)

    # 筛选时决定需要筛选的条目
    def get_searched_properties(self) -> list[str]:
        # 关键字筛选：对名称与路径做子串匹配（见 TableFacade.filter_results）
        n = self.name or ""
        p = self.path or ""
        return [str(n), str(p)]

    # 读取所有显示模式共有的信息
    def read_common_data(self, inclusion_cache: dict[str, bool] | None = None):
        self[CHECK_BOX_COL] = True
        can_set_inclusion = common_utils.can_set_object_inclusion(self.wwise_object)
        is_included = common_utils.is_object_included(self.wwise_object, inclusion_cache=inclusion_cache)
        self[ENABLE_COL] = is_included
        if not can_set_inclusion:
            self.cells[ENABLE_COL].is_enabled = False
            self.set_cell_severity(ENABLE_COL, CellSeverity.Ignored)
        self[NAME_COL] = self.name
        self[TYPE_COL] = self.type.name
        self.set_path_cell(PATH_COL, self.path)
        self[DESCRIPTION_COL] = self.notes
        self.apply_inclusion_text_style()

    def apply_inclusion_text_style(self):
        if self[ENABLE_COL] or not self.cells[ENABLE_COL].is_enabled:
            return
        for column in range(NAME_COL, len(self.cells)):
            self.set_cell_severity(column, CellSeverity.Ignored)

    def read_design_info(self):
        self[VOLUME_COL] = self.design_info.volume
        self.read_output_bus()
        self.read_attenuation()
        self.read_conversion()
        self.read_playback_limit()
        self.read_wwise_original_path()
        self.apply_inclusion_text_style()

    def read_integration_info(self):
        self.read_wwise_target_info()
        self.read_wwise_localization()
        self.apply_inclusion_text_style()

    # 读取总线
    def read_output_bus(self):
        bus = self.design_info.output_bus
        if bus and bus.name != "Master Audio Bus":
            self[OUTPUT_BUS_COL] = bus.name
        else:
            self[OUTPUT_BUS_COL] = "默认"

    # 读取衰减
    def read_attenuation(self):
        setting = self.design_info.attenuation
        if setting.is_valid:
            self[ATTENUATION_COL] = setting.name
        else:
            self[ATTENUATION_COL] = "无"

    # 读取音质
    def read_conversion(self):
        setting = self.design_info.conversion_setting
        if setting:
            self[CONVERSION_COL] = setting.name
        else:
            self[CONVERSION_COL] = "默认"

    # 读取最大发声数
    def read_playback_limit(self):
        limit = self.design_info.playback_limit
        if limit == 0:
            self[PLAYBACK_LIMIT_COL] = "不限"
        else:
            self[PLAYBACK_LIMIT_COL] = limit

    # 读取播放对象的类型和路径
    def read_wwise_target_info(self):
        if self.type != WwiseObjectType.Event:
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
            self[TARGET_TYPE_COL] = targets[0].type.name
            self.set_path_cell(TARGET_PATH_COL, targets[0].path)

    # 读取事件源文件路径
    def read_wwise_original_path(self):
        wave_paths = audio_source_utils.get_all_audio_file_paths(self.wwise_object)
        wave_count = len(wave_paths)
        if wave_count == 0:
            self[ORIGINAL_PATH_COL] = "事件不包含源文件"
            self.set_cell_severity(ORIGINAL_PATH_COL, CellSeverity.Ignored)
        elif wave_count > 1:
            self[ORIGINAL_PATH_COL] = f"共包含{wave_count}条音频资源"
        else:
            self[ORIGINAL_PATH_COL] = wave_paths[0]

    # 读取事件是否包含本地化内容
    def read_wwise_localization(self):
        is_localized = localization_utils.is_localized(self.wwise_object)
        self[LOCALIZATION_COL] = "是" if is_localized else "否"
