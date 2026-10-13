from dataclasses import dataclass

from libraries.utils import user_config
from libraries.utils.wwise import audio_source_utils, waapi_utils
from libraries.wwise_object import WwiseObject


LONG_CATEGORY = "long"
SHORT_CATEGORY = "short"

# 占优比例的兜底默认值（配置里可改）：占比严格超过它才算某一种音效明显占优
DEFAULT_DOMINANCE_RATIO = 0.6


@dataclass
class ConversionAssignmentPlan:
    target: WwiseObject
    conversion: WwiseObject
    effective_category: str
    override_enabled: bool
    long_source_count: int
    short_source_count: int


def _path_prefixes(path: str) -> list[str]:
    parts = [part for part in (path or "").replace("/", "\\").split("\\") if part]
    return ["\\" + "\\".join(parts[:index]) for index in range(1, len(parts))]


# 本层是否被某一种音效明显占优：占比不超过阈值（如 40:60）或正好打平时返回 None，交给上层继承
def dominant_category(counts: dict, dominance_ratio: float) -> str:
    long_count = counts.get(LONG_CATEGORY, 0)
    short_count = counts.get(SHORT_CATEGORY, 0)
    total = long_count + short_count
    if not total or long_count == short_count:
        return None
    if max(long_count, short_count) / total <= dominance_ratio:
        return None
    return LONG_CATEGORY if long_count > short_count else SHORT_CATEGORY


def build_conversion_plans(
    targets: list[WwiseObject],
    audio_sources: list[WwiseObject],
    duration_by_source_id: dict,
    duration_threshold: float,
    long_conversion: WwiseObject,
    short_conversion: WwiseObject,
    dominance_ratio: float = None,
) -> tuple[list[ConversionAssignmentPlan], dict]:
    if dominance_ratio is None:
        dominance_ratio = user_config.get_tool_conversion_dominance_ratio()
    targets_by_id = {obj.id: obj for obj in targets if obj and obj.id}
    targets_by_path = {
        "\\" + "\\".join(part for part in obj.path.replace("/", "\\").split("\\") if part): obj
        for obj in targets_by_id.values()
        if obj.path
    }
    source_by_id = {obj.id: obj for obj in audio_sources if obj and obj.id}
    target_counts = {
        object_id: {LONG_CATEGORY: 0, SHORT_CATEGORY: 0}
        for object_id in targets_by_id
    }
    total_counts = {LONG_CATEGORY: 0, SHORT_CATEGORY: 0}
    valid_duration_count = 0

    for source in source_by_id.values():
        duration = audio_source_utils.get_audio_source_duration_seconds(
            duration_by_source_id.get(source.id)
        )
        if duration is None:
            continue
        category = LONG_CATEGORY if duration > duration_threshold else SHORT_CATEGORY
        total_counts[category] += 1
        valid_duration_count += 1
        for path in _path_prefixes(source.path):
            target = targets_by_path.get(path)
            if target:
                target_counts[target.id][category] += 1

    # 默认类别由全部样本的多数结果推导（即最上层根节点的判定结果），用户不需要手动指定
    default_category = (
        LONG_CATEGORY if total_counts[LONG_CATEGORY] >= total_counts[SHORT_CATEGORY] else SHORT_CATEGORY
    )
    conversion_by_category = {
        LONG_CATEGORY: long_conversion,
        SHORT_CATEGORY: short_conversion,
    }
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
    plans = []
    for target in sorted_targets:
        parent_id = parent_by_id.get(target.id)
        parent_category = effective_category_by_id.get(parent_id)
        counts = target_counts[target.id]
        if parent_category is None:
            category = default_category
            override_enabled = True
        else:
            # 占比不够明显时继承上层，把 override 留给更下层的节点
            category = dominant_category(counts, dominance_ratio) or parent_category
            override_enabled = category != parent_category
        effective_category_by_id[target.id] = category
        plans.append(ConversionAssignmentPlan(
            target=target,
            conversion=conversion_by_category[category],
            effective_category=category,
            override_enabled=override_enabled,
            long_source_count=counts[LONG_CATEGORY],
            short_source_count=counts[SHORT_CATEGORY],
        ))

    return plans, {
        "long_count": total_counts[LONG_CATEGORY],
        "short_count": total_counts[SHORT_CATEGORY],
        "default_category": default_category,
        "valid_duration_count": valid_duration_count,
        "unclassified_count": len(source_by_id) - valid_duration_count,
        "override_enable_count": sum(plan.override_enabled for plan in plans),
        "dominance_ratio": dominance_ratio,
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
