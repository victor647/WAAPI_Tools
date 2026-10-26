from dataclasses import dataclass

from libraries.utils import user_config
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import audio_source_utils, mixing_utils, waapi_utils, wwise_compat
from libraries.wwise_object import WwiseObject, WwiseObjectType


LONG_CATEGORY = "long"
MEDIUM_CATEGORY = "medium"
SHORT_CATEGORY = "short"

# 长/短档在默认档 Conversion 名称后加后缀；中档直接用用户选的默认 Conversion
CATEGORY_SUFFIXES = {LONG_CATEGORY: "_Long", SHORT_CATEGORY: "_Short"}
# 票数相同时的取档顺序（默认档优先）
CATEGORY_PREFERENCE = (MEDIUM_CATEGORY, LONG_CATEGORY, SHORT_CATEGORY)

# 占优比例的兜底默认值（配置里可改）：占比严格超过它才算某一种音效明显占优
DEFAULT_DOMINANCE_RATIO = 0.6

# 设置窗口与工具共用的持久化键与默认阈值
WINDOW_SETTINGS_KEY = "auto_compression_settings"
DEFAULT_SHORT_THRESHOLD = 0.5
DEFAULT_LONG_THRESHOLD = 5.0

# 目标节点类型：PropertyContainer（旧版 ActorMixer）与各种 Container
CONTAINER_TYPE_VALUES = tuple(dict.fromkeys(
    object_type.value for object_type in WwiseObjectType if object_type.value.endswith("Container")
))
TARGET_DISCOVERY_TYPE_VALUES = (
    *wwise_compat.property_container_type_names(),
    *CONTAINER_TYPE_VALUES,
)

# 判断「节点已有的 Override 是否和本次方案冲突」需要读的两个属性
OVERRIDE_STATE_PROPERTIES = ("OverrideConversion", "Conversion")


@dataclass
class ConversionAssignmentPlan:
    target: WwiseObject
    conversion: WwiseObject
    effective_category: str
    override_enabled: bool
    counts_by_category: dict
    # 该节点下面是否还有 ActorMixer / Container 子节点（没有即为最底层节点）
    has_child_target: bool
    # 已经打开 Override，但指向的不是本次方案给它指定的 Conversion
    conflict: bool = False
    existing_conversion_name: str = ""


@dataclass
class NameConversionPlan:
    target: WwiseObject
    keyword: str
    conversion: WwiseObject
    conflict: bool = False
    existing_conversion_name: str = ""


@dataclass
class BusConversionPlan:
    target: WwiseObject
    bus: WwiseObject
    conversion: WwiseObject
    conflict: bool = False
    existing_conversion_name: str = ""


def _path_prefixes(path: str) -> list[str]:
    parts = [part for part in (path or "").replace("/", "\\").split("\\") if part]
    return ["\\" + "\\".join(parts[:index]) for index in range(1, len(parts))]


# 统一成「\A\B」形式，便于按前缀判断包含关系
def normalized_path(path: str) -> str:
    parts = [part for part in (path or "").replace("/", "\\").split("\\") if part]
    return "\\" + "\\".join(parts)


# 本次启用的档位（默认档一定在里面），顺序按 CATEGORY_PREFERENCE
def enabled_categories(use_short: bool = True, use_long: bool = True) -> tuple:
    enabled = {MEDIUM_CATEGORY}
    if use_long:
        enabled.add(LONG_CATEGORY)
    if use_short:
        enabled.add(SHORT_CATEGORY)
    return tuple(category for category in CATEGORY_PREFERENCE if category in enabled)


# 某个对象是否被排除：取它自己或它上层最近的「表格行」，那一行没勾选就整棵子树都不分析
# row_checked_by_path 为 {规范化路径: 该行是否勾选}
def is_excluded_by_rows(path: str, row_checked_by_path: dict) -> bool:
    if not row_checked_by_path:
        return False
    parts = [part for part in normalized_path(path).split("\\") if part]
    for index in range(len(parts), 0, -1):
        checked = row_checked_by_path.get("\\" + "\\".join(parts[:index]))
        if checked is not None:
            return not checked
    return False


