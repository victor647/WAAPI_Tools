# 对 libraries.wwise.WAAPIClient() 的薄封装（GUID 入参）；不经 WwiseObject
from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

from libraries.waapi_client import WAAPIClient
from waapi_mcp.mcp_instance import mcp
from waapi_mcp.serialize import coerce_create_at_default_type

from libraries.wwise_object import WwiseObject, WwiseObjectType

F = TypeVar("F", bound=Callable[..., object])


def _ensure_waapi_client(fn: F) -> F:
    """在调用 WAAPIClient() 前创建/复用 WaapiClient（与 __main__ 中 get_client 行为一致）。"""

    @functools.wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> object:
        WAAPIClient().connect()
        return fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def _objs(ids: list[str]):
    return [WwiseObject.dict_from_id(i) for i in ids]


# ---------- 连接 ----------


@mcp.tool(description='断开并清理模块级全局 WaapiClient（与 GUI 共用同一 client 变量时需注意）。')
def close_client() -> bool:
    WAAPIClient().disconnect()
    return True


# ---------- 查询 ----------

@mcp.tool(description='读取 ak.wwise.core.getInfo 返回字典中的某字段（如 version、displayName）。')
@_ensure_waapi_client
def get_authoring_info(property_name: str) -> Any:
    return WAAPIClient().get_authoring_info(property_name)

@mcp.tool(description='读取 ak.wwise.core.getProjectInfo 返回字典中的某字段。')
@_ensure_waapi_client
def get_project_info(property_name: str) -> Any:
    return WAAPIClient().get_project_info(property_name)

@mcp.tool(description='在工程根「Project」对象上读取单个属性。')
@_ensure_waapi_client
def get_project_property(property_name: str) -> Any:
    return WAAPIClient().get_project_property(property_name)

@mcp.tool(description='读取指定 Wwise 对象上某一属性的值（属性名随对象类型变化）。')
@_ensure_waapi_client
def get_object_property(object_id: str, property_name: str) -> Any:
    return WAAPIClient().get_object_property(WwiseObject.dict_from_id(object_id), property_name)

@mcp.tool(description='获取当前在 Wwise 工程浏览器 / UI 中选中的对象列表。')
@_ensure_waapi_client
def get_selected_objects() -> list:
    return WAAPIClient().get_selected_objects()

@mcp.tool(description='按路径解析对象（内部随 Wwise 版本使用 WAQL 或 path 查询）。')
@_ensure_waapi_client
def get_object_from_path(path: str) -> Any:
    return WAAPIClient().get_object_from_path(path)

@mcp.tool(description='查询「引用该对象」的所有对象。')
@_ensure_waapi_client
def get_object_references(object_id: str) -> list:
    return WAAPIClient().get_object_references(WwiseObject.dict_from_id(object_id))


@mcp.tool(description='获取直接父对象。')
@_ensure_waapi_client
def get_parent_object(object_id: str) -> Any:
    return WAAPIClient().get_parent_object(WwiseObject.dict_from_id(object_id))

@mcp.tool(description='从父级向上直到工程根的祖先链。')
@_ensure_waapi_client
def get_ancestor_objects(object_id: str) -> list:
    return WAAPIClient().get_ancestor_objects(WwiseObject.dict_from_id(object_id))

@mcp.tool(description='获取子对象；include_descendants=True 时包含全部后代（WAAPIClient() 内部分页拉取）。')
@_ensure_waapi_client
def get_child_objects(object_id: str, include_descendants: bool = False) -> list:
    return WAAPIClient().get_child_objects(WwiseObject.dict_from_id(object_id), include_descendants=include_descendants)

@mcp.tool(description='仅根据 GUID 拉取 id/name/type/path 等基础字段。')
@_ensure_waapi_client
def get_full_info_from_obj_id(object_id: str) -> Any:
    return WAAPIClient().get_full_info_from_obj_id(object_id)

@mcp.tool(description='按路径查找单个对象（与 get_object_from_path 实现细节略有不同，与 WAAPIClient() 保持一致）。')
@_ensure_waapi_client
def find_object_by_path(path: str) -> Any:
    return WAAPIClient().find_object_by_path(path)

@mcp.tool(description='按名称 + 类型查找；exact_match 控制是否要求名称完全一致。')
@_ensure_waapi_client
def find_object_by_name_and_type(obj_name: str, obj_type: str, exact_match: bool = True) -> Any:
    return WAAPIClient().find_object_by_name_and_type(obj_name, WwiseObjectType(obj_type).value, exact_match=exact_match)

@mcp.tool(description='在工程内按名称搜索（工程版本大于 2020 时用 WAQL search；exact_match=False 时返回搜索命中全部结果，常再在客户端按 type/名称前缀筛选）。')
@_ensure_waapi_client
def find_all_objects_by_name(obj_name: str, exact_match: bool) -> list:
    return WAAPIClient().find_all_objects_by_name(obj_name, exact_match)

@mcp.tool(description='列出某 Wwise 类型的全部对象。')
@_ensure_waapi_client
def find_all_objects_by_type(obj_type: str) -> list:
    return WAAPIClient().find_all_objects_by_type(WwiseObjectType(obj_type).value)

