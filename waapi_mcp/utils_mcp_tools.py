# 将 libraries.wwise 下 *_utils 封装为 MCP tool；对象参数一律为 GUID 字符串
from __future__ import annotations

import functools
from typing import Callable, TypeVar

from waapi_mcp.mcp_instance import mcp
from waapi_mcp.serialize import wwise_object_as_dict, wwise_objects_as_dicts

from libraries.waapi_client import WAAPIClient
from libraries.wwise_object import WwiseObject, WwiseObjectType
from libraries.utils.wwise import common_utils, audio_source_utils, game_sync_utils, soundbank_utils, \
    localization_utils, project_utils, event_utils, container_utils, transport_utils, mixing_utils

F = TypeVar("F", bound=Callable[..., object])


def _ensure_waapi_client(fn: F) -> F:
    """在调用 waapi_utils / *_utils 前创建/复用 WaapiClient。"""

    @functools.wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> object:
        WAAPIClient().connect()
        return fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


# ---------- common_utils ----------


# 读取 Notes 文本
@mcp.tool()
@_ensure_waapi_client
def get_object_notes(object_id: str) -> str:
    return common_utils.get_object_notes(WwiseObject.from_id(object_id))


# Actor-Mixer 等层级中是否启用 Inclusion
@mcp.tool()
@_ensure_waapi_client
def is_object_included(object_id: str, check_ancestors: bool = True) -> bool:
    return common_utils.is_object_included(WwiseObject.from_id(object_id), check_ancestors=check_ancestors)


# 设置 Inclusion 开关
@mcp.tool()
@_ensure_waapi_client
def set_object_inclusion(object_id: str, included: bool) -> bool:
    return common_utils.set_object_inclusion(WwiseObject.from_id(object_id), included)


# 设置颜色值
@mcp.tool()
@_ensure_waapi_client
def set_object_color(object_id: str, color: int) -> bool:
    return common_utils.set_object_color(WwiseObject.from_id(object_id), color)


# 名称改为小写
@mcp.tool()
@_ensure_waapi_client
def rename_to_lower_case(object_id: str) -> bool:
    return common_utils.rename_to_lower_case(WwiseObject.from_id(object_id))


# 名称改为 Title Case
@mcp.tool()
@_ensure_waapi_client
def rename_to_title_case(object_id: str) -> bool:
    return common_utils.rename_to_title_case(WwiseObject.from_id(object_id))


# 名称改为大写
@mcp.tool()
@_ensure_waapi_client
def rename_to_upper_case(object_id: str) -> bool:
    return common_utils.rename_to_upper_case(WwiseObject.from_id(object_id))


# 在父级下插入一层指定类型父对象，并把对象移入其下
@mcp.tool()
@_ensure_waapi_client
def create_parent(object_id: str, target_type: str) -> dict:
    return wwise_object_as_dict(
        common_utils.create_parent(WwiseObject.from_id(object_id), WwiseObjectType(target_type)))


# 按路径逐级创建 Folder/WorkUnit，返回末端对象
@mcp.tool()
@_ensure_waapi_client
def create_folders_recursively(path: str) -> dict:
    return wwise_object_as_dict(common_utils.create_folders_recursively(path))


# 按下划线第一段建文件夹并移入、重命名剩余部分
@mcp.tool()
@_ensure_waapi_client
def split_underscore_to_folder(object_id: str) -> bool:
    return common_utils.split_underscore_to_folder(WwiseObject.from_id(object_id))


# 转换对象类型（复制子级、迁移 Switch 映射与引用）
@mcp.tool()
@_ensure_waapi_client
def convert_to_type(object_id: str, target_type: str) -> bool:
    return common_utils.convert_to_type(WwiseObject.from_id(object_id), WwiseObjectType(target_type))


# 从一批对象中按 Inclusion 状态筛选
@mcp.tool()
@_ensure_waapi_client
def filter_objects_by_inclusion(object_ids: list[str], inclusion: bool) -> list[dict]:
    return wwise_objects_as_dicts(
        common_utils.filter_objects_by_inclusion([WwiseObject.from_id(i) for i in object_ids], inclusion))


