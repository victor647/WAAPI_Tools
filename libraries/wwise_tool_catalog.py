# 自动生成：MCP legacy 工具的中立实现（AI 助手与 MCP 共用）。
# 生成逻辑见历史 waapi_mcp/utils_mcp_tools.py + waapi_mcp/waapi_mcp_tools.py；
# 手工改动请直接编辑本文件，并保持与注册表一致。
from __future__ import annotations

import inspect as _inspect

from libraries import tool_registry
from libraries.waapi_client import WAAPIClient
from libraries.wwise_object import WwiseObject, WwiseObjectType
from libraries.utils.wwise import (
    wwise_compat,
    waapi_utils,
    common_utils,
    audio_source_utils,
    game_sync_utils,
    soundbank_utils,
    localization_utils,
    project_utils,
    event_utils,
    container_utils,
    transport_utils,
    mixing_utils,
)


def wwise_object_as_dict(obj):
    if not obj or not obj.wwise_dict:
        return {}
    return dict(obj.wwise_dict)


def wwise_objects_as_dicts(objs):
    return [wwise_object_as_dict(o) for o in objs]


def coerce_create_at_default_type(type_str):
    specials = {"Trigger", "Attenuation", "Conversion"}
    if type_str in specials:
        return type_str
    for member in WwiseObjectType:
        if member.value == type_str or member.name == type_str:
            return member
    return type_str


def require_confirmation(confirmed):
    if not confirmed:
        raise ValueError("危险操作被拦截：请显式传入 confirmed=True 确认执行")


def _objs(ids):
    return [WwiseObject.dict_from_id(i) for i in ids]


def get_object_notes(object_id: str) -> str:
    return common_utils.get_object_notes(WwiseObject.from_id(object_id))

def is_object_included(object_id: str, check_ancestors: bool = True) -> bool:
    return common_utils.is_object_included(WwiseObject.from_id(object_id), check_ancestors=check_ancestors)

def set_object_inclusion(object_id: str, included: bool) -> bool:
    return common_utils.set_object_inclusion(WwiseObject.from_id(object_id), included)

def set_object_color(object_id: str, color: int) -> bool:
    return common_utils.set_object_color(WwiseObject.from_id(object_id), color)

def create_parent(object_id: str, target_type: str) -> dict:
    return wwise_object_as_dict(
        common_utils.create_parent(
            WwiseObject.from_id(object_id),
            WwiseObjectType(wwise_compat.resolve_wrapper_type(target_type)),
        ))

def create_folders_recursively(path: str) -> dict:
    return wwise_object_as_dict(common_utils.create_folders_recursively(path))

def split_underscore_to_folder(object_id: str) -> bool:
    return common_utils.split_underscore_to_folder(WwiseObject.from_id(object_id))

def convert_to_type(object_id: str, target_type: str) -> bool:
    return common_utils.convert_to_type(
        WwiseObject.from_id(object_id),
        WwiseObjectType(wwise_compat.resolve_wrapper_type(target_type)),
    )

def get_source_file_path(object_id: str) -> str:
    return audio_source_utils.get_source_absolute_path(WwiseObject.from_id(object_id))

def apply_source_edits(object_id: str, confirmed: bool) -> bool:
    require_confirmation(confirmed)
    return audio_source_utils.apply_source_edits(WwiseObject.from_id(object_id))

def reset_source_editor(object_id: str, confirmed: bool) -> bool:
    require_confirmation(confirmed)
    return audio_source_utils.reset_source_editor(WwiseObject.from_id(object_id))

def replace_audio_file(object_id: str, new_wav_path: str, language: str, confirmed: bool) -> bool:
    require_confirmation(confirmed)
    return audio_source_utils.replace_audio_file(WwiseObject.from_id(object_id), new_wav_path, language)

def auto_import_by_path(object_id: str, confirmed: bool) -> dict:
    require_confirmation(confirmed)
    return wwise_object_as_dict(audio_source_utils.auto_import_by_path(WwiseObject.from_id(object_id)))

def rename_original_to_wwise(object_id: str, confirmed: bool) -> bool:
    require_confirmation(confirmed)
    return audio_source_utils.rename_original_to_wwise(WwiseObject.from_id(object_id))

def tidy_original_folders(object_id: str, confirmed: bool) -> bool:
    require_confirmation(confirmed)
    return audio_source_utils.tidy_original_folders(WwiseObject.from_id(object_id))

def get_wav_subfolder(object_id: str, path: str = "") -> str:
    return audio_source_utils.get_wav_subfolder(WwiseObject.from_id(object_id), path)

def delete_unused_akd_files(confirmed: bool) -> None:
    require_confirmation(confirmed)
    audio_source_utils.delete_unused_akd_files()

def add_silence(object_id: str, duration: int, language: str) -> bool:
    return audio_source_utils.add_silence(WwiseObject.from_id(object_id), duration, language)

def get_sound_language(object_id: str) -> str:
    return localization_utils.get_sound_language(WwiseObject.from_id(object_id))

def get_default_language() -> str:
    return localization_utils.get_default_language()

def get_current_language() -> str:
    return localization_utils.get_current_language()