# ---------- 通用对象操作 ----------

@mcp.tool(description='在各类对象默认的 Work Unit 路径下创建对象（类型需与 WAAPIClient() 中分支一致）。')
@_ensure_waapi_client
def create_object_at_default_location(obj_name: str, obj_type: str) -> Any:
    t = coerce_create_at_default_type(obj_type)
    api_type = t.value if isinstance(t, WwiseObjectType) else t
    return WAAPIClient().create_object_at_default_location(obj_name, api_type)

@mcp.tool(description='按完整 Wwise 路径（父路径 + 对象名）创建对象。')
@_ensure_waapi_client
def create_object_by_path(obj_path: str, obj_type: str, on_name_conflict: str = "fail") -> Any:
    return WAAPIClient().create_object_by_path(obj_path, obj_type, on_name_conflict=on_name_conflict)

@mcp.tool(description='将对象移动到新的父对象下（改变层级）。')
@_ensure_waapi_client
def move_object(object_id: str, new_parent_object_id: str) -> bool:
    return WAAPIClient().move_object(WwiseObject.dict_from_id(object_id), WwiseObject.dict_from_id(new_parent_object_id))

@mcp.tool(description='在指定父对象下复制一份对象。')
@_ensure_waapi_client
def copy_object(object_id: str, parent_object_id: str) -> Any:
    return WAAPIClient().copy_object(WwiseObject.dict_from_id(object_id), WwiseObject.dict_from_id(parent_object_id))

@mcp.tool(description='重命名对象。')
@_ensure_waapi_client
def rename_object(object_id: str, new_name: str) -> bool:
    return WAAPIClient().rename_object(WwiseObject.dict_from_id(object_id), new_name)

@mcp.tool(description='设置对象属性（如 Volume）；platform 非空时表示仅设置某平台覆盖。')
@_ensure_waapi_client
def set_object_property(object_id: str, property_name: str, value: Any, platform: str | None = None) -> bool:
    return WAAPIClient().set_object_property(WwiseObject.dict_from_id(object_id), property_name, value, platform=platform)

@mcp.tool(description='设置引用类属性，指向另一个对象（如 Output Bus 等）。')
@_ensure_waapi_client
def set_object_reference(object_id: str, reference_type: str, value_object_id: str) -> bool:
    return WAAPIClient().set_object_reference(WwiseObject.dict_from_id(object_id), reference_type, WwiseObject.dict_from_id(value_object_id))

@mcp.tool(description='设置对象的 Notes 文本。')
@_ensure_waapi_client
def set_object_notes(object_id: str, notes: str) -> bool:
    return WAAPIClient().set_object_notes(WwiseObject.dict_from_id(object_id), notes)

@mcp.tool(description='删除对象（含子树策略由 Wwise / API 决定）。')
@_ensure_waapi_client
def delete_object(object_id: str) -> bool:
    return WAAPIClient().delete_object(WwiseObject.dict_from_id(object_id))


# ---------- 逻辑容器（顺序 / Switch） ----------
@mcp.tool(description='为顺序容器设置播放列表顺序（子对象 id 列表即顺序）。')
@_ensure_waapi_client
def set_sequence_container_playlist(container_object_id: str, child_object_ids: list[str]) -> bool:
    return WAAPIClient().set_sequence_container_playlist(WwiseObject.dict_from_id(container_object_id), _objs(child_object_ids))

@mcp.tool(description='读取 Switch 容器当前的 Switch/State 分配列表。')
@_ensure_waapi_client
def get_switch_mappings(container_object_id: str) -> list:
    return WAAPIClient().get_switch_mappings(WwiseObject.dict_from_id(container_object_id))

@mcp.tool(description='为子对象分配对应的 Switch 或 State（switch_object_id 可为 GUID 字符串）。')
@_ensure_waapi_client
def assign_switch_mapping(target_object_id: str, switch_object_id: str) -> bool:
    return WAAPIClient().assign_switch_mapping(WwiseObject.dict_from_id(target_object_id), WwiseObject.dict_from_id(switch_object_id))

@mcp.tool(description='移除该 Switch 容器下所有分配。')
@_ensure_waapi_client
def remove_switch_mappings(switch_container_object_id: str) -> bool:
    return WAAPIClient().remove_switch_mappings(WwiseObject.dict_from_id(switch_container_object_id))


# ---------- 音频源 ----------

@mcp.tool(description='将本地波形文件导入到指定 Sound 对象下（language 为导入语言，默认 SFX）。')
@_ensure_waapi_client
def import_audio_file(wave_path: str, sound_object_id: str, language: str = "SFX") -> Any:
    return WAAPIClient().import_audio_file(wave_path, WwiseObject.dict_from_id(sound_object_id), language=language)

@mcp.tool(description='在对象下添加静音 SourcePlugin（length 等单位与 WAAPIClient() 一致）。')
@_ensure_waapi_client
def add_silence(object_id: str, length: int, language: str = "SFX") -> bool:
    return WAAPIClient().add_silence(WwiseObject.dict_from_id(object_id), length, language=language)

