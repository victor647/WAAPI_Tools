# MCP模式
mcp_mode = False
# 多线程批处理器与进度条窗口
batch_processor = None
progress_bar = None
# 表格中所有Wwise对象
active_objects = []
# 主窗口引用：子窗口要用主窗口对象时通过这里临时获取，不要在构造时把列表固化下来
main_window = None
# WAAPI访问端
waapi_client = None


# 主窗口表格当前对象：每次调用都重新取，保证子窗口与主窗口同步
def get_table_objects() -> list:
    window = main_window
    if window is not None:
        return list(window.get_visible_objects())
    return list(active_objects)


# 主窗口表格里勾选了「选中」列的可见对象：分析类工具只处理这些对象
def get_checked_table_objects() -> list:
    window = main_window
    if window is not None:
        return list(window.get_checked_visible_objects())
    return list(active_objects)


# 主窗口表格里未勾选「选中」列的可见对象路径：这些对象及其整棵子树都不参与分析
def get_unchecked_table_paths() -> list:
    window = main_window
    if window is not None:
        return list(window.get_unchecked_visible_paths())
    return []


# 工具目标对象：按「自动获取子对象」与高级筛选的语言设置临时采集
def get_tool_targets(target_types=None, expand: bool = None) -> list:
    window = main_window
    if window is None:
        return list(active_objects)
    return window.collect_tool_targets(target_types, expand)


# 分析类工具目标：只取主窗口「选中」列已勾选的对象，未勾选行的子树不参与
def get_checked_tool_targets(target_types=None, expand: bool = None) -> list:
    window = main_window
    if window is None:
        return list(active_objects)
    return window.collect_tool_targets(target_types, expand, checked_only=True)