def get_all_language_names() -> list[str]:
    return localization_utils.get_all_language_names()

def is_localized(object_id: str) -> bool:
    return localization_utils.is_localized(WwiseObject.from_id(object_id))

def get_wave_path_for_language(object_id: str, language: str) -> str | None:
    return localization_utils.get_wave_path_for_language(WwiseObject.from_id(object_id), language)

def localize_languages(object_id: str) -> bool:
    return localization_utils.localize_languages(WwiseObject.from_id(object_id))

def import_silence(object_id: str, ref_language_only: bool) -> bool:
    if ref_language_only:
        return localization_utils.import_silence_for_ref_language(WwiseObject.from_id(object_id))
    else:
        return localization_utils.import_silence_for_all_languages(WwiseObject.from_id(object_id))

def create_bank_for_object(object_id: str) -> bool:
    return soundbank_utils.create_bank_for_object(WwiseObject.from_id(object_id))

def create_sound_bank_by_name(bank_name: str) -> dict:
    return wwise_object_as_dict(soundbank_utils.create_sound_bank_by_name(bank_name))

def get_total_bank_size(bank_object_ids: list[str]) -> dict[str, float | list[str]]:
    wav, mem, stream, used = soundbank_utils.get_total_bank_size([WwiseObject.from_id(i) for i in bank_object_ids])
    return {
        "wav_kb": wav,
        "memory_wem_kb": mem,
        "stream_wem_kb": stream,
        "used_wav_paths": used,
    }

def add_objects_to_bank(bank_object_id: str, object_ids: list[str], inclusion_type: list) -> bool:
    return soundbank_utils.add_objects_to_bank(WwiseObject.from_id(bank_object_id), [WwiseObject.from_id(i) for i in object_ids], inclusion_type)

def set_inclusion_type(bank_object_id: str, inclusion_types: list) -> bool:
    return soundbank_utils.set_inclusion_type(WwiseObject.from_id(bank_object_id), inclusion_types)

def break_container(object_id: str, confirmed: bool) -> bool:
    require_confirmation(confirmed)
    return container_utils.break_container(WwiseObject.from_id(object_id))

def replace_parent(object_id: str) -> bool:
    return container_utils.replace_parent(WwiseObject.from_id(object_id))

def auto_assign_switch_mappings(object_id: str) -> bool:
    return container_utils.auto_assign_switch_mappings(WwiseObject.from_id(object_id))

def get_available_switch_items(object_id: str) -> list[dict]:
    return wwise_objects_as_dicts(container_utils.get_available_switch_items(WwiseObject.from_id(object_id)))

def assign_to_generic_path(object_id: str) -> bool:
    return container_utils.assign_to_generic_path(WwiseObject.from_id(object_id))

def split_by_net_role(object_id: str, has_teammate: bool, has_enemy: bool, confirmed: bool) -> bool:
    require_confirmation(confirmed)
    return container_utils.split_by_net_role(WwiseObject.from_id(object_id), has_teammate, has_enemy)

def create_play_event(object_id: str, like_object_id: str | None = None) -> bool:
    like_object = WwiseObject.from_id(like_object_id) if like_object_id else None
    return event_utils.create_play_event(WwiseObject.from_id(object_id), like_object)

def create_event_action(event_object_id: str, target_object_id: str, action_type: int) -> dict:
    return wwise_object_as_dict(
        event_utils.create_event_action(
            WwiseObject.from_id(event_object_id), WwiseObject.from_id(target_object_id), action_type))

def clear_event_actions(object_id: str) -> bool:
    return event_utils.clear_event_actions(WwiseObject.from_id(object_id))

def get_event_targets(object_id: str) -> list[dict]:
    return wwise_objects_as_dicts(event_utils.get_event_targets(WwiseObject.from_id(object_id)))

def rename_event_by_target(object_id: str) -> bool:
    return event_utils.rename_event_by_target(WwiseObject.from_id(object_id))

def get_all_wave_paths(object_id: str, relative_path: bool) -> list[str]:
    return event_utils.get_all_wave_paths(WwiseObject.from_id(object_id), relative_path)

def clear_rtpc(object_id: str) -> bool:
    return game_sync_utils.clear_rtpc(WwiseObject.from_id(object_id))

def copy_rtpc(source_object_id: str, target_object_ids: list[str]) -> bool:
    return game_sync_utils.copy_rtpc(WwiseObject.from_id(source_object_id), [WwiseObject.from_id(i) for i in target_object_ids])

def clear_effects(object_id: str) -> bool:
    return mixing_utils.clear_effects(WwiseObject.from_id(object_id))

def get_or_create_bus(bus_name: str, parent_bus_object_id: str) -> dict:
    return wwise_object_as_dict(mixing_utils.get_or_create_bus(bus_name, WwiseObject.from_id(parent_bus_object_id)))

def set_output_bus(object_id: str, bus_object_id: str) -> bool:
    return mixing_utils.set_output_bus(WwiseObject.from_id(object_id), WwiseObject.from_id(bus_object_id))

