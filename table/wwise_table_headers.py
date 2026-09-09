# 表格视图模式显示名称（顺序与 WwiseTableDisplayMode：General / Design / Integration 一致）
TABLE_DISPLAY_MODE_LABELS = ("通用视图", "设计视图", "集成视图")

# 通用视图
CHECK_BOX_COL = 0
ENABLE_COL = 1
NAME_COL = 2
TYPE_COL = 3
PATH_COL = 4
DESCRIPTION_COL = 5
REFERENCE_COUNT_COL = 6
COMMON_HEADERS = ["选中", "启用", "名称", "类型", "路径", "描述", "引用计数"]
# 设计视图
VOLUME_COL = 7
OUTPUT_BUS_COL = 8
ATTENUATION_COL = 9
CONVERSION_COL = 10
PLAYBACK_LIMIT_COL = 11
ORIGINAL_PATH_COL = 12
DESIGN_HEADERS = ["音量", "总线", "衰减", "音质", "最大发声数", "源文件路径"]
# 集成视图
ACTION_COL = 7
TARGET_TYPE_COL = 8
TARGET_PATH_COL = 9
LOCALIZATION_COL = 10
SOUNDBANK_COL = 11
INTEGRATION_HEADERS = ["动作", "播放对象类型", "播放对象路径", "本地化", "所属SoundBank"]