@mcp.tool(description='从 Sound 层级取第一个子对象（一般为 AudioFileSource）。')
@_ensure_waapi_client
def get_default_audio_source(sound_object_id: str) -> Any:
    return WAAPIClient().get_default_audio_source(WwiseObject.dict_from_id(sound_object_id))


# ---------- SoundBank ----------

@mcp.tool(description='读取 SoundBank 的包含项列表。')
@_ensure_waapi_client
def get_bank_inclusions(bank_object_id: str) -> list:
    return WAAPIClient().get_bank_inclusions(WwiseObject.dict_from_id(bank_object_id))

@mcp.tool(description='清空 SoundBank 的全部包含。')
@_ensure_waapi_client
def clear_bank_inclusions(bank_object_id: str) -> bool:
    return WAAPIClient().clear_bank_inclusions(WwiseObject.dict_from_id(bank_object_id))

@mcp.tool(description='设置或追加 SoundBank 包含；replace 为 True 时整批替换；inclusion 结构见 WAAPIClient()。')
@_ensure_waapi_client
def set_bank_inclusion(bank_object_id: str, inclusion: dict[str, Any],
                       replace: bool, inclusion_type: list[str] | None = None) -> bool:
    return WAAPIClient().set_bank_inclusion(WwiseObject.dict_from_id(bank_object_id), inclusion, replace, inclusion_type=inclusion_type)


# ---------- GameSync / 混音 ----------

@mcp.tool(description='为目标对象追加一条 RTPC 曲线（控制点列表格式与 Wwise WAAPIClient() 一致）。')
@_ensure_waapi_client
def add_rtpc(target_object_id: str, rtpc_object_id: str, target_property: str, points: list) -> bool:
    return WAAPIClient().add_rtpc(WwiseObject.dict_from_id(target_object_id), WwiseObject.dict_from_id(rtpc_object_id), target_property, points)

@mcp.tool(description='清空对象上某列表型属性（如 @RTPC、@Effects 等，槽位名与 WAAPIClient() 一致）。')
@_ensure_waapi_client
def clear_slots(object_id: str, slot_name: str) -> bool:
    return WAAPIClient().clear_slots(WwiseObject.dict_from_id(object_id), slot_name)

@mcp.tool(description='追加一个 Effect 槽，引用指定名称的 ShareSet。')
@_ensure_waapi_client
def add_effect(object_id: str, share_set_name: str) -> bool:
    return WAAPIClient().add_effect(WwiseObject.dict_from_id(object_id), share_set_name)


# ---------- 本地化 ----------

@mcp.tool(description='列出工程中所有 Language 对象（名称等）。')
@_ensure_waapi_client
def get_language_list() -> list:
    return WAAPIClient().get_language_list()


# ---------- Transport 播放 ----------

@mcp.tool(description='在 Transport 中播放该对象；返回 transport_id，供停止或销毁使用。')
@_ensure_waapi_client
def play_sound_in_transport(object_id: str) -> int:
    return WAAPIClient().play_sound_in_transport(WwiseObject.dict_from_id(object_id))

@mcp.tool(description='按 transport_id 停止播放并销毁 Transport。')
@_ensure_waapi_client
def stop_sound_in_transport(transport_id: int) -> bool:
    return WAAPIClient().stop_sound_in_transport(transport_id)

# ---------- UI / 撤销 / 源码管理 ----------

@mcp.tool(description='执行 Wwise 内置 UI 命令名（command 字符串与 Wwise 命令系统一致）。')
@_ensure_waapi_client
def execute_ui_command(object_ids: list[str], command: str) -> bool:
    return WAAPIClient().execute_ui_command(_objs(object_ids), command)

@mcp.tool(description='在工程浏览器中选中并 Inspect 指定对象。')
@_ensure_waapi_client
def select_objects_in_wwise(object_ids: list[str]) -> bool:
    return WAAPIClient().select_objects_in_wwise(_objs(object_ids))

@mcp.tool(description='将 Wwise 主窗口置于前台。')
@_ensure_waapi_client
def bring_wwise_to_foreground() -> bool:
    return WAAPIClient().bring_wwise_to_foreground()

@mcp.tool(description='开始一组可撤销操作（action 为显示名称相关描述）。')
@_ensure_waapi_client
def begin_undo_group(action: str) -> bool:
    return WAAPIClient().begin_undo_group(action)

@mcp.tool(description='结束撤销组。')
@_ensure_waapi_client
def end_undo_group(action: str) -> bool:
    return WAAPIClient().end_undo_group(action)

@mcp.tool(description='撤销一步。')
@_ensure_waapi_client
def undo() -> bool:
    return WAAPIClient().undo()

@mcp.tool(description='重做一步。')
@_ensure_waapi_client
def redo() -> bool:
    return WAAPIClient().redo()

@mcp.tool(description='将文件路径加入 Wwise 源码管理（add）。')
@_ensure_waapi_client
def add_to_source_control(file_path: str) -> bool:
    return WAAPIClient().add_to_source_control(file_path)