# 从一批对象中按类型名筛选（filter_type 可为 All）
@mcp.tool()
@_ensure_waapi_client
def filter_objects_by_type(object_ids: list[str], filter_type: str) -> list[dict]:
    return wwise_objects_as_dicts(
        common_utils.filter_objects_by_type([WwiseObject.from_id(i) for i in object_ids], filter_type))


# ---------- audio_source_utils ----------


# originalWavFilePath
@mcp.tool()
@_ensure_waapi_client
def get_source_file_path(object_id: str) -> str:
    return audio_source_utils.get_source_file_path(WwiseObject.from_id(object_id))


# 自根对象收集去重后的 wav 路径
@mcp.tool()
@_ensure_waapi_client
def get_all_audio_file_paths(object_id: str) -> list[str]:
    return audio_source_utils.get_all_audio_file_paths(WwiseObject.from_id(object_id))


# 将 Source Editor 裁剪/淡变写入磁盘 wav
@mcp.tool()
@_ensure_waapi_client
def apply_source_edits(object_id: str) -> bool:
    return audio_source_utils.apply_source_edits(WwiseObject.from_id(object_id))


# 重置裁剪与淡变参数
@mcp.tool()
@_ensure_waapi_client
def reset_source_editor(object_id: str) -> bool:
    return audio_source_utils.reset_source_editor(WwiseObject.from_id(object_id))


# 替换样本并尽量保留原 Source 参数
@mcp.tool()
@_ensure_waapi_client
def replace_audio_file(object_id: str, new_wav_path: str, language: str) -> bool:
    return audio_source_utils.replace_audio_file(WwiseObject.from_id(object_id), new_wav_path, language)


# 按 Originals 下约定路径自动导入 wav（失败返回空对象）
@mcp.tool()
@_ensure_waapi_client
def auto_import_by_path(object_id: str) -> dict:
    return wwise_object_as_dict(audio_source_utils.auto_import_by_path(WwiseObject.from_id(object_id)))


# 将磁盘 wav 文件名对齐 Wwise 命名
@mcp.tool()
@_ensure_waapi_client
def rename_original_to_wwise(object_id: str) -> bool:
    return audio_source_utils.rename_original_to_wwise(WwiseObject.from_id(object_id))


# 整理 Originals 子目录并更新引用
@mcp.tool()
@_ensure_waapi_client
def tidy_original_folders(object_id: str) -> bool:
    return audio_source_utils.tidy_original_folders(WwiseObject.from_id(object_id))


# 向上解析最近的 Folder/WorkUnit 得到 wav 子目录片段
@mcp.tool()
@_ensure_waapi_client
def get_wav_subfolder(object_id: str, path: str = "") -> str:
    return audio_source_utils.get_wav_subfolder(WwiseObject.from_id(object_id), path)


# 删除无对应 wav 的 .akd 文件（整工程扫描）
@mcp.tool()
@_ensure_waapi_client
def delete_unused_akd_files() -> None:
    audio_source_utils.delete_unused_akd_files()


# 为语音添加静音（工程版本大于 2021 走 WAAPI.add_silence，否则生成静音 wav）
@mcp.tool()
@_ensure_waapi_client
def add_silence(object_id: str, duration: int, language: str) -> bool:
    return audio_source_utils.add_silence(WwiseObject.from_id(object_id), duration, language)


# ---------- localization_utils ----------


# Sound/AudioSource 的语言名
@mcp.tool()
@_ensure_waapi_client
def get_sound_language(object_id: str) -> str:
    return localization_utils.get_sound_language(WwiseObject.from_id(object_id))


# 工程默认语言
@mcp.tool()
@_ensure_waapi_client
def get_default_language() -> str:
    return localization_utils.get_default_language()


# 当前编辑语言
@mcp.tool()
@_ensure_waapi_client
def get_current_language() -> str:
    return localization_utils.get_current_language()


# 除 SFX/External/Mixed 外的语言名列表
@mcp.tool()
@_ensure_waapi_client
def get_all_language_names() -> list[str]:
    return localization_utils.get_all_language_names()


# 子树是否存在非 SFX 的语音
@mcp.tool()
@_ensure_waapi_client
def is_localized(object_id: str) -> bool:
    return localization_utils.is_localized(WwiseObject.from_id(object_id))


# 某语言下 wav 绝对路径
@mcp.tool()
@_ensure_waapi_client
def get_wave_path_for_language(object_id: str, language: str) -> str | None:
    return localization_utils.get_wave_path_for_language(WwiseObject.from_id(object_id), language)


