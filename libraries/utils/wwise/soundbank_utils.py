import os
from libraries.utils import io_utils
from libraries.utils.wwise import common_utils, audio_source_utils, event_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType


# 为每个选中的对象创建一个SoundBank
def create_bank_for_object(obj: WwiseObject) -> bool:
    bank_name = common_utils.get_full_name_with_acronym(obj)
    if bank_name.startswith('Events_'):
        bank_name = bank_name[7:]
    bank = waapi_utils.find_object_by_name_and_type(bank_name, WwiseObjectType.SoundBank)
    if bank is None:
        bank = create_sound_bank_by_name(bank_name)
    else:
        print(f'SoundBank [{bank_name}] already exists, replacing its inclusion instead.')
    waapi_utils.set_bank_inclusion_object(bank, obj, True)
    common_utils.update_notes_and_color(obj)
    waapi_utils.select_objects_in_wwise([bank])
    return True

# 根据名字创建SoundBank
def create_sound_bank_by_name(bank_name: str) -> WwiseObject:
    if '_' in bank_name:
        parent_path = '\\SoundBanks\\' + bank_name.replace('_', '\\')
        parent_path = os.path.dirname(parent_path)
        parent = common_utils.create_folders_recursively(parent_path)
    else:
        parent_path = '\\SoundBanks\\Default Work Unit'
        parent = waapi_utils.find_object_by_path(parent_path)
    new_bank = waapi_utils.create_child_object(bank_name, WwiseObjectType.SoundBank, parent)
    return new_bank

# 计算多个Bank合计大小
def get_total_bank_size(banks: list) -> tuple:
    wav_size = memory_wem_size = stream_wem_size = 0
    used_files = []
    for bank in banks:
        if bank.type == WwiseObjectType.SoundBank:
            wav_size, memory_wem_size, stream_wem_size, used_files = get_bank_size(bank, wav_size, memory_wem_size, stream_wem_size, used_files)
    wav_size = round(wav_size / 1024, 2)
    memory_wem_size = round(memory_wem_size / 1024, 2)
    stream_wem_size = round(stream_wem_size / 1024, 2)
    return wav_size, memory_wem_size, stream_wem_size, used_files

# 传统方式获取Bank大小
def get_bank_size(bank: WwiseObject, total_wav_size: float, total_memory_wem_size: float, total_stream_wem_size: float, used_files: list) -> tuple:
    for inclusion in waapi_utils.get_bank_inclusions(bank):
        if 'media' in inclusion['filter']:
            inclusion_obj = waapi_utils.get_full_info_from_obj_id(inclusion['object'])
            # Bank包含Events中的内容
            if 'Events' in inclusion_obj.path:
                total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files = (
                    get_event_media_size(inclusion_obj, total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files))
            # Bank包含ActorMixerHierarchy中的内容
            else:
                total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files = (
                    get_object_media_size(inclusion_obj, total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files))
    return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files

# 获取Events中的对象包含的所有音频文件的大小
def get_event_media_size(obj: WwiseObject, total_wav_size: float, total_memory_wem_size: float, total_stream_wem_size: float, used_files: list) -> tuple:
    events = waapi_utils.get_descendants_of_type(obj, WwiseObjectType.Event)
    if len(events) > 0:
        for event in events:
            targets = event_utils.get_event_targets(event)
            for target in targets:
                total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files = (
                    get_object_media_size(target, total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files))
    return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files

# 获取ActorMixerHierarchy中的对象包含的所有音频文件的大小
def get_object_media_size(obj: WwiseObject, total_wav_size: float, total_memory_wem_size: float, total_stream_wem_size: float, used_files: list) -> tuple:
    audio_sources = waapi_utils.get_descendants_of_type(obj, WwiseObjectType.AudioSource)
    if len(audio_sources) > 0:
        for audio_source in audio_sources:
            wav_path = audio_source_utils.get_source_file_path(audio_source)
            if not os.path.exists(wav_path) or wav_path in used_files:
                continue
            used_files.append(wav_path)
            wav_size = os.path.getsize(wav_path) / 1024
            total_wav_size += wav_size
            print(f'{wav_path} has size of {wav_size}KB')
            wem_path = waapi_utils.get_object_property(audio_source, 'convertedWemFilePath')
            if os.path.exists(wem_path):
                wem_size = os.path.getsize(wem_path) / 1024
                is_streaming = waapi_utils.get_object_property(waapi_utils.get_parent_object(audio_source), 'IsStreamingEnabled')
                if is_streaming:
                    total_stream_wem_size += wem_size
                else:
                    total_memory_wem_size += wem_size
                print(f'{wem_path} has size of {wem_size}KB')
    return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files

# 把一批对象添加到的bank中，使用统一的inclusion
def add_objects_to_bank(bank: WwiseObject, objects: list, inclusion_type: list) -> bool:
    for obj in objects:
        waapi_utils.set_bank_inclusion_object(bank, obj, False, inclusion_type)
    return True

# 设置SoundBank的包含内容
def set_inclusion_type(bank: WwiseObject, inclusion_types: list) -> bool:
    if bank.type != WwiseObjectType.SoundBank:
        return False
    inclusions = waapi_utils.get_bank_inclusions(bank)
    success = False
    for inclusion in inclusions:
        success |= waapi_utils.set_bank_inclusion(bank, inclusion, False, inclusion_types)
    return success

# 为Bank添加内容，可选择是否清除已有内容
def set_inclusions(bank: WwiseObject, inclusion: dict, remove_existing: bool) -> bool:
    if remove_existing:
        waapi_utils.clear_bank_inclusions(bank)
    return waapi_utils.set_bank_inclusion(bank, inclusion, remove_existing)


def replace_bank_inclusion_with_object(bank: WwiseObject, included_obj: WwiseObject) -> bool:
    """清除 Bank 内全部包含后，仅包含指定对象（用于类型转换后刷新 SoundBank 引用）。"""
    waapi_utils.clear_bank_inclusions(bank)
    return waapi_utils.set_bank_inclusion_object(bank, included_obj, True)

# 生成所有Event与Bank的对应关系
def generate_event_bank_map():
    event_bank_map = {}
    all_banks = waapi_utils.find_all_objects_by_type(WwiseObjectType.SoundBank)
    for bank in all_banks:
        inclusions = waapi_utils.get_bank_inclusions(bank)
        for inclusion in inclusions:
            obj_id = inclusion['object']
            obj = waapi_utils.get_full_info_from_obj_id(obj_id)
            if obj.path.startswith('\\Events\\'):
                descendants = waapi_utils.get_descendants_of_type(obj, WwiseObjectType.Event)
                for event in descendants:
                    event_bank_map[event.name] = bank.name
    io_utils.export_to_json(event_bank_map, 'EventBankMap')