def set_sound_3d(object_id: str, is3d: bool) -> None:
    mixing_utils.set_sound_3d(WwiseObject.from_id(object_id), is3d)

def play_sound(object_id: str) -> int:
    return transport_utils.play_sound(WwiseObject.from_id(object_id))

def stop_sound(transport_id: int) -> None:
    transport_utils.stop_sound(transport_id)

def get_project_path() -> str:
    return project_utils.get_project_path()

def get_project_directory() -> str:
    return project_utils.get_project_directory()

def get_originals_folder() -> str:
    return project_utils.get_originals_folder()

def get_project_version() -> int:
    return project_utils.get_project_version()

def save_project() -> bool:
    return project_utils.save_project()

def close_client() -> bool:
    WAAPIClient().disconnect()
    return True

def get_authoring_info(property_name: str) -> Any:
    return WAAPIClient().get_authoring_info(property_name)

def get_project_info(property_name: str) -> Any:
    return WAAPIClient().get_project_info(property_name)

def get_project_property(property_name: str) -> Any:
    return WAAPIClient().get_project_property(property_name)

def get_object_property(object_id: str, property_name: str) -> Any:
    return waapi_utils.get_object_property(WwiseObject.from_id(object_id), property_name)

def get_selected_objects() -> list:
    return WAAPIClient().get_selected_objects()

def get_object_references(object_id: str) -> list:
    return WAAPIClient().get_object_references(WwiseObject.dict_from_id(object_id))

def get_parent_object(object_id: str) -> Any:
    return WAAPIClient().get_parent_object(WwiseObject.dict_from_id(object_id))

def get_ancestor_objects(object_id: str) -> list:
    return WAAPIClient().get_ancestor_objects(WwiseObject.dict_from_id(object_id))

def get_child_objects(object_id: str, include_descendants: bool = False) -> list:
    return WAAPIClient().get_child_objects(WwiseObject.dict_from_id(object_id), include_descendants=include_descendants)

def get_full_info_from_obj_id(object_id: str) -> Any:
    return WAAPIClient().get_full_info_from_obj_id(object_id)

def find_object_by_path(path: str) -> Any:
    return WAAPIClient().find_object_by_path(path)

def find_object_by_name_and_type(obj_name: str, obj_type: str, exact_match: bool = True) -> Any:
    return WAAPIClient().find_object_by_name_and_type(obj_name, WwiseObjectType(obj_type).value, exact_match=exact_match)

def find_all_objects_by_name(obj_name: str, exact_match: bool) -> list:
    return WAAPIClient().find_all_objects_by_name(obj_name, exact_match)

def find_all_objects_by_type(obj_type: str) -> list:
    return WAAPIClient().find_all_objects_by_type(WwiseObjectType(obj_type).value)

def create_object_at_default_location(obj_name: str, obj_type: str) -> Any:
    t = coerce_create_at_default_type(obj_type)
    api_type = t.value if isinstance(t, WwiseObjectType) else t
    return WAAPIClient().create_object_at_default_location(obj_name, api_type)

def create_object_by_path(obj_path: str, obj_type: str, on_name_conflict: str = "fail") -> Any:
    return WAAPIClient().create_object_by_path(obj_path, obj_type, on_name_conflict=on_name_conflict)

def move_object(object_id: str, new_parent_object_id: str) -> bool:
    return WAAPIClient().move_object(WwiseObject.dict_from_id(object_id), WwiseObject.dict_from_id(new_parent_object_id))

def copy_object(object_id: str, parent_object_id: str) -> Any:
    return WAAPIClient().copy_object(WwiseObject.dict_from_id(object_id), WwiseObject.dict_from_id(parent_object_id))

def rename_object(object_id: str, new_name: str) -> bool:
    return WAAPIClient().rename_object(WwiseObject.dict_from_id(object_id), new_name)

def set_object_property(object_id: str, property_name: str, value: Any, platform: str | None = None) -> bool:
    return WAAPIClient().set_object_property(WwiseObject.dict_from_id(object_id), property_name, value, platform=platform)

def set_object_reference(object_id: str, reference_type: str, value_object_id: str) -> bool:
    return WAAPIClient().set_object_reference(WwiseObject.dict_from_id(object_id), reference_type, WwiseObject.dict_from_id(value_object_id))

def set_object_notes(object_id: str, notes: str) -> bool:
    return WAAPIClient().set_object_notes(WwiseObject.dict_from_id(object_id), notes)

def delete_object(object_id: str, confirmed: bool) -> bool:
    require_confirmation(confirmed)
    return WAAPIClient().delete_object(WwiseObject.dict_from_id(object_id))

def set_sequence_container_playlist(container_object_id: str, child_object_ids: list[str]) -> bool:
    return WAAPIClient().set_sequence_container_playlist(WwiseObject.dict_from_id(container_object_id), _objs(child_object_ids))

def get_switch_mappings(container_object_id: str) -> list:
    return WAAPIClient().get_switch_mappings(WwiseObject.dict_from_id(container_object_id))

def assign_switch_mapping(target_object_id: str, switch_object_id: str) -> bool:
    return WAAPIClient().assign_switch_mapping(WwiseObject.dict_from_id(target_object_id), WwiseObject.dict_from_id(switch_object_id))

