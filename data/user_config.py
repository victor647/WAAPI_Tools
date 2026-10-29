import json
import os
import sys

from libraries.utils.log_utils import Logger

CONFIG_FILE_NAME = "user_config.json"

# 优化随机数量工具的窗口设置节点与默认允许数量
OPTIMIZE_RANDOM_COUNT_WINDOW_KEY = "optimize_random_count"
DEFAULT_OPTIMIZE_RANDOM_ALLOWED_COUNT = 3

# 用户可编辑的默认配置；user_config.json 中的同名键会覆盖这里的值
DEFAULT_CONFIG = {
    "tools": {
        # 工具执行前是否自动展开可见对象的子级来筛选目标类型
        "auto_fetch_children": True,
        # 查找/筛选是否只作用于勾选「选中」列的对象；未勾选的行原样保留，始终显示
        "find_filter_checked_only": True,
        # WAAPI 查询分页大小（子对象/后代/批量查询每次拉取的数量）
        "page_size": 500,
        # 表格「路径」列是否使用简写显示；关闭时显示完整路径
        "path_display_compact": True,
        # 表格「路径」列是否隐藏顶层根目录（如 Actor-Mixer Hierarchy）
        "path_hide_root": True,
        # RMS 响度分析的分块采样点数（每 buffer 单独求功率后按门限取平均）
        "loudness_buffer_samples": 1024,
        # 填补缺失资源（静音/正弦波）时新建源的时长（秒）
        "silence_duration": 2.0,
        # 正弦波填补使用的 Wwise Sine 频率（Hz）
        "sine_frequency": 1000,
        # 是否记录明细日志（批量逐个对象的处理记录、WAAPI 调用流水）；关闭可减少日志写入开销
        "detail_log": False,
        # 自动转码：长/短音效占优比例，超过它才覆盖上层设置（0.6 即 40:60 分界）
        "conversion_dominance_ratio": 0.6,
        # 导出对象属性（JSON）时是否只包含可写属性（跳过 id/name/path/children 等只读访问器与列表值）
        "dump_only_writable_properties": True,
    },
    "window_settings": {},
    "ai": {
        # AI 对话使用的 OpenAI 兼容代理地址（软件内 AI 助手功能）
        "proxy": "http://127.0.0.1:15721",
        # proxy=代理模式；official=官方 API 模式（provider 决定具体厂商）
        "mode": "proxy",
        "provider": "openai",
        # 官方模式下选择“自定义”时的 OpenAI 兼容地址
        "base_url": "",
        "api_key": "",
        # 留空表示不传 model 字段，由代理自行选择
        "model": "",
        # 一次发给 AI 的表格对象上限，超出部分会在提示词中提示被截断
        "max_context_objects": 300,
        # 单次对话允许的最大往返轮数（防止模型陷入工具循环）
        "max_turns": 20,
        # 是否允许 AI 执行临时脚本（run_wwise_script）。默认关闭：IDE 调试器下可能不稳定
        "enable_script_tool": False,
        # AI 修改策略：read_only=只读 / ask_before_changes=改动工程前弹窗让用户确认 / allow_changes=直接执行
        "mutation_policy": "ask_before_changes",
    },
    "localization": {
        # 参考语言：True 时直接读 Wwise 工程的参考语言，False 时用下面手填的语言名
        "use_default_reference_language": True,
        "reference_language": "",
    },
    "advanced_filter": {
        # 高级筛选窗口各选项的持久化状态
        "case_sensitive": False,
        "only_included": False,
        # Event 引用筛选：all / with_ref / without_ref
        "event_filter": "all",
        # 语言筛选：all / active
        "language_filter": "all",
        # 是否只显示「在用」的 AudioFileSource（Wwise ActiveSourceList 里的源）
        "only_in_use": False,
    },
    "advanced_find": {
        # 高级查找窗口各选项的持久化状态
        "recursive_find": True,
        "keep_self": False,
        # 查找特定类型子对象时勾选的类型（空列表即全部类型）
        "find_child_types": ["AudioFileSource"],
        # 「找属性」下拉框上次选择的属性名
        "find_property": "Attenuation",
    },
    "appearance": {
        # qt_material 主题（themes/*.xml 文件名）
        "theme": "dark_cyan.xml",
        # 界面缩放：auto=跟随系统；也可以写 "100" / "125" / "150" 等百分比（固定缩放，需重启）
        "ui_scale": "auto",
    },
    # 帮助菜单打开的文档链接（产品默认值，用户可在 user_config.json 里覆盖）
    "Documentation": "https://docs.popo.netease.com/lingxi/730bd7bd4c59499dabca39201cd64c8e",
}