# 按播放时长分档：<=短阈值 为短档，>=长阈值 为长档，中间为中档
# 未启用的档位不参与分档，落在该档的样本一律算默认档（中档）
def category_for_duration(
    duration: float, short_threshold: float, long_threshold: float,
    use_short: bool = True, use_long: bool = True,
) -> str:
    if duration is None:
        return None
    if use_short and duration <= short_threshold:
        return SHORT_CATEGORY
    if use_long and duration >= long_threshold:
        return LONG_CATEGORY
    return MEDIUM_CATEGORY


# 本层是否被某一档明显占优：占比不超过阈值（如 40:60）或正好打平时返回 None，交给上层继承
def dominant_category(
    counts: dict, dominance_ratio: float, categories: tuple = CATEGORY_PREFERENCE
) -> str:
    total = sum(counts.get(category, 0) for category in categories)
    if not total:
        return None
    best_count = max((counts.get(category, 0) for category in categories), default=0)
    if best_count / total <= dominance_ratio:
        return None
    return next((c for c in categories if counts.get(c, 0) == best_count), None)


# 票数最多的档（票数相同时按 CATEGORY_PREFERENCE 取档），用于推导根节点的默认档
def majority_category(counts: dict, categories: tuple = CATEGORY_PREFERENCE) -> str:
    best_count = max((counts.get(category, 0) for category in categories), default=0)
    if not best_count:
        return None
    return next((c for c in categories if counts.get(c, 0) == best_count), None)


# 某节点包含的音频明细：[(音频源, 时长秒或 None, 档位)]，按时长从长到短排序
def describe_target_sources(target, audio_sources, duration_by_source_id, short_threshold: float,
                            long_threshold: float, use_short: bool = True,
                            use_long: bool = True) -> list:
    prefix = normalized_path(target.path) + "\\"
    rows = []
    for source in audio_sources:
        if not normalized_path(source.path).startswith(prefix):
            continue
        duration = audio_source_utils.get_audio_source_duration_seconds(
            duration_by_source_id.get(source.id)
        )
        rows.append((
            source, duration,
            category_for_duration(duration, short_threshold, long_threshold, use_short, use_long),
        ))
    rows.sort(key=lambda item: (item[1] is None, -(item[1] or 0.0)))
    return rows


# 按即将应用的 Override 节点，统计每个音频文件最终会用哪一档的 Conversion：
# 从文件所在位置由内向外找最近的 Override 节点（selected_target_ids 为空表示用全部 Override 节点）
def count_files_by_conversion(plans: list, audio_sources: list, selected_target_ids=None) -> dict:
    override_category_by_path = {}
    for plan in plans:
        if not plan.override_enabled or not plan.target.path:
            continue
        if selected_target_ids is not None and plan.target.id not in selected_target_ids:
            continue
        override_category_by_path[normalized_path(plan.target.path)] = plan.effective_category
    counts = {category: 0 for category in CATEGORY_PREFERENCE}
    for source in audio_sources:
        for path in reversed(_path_prefixes(source.path)):
            category = override_category_by_path.get(path)
            if category:
                counts[category] += 1
                break
    return counts


# 按名称匹配：节点名包含关键词就映射到对应 Conversion
# 关键词不区分大小写；同一节点命中多个关键词时取列表里第一个；父节点已命中时不再匹配其子节点
def build_name_conversion_plans(targets: list, mapping: list) -> list:
    pairs = [(str(keyword).strip(), conversion) for keyword, conversion in mapping if str(keyword).strip() and conversion]
    matched_paths: set = set()
    plans = []
    for target in sorted(
        targets, key=lambda obj: (obj.path.count("\\") if obj.path else 0, obj.path)
    ):
        if any(prefix in matched_paths for prefix in _path_prefixes(target.path)):
            continue
        name = (target.name or "").lower()
        if not name:
            continue
        for keyword, conversion in pairs:
            if keyword.lower() in name:
                plans.append(NameConversionPlan(target=target, keyword=keyword, conversion=conversion))
                matched_paths.add(normalized_path(target.path))
                break
    return plans


