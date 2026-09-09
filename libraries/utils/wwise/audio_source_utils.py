import os
import soundfile
from data import project_conventions
from libraries.utils import audio_utils, path_utils
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import common_utils, localization_utils, project_utils, event_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType


# 检测Sound是否播放样本，还是播放其他插件
def sound_play_from_plugin(sound: WwiseObject) -> bool:
    children = waapi_utils.get_child_objects(sound)
    if len(children) == 0:
        return False
    for child in children:
        if child.type != WwiseObjectType.AudioSource:
            return True
    return False

# 获取当前Sound下面指定语言的AudioSource并删除
def delete_audio_source_by_language(sound: WwiseObject, language: str) -> bool:
    if sound.type != WwiseObjectType.Sound:
        return False
    audio_sources = waapi_utils.get_child_objects(sound)
    for audio_source in audio_sources:
        source_language = localization_utils.get_sound_language(audio_source)
        if source_language == language:
            return waapi_utils.delete_object(audio_source)
    return False

# 获取音效的源文件路径
def get_source_file_path(sound_or_source: WwiseObject) -> str:
    return waapi_utils.get_object_property(sound_or_source, 'sound:originalWavFilePath')

# 获取源文件相对路径
def get_source_relative_path(sound_or_source: WwiseObject) -> str:
    full_path = get_source_file_path(sound_or_source)
    original_path = project_utils.get_originals_folder()
    return os.path.relpath(full_path, original_path)


# 把 Originals 下的绝对路径转为相对路径（等同 Wwise 的 originalRelativeFilePath）；否则原样返回
def to_originals_relative_path(file_path: str) -> str:
    if not file_path:
        return file_path
    try:
        originals_folder = project_utils.get_originals_folder()
        relative_path = os.path.relpath(file_path, originals_folder)
    except (TypeError, ValueError):
        return file_path
    if relative_path.startswith("..") or os.path.isabs(relative_path):
        return file_path
    return relative_path


# 自根对象递归收集其下所有音频源文件路径（Event 通过 event_utils 解析 targets；结果按路径去重）
def get_all_audio_file_paths(root: WwiseObject) -> list[str]:
    if not root or not root.id:
        return []

    collected: list[str] = []
    visited_containers: set[str] = set()

    def visit(obj: WwiseObject) -> None:
        if not obj or not obj.id:
            return

        if obj.type == WwiseObjectType.Sound or obj.type == WwiseObjectType.AudioSource:
            path = get_source_file_path(obj)
            if path:
                collected.extend(path)
            return
        if obj.type == WwiseObjectType.Event:
            for target in event_utils.get_event_targets(obj):
                visit(target)
            return
        if obj.id in visited_containers:
            return
        visited_containers.add(obj.id)

        for child in waapi_utils.get_child_objects(obj):
            visit(child)

    visit(root)
    return list(dict.fromkeys(p for p in collected if p))

# 获取Source Editor里的裁剪信息（返回 TrimBegin/TrimEnd/FadeIn/FadeOut/LoopBegin/LoopEnd）
def get_source_edit_info(obj: WwiseObject):
    if obj.type != WwiseObjectType.AudioSource:
        return None
    trim_begin = waapi_utils.get_object_property(obj, 'TrimBegin')
    trim_end = waapi_utils.get_object_property(obj, 'TrimEnd')
    fade_in = waapi_utils.get_object_property(obj, 'FadeInDuration')
    fade_out = waapi_utils.get_object_property(obj, 'FadeOutDuration')
    loop_begin = waapi_utils.get_object_property(obj, 'LoopBegin')
    loop_end = waapi_utils.get_object_property(obj, 'LoopEnd')
    return trim_begin, trim_end, fade_in, fade_out, loop_begin, loop_end