def remove_switch_mappings(switch_container_object_id: str) -> bool:
    return WAAPIClient().remove_switch_mappings(WwiseObject.dict_from_id(switch_container_object_id))

def import_audio_file(wave_path: str, sound_object_id: str, language: str = "SFX") -> Any:
    return WAAPIClient().import_audio_file(wave_path, WwiseObject.dict_from_id(sound_object_id), language=language)

def get_default_audio_source(sound_object_id: str) -> Any:
    return WAAPIClient().get_default_audio_source(WwiseObject.dict_from_id(sound_object_id))

def get_bank_inclusions(bank_object_id: str) -> list:
    return WAAPIClient().get_bank_inclusions(WwiseObject.dict_from_id(bank_object_id))

def clear_bank_inclusions(bank_object_id: str, confirmed: bool) -> bool:
    require_confirmation(confirmed)
    return WAAPIClient().clear_bank_inclusions(WwiseObject.dict_from_id(bank_object_id))

def set_bank_inclusion(bank_object_id: str, inclusion: dict[str, Any],
                       replace: bool, inclusion_type: list[str] | None = None) -> bool:
    return WAAPIClient().set_bank_inclusion(WwiseObject.dict_from_id(bank_object_id), inclusion, replace, inclusion_type=inclusion_type)

def add_rtpc(target_object_id: str, rtpc_object_id: str, target_property: str, points: list) -> bool:
    return WAAPIClient().add_rtpc(WwiseObject.dict_from_id(target_object_id), WwiseObject.dict_from_id(rtpc_object_id), target_property, points)

def add_effect(object_id: str, share_set_name: str) -> bool:
    return WAAPIClient().add_effect(WwiseObject.dict_from_id(object_id), share_set_name)

def execute_ui_command(object_ids: list[str], command: str) -> bool:
    return WAAPIClient().execute_ui_command(_objs(object_ids), command)

def select_objects_in_wwise(object_ids: list[str]) -> bool:
    return WAAPIClient().select_objects_in_wwise(_objs(object_ids))

def bring_wwise_to_foreground() -> bool:
    return WAAPIClient().bring_wwise_to_foreground()

def begin_undo_group(action: str) -> bool:
    return WAAPIClient().begin_undo_group(action)

def end_undo_group(action: str) -> bool:
    return WAAPIClient().end_undo_group(action)

def undo() -> bool:
    return WAAPIClient().undo()

def redo() -> bool:
    return WAAPIClient().redo()

def add_to_source_control(file_path: str) -> bool:
    return WAAPIClient().add_to_source_control(file_path)