# 应用「命中即覆盖」的方案（名称模式 / OutputBus 模式）：打开 OverrideConversion 并指向对应 Conversion
def apply_override_conversion_plans(plans: list) -> list[str]:
    if not plans:
        return []

    failed_ids = set()
    assignments = [(plan.target, True) for plan in plans]
    if not waapi_utils.set_objects_property_values(assignments, "OverrideConversion"):
        for plan in plans:
            if not waapi_utils.set_object_property(plan.target, "OverrideConversion", True):
                failed_ids.add(plan.target.id)

    reference_plans = [plan for plan in plans if plan.target.id not in failed_ids]
    reference_assignments = [(plan.target, plan.conversion.id) for plan in reference_plans]
    if reference_assignments and not waapi_utils.set_objects_property_values(
        reference_assignments, "Conversion"
    ):
        for plan in reference_plans:
            if not waapi_utils.set_object_reference(plan.target, "Conversion", plan.conversion):
                failed_ids.add(plan.target.id)

    return [
        plan.target.path or plan.target.name
        for plan in plans
        if plan.target.id in failed_ids
    ]


# 按 OutputBus 匹配：节点当前有效 OutputBus 命中映射就设置对应 Conversion
# 与名称模式一致：父节点已命中时不再匹配其子节点；同一总线在映射里出现多次时取第一个
def build_bus_conversion_plans(targets: list, output_bus_by_target_id: dict, mapping: list) -> list:
    conversion_by_bus_id = {
        _normalized_object_id(bus.id): conversion
        for bus, conversion in mapping
        if bus and conversion
    }
    matched_paths: set = set()
    plans = []
    for target in sorted(
        targets, key=lambda obj: (obj.path.count("\\") if obj.path else 0, obj.path)
    ):
        if any(prefix in matched_paths for prefix in _path_prefixes(target.path)):
            continue
        bus = mixing_utils.get_output_bus(target, output_bus_by_target_id.get(target.id) or {})
        bus_id = _normalized_object_id(bus.id) if bus else ""
        if not bus_id:
            continue
        conversion = conversion_by_bus_id.get(bus_id)
        if conversion is None:
            continue
        plans.append(BusConversionPlan(target=target, bus=bus, conversion=conversion))
        matched_paths.add(normalized_path(target.path))
    return plans


# 按档位后缀在工程里找 Conversion；找不到就复制默认档的 Conversion 再改名
# 返回 (各档 Conversion, 本次新建的档位集合)；新建的对象还没写进 WorkUnit，参数只能沿用默认档
# 表格对象里只保留「不是其它对象后代」的根，避免同一棵子树被重复扫描
def scan_roots(objects: list) -> list:
    unique_objects = {obj.id: obj for obj in objects if obj and obj.id}
    roots = list(unique_objects.values())
    root_paths = [obj.path.rstrip("\\") for obj in roots if obj.path]
    return [
        obj for obj in roots
        if not obj.path or not any(
            path != obj.path.rstrip("\\") and obj.path.startswith(path + "\\")
            for path in root_paths
        )
    ]


# 单个根下的目标节点与音频源：PropertyContainer/ActorMixer 全收，
# Container 只收位于某个 PropertyContainer 之下且支持 Conversion 的
# include_sources=False 时（按名称模式）不查音频源，省一次后代查询
def discover_targets_and_sources(root: WwiseObject, include_sources: bool = True) -> tuple:
    root_type = (root.wwise_dict or {}).get("type", "")
    target_nodes = [root] if wwise_compat.is_property_container_type(root_type) or root_type.endswith(
        "Container"
    ) else []
    target_nodes.extend(waapi_utils.get_descendants_of_type(root, TARGET_DISCOVERY_TYPE_VALUES))
    audio_sources = []
    if include_sources:
        if root_type == WwiseObjectType.AudioSource.value:
            audio_sources.append(root)
        audio_sources.extend(waapi_utils.get_descendants_of_type(root, WwiseObjectType.AudioSource))
    property_container_paths = {
        obj.path.rstrip("\\")
        for obj in target_nodes
        if wwise_compat.is_property_container_type((obj.wwise_dict or {}).get("type", "")) and obj.path
    }
    targets = []
    for obj in target_nodes:
        object_type = (obj.wwise_dict or {}).get("type", "")
        if wwise_compat.is_property_container_type(object_type):
            targets.append(obj)
        elif (
            isinstance(object_type, str)
            and object_type.endswith("Container")
            and obj.has_property("Conversion")
            and obj.has_property("OverrideConversion")
            and any(obj.path.startswith(path + "\\") for path in property_container_paths)
        ):
            targets.append(obj)
    sources = [
        obj for obj in audio_sources
        if (obj.wwise_dict or {}).get("type") == WwiseObjectType.AudioSource.value
    ]
    return targets, sources