# 按已有语言路径批量复制到其他语言槽位
@mcp.tool()
@_ensure_waapi_client
def localize_languages(object_id: str) -> bool:
    return localization_utils.localize_languages(WwiseObject.from_id(object_id))


# 为参考语言导入静音（返回 bool 或内部结果）
@mcp.tool()
@_ensure_waapi_client
def import_silence(object_id: str, ref_language_only: bool) -> bool:
    if ref_language_only:
        return localization_utils.import_silence_for_ref_language(WwiseObject.from_id(object_id))
    else:
        return localization_utils.import_silence_for_all_languages(WwiseObject.from_id(object_id))


# ---------- soundbank_utils ----------


# 为对象创建/复用 SoundBank 并设置 inclusion
@mcp.tool()
@_ensure_waapi_client
def create_bank_for_object(object_id: str) -> bool:
    return soundbank_utils.create_bank_for_object(WwiseObject.from_id(object_id))


# 按名称创建 SoundBank 对象
@mcp.tool()
@_ensure_waapi_client
def create_sound_bank_by_name(bank_name: str) -> dict:
    return wwise_object_as_dict(soundbank_utils.create_sound_bank_by_name(bank_name))


# 多 Bank 合计体积（KB）与已计 wav 路径列表
@mcp.tool()
@_ensure_waapi_client
def get_total_bank_size(bank_object_ids: list[str]) -> dict[str, float | list[str]]:
    wav, mem, stream, used = soundbank_utils.get_total_bank_size([WwiseObject.from_id(i) for i in bank_object_ids])
    return {
        "wav_kb": wav,
        "memory_wem_kb": mem,
        "stream_wem_kb": stream,
        "used_wav_paths": used,
    }


# 批量向 Bank 追加 inclusion
@mcp.tool()
@_ensure_waapi_client
def add_objects_to_bank(bank_object_id: str, object_ids: list[str], inclusion_type: list) -> bool:
    return soundbank_utils.add_objects_to_bank(WwiseObject.from_id(bank_object_id), [WwiseObject.from_id(i) for i in object_ids], inclusion_type)


# 对 Bank 现有 inclusion 统一设置 inclusion 类型列表
@mcp.tool()
@_ensure_waapi_client
def set_inclusion_type(bank_object_id: str, inclusion_types: list) -> bool:
    return soundbank_utils.set_inclusion_type(WwiseObject.from_id(bank_object_id), inclusion_types)


# ---------- container_utils ----------


# 打散容器，子对象移到上一层并删除容器
@mcp.tool()
@_ensure_waapi_client
def break_container(object_id: str) -> bool:
    return container_utils.break_container(WwiseObject.from_id(object_id))


# 跳过父级上移并尝试修复 Switch 映射
@mcp.tool()
@_ensure_waapi_client
def replace_parent(object_id: str) -> bool:
    return container_utils.replace_parent(WwiseObject.from_id(object_id))


# 按子对象与 Switch 名匹配自动分配
@mcp.tool()
@_ensure_waapi_client
def auto_assign_switch_mappings(object_id: str) -> bool:
    return container_utils.auto_assign_switch_mappings(WwiseObject.from_id(object_id))


# Switch 容器关联的 Group 下可选值
@mcp.tool()
@_ensure_waapi_client
def get_available_switch_items(object_id: str) -> list[dict]:
    return wwise_objects_as_dicts(container_utils.get_available_switch_items(WwiseObject.from_id(object_id)))


# 为父 Switch 容器中未分配项补映射
@mcp.tool()
@_ensure_waapi_client
def assign_to_generic_path(object_id: str) -> bool:
    return container_utils.assign_to_generic_path(WwiseObject.from_id(object_id))


# 按 1P/2P/3P 拆分为 SwitchContainer 并设置 Bus/3D
@mcp.tool()
@_ensure_waapi_client
def split_by_net_role(object_id: str, has_teammate: bool, has_enemy: bool) -> bool:
    return container_utils.split_by_net_role(WwiseObject.from_id(object_id), has_teammate, has_enemy)


# ---------- event_utils ----------


