# MCP 工具：类型归一；WwiseObject 对外输出用 wwise_dict（与 WAAPI 一致）
from __future__ import annotations

from libraries.wwise_object import WwiseObject, WwiseObjectType


def wwise_object_as_dict(obj: WwiseObject | None) -> dict:
    """将 WwiseObject 转为可 JSON 化的 dict（拷贝 wwise_dict，避免误改内部引用）。"""
    if not obj or not obj.wwise_dict:
        return {}
    return dict(obj.wwise_dict)


def wwise_objects_as_dicts(objs: list) -> list[dict]:
    return [wwise_object_as_dict(o) for o in objs]


def coerce_create_at_default_type(type_str: str):
    specials = {"Trigger", "Attenuation", "Conversion"}
    if type_str in specials:
        return type_str
    for member in WwiseObjectType:
        if member.value == type_str or member.name == type_str:
            return member
    return type_str