_ORDER = ["get_object_notes", "is_object_included", "set_object_inclusion", "set_object_color", "create_parent", "create_folders_recursively", "split_underscore_to_folder", "convert_to_type", "get_source_file_path", "apply_source_edits", "reset_source_editor", "replace_audio_file", "auto_import_by_path", "rename_original_to_wwise", "tidy_original_folders", "get_wav_subfolder", "delete_unused_akd_files", "add_silence", "get_sound_language", "get_default_language", "get_current_language", "get_all_language_names", "is_localized", "get_wave_path_for_language", "localize_languages", "import_silence", "create_bank_for_object", "create_sound_bank_by_name", "get_total_bank_size", "add_objects_to_bank", "set_inclusion_type", "break_container", "replace_parent", "auto_assign_switch_mappings", "get_available_switch_items", "assign_to_generic_path", "split_by_net_role", "create_play_event", "create_event_action", "clear_event_actions", "get_event_targets", "rename_event_by_target", "get_all_wave_paths", "clear_rtpc", "copy_rtpc", "clear_effects", "get_or_create_bus", "set_output_bus", "set_sound_3d", "play_sound", "stop_sound", "get_project_path", "get_project_directory", "get_originals_folder", "get_project_version", "save_project", "close_client", "get_authoring_info", "get_project_info", "get_project_property", "get_object_property", "get_selected_objects", "get_object_references", "get_parent_object", "get_ancestor_objects", "get_child_objects", "get_full_info_from_obj_id", "find_object_by_path", "find_object_by_name_and_type", "find_all_objects_by_name", "find_all_objects_by_type", "create_object_at_default_location", "create_object_by_path", "move_object", "copy_object", "rename_object", "set_object_property", "set_object_reference", "set_object_notes", "delete_object", "set_sequence_container_playlist", "get_switch_mappings", "assign_switch_mapping", "remove_switch_mappings", "import_audio_file", "get_default_audio_source", "get_bank_inclusions", "clear_bank_inclusions", "set_bank_inclusion", "add_rtpc", "add_effect", "execute_ui_command", "select_objects_in_wwise", "bring_wwise_to_foreground", "begin_undo_group", "end_undo_group", "undo", "redo", "add_to_source_control"]
_DESC = {"get_object_notes": "读取对象备注（Notes）。用户说「看备注/说明」时用它。", "is_object_included": "查询对象是否启用（勾选），check_ancestors=True 时连同父级判断。用户问「有没有启用/被停用」时用。", "set_object_inclusion": "启用/停用对象。included=True 启用、False 停用。", "set_object_color": "设置对象颜色值（数值色板索引，需配合工程色板）。", "create_parent": "在对象上方插入一层目标类型父级并把对象移入其下。target_type 支持 ActorMixer/BlendContainer/RandomSequenceContainer/SwitchContainer/Folder/WorkUnit。用户说「包一层/建父级」时用。", "create_folders_recursively": "按 Wwise 路径逐级创建缺失的 Folder/WorkUnit，返回末端对象。用户说「建目录结构/按路径创建」时用。", "split_underscore_to_folder": "把对象名中第一个下划线前的内容建为子文件夹、移入对象并去掉该前缀。", "convert_to_type": "把对象转换为其它容器类型（会复制子级、迁移 Switch 映射与引用，原对象重建、id 变化）；改类型前会读出全部属性，改完回填两个类型共有的属性/引用。target_type 传目标类型名。", "get_source_file_path": "读取对象/音频源的原始 wav 磁盘路径（originalWavFilePath）。", "apply_source_edits": "把 Source Editor 里的裁剪/淡变参数写入磁盘 wav 文件。危险：直接改源文件，必须 confirmed=true。", "reset_source_editor": "清空 Source Editor 的裁剪/淡变参数。危险，必须 confirmed=true。", "replace_audio_file": "用 new_wav_path 替换指定 language 下的样本，尽量保留原 Source 参数。危险，必须 confirmed=true。", "auto_import_by_path": "按 Originals 约定路径自动导入 wav（失败返回空对象）。危险（会导入文件），必须 confirmed=true。", "rename_original_to_wwise": "把磁盘 wav 文件名改成与 Wwise 对象一致。危险（磁盘改名），必须 confirmed=true。", "tidy_original_folders": "整理 Originals 子目录并更新引用。危险（移动磁盘文件），必须 confirmed=true。", "get_wav_subfolder": "向上解析最近的 Folder/WorkUnit 得到 wav 子目录片段；path 为空时自动推导。", "delete_unused_akd_files": "删除工程中无对应 wav 的 .akd 文件（全工程扫描）。危险，必须 confirmed=true。", "add_silence": "为语音对象添加静音源。duration 为秒数，language 为目标语言名（如 Chinese）。", "get_sound_language": "读取 Sound/AudioSource 的语言（SFX 或具体语言名）。用户问「这个语音是什么语言」时用。", "get_default_language": "读取工程默认语言。", "get_current_language": "读取当前编辑语言。", "get_all_language_names": "列出除 SFX/External/Mixed 外的全部语言名（铺本地化语言时用）。", "is_localized": "判断对象子树是否存在非 SFX 的语音（是否本地化）。", "get_wave_path_for_language": "取某 language 下语音样本的 wav 路径；没有返回 null。", "localize_languages": "按已有语言的样本路径把其它语言槽位一并导入。会向工程导入文件，谨慎使用。", "import_silence": "为语音补静音：ref_language_only=True 只补参考语言，False 补所有未导入语言。", "create_bank_for_object": "为对象创建/复用同名 SoundBank 并把对象加入包含。用户说「建 Bank」时用。", "create_sound_bank_by_name": "按名称创建 SoundBank（必要时自动建 WorkUnit/Folder 层级）。", "get_total_bank_size": "统计多个 Bank 的原始 wav / 内存 wem / 流式 wem 大小（KB）与文件列表。用户问「Bank 多大」时用。", "add_objects_to_bank": "把一批对象加入 Bank，inclusion_type 可取 events/structures/media（数组）。", "set_inclusion_type": "把 Bank 现有包含统一改为指定 inclusion_types 数组。", "break_container": "打散容器：子对象上移到上一层并删除容器。危险（破坏层级），必须 confirmed=true。", "replace_parent": "把对象跳过父级上移一层，并尽量修复 Switch 映射。", "auto_assign_switch_mappings": "按子对象名与 Switch 值自动分配 Switch 容器映射。", "get_available_switch_items": "列出 Switch 容器关联 Group 下可选的 Switch/State（分配前先查）。", "assign_to_generic_path": "把父 Switch 容器中未分配的子对象按通用路径补上映射。", "split_by_net_role": "把对象按 1P/2P/3P 拆分重组为 SwitchContainer。has_teammate=True 生成 2P，has_enemy=True 生成 3P。危险（大结构重组），必须 confirmed=true。", "create_play_event": "为对象创建或更新引用它的 Play Event（实现“能播放”）。", "create_event_action": "在事件下创建 EventAction 并指向目标对象。action_type 为 Wwise 动作类型值（1=Play 等）。", "clear_event_actions": "删除事件下的全部 Action。", "get_event_targets": "列出事件动作指向的目标对象。用户问「这个事件播什么」时用。", "rename_event_by_target": "单目标事件按播放对象推导并重命名事件名。", "get_all_wave_paths": "列出事件目标下所有 wav 路径；relative_path=True 时返回相对 Originals 的路径。", "clear_rtpc": "清空对象上的 RTPC 曲线。", "copy_rtpc": "把源对象上的 RTPC 复制（替换）到多个目标对象。", "clear_effects": "清空对象 Effects 效果器槽。", "get_or_create_bus": "按名称查找 Bus，不存在则在 parent_bus_object_id 下创建并返回。", "set_output_bus": "把对象 Output Bus 指向 bus_object_id（自动开启 OverrideOutput）。", "set_sound_3d": "设置对象 3D 定位：is3d=True 为 3D，False 为 2D。", "play_sound": "在 Transport 中播放对象，返回 transport_id（失败为 -1）；结束后用 stop_sound 停止。", "stop_sound": "停止并销毁指定 transport_id 的播放。", "get_project_path": "读取工程 .wproj 绝对路径。", "get_project_directory": "读取工程所在目录（.wproj 的上级）。", "get_originals_folder": "读取 Originals 根目录（音频源文件所在）。", "get_project_version": "读取 Wwise 主版本年份（如 2023，模块内缓存）。", "save_project": "保存工程（把 Wwise 里未保存的改动写回 .wproj 与各 WorkUnit 文件）。用户说「保存工程 / 存档 / save」时用。", "close_client": "断开并清理模块级全局 WaapiClient（与 GUI 共用同一 client 变量时需注意）。", "get_authoring_info": "读取 ak.wwise.core.getInfo 返回字典中的某字段（如 version、displayName）。", "get_project_info": "读取 ak.wwise.core.getProjectInfo 返回字典中的某字段。", "get_project_property": "在工程根「Project」对象上读取单个属性。", "get_object_property": "读取指定 Wwise 对象上某一属性的值（属性名随对象类型变化）。", "get_selected_objects": "获取当前在 Wwise 工程浏览器 / UI 中选中的对象列表。", "get_object_references": "查询「引用该对象」的所有对象。", "get_parent_object": "获取直接父对象。", "get_ancestor_objects": "从父级向上直到工程根的祖先链。", "get_child_objects": "获取子对象；include_descendants=True 时包含全部后代（WAAPIClient() 内部分页拉取）。", "get_full_info_from_obj_id": "仅根据 GUID 拉取 id/name/type/path 等基础字段。", "find_object_by_path": "按路径查找单个对象（与 get_object_from_path 实现细节略有不同，与 WAAPIClient() 保持一致）。", "find_object_by_name_and_type": "按名称 + 类型查找；exact_match 控制是否要求名称完全一致。", "find_all_objects_by_name": "在工程内按名称搜索（工程版本大于 2020 时用 WAQL search；exact_match=False 时返回搜索命中全部结果，常再在客户端按 type/名称前缀筛选）。", "find_all_objects_by_type": "列出某 Wwise 类型的全部对象。", "create_object_at_default_location": "在各类对象默认的 Work Unit 路径下创建对象（类型需与 WAAPIClient() 中分支一致）。", "create_object_by_path": "按完整 Wwise 路径（父路径 + 对象名）创建对象。", "move_object": "将对象移动到新的父对象下（改变层级）。", "copy_object": "在指定父对象下复制一份对象。", "rename_object": "重命名对象。", "set_object_property": "设置对象属性（如 Volume）；platform 非空时表示仅设置某平台覆盖。", "set_object_reference": "设置引用类属性，指向另一个对象（如 Output Bus 等）。", "set_object_notes": "设置对象的 Notes 文本。", "delete_object": "删除对象（含子树策略由 Wwise / API 决定）。", "set_sequence_container_playlist": "为顺序容器设置播放列表顺序（子对象 id 列表即顺序）。", "get_switch_mappings": "读取 Switch 容器当前的 Switch/State 分配列表。", "assign_switch_mapping": "为子对象分配对应的 Switch 或 State（switch_object_id 可为 GUID 字符串）。", "remove_switch_mappings": "移除该 Switch 容器下所有分配。", "import_audio_file": "将本地波形文件导入到指定 Sound 对象下（language 为导入语言，默认 SFX）。", "get_default_audio_source": "从 Sound 层级取第一个子对象（一般为 AudioFileSource）。", "get_bank_inclusions": "读取 SoundBank 的包含项列表。", "clear_bank_inclusions": "清空 SoundBank 的全部包含。", "set_bank_inclusion": "设置或追加 SoundBank 包含；replace 为 True 时整批替换；inclusion 结构见 WAAPIClient()。", "add_rtpc": "为目标对象追加一条 RTPC 曲线（控制点列表格式与 Wwise WAAPIClient() 一致）。", "add_effect": "追加一个 Effect 槽，引用指定名称的 ShareSet。", "execute_ui_command": "执行 Wwise 内置 UI 命令名（command 字符串与 Wwise 命令系统一致）。", "select_objects_in_wwise": "在工程浏览器中选中并 Inspect 指定对象。", "bring_wwise_to_foreground": "将 Wwise 主窗口置于前台。", "begin_undo_group": "开始一组可撤销操作（action 为显示名称相关描述）。", "end_undo_group": "结束撤销组。", "undo": "撤销一步。", "redo": "重做一步。", "add_to_source_control": "将文件路径加入 Wwise 源码管理（add）。"}
_SCHEMAS = {"get_object_notes": {}, "is_object_included": {}, "set_object_inclusion": {}, "set_object_color": {}, "create_parent": {}, "create_folders_recursively": {}, "split_underscore_to_folder": {}, "convert_to_type": {}, "get_source_file_path": {}, "apply_source_edits": {}, "reset_source_editor": {}, "replace_audio_file": {}, "auto_import_by_path": {}, "rename_original_to_wwise": {}, "tidy_original_folders": {}, "get_wav_subfolder": {}, "delete_unused_akd_files": {}, "add_silence": {}, "get_sound_language": {}, "get_default_language": {}, "get_current_language": {}, "get_all_language_names": {}, "is_localized": {}, "get_wave_path_for_language": {}, "localize_languages": {}, "import_silence": {}, "create_bank_for_object": {}, "create_sound_bank_by_name": {}, "get_total_bank_size": {}, "add_objects_to_bank": {}, "set_inclusion_type": {}, "break_container": {}, "replace_parent": {}, "auto_assign_switch_mappings": {}, "get_available_switch_items": {}, "assign_to_generic_path": {}, "split_by_net_role": {}, "create_play_event": {}, "create_event_action": {}, "clear_event_actions": {}, "get_event_targets": {}, "rename_event_by_target": {}, "get_all_wave_paths": {}, "clear_rtpc": {}, "copy_rtpc": {}, "clear_effects": {}, "get_or_create_bus": {}, "set_output_bus": {}, "set_sound_3d": {}, "play_sound": {}, "stop_sound": {}, "get_project_path": {}, "get_project_directory": {}, "get_originals_folder": {}, "get_project_version": {}, "save_project": {}, "close_client": {}, "get_authoring_info": {}, "get_project_info": {}, "get_project_property": {}, "get_object_property": {}, "get_selected_objects": {}, "get_object_references": {}, "get_parent_object": {}, "get_ancestor_objects": {}, "get_child_objects": {}, "get_full_info_from_obj_id": {}, "find_object_by_path": {}, "find_object_by_name_and_type": {}, "find_all_objects_by_name": {}, "find_all_objects_by_type": {}, "create_object_at_default_location": {}, "create_object_by_path": {}, "move_object": {}, "copy_object": {}, "rename_object": {}, "set_object_property": {}, "set_object_reference": {}, "set_object_notes": {}, "delete_object": {}, "set_sequence_container_playlist": {}, "get_switch_mappings": {}, "assign_switch_mapping": {}, "remove_switch_mappings": {}, "import_audio_file": {}, "get_default_audio_source": {}, "get_bank_inclusions": {}, "clear_bank_inclusions": {}, "set_bank_inclusion": {}, "add_rtpc": {}, "add_effect": {}, "execute_ui_command": {}, "select_objects_in_wwise": {}, "bring_wwise_to_foreground": {}, "begin_undo_group": {}, "end_undo_group": {}, "undo": {}, "redo": {}, "add_to_source_control": {}}
_MUTATING = {'get_object_notes': False, 'is_object_included': False, 'set_object_inclusion': True, 'set_object_color': True, 'create_parent': True, 'create_folders_recursively': True, 'split_underscore_to_folder': True, 'convert_to_type': True, 'get_source_file_path': False, 'apply_source_edits': True, 'reset_source_editor': True, 'replace_audio_file': True, 'auto_import_by_path': True, 'rename_original_to_wwise': True, 'tidy_original_folders': True, 'get_wav_subfolder': False, 'delete_unused_akd_files': True, 'add_silence': True, 'get_sound_language': False, 'get_default_language': False, 'get_current_language': False, 'get_all_language_names': False, 'is_localized': False, 'get_wave_path_for_language': False, 'localize_languages': True, 'import_silence': True, 'create_bank_for_object': True, 'create_sound_bank_by_name': True, 'get_total_bank_size': False, 'add_objects_to_bank': True, 'set_inclusion_type': True, 'break_container': True, 'replace_parent': True, 'auto_assign_switch_mappings': True, 'get_available_switch_items': False, 'assign_to_generic_path': True, 'split_by_net_role': True, 'create_play_event': True, 'create_event_action': True, 'clear_event_actions': True, 'get_event_targets': False, 'rename_event_by_target': True, 'get_all_wave_paths': False, 'clear_rtpc': True, 'copy_rtpc': True, 'clear_effects': True, 'get_or_create_bus': False, 'set_output_bus': True, 'set_sound_3d': True, 'play_sound': False, 'stop_sound': False, 'get_project_path': False, 'get_project_directory': False, 'get_originals_folder': False, 'get_project_version': False, 'save_project': True, 'close_client': False, 'get_authoring_info': False, 'get_project_info': False, 'get_project_property': False, 'get_object_property': False, 'get_selected_objects': False, 'get_object_references': False, 'get_parent_object': False, 'get_ancestor_objects': False, 'get_child_objects': False, 'get_full_info_from_obj_id': False, 'find_object_by_path': False, 'find_object_by_name_and_type': False, 'find_all_objects_by_name': False, 'find_all_objects_by_type': False, 'create_object_at_default_location': True, 'create_object_by_path': True, 'move_object': True, 'copy_object': True, 'rename_object': True, 'set_object_property': True, 'set_object_reference': True, 'set_object_notes': True, 'delete_object': True, 'set_sequence_container_playlist': True, 'get_switch_mappings': False, 'assign_switch_mapping': True, 'remove_switch_mappings': True, 'import_audio_file': True, 'get_default_audio_source': False, 'get_bank_inclusions': False, 'clear_bank_inclusions': True, 'set_bank_inclusion': True, 'add_rtpc': True, 'add_effect': True, 'execute_ui_command': True, 'select_objects_in_wwise': False, 'bring_wwise_to_foreground': False, 'begin_undo_group': False, 'end_undo_group': False, 'undo': False, 'redo': False, 'add_to_source_control': True}

