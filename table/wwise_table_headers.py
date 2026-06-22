# 表格视图模式显示名称（顺序与 WwiseTableDisplayMode：General / Design / Integration 一致）
TABLE_DISPLAY_MODE_LABELS = ("通用视图", "设计视图", "集成视图")

# 通用视图
CHECK_BOX_COL = 0
ENABLE_COL = 1
NAME_COL = 2
TYPE_COL = 3
PATH_COL = 4
DESCRIPTION_COL = 5
COMMON_HEADERS = ["选中", "启用", "名称", "类型", "路径", "描述"]
# 设计视图
VOLUME_COL = 6
OUTPUT_BUS_COL = 7
ATTENUATION_COL = 8
CONVERSION_COL = 9
PLAYBACK_LIMIT_COL = 10
ORIGINAL_PATH_COL = 11
DESIGN_HEADERS = ["音量", "总线", "衰减", "音质", "最大发声数", "源文件路径"]
# 集成视图
ACTION_COL = 6
TARGET_TYPE_COL = 7
TARGET_PATH_COL = 8
LOCALIZATION_COL = 9
SOUNDBANK_COL = 10
INTEGRATION_HEADERS = ["动作", "播放对象类型", "播放对象路径", "本地化", "所属SoundBank"]