# 创建或更新 Play 事件指向该对象
@mcp.tool()
@_ensure_waapi_client
def create_play_event(object_id: str) -> bool:
    return event_utils.create_play_event(WwiseObject.from_id(object_id))


# 在事件下创建 EventAction 并设目标
@mcp.tool()
@_ensure_waapi_client
def create_event_action(event_object_id: str, target_object_id: str, action_type: int) -> dict:
    return wwise_object_as_dict(
        event_utils.create_event_action(
            WwiseObject.from_id(event_object_id), WwiseObject.from_id(target_object_id), action_type))


# 删除事件下全部动作
@mcp.tool()
@_ensure_waapi_client
def clear_event_actions(object_id: str) -> bool:
    return event_utils.clear_event_actions(WwiseObject.from_id(object_id))


# 事件动作的目标对象列表
@mcp.tool()
@_ensure_waapi_client
def get_event_targets(object_id: str) -> list[dict]:
    return wwise_objects_as_dicts(event_utils.get_event_targets(WwiseObject.from_id(object_id)))


# 单目标事件按目标推导名重命名
@mcp.tool()
@_ensure_waapi_client
def rename_event_by_target(object_id: str) -> bool:
    return event_utils.rename_event_by_target(WwiseObject.from_id(object_id))


# 事件目标下所有 wav 路径
@mcp.tool()
@_ensure_waapi_client
def get_all_wave_paths(object_id: str, relative_path: bool) -> list[str]:
    return event_utils.get_all_wave_paths(WwiseObject.from_id(object_id), relative_path)


# ---------- game_sync_utils ----------


# 清空 RTPC 槽
@mcp.tool()
@_ensure_waapi_client
def clear_rtpc(object_id: str) -> bool:
    return game_sync_utils.clear_rtpc(WwiseObject.from_id(object_id))


# 从源对象粘贴 Rtpc 到多个目标
@mcp.tool()
@_ensure_waapi_client
def copy_rtpc(source_object_id: str, target_object_ids: list[str]) -> bool:
    return game_sync_utils.copy_rtpc(WwiseObject.from_id(source_object_id), [WwiseObject.from_id(i) for i in target_object_ids])


# ---------- mixing_utils ----------

# 清空 Effects 槽
@mcp.tool()
@_ensure_waapi_client
def clear_effects(object_id: str) -> bool:
    return mixing_utils.clear_effects(WwiseObject.from_id(object_id))


# 按名查找或创建 Bus
@mcp.tool()
@_ensure_waapi_client
def get_or_create_bus(bus_name: str, parent_bus_object_id: str) -> dict:
    return wwise_object_as_dict(mixing_utils.get_or_create_bus(bus_name, WwiseObject.from_id(parent_bus_object_id)))


# 设置 OutputBus
@mcp.tool()
@_ensure_waapi_client
def set_output_bus(object_id: str, bus_object_id: str) -> bool:
    return mixing_utils.set_output_bus(WwiseObject.from_id(object_id), WwiseObject.from_id(bus_object_id))


# 设置 3D Spatialization
@mcp.tool()
@_ensure_waapi_client
def set_sound_3d(object_id: str, is3d: bool) -> None:
    mixing_utils.set_sound_3d(WwiseObject.from_id(object_id), is3d)

# ---------- transport_utils ----------


# Transport 播放，返回 transport_id（失败为 -1）
@mcp.tool()
@_ensure_waapi_client
def play_sound(object_id: str) -> int:
    return transport_utils.play_sound(WwiseObject.from_id(object_id))


# 停止并销毁 Transport
@mcp.tool()
@_ensure_waapi_client
def stop_sound(transport_id: int) -> None:
    transport_utils.stop_sound(transport_id)


# ---------- project_utils ----------


# 工程 .wproj 路径
@mcp.tool()
@_ensure_waapi_client
def get_project_path() -> str:
    return project_utils.get_project_path()


# 工程所在目录
@mcp.tool()
@_ensure_waapi_client
def get_project_directory() -> str:
    return project_utils.get_project_directory()


# Originals 根目录
@mcp.tool()
@_ensure_waapi_client
def get_originals_folder() -> str:
    return project_utils.get_originals_folder()


# Wwise 主版本年（缓存）
@mcp.tool()
@_ensure_waapi_client
def get_project_version() -> int:
    return project_utils.get_project_version()