# 迁移时快照没有携带参数 schema，这里按函数签名补全（_SCHEMAS 非空时仍以快照为准）
_PARAM_HINTS = {
    "object_id": "Wwise 对象 GUID",
    "object_ids": "Wwise 对象 GUID 数组",
    "bank_object_id": "SoundBank 对象 GUID",
    "bank_object_ids": "SoundBank 对象 GUID 数组",
    "target_object_id": "目标对象 GUID",
    "parent_object_id": "父对象 GUID",
    "switch_object_id": "Switch/State 对象 GUID",
    "bus_object_id": "Bus 对象 GUID",
    "parent_bus_object_id": "父 Bus 对象 GUID",
    "rtpc_object_id": "RTPC（GameParameter）对象 GUID",
    "event_object_id": "事件对象 GUID",
    "like_object_id": "参照对象 GUID：新 Event 会建在「播放该对象的现有 Event」所在层级（把容器子节点拆成独立 Event 时传原容器，避免另起一套 Events 目录）",
    "obj_name": "对象名称",
    "obj_type": "Wwise 类型（WwiseObjectType 值或名称，如 Sound / Event）",
    "target_type": "目标类型（WwiseObjectType 值或名称）",
    "property_name": "属性名（如 Volume / Pitch / Notes）",
    "value": "要设置的值",
    "included": "True 启用，False 停用",
    "color": "颜色值（数值色板索引）",
    "confirmed": "危险操作确认：用户明确要求后传 true",
    "language": "语言名（如 Chinese / SFX）",
    "path": "Wwise 路径或文件路径",
    "new_name": "新名称",
    "notes": "备注文本",
    "action": "撤销组显示名称",
    "command": "Wwise UI 命令名",
    "transport_id": "Transport ID",
    "relative_path": "True 返回相对 Originals 的路径",
    "ref_language_only": "True 只补参考语言",
    "duration": "静音时长（秒）",
    "bank_name": "SoundBank 名称",
    "inclusion_type": "包含类型数组（events/structures/media）",
    "inclusion_types": "包含类型数组（events/structures/media）",
    "slot_name": "列表型槽位名（如 RTPC / Effects）",
    "share_set_name": "效果器 ShareSet 名",
    "points": "RTPC 控制点数组",
    "platform": "平台名（留空表示默认）",
    "timeout": "执行时间上限（秒）",
}
_TYPE_KEYWORDS = {"str": "string", "int": "integer", "float": "number", "bool": "boolean"}