# 读取一批音频源的播放时长，返回 {对象ID: 属性字典}（窗口按页调用以显示进度）
def read_page_source_durations(page: list) -> dict:
    return waapi_utils.get_objects_properties(
        page, [audio_source_utils.AUDIO_SOURCE_PLAYBACK_DURATION_PROPERTY]
    )


# 读取一批目标节点当前的 OverrideConversion 与 Conversion（窗口按页调用以步进进度条）
def read_page_override_states(page: list) -> dict:
    return waapi_utils.get_objects_properties(page, list(OVERRIDE_STATE_PROPERTIES))


# OutputBus 模式：一次读回有效 OutputBus 与现有 Override 状态（用于冲突提示）
def read_page_bus_states(page: list) -> dict:
    return waapi_utils.get_objects_properties_raw(
        page, ["OutputBus", *OVERRIDE_STATE_PROPERTIES]
    )


# Wwise 回传的 GUID 带花括号且大小写不固定，比较前统一规范化
def _normalized_object_id(value) -> str:
    if isinstance(value, dict):
        value = value.get("id")
    return str(value or "").strip().strip("{}").lower()


# 本次方案给某个节点指定的 Conversion：需要 Override 的节点用方案里的档位，
# 继承上层的节点用它继承到的档位（换算成对应 Conversion）
def plan_designated_conversion(plan, conversions_by_category: dict = None) -> WwiseObject:
    if getattr(plan, "override_enabled", True) or not conversions_by_category:
        return plan.conversion
    return conversions_by_category.get(getattr(plan, "effective_category", None)) or plan.conversion


# 标记「当前已经打开 Override，但指向的不是本次方案指定的 Conversion」的节点
# 这类节点会被方案改写（改指方案档位，或清掉 Override 改回继承），因此要在表格里提示
# 返回被标记的节点列表（同时把 conflict / existing_conversion_name 写到方案对象上）
def mark_conversion_conflicts(
    plans: list, override_states: dict, conversions_by_category: dict = None
) -> list:
    conflicts = []
    for plan in plans:
        plan.conflict = False
        plan.existing_conversion_name = ""
        state = override_states.get(plan.target.id) or {}
        if not state.get("OverrideConversion"):
            continue
        designated = plan_designated_conversion(plan, conversions_by_category)
        current = state.get("Conversion")
        current_id = _normalized_object_id(current)
        # 读不到现有 Conversion 时不判定为冲突，避免误报
        if not current_id or designated is None:
            continue
        if current_id == _normalized_object_id(designated.id):
            continue
        plan.conflict = True
        plan.existing_conversion_name = current.get("name", "") if isinstance(current, dict) else ""
        conflicts.append(plan)
    return conflicts


# 按「查询分页大小」分页批量读取音频源播放时长，返回 {对象ID: 属性字典}
def read_source_durations(sources: list) -> dict:
    durations = {}
    for page in waapi_utils.iter_object_pages(sources):
        durations.update(read_page_source_durations(page))
    return durations


# 按名称查已有的档位 Conversion；返回 ({档位: Conversion}, [(档位, 待创建名称)])
# categories 为空表示长/短档都启用；未启用的档位不查找也不创建
def resolve_category_conversions(default_conversion: WwiseObject, categories: tuple = None) -> tuple:
    existing_by_name = {}
    for obj in waapi_utils.find_all_objects_by_type(WwiseObjectType.Conversion):
        existing_by_name.setdefault(obj.name, obj)
    conversions = {MEDIUM_CATEGORY: default_conversion}
    missing = []
    for category, suffix in CATEGORY_SUFFIXES.items():
        if categories is not None and category not in categories:
            continue
        name = default_conversion.name + suffix
        if name in existing_by_name:
            conversions[category] = existing_by_name[name]
        else:
            missing.append((category, name))
    return conversions, missing