# 写入Source Editor里的裁剪信息
def set_source_edit_info(
    obj: WwiseObject,
    trim_begin,
    trim_end,
    fade_in,
    fade_out,
    loop_begin,
    loop_end,
) -> bool:
    if obj.type != WwiseObjectType.AudioSource:
        return False
    modified = True
    modified &= waapi_utils.set_object_property(obj, 'TrimBegin', trim_begin)
    modified &= waapi_utils.set_object_property(obj, 'TrimEnd', trim_end)
    modified &= waapi_utils.set_object_property(obj, 'FadeInDuration', fade_in)
    modified &= waapi_utils.set_object_property(obj, 'FadeOutDuration', fade_out)
    modified &= waapi_utils.set_object_property(obj, 'LoopBegin', loop_begin)
    modified &= waapi_utils.set_object_property(obj, 'LoopEnd', loop_end)
    return modified


# 将Source Editor里编辑的信息写入源文件中
def apply_source_edits(obj: WwiseObject) -> bool:
    modified = False
    if obj.type == WwiseObjectType.Sound:
        for child in waapi_utils.get_child_objects(obj):
            modified |= apply_source_edits(child)
        return modified
    elif obj.type != WwiseObjectType.AudioSource:
        return False
    source_path = get_source_file_path(obj)
    if not source_path:
        return False
    trim_begin, trim_end, fade_in, fade_out, _, _ = get_source_edit_info(obj)
    sound_file = soundfile.SoundFile(file=source_path)
    sound_data = sound_file.read()
    sample_rate = sound_file.samplerate
    if trim_end > 0:
        sound_data = audio_utils.trim(sound_data, 0, trim_end * sample_rate)
    if trim_begin > 0:
        sound_data = audio_utils.trim(sound_data, trim_begin * sample_rate, 0)
    if fade_in > 0:
        audio_utils.fade(sound_data, fade_in * sample_rate, 1)
    if fade_out > 0:
        audio_utils.fade(sound_data, fade_out * sample_rate, -1)
    soundfile.write(file=source_path, data=sound_data, samplerate=sample_rate)
    return reset_source_editor(obj)

# 重置所有的淡入淡出和裁剪
def reset_source_editor(obj: WwiseObject) -> bool:
    modified = False
    if obj.type == WwiseObjectType.Sound:
        for child in waapi_utils.get_child_objects(obj):
            modified |= reset_source_editor(child)
        return modified
    elif obj.type != WwiseObjectType.AudioSource:
        return False
    modified |= waapi_utils.set_object_property(obj, 'FadeInDuration', 0)
    modified |= waapi_utils.set_object_property(obj, 'FadeOutDuration', 0)
    modified |= waapi_utils.set_object_property(obj, 'TrimBegin', -1)
    modified |= waapi_utils.set_object_property(obj, 'TrimEnd', -1)
    modified |= waapi_utils.set_object_property(obj, 'LoopBegin', -1)
    modified |= waapi_utils.set_object_property(obj, 'LoopEnd', -1)
    return modified

# 替换样本文件
def replace_audio_file(sound: WwiseObject, new_wav_path: str, language: str) -> bool:
    old_source = waapi_utils.get_default_audio_source(sound)
    if not old_source:
        return False
    trim_begin, trim_end, fade_in, fade_out, loop_begin, loop_end = get_source_edit_info(old_source)
    delete_audio_source_by_language(sound, language)

    if not waapi_utils.import_audio_file(new_wav_path, sound, language):
        return False
    new_source = waapi_utils.get_default_audio_source(sound)
    if not new_source:
        return False
    return set_source_edit_info(new_source, trim_begin, trim_end, fade_in, fade_out, loop_begin, loop_end)

# 根据声音路径自动导入源文件
def auto_import_by_path(sound: WwiseObject) -> WwiseObject:
    language = localization_utils.get_sound_language(sound)
    delete_audio_source_by_language(sound, language)
    base_folder = project_utils.get_originals_folder()
    wav_sub_folder = get_wav_subfolder(sound)
    full_name = common_utils.get_full_name_with_acronym(sound)
    wav_path = os.path.join(base_folder, language, wav_sub_folder, full_name + '.wav')
    if os.path.exists(wav_path):
        return waapi_utils.import_audio_file(str(wav_path), sound, language)
    else:
        suffix = project_conventions.get_net_role_suffix_from_name(full_name)
        if suffix:
            suffix_1p = project_conventions.get_default_net_role_suffix()
            # 如果1P找不到，则找不带1P的文件
            if suffix == suffix_1p:
                wav_path = wav_path.replace(suffix, '')
            # 如果3P找不到，则去找1P的文件
            else:
                wav_path = wav_path.replace(suffix, suffix_1p)
            if os.path.exists(wav_path):
                return waapi_utils.import_audio_file(str(wav_path), sound, language)
    return WwiseObject()