def _schema_type(annotation) -> dict:
    # 兼容 from __future__ annotations：注解多为字符串
    if annotation is _inspect.Parameter.empty:
        return {}
    text = annotation if isinstance(annotation, str) else getattr(annotation, "__name__", "")
    text = str(text).strip().strip("'\"")
    if text.startswith("list"):
        return {"type": "array", "items": {"type": "string"}}
    if text.startswith("dict"):
        return {"type": "object"}
    if text in _TYPE_KEYWORDS:
        return {"type": _TYPE_KEYWORDS[text]}
    return {}


def _signature_schema(fn) -> dict:
    properties = {}
    required = []
    for name, param in _inspect.signature(fn).parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        prop = _schema_type(param.annotation)
        prop["description"] = _PARAM_HINTS.get(name, "")
        properties[name] = prop
        if param.default is _inspect.Parameter.empty:
            required.append(name)
    return {"type": "object", "properties": properties, "required": required}


_EFFECTIVE_SCHEMAS = {}
for _name in _ORDER:
    _snapshot = _SCHEMAS.get(_name) or {}
    _EFFECTIVE_SCHEMAS[_name] = _snapshot if _snapshot.get("properties") else _signature_schema(globals()[_name])

_PROPS = {name: tuple(_EFFECTIVE_SCHEMAS[name].get("properties", {})) for name in _ORDER}


def _run_tool(name, arguments):
    WAAPIClient().connect()
    props = _PROPS[name]
    kwargs = {k: arguments[k] for k in props if k in arguments}
    return globals()[name](**kwargs)


for _name in _ORDER:
    tool_registry.register_tool(
        _name,
        _DESC[_name],
        _EFFECTIVE_SCHEMAS[_name],
        lambda args, n=_name: _run_tool(n, args),
        mutating=_MUTATING.get(_name, False),
    )