# 解析默认档 Conversion：优先用传入的 id，其次用设置窗口里保存的那个
def resolve_default_conversion(conversion_id: str = "") -> WwiseObject:
    saved = user_config.get_window_settings(WINDOW_SETTINGS_KEY)
    target_id = str(conversion_id or "").strip() or str(saved.get("default_conversion_id") or "").strip()
    if not target_id:
        return None
    obj = waapi_utils.get_full_info_from_obj_id(target_id)
    if obj.is_valid and obj.type == WwiseObjectType.Conversion:
        return obj
    return None


def ensure_category_conversions(default_conversion: WwiseObject, categories: tuple = None) -> tuple:
    conversions, missing = resolve_category_conversions(default_conversion, categories)
    created_categories: set = set()
    if not missing:
        return conversions, created_categories

    parent = default_conversion.parent
    if not parent or not parent.is_valid:
        for _category, name in missing:
            Logger().error(f"默认 Conversion [{default_conversion.name}] 没有有效的父级，无法复制出 [{name}]")
        return conversions, created_categories

    undo_group_opened = waapi_utils.begin_undo_group("自动转码设置：创建 Conversion")
    try:
        for category, name in missing:
            copied = waapi_utils.copy_object(default_conversion, parent)
            if not copied or not copied.is_valid or not waapi_utils.rename_object(copied, name):
                Logger().error(f"复制默认 Conversion 生成 [{name}] 失败")
                continue
            refreshed = waapi_utils.get_full_info_from_obj_id(copied.id)
            conversions[category] = refreshed if refreshed.is_valid else copied
            created_categories.add(category)
            Logger().info(f"已复制默认 Conversion：{default_conversion.name} → {name}")
    finally:
        if undo_group_opened:
            waapi_utils.end_undo_group("自动转码设置：创建 Conversion")
    return conversions, created_categories


def build_conversion_plans(
    targets: list[WwiseObject],
    audio_sources: list[WwiseObject],
    duration_by_source_id: dict,
    short_threshold: float,
    long_threshold: float,
    conversions_by_category: dict,
    dominance_ratio: float = None,
    use_short: bool = True,
    use_long: bool = True,
) -> tuple[list[ConversionAssignmentPlan], dict]:
    if dominance_ratio is None:
        dominance_ratio = user_config.get_tool_conversion_dominance_ratio()
    categories = enabled_categories(use_short, use_long)
    targets_by_id = {obj.id: obj for obj in targets if obj and obj.id}
    targets_by_path = {
        "\\" + "\\".join(part for part in obj.path.replace("/", "\\").split("\\") if part): obj
        for obj in targets_by_id.values()
        if obj.path
    }
    source_by_id = {obj.id: obj for obj in audio_sources if obj and obj.id}
    target_counts = {
        object_id: {category: 0 for category in CATEGORY_PREFERENCE}
        for object_id in targets_by_id
    }
    total_counts = {category: 0 for category in CATEGORY_PREFERENCE}
    valid_duration_count = 0

    for source in source_by_id.values():
        duration = audio_source_utils.get_audio_source_duration_seconds(
            duration_by_source_id.get(source.id)
        )
        category = category_for_duration(
            duration, short_threshold, long_threshold, use_short, use_long
        )
        if category is None:
            continue
        total_counts[category] += 1
        valid_duration_count += 1
        for path in _path_prefixes(source.path):
            target = targets_by_path.get(path)
            if target:
                target_counts[target.id][category] += 1

    # 默认档由全部样本的多数结果推导（即最上层根节点的判定结果），用户不需要手动指定
    default_category = majority_category(total_counts, categories)
    parent_by_id = {}
    for target in targets_by_id.values():
        for path in _path_prefixes(target.path):
            parent = targets_by_path.get(path)
            if parent:
                parent_by_id[target.id] = parent.id

    sorted_targets = sorted(
        targets_by_id.values(),
        key=lambda obj: (obj.path.count("\\") if obj.path else 0, obj.path),
    )
    effective_category_by_id = {}
    parent_ids_with_children = set(parent_by_id.values())
    plans = []
    for target in sorted_targets:
        parent_id = parent_by_id.get(target.id)
        parent_category = effective_category_by_id.get(parent_id)
        counts = target_counts[target.id]
        if parent_category is None:
            category = default_category
            override_enabled = True
        else:
            # 某一档占比不够明显时继承上层，把 override 留给更下层的节点
            category = dominant_category(counts, dominance_ratio, categories) or parent_category
            override_enabled = category != parent_category
        effective_category_by_id[target.id] = category
        plans.append(ConversionAssignmentPlan(
            target=target,
            conversion=conversions_by_category.get(category),
            effective_category=category,
            override_enabled=override_enabled,
            counts_by_category=dict(counts),
            has_child_target=target.id in parent_ids_with_children,
        ))

    return plans, {
        "long_count": total_counts[LONG_CATEGORY],
        "medium_count": total_counts[MEDIUM_CATEGORY],
        "short_count": total_counts[SHORT_CATEGORY],
        "default_category": default_category,
        "valid_duration_count": valid_duration_count,
        "unclassified_count": len(source_by_id) - valid_duration_count,
        "override_enable_count": sum(plan.override_enabled for plan in plans),
        "dominance_ratio": dominance_ratio,
        "short_threshold": short_threshold,
        "long_threshold": long_threshold,
        "use_short": use_short,
        "use_long": use_long,
    }