# 将原始资源文件名字改为Wwise中资源名字
def rename_original_to_wwise(sound: WwiseObject) -> bool:
    if sound.type != WwiseObjectType.Sound:
        return False
    # 去除1P和3P后缀
    sound_name = sound.name
    if '_' not in sound_name:
        sound_name = common_utils.get_full_name_with_acronym(sound)
    suffix = project_conventions.get_net_role_suffix_from_name(sound_name)
    sources = waapi_utils.get_child_objects(sound)
    modified = False
    for source in sources:
        language = localization_utils.get_sound_language(source)
        original_wave_path = get_source_file_path(source)
        if not original_wave_path:
            print(f'AudioFile of Sound [{sound_name}] missing at [{original_wave_path}]!')
            continue
        original_wave_name = os.path.basename(original_wave_path)
        # Sound名称包含NetRole但源文件不区分
        if suffix and suffix not in original_wave_name:
            new_wave_name = sound_name[:-len(suffix)] + '.wav'
        else:
            new_wave_name = sound_name + '.wav'
        if original_wave_name != new_wave_name:
            new_wave_path = original_wave_path.replace(original_wave_name, new_wave_name)
            # 重命名源文件，若已存在则覆盖
            if os.path.exists(original_wave_path):
                os.replace(original_wave_path, new_wave_path)
            if os.path.exists(new_wave_path):
                modified = replace_audio_file(sound, new_wave_path, language)
    return modified

# 按照文件夹与WorkUnit整理源文件目录
def tidy_original_folders(sound: WwiseObject) -> bool:
    if sound.type != WwiseObjectType.Sound:
        return False
    original_path = get_source_file_path(sound)
    if not original_path:
        return False
    file_name = os.path.basename(original_path)
    language = localization_utils.get_sound_language(sound)
    base_folder = project_utils.get_originals_folder()
    wav_sub_folder = get_wav_subfolder(sound)
    new_path = os.path.join(base_folder, language, wav_sub_folder, file_name)
    if original_path == new_path:
        return False
    path_utils.move_file(original_path, new_path)
    print(f'[{sound.name}] moved from [{original_path}] to [{new_path}]')
    return replace_audio_file(sound, str(new_path), language)

# 递归查找最近的Folder或WorkUnit
def get_wav_subfolder(obj: WwiseObject, path='') -> str:
    parent = waapi_utils.get_parent_object(obj)    
    if parent.type == WwiseObjectType.WorkUnit or parent.type == WwiseObjectType.Folder:
        parent_name = parent.name
        if parent_name == 'Actor-Mixer Hierarchy':
            return path
        if parent_name not in path:
            path = os.path.join(parent_name, path)
    return get_wav_subfolder(parent, path)

# 清除工程中多余的akd文件
def delete_unused_akd_files():
    count = 0
    originals_folder = project_utils.get_originals_folder()
    for root, dirs, files in os.walk(originals_folder):
        for file in files:
            if file.endswith(".akd"):
                full_path = os.path.join(root, file)
                wave_path = full_path.replace('.akd', '.wav')
                if not os.path.exists(wave_path):
                    os.remove(full_path)
                    count += 1
    Logger().info(f'删除完毕，共删除了{count}个akd文件！')

# 为语音添加临时的静音
def add_silence(sound: WwiseObject, duration: int, language: str) -> bool:
    version = project_utils.get_project_version()
    if version > 2021:
        return waapi_utils.add_silence(sound, duration, language)
    else:
        ref_wav_path, ref_language = localization_utils.get_wave_path_for_any_existing_language(sound)
        if not ref_wav_path or not ref_language:
            return False
        new_wav_path = ref_wav_path.replace(ref_language, language)
        audio_utils.create_silence_audio_file(new_wav_path, duration)
        source = waapi_utils.import_audio_file(new_wav_path, sound, language)
        return waapi_utils.set_object_notes(source, 'Silence')
