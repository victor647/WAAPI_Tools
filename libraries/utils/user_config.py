import json
import os
import sys

from libraries.utils.log_utils import Logger

CONFIG_FILE_NAME = "user_config.json"

# 用户可编辑的默认配置；user_config.json 中的同名键会覆盖这里的值
DEFAULT_CONFIG = {
    "tools": {
        # 工具执行前是否自动展开可见对象的子级来筛选目标类型
        "auto_fetch_children": True,
    },
    "window_settings": {},
    "ai": {
        # AI 对话使用的 OpenAI 兼容代理地址（软件内 AI 助手功能）
        "proxy": "http://127.0.0.1:15721",
        "api_key": "",
        # 留空表示不传 model 字段，由代理自行选择
        "model": "",
        # 一次发给 AI 的表格对象上限，超出部分会在提示词中提示被截断
        "max_context_objects": 300,
        # 单次对话允许的最大往返轮数（防止模型陷入工具循环）
        "max_turns": 20,
    },
    "advanced_filter": {
        # 高级筛选窗口各选项的持久化状态
        "case_sensitive": False,
        "only_included": False,
        # Event 引用筛选：all / with_ref / without_ref
        "event_filter": "all",
        # 语言筛选：all / active
        "language_filter": "all",
    },
}

_config_cache = None


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


def get_config_path() -> str:
    # 打包后配置文件放在 exe 所在目录，开发环境放在仓库根目录
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), CONFIG_FILE_NAME)
    return os.path.join(_find_repo_root(), CONFIG_FILE_NAME)


def _bundled_config_path() -> str:
    # 打包时随 exe 打入的资源副本（见 packager/WAAPI_Tools_GUI.spec 的 datas）
    if not getattr(sys, "frozen", False):
        return ""
    from libraries.utils import path_utils

    bundled = path_utils.get_resource_path(CONFIG_FILE_NAME)
    return bundled if os.path.isfile(bundled) else ""


def _initialize_config_file() -> str:
    # 首次运行（exe 目录尚无 user_config.json）时把内置副本复制为用户的初始配置；
    # 复制失败（例如目录只读）时本次直接读取内置副本
    bundled = _bundled_config_path()
    if not bundled:
        return ""
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


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_from_disk() -> dict:
    config = _deep_merge(DEFAULT_CONFIG, {})
    path = get_config_path()
    if not os.path.isfile(path):
        # exe 目录还没有用户配置时，用打包内置的副本初始化
        path = _initialize_config_file()
        if not path:
            return config
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
    return _config_cache


def get_tool_auto_fetch_children() -> bool:
    return bool(load_config()["tools"].get("auto_fetch_children", True))


def set_tool_auto_fetch_children(enabled: bool) -> None:
    config = load_config()
    config.setdefault("tools", {})["auto_fetch_children"] = bool(enabled)
    _write_config(config)


# 读取某个窗口的持久化设置（不存在时返回空字典）
def get_window_settings(window_key: str) -> dict:
    return dict(load_config().get("window_settings", {}).get(window_key, {}))


# 保存某个窗口的持久化设置（window_settings.<window_key>）
def set_window_settings(window_key: str, values: dict) -> None:
    config = load_config()
    config.setdefault("window_settings", {})[window_key] = dict(values)
    _write_config(config)


def _write_config(config: dict) -> None:
    try:
        with open(get_config_path(), "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except OSError as e:
        Logger().error(f"写入用户配置文件失败：{get_config_path()} ({e})")


def get_ai_proxy_url() -> str:
    return load_config()["ai"].get("proxy", DEFAULT_CONFIG["ai"]["proxy"])


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