_config_cache = None
# 实际读取/写入的配置文件路径（解析一次后记住，避免读写落到不同文件）
_config_path = ""


def _find_repo_root() -> str:
    # 开发环境从本文件向上找到包含 main.py 的仓库根目录。
    # 不依赖 path_utils，避免配置模块与路径工具互相导入。
    current = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isfile(os.path.join(current, "main.py")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return current
        current = parent


# 应用目录：打包后为 exe 所在目录，开发环境为 main.py 所在（仓库根）目录
def _app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return _find_repo_root()


# 解析已存在的配置文件：Wwise 工程目录优先，其次应用目录（exe / main.py 同目录）
def resolve_config_path() -> str | None:
    try:
        # 延迟导入：project_utils → waapi_utils → waapi_client 顶部依赖本模块
        from libraries.utils.wwise import project_utils

        project_directory = project_utils.get_project_directory()
    except Exception:
        project_directory = ""
    for directory in (project_directory, _app_dir()):
        if not directory:
            continue
        candidate = os.path.join(directory, CONFIG_FILE_NAME)
        if os.path.isfile(candidate):
            return candidate
    return None


def get_config_path() -> str:
    # 这里不能去解析 Wwise 工程目录：解析要连 Wwise，而 WAAPI 调用会触发 Logger 初始化，
    # Logger 初始化又要读本配置，会在配置尚未读出时形成递归。
    # 「工程目录优先」由连上 Wwise 后的 reload_config() 负责切换。
    if _config_path:
        return _config_path
    return os.path.join(_app_dir(), CONFIG_FILE_NAME)


def _bundled_config_path() -> str:
    # 打包时随 exe 打入的资源副本（见 packager/WAAPI_Tools_GUI.spec 的 datas）
    if not getattr(sys, "frozen", False):
        return ""
    from libraries.utils import path_utils

    bundled = path_utils.get_resource_path(CONFIG_FILE_NAME)
    return bundled if os.path.isfile(bundled) else ""


def _initialize_config_file() -> str:
    # 任何位置都没有用户配置时，在应用目录生成一份：优先用打包内置副本，
    # 开发环境没有内置副本则直接写出代码里的默认配置
    bundled = _bundled_config_path()
    if not bundled:
        return _write_default_config()
    user_path = get_config_path()
    try:
        os.makedirs(os.path.dirname(user_path), exist_ok=True)
        with open(bundled, "r", encoding="utf-8") as src, open(user_path, "w", encoding="utf-8") as dst:
            dst.write(src.read())
        Logger().info(f"已使用内置配置初始化用户配置文件: {user_path}")
        return user_path
    except OSError as e:
        Logger().warning(f"写入用户配置文件失败，本次直接读取内置配置: {user_path} ({e})")
        return bundled


def _write_default_config() -> str:
    user_path = get_config_path()
    try:
        os.makedirs(os.path.dirname(user_path), exist_ok=True)
        with open(user_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        Logger().info(f"已生成默认用户配置文件: {user_path}")
        return user_path
    except OSError as e:
        Logger().warning(f"生成默认用户配置文件失败，本次使用内置默认值: {user_path} ({e})")
        return ""


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_from_disk() -> dict:
    global _config_path
    config = _deep_merge(DEFAULT_CONFIG, {})
    path = get_config_path()
    if not os.path.isfile(path):
        # 任何位置都没有用户配置时，用内置副本或代码默认值在应用目录初始化一份
        path = _initialize_config_file()
        if not path:
            return config
    _config_path = path
    try:
        with open(path, "r", encoding="utf-8") as f:
            disk_config = json.load(f)
        if isinstance(disk_config, dict):
            config = _deep_merge(config, disk_config)
    except (OSError, ValueError) as e:
        Logger().error(f"读取用户配置文件失败，使用默认配置: {path} ({e})")
    return config


# 配置只读取一次并缓存；修改 user_config.json 后需重启应用生效
def load_config() -> dict:
    global _config_cache
    if _config_cache is None:
        _config_cache = _load_from_disk()
        Logger().debug(f"用户配置已加载：{get_config_path()}")
    return _config_cache


# 连接 Wwise 之后重新解析配置文件：工程目录里的配置此时才可能出现，需要改用它
def reload_config() -> None:
    global _config_cache, _config_path
    previous = _config_path
    found = resolve_config_path()
    if not found or found == previous:
        return
    _config_path = found
    _config_cache = None
    Logger().info(f"已切换到工程目录的用户配置：{found}")


def get_tool_auto_fetch_children() -> bool:
    return bool(load_config()["tools"].get("auto_fetch_children", True))


# 查找/筛选只作用于勾选「选中」列的对象
def get_tool_find_filter_checked_only() -> bool:
    return bool(load_config()["tools"].get("find_filter_checked_only", True))


def get_tool_page_size() -> int:
    # 分页大小：限制在 10~1000，避免过小拖慢、过大被服务端截断
    try:
        value = int(load_config()["tools"].get("page_size", 500))
    except (TypeError, ValueError):
        value = 500
    return max(10, min(1000, value))


def set_tool_page_size(page_size: int) -> None:
    config = load_config()
    config.setdefault("tools", {})["page_size"] = max(10, min(1000, int(page_size)))
    _write_config(config)


def set_tool_auto_fetch_children(enabled: bool) -> None:
    config = load_config()
    config.setdefault("tools", {})["auto_fetch_children"] = bool(enabled)
    _write_config(config)


def set_tool_find_filter_checked_only(enabled: bool) -> None:
    config = load_config()
    config.setdefault("tools", {})["find_filter_checked_only"] = bool(enabled)
    _write_config(config)


# 自动转码：长/短音效「占优比例」，超过它才覆盖上层设置（默认 0.6，即 40:60 分界）
def get_tool_conversion_dominance_ratio() -> float:
    try:
        value = float(load_config()["tools"].get("conversion_dominance_ratio", 0.6))
    except (TypeError, ValueError):
        value = 0.6
    return max(0.5, min(1.0, value))


def set_tool_conversion_dominance_ratio(ratio: float) -> None:
    config = load_config()
    config.setdefault("tools", {})["conversion_dominance_ratio"] = max(0.5, min(1.0, float(ratio)))
    _write_config(config)


# 是否记录明细日志（批量逐对象处理、WAAPI 调用流水）
def get_tool_detail_log_enabled() -> bool:
    return bool(load_config()["tools"].get("detail_log", False))


def set_tool_detail_log_enabled(enabled: bool) -> None:
    config = load_config()
    config.setdefault("tools", {})["detail_log"] = bool(enabled)
    _write_config(config)
    # 立即生效，避免每次写明细日志都要重新读配置
    try:
        Logger().refresh_detail_log_setting()
    except Exception:
        pass


def get_tool_path_display_compact() -> bool:
    return bool(load_config()["tools"].get("path_display_compact", True))


def set_tool_path_display_compact(enabled: bool) -> None:
    config = load_config()
    config.setdefault("tools", {})["path_display_compact"] = bool(enabled)
    _write_config(config)


def get_tool_path_hide_root() -> bool:
    return bool(load_config()["tools"].get("path_hide_root", True))


def set_tool_path_hide_root(enabled: bool) -> None:
    config = load_config()
    config.setdefault("tools", {})["path_hide_root"] = bool(enabled)
    _write_config(config)


# 导出对象属性时是否只包含可写属性（跳过只读访问器与列表值）
def get_dump_only_writable_properties() -> bool:
    return bool(load_config()["tools"].get("dump_only_writable_properties", True))


def set_dump_only_writable_properties(enabled: bool) -> None:
    config = load_config()
    config.setdefault("tools", {})["dump_only_writable_properties"] = bool(enabled)
    _write_config(config)


# 响度分析的分块采样点数：限制在 128~65536，避免过小噪声大、过大退化成整体响度
def get_tool_loudness_buffer_samples() -> int:
    try:
        value = int(load_config()["tools"].get("loudness_buffer_samples", 1024))
    except (TypeError, ValueError):
        value = 1024
    return max(128, min(65536, value))


def set_tool_loudness_buffer_samples(samples: int) -> None:
    config = load_config()
    config.setdefault("tools", {})["loudness_buffer_samples"] = max(128, min(65536, int(samples)))
    _write_config(config)


# 填补缺失资源的新建源时长（秒）：限制在 0.1~60，避免填成 0 或异常长的源
def get_tool_silence_duration() -> float:
    try:
        value = float(load_config()["tools"].get("silence_duration", 2.0))
    except (TypeError, ValueError):
        value = 2.0
    return max(0.1, min(60.0, value))


def set_tool_silence_duration(duration: float) -> None:
    config = load_config()
    config.setdefault("tools", {})["silence_duration"] = round(max(0.1, min(60.0, float(duration))), 1)
    _write_config(config)


# 正弦波填补使用的 Wwise Sine 频率（Hz）：限制在 20~20000
def get_tool_sine_frequency() -> int:
    try:
        value = int(load_config()["tools"].get("sine_frequency", 1000))
    except (TypeError, ValueError):
        value = 1000
    return max(20, min(20000, value))


def set_tool_sine_frequency(frequency: int) -> None:
    config = load_config()
    config.setdefault("tools", {})["sine_frequency"] = max(20, min(20000, int(frequency)))
    _write_config(config)


# 参考语言设置：是否使用工程默认
def get_reference_language_use_default() -> bool:
    return bool(load_config().get("localization", {}).get("use_default_reference_language", True))


def set_reference_language_use_default(enabled: bool) -> None:
    config = load_config()
    config.setdefault("localization", {})["use_default_reference_language"] = bool(enabled)
    _write_config(config)


# 参考语言设置：手动填写的语言名（use_default 打开时不生效）
def get_configured_reference_language() -> str:
    return str(load_config().get("localization", {}).get("reference_language", "")).strip()


def set_configured_reference_language(language: str) -> None:
    config = load_config()
    config.setdefault("localization", {})["reference_language"] = str(language or "").strip()
    _write_config(config)


# 读取某个窗口的持久化设置（不存在时返回空字典）
def get_window_settings(window_key: str) -> dict:
    return dict(load_config().get("window_settings", {}).get(window_key, {}))


# 保存某个窗口的持久化设置（window_settings.<window_key>）
def set_window_settings(window_key: str, values: dict) -> None:
    config = load_config()
    config.setdefault("window_settings", {})[window_key] = dict(values)
    _write_config(config)


# 优化随机数量：读取默认允许数量与各平台覆盖值
def get_optimize_random_count_settings() -> dict:
    settings = get_window_settings(OPTIMIZE_RANDOM_COUNT_WINDOW_KEY)
    try:
        default = max(0, int(settings.get("allowed_count", DEFAULT_OPTIMIZE_RANDOM_ALLOWED_COUNT)))
    except (TypeError, ValueError):
        default = DEFAULT_OPTIMIZE_RANDOM_ALLOWED_COUNT
    allowed_by_platform = {}
    raw = settings.get("allowed_by_platform") or {}
    if isinstance(raw, dict):
        for name, value in raw.items():
            try:
                allowed_by_platform[str(name)] = max(0, int(value))
            except (TypeError, ValueError):
                continue
    selected_platforms = None
    raw_selected = settings.get("selected_platforms")
    if isinstance(raw_selected, list):
        selected_platforms = []
        for name in raw_selected:
            name = str(name).strip()
            if name and name not in selected_platforms:
                selected_platforms.append(name)
    return {
        "allowed_count": default,
        "allowed_by_platform": allowed_by_platform,
        "selected_platforms": selected_platforms,
    }


# 指定平台未单独配置时回退到默认允许数量
def get_optimize_random_allowed_count(platform: str = "") -> int:
    settings = get_optimize_random_count_settings()
    if platform:
        return settings["allowed_by_platform"].get(platform, settings["allowed_count"])
    return settings["allowed_count"]


def save_optimize_random_count_settings(default: int, allowed_by_platform: dict) -> None:
    clean = {}
    for name, value in (allowed_by_platform or {}).items():
        try:
            clean[str(name)] = max(0, int(value))
        except (TypeError, ValueError):
            continue
    try:
        default_value = max(0, int(default))
    except (TypeError, ValueError):
        default_value = DEFAULT_OPTIMIZE_RANDOM_ALLOWED_COUNT
    current = get_window_settings(OPTIMIZE_RANDOM_COUNT_WINDOW_KEY)
    current["allowed_count"] = default_value
    current["allowed_by_platform"] = clean
    set_window_settings(OPTIMIZE_RANDOM_COUNT_WINDOW_KEY, current)


# 工具窗口内调整数量时，按当前平台写回对应覆盖值
def set_optimize_random_allowed_count(platform: str, value: int) -> None:
    settings = get_optimize_random_count_settings()
    if platform:
        settings["allowed_by_platform"][platform] = max(0, int(value))
    else:
        settings["allowed_count"] = max(0, int(value))
    save_optimize_random_count_settings(settings["allowed_count"], settings["allowed_by_platform"])


# 工具窗口的「仅显示超标对象」过滤开关
def get_optimize_random_only_over_limit() -> bool:
    return bool(get_window_settings(OPTIMIZE_RANDOM_COUNT_WINDOW_KEY).get("only_over_limit", False))


def set_optimize_random_only_over_limit(enabled: bool) -> None:
    current = get_window_settings(OPTIMIZE_RANDOM_COUNT_WINDOW_KEY)
    current["only_over_limit"] = bool(enabled)
    set_window_settings(OPTIMIZE_RANDOM_COUNT_WINDOW_KEY, current)


# 是否显示包含多种名称前缀的随机容器
def get_optimize_random_show_multi_group() -> bool:
    return bool(
        get_window_settings(OPTIMIZE_RANDOM_COUNT_WINDOW_KEY).get("show_multi_group", False)
    )


def set_optimize_random_show_multi_group(enabled: bool) -> None:
    current = get_window_settings(OPTIMIZE_RANDOM_COUNT_WINDOW_KEY)
    current["show_multi_group"] = bool(enabled)
    set_window_settings(OPTIMIZE_RANDOM_COUNT_WINDOW_KEY, current)


# 「优化所选平台」勾选的平台列表
def set_optimize_random_selected_platforms(platforms: list[str]) -> None:
    current = get_window_settings(OPTIMIZE_RANDOM_COUNT_WINDOW_KEY)
    current["selected_platforms"] = [
        str(name).strip() for name in platforms if str(name).strip()
    ]
    set_window_settings(OPTIMIZE_RANDOM_COUNT_WINDOW_KEY, current)


def _write_config(config: dict) -> None:
    try:
        with open(get_config_path(), "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except OSError as e:
        Logger().error(f"写入用户配置文件失败：{get_config_path()} ({e})")


def get_ai_proxy_url() -> str:
    return load_config()["ai"].get("proxy", DEFAULT_CONFIG["ai"]["proxy"])


def get_ai_mode() -> str:
    mode = str(load_config()["ai"].get("mode", DEFAULT_CONFIG["ai"]["mode"])).strip().lower()
    return mode if mode in ("proxy", "official") else DEFAULT_CONFIG["ai"]["mode"]


def get_ai_provider() -> str:
    return str(load_config()["ai"].get("provider", DEFAULT_CONFIG["ai"]["provider"])).strip()


def get_ai_base_url() -> str:
    return str(load_config()["ai"].get("base_url", DEFAULT_CONFIG["ai"]["base_url"])).strip()


def get_ai_api_key() -> str:
    return load_config()["ai"].get("api_key", DEFAULT_CONFIG["ai"]["api_key"])


def get_ai_model() -> str:
    return load_config()["ai"].get("model", DEFAULT_CONFIG["ai"]["model"])


# 读取 AI 设置整段（未配置项自动回退默认值）
def get_ai_config() -> dict:
    config = load_config()
    ai_defaults = DEFAULT_CONFIG["ai"]
    stored = config.get("ai")
    if not isinstance(stored, dict):
        stored = {}
    return {key: stored.get(key, default) for key, default in ai_defaults.items()}


# 部分更新 AI 设置（如 {"model": ...}），写回 user_config.json 并立即更新缓存
def save_ai_config(patch: dict) -> None:
    config = load_config()
    config.setdefault("ai", {}).update(patch)
    _write_config(config)


# 把界面中选择的模型写回 user_config.json（下次启动仍生效）
def save_ai_model(model: str) -> None:
    save_ai_config({"model": model})


def get_ai_max_context_objects() -> int:
    return load_config()["ai"].get("max_context_objects", DEFAULT_CONFIG["ai"]["max_context_objects"])


def get_ai_max_turns() -> int:
    return load_config()["ai"].get("max_turns", DEFAULT_CONFIG["ai"]["max_turns"])


def get_ai_enable_script_tool() -> bool:
    return bool(load_config()["ai"].get("enable_script_tool", DEFAULT_CONFIG["ai"]["enable_script_tool"]))


# AI 修改策略取值：只读 / 改动前由用户确认 / 直接执行
MUTATION_POLICIES = ("read_only", "ask_before_changes", "allow_changes")


def get_ai_mutation_policy() -> str:
    policy = load_config()["ai"].get("mutation_policy", DEFAULT_CONFIG["ai"]["mutation_policy"])
    return policy if policy in MUTATION_POLICIES else DEFAULT_CONFIG["ai"]["mutation_policy"]


def get_appearance_theme() -> str:
    return load_config()["appearance"].get("theme", DEFAULT_CONFIG["appearance"]["theme"])


def save_appearance_theme(theme: str) -> None:
    config = load_config()
    config.setdefault("appearance", {})["theme"] = theme
    _write_config(config)


# 界面缩放：auto 跟随系统，其余为固定百分比（QT_SCALE_FACTOR，只在启动时生效）
def get_appearance_ui_scale() -> str:
    value = str(load_config()["appearance"].get("ui_scale", DEFAULT_CONFIG["appearance"]["ui_scale"])).strip()
    return value if value == "auto" or value.isdigit() else DEFAULT_CONFIG["appearance"]["ui_scale"]


def save_appearance_ui_scale(scale: str) -> None:
    config = load_config()
    config.setdefault("appearance", {})["ui_scale"] = scale if scale == "auto" or str(scale).isdigit() else "auto"
    _write_config(config)


# 帮助文档链接：统一维护在 user_config.json 顶层 Documentation（兼容小写拼写），未配置返回空串
def get_documentation_url() -> str:
    config = load_config()
    url = config.get("documentation") or config.get("Documentation")
    return str(url or "").strip()


def get_advanced_filter_settings() -> dict:
    defaults = DEFAULT_CONFIG["advanced_filter"]
    stored = load_config().get("advanced_filter")
    if not isinstance(stored, dict):
        stored = {}
    return {key: stored.get(key, defaults[key]) for key in defaults}


def get_advanced_find_settings() -> dict:
    defaults = DEFAULT_CONFIG["advanced_find"]
    stored = load_config().get("advanced_find")
    if not isinstance(stored, dict):
        stored = {}
    # 类型默认一个都不勾（即「全部类型」）；旧版的 find_child_type 单值不再沿用
    return {key: stored.get(key, defaults[key]) for key in defaults}


# 把高级查找窗口的选项写回 user_config.json（下次打开窗口时沿用）
def save_advanced_find_settings(settings: dict) -> None:
    config = load_config()
    section = config.setdefault("advanced_find", {})
    allowed = set(DEFAULT_CONFIG["advanced_find"])
    section.update({key: value for key, value in settings.items() if key in allowed})
    # 清掉旧版遗留的单值键，避免和 find_child_types 并存产生歧义
    section.pop("find_child_type", None)
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except OSError as e:
        Logger().error(f"写入高级查找配置失败：{path} ({e})")


# 把高级筛选窗口的选项写回 user_config.json（下次打开窗口时沿用）
def save_advanced_filter_settings(settings: dict) -> None:
    config = load_config()
    section = config.setdefault("advanced_filter", {})
    allowed = set(DEFAULT_CONFIG["advanced_filter"])
    section.update({key: value for key, value in settings.items() if key in allowed})
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except OSError as e:
        Logger().error(f"写入高级筛选配置失败：{path} ({e})")