# 一次算清自动转码方案：扫描根 → 收目标与音频源 → 读时长 → 生成档位分配
# create_missing=True 时先把缺失的 _Long/_Short 档位 Conversion 从默认档复制出来
def analyze_auto_compression(
    objects: list,
    short_threshold: float,
    long_threshold: float,
    default_conversion: WwiseObject,
    create_missing: bool = False,
    use_short: bool = True,
    use_long: bool = True,
) -> dict:
    categories = enabled_categories(use_short, use_long)
    targets_by_id: dict = {}
    sources_by_id: dict = {}
    for root in scan_roots(objects):
        targets, sources = discover_targets_and_sources(root)
        for obj in targets:
            targets_by_id.setdefault(obj.id, obj)
        for obj in sources:
            sources_by_id.setdefault(obj.id, obj)
    if create_missing:
        conversions, created_categories = ensure_category_conversions(default_conversion, categories)
        missing_categories = []
    else:
        conversions, missing_categories = resolve_category_conversions(default_conversion, categories)
        created_categories = set()
    plans, summary = build_conversion_plans(
        list(targets_by_id.values()),
        list(sources_by_id.values()),
        read_source_durations(list(sources_by_id.values())),
        short_threshold,
        long_threshold,
        conversions,
        use_short=use_short,
        use_long=use_long,
    )
    return {
        "target_count": len(targets_by_id),
        "source_count": len(sources_by_id),
        "plans": plans,
        "summary": summary,
        "conversions": conversions,
        "missing_categories": missing_categories,
        "created_categories": created_categories,
    }


def apply_conversion_plan(plan: ConversionAssignmentPlan) -> bool:
    if not plan.override_enabled:
        return waapi_utils.set_object_property(plan.target, "OverrideConversion", False)
    if not waapi_utils.set_object_property(plan.target, "OverrideConversion", True):
        return False
    return waapi_utils.set_object_reference(plan.target, "Conversion", plan.conversion)


def apply_conversion_plans(plans: list[ConversionAssignmentPlan]) -> list[str]:
    if not plans:
        return []

    failed_ids = set()
    assignments = [(plan.target, plan.override_enabled) for plan in plans]
    if not waapi_utils.set_objects_property_values(assignments, "OverrideConversion"):
        for plan in plans:
            if not waapi_utils.set_object_property(plan.target, "OverrideConversion", plan.override_enabled):
                failed_ids.add(plan.target.id)

    reference_plans = [
        plan for plan in plans
        if plan.override_enabled and plan.target.id not in failed_ids
    ]
    reference_assignments = [(plan.target, plan.conversion.id) for plan in reference_plans]
    if reference_assignments and not waapi_utils.set_objects_property_values(
        reference_assignments, "Conversion"
    ):
        for plan in reference_plans:
            if not waapi_utils.set_object_reference(plan.target, "Conversion", plan.conversion):
                failed_ids.add(plan.target.id)

    return [
        plan.target.path or plan.target.name
        for plan in plans
        if plan.target.id in failed_ids
    ]
