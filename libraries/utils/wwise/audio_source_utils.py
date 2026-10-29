import os
from typing import Optional

import soundfile

from data import project_conventions
from libraries.utils import audio_utils, path_utils
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import common_utils, localization_utils, project_utils, event_utils, waapi_utils, \
    workunit_utils, wwise_compat
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
    audio_sources = [
        child for child in waapi_utils.get_child_objects(sound)
        if child.type == WwiseObjectType.AudioSource
    ]
    languages_by_id = localization_utils.get_sound_languages(audio_sources)
    for audio_source in audio_sources:
        source_language = languages_by_id.get(audio_source.id, localization_utils.SFX_LANGUAGE_NAME)
        if source_language == language:
            return waapi_utils.delete_object(audio_source)
    return False

# 获取音效的源文件路径
def get_source_absolute_path(sound_or_source: WwiseObject, properties: dict = None) -> str:
    if properties is not None:
        return properties.get('originalFilePath')
    return waapi_utils.get_object_property(sound_or_source, 'originalFilePath')

# 获取源文件相对路径
def get_source_relative_path(sound_or_source: WwiseObject) -> str:
    return waapi_utils.get_object_property(sound_or_source, 'originalRelativeFilePath')


# 响度/裁剪分析需要的源属性：一次批量查询就能取全，避免逐个属性往返
AUDIO_SOURCE_PLAYBACK_DURATION_PROPERTY = 'audioSource:playbackDuration'

SOURCE_ANALYSIS_PROPERTIES = (
    'originalFilePath',
    'workUnit.filePath',
    'audioSource:language',
    AUDIO_SOURCE_PLAYBACK_DURATION_PROPERTY,
    'TrimBegin',
    'TrimEnd',
    'FadeInDuration',
    'FadeOutDuration',
    'LoopBegin',
    'LoopEnd',
)

# 单次测量的最大内存占用（采样点，按 48kHz 60 秒估算）：更长的音频退回流式读取
IN_MEMORY_MEASURE_FRAME_LIMIT = 48000 * 60


# 批量取回多个对象的分析属性：返回 {对象ID: {属性名: 值}}
def get_source_analysis_properties(objects: list) -> dict:
    return waapi_utils.get_objects_properties(objects, list(SOURCE_ANALYSIS_PROPERTIES))


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
            path = get_source_absolute_path(obj)
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
# properties 传调用方批量取回的结果（get_source_analysis_properties），未传则单对象查一次
def get_source_edit_info(obj: WwiseObject, properties: dict = None):
    if obj.type != WwiseObjectType.AudioSource:
        return None
    if not properties:
        properties = waapi_utils.get_object_properties(obj, [
            'TrimBegin', 'TrimEnd', 'FadeInDuration', 'FadeOutDuration', 'LoopBegin', 'LoopEnd',
        ])
    return (properties.get('TrimBegin'), properties.get('TrimEnd'),
            properties.get('FadeInDuration'), properties.get('FadeOutDuration'),
            properties.get('LoopBegin'), properties.get('LoopEnd'))


# Sound 当前语言下实际播放的 AudioSource（WAAPI 的 activeSource 访问器，未使用/无源时为空对象）
def get_active_source(sound_or_source: WwiseObject) -> WwiseObject:
    active = waapi_utils.get_object_property(sound_or_source, 'activeSource')
    obj = WwiseObject(active) if isinstance(active, dict) else WwiseObject()
    return obj if obj.is_valid else WwiseObject()


# Sound 实际在用的 AudioSource 列表：
# 1) 优先读所在 WorkUnit 的 ActiveSourceList（Wwise 真正会播放的源，和语言无关，最准确）；
# 2) 取不到时退回 WAAPI 的 activeSource 访问器（只对当前工程语言有效）。
# children / workunit_path 已由调用方批量取到时直接传入，省掉重复的子对象查询与 workUnit 属性查询
def get_active_sources(sound: WwiseObject, children: list = None, workunit_path: str = None) -> list:
    source_children = children if children is not None else waapi_utils.get_child_objects(sound)
    source_children = [child for child in source_children if child.type == WwiseObjectType.AudioSource]
    active_ids = workunit_utils.get_active_source_ids_for_object(sound, workunit_path)
    if active_ids:
        matched = [child for child in source_children if child.id in active_ids]
        if matched:
            return matched
    active = get_active_source(sound)
    return [active] if active.is_valid else []


# 从 AudioFileSource 的 playbackDuration 属性值中提取秒数
def get_audio_source_duration_seconds(properties: dict) -> Optional[float]:
    duration = (properties or {}).get(AUDIO_SOURCE_PLAYBACK_DURATION_PROPERTY)
    if isinstance(duration, dict):
        duration = duration.get('playbackDurationMax', duration.get('playbackDurationMin'))
    if isinstance(duration, (int, float)) and not isinstance(duration, bool):
        return float(duration)
    return None


# 音频源的（裁剪后）播放时长秒：优先用 audioSource:playbackDuration 访问器，取不到再手工算
def get_trimmed_duration(obj: WwiseObject, properties: dict = None) -> float:
    if not properties:
        properties = waapi_utils.get_object_properties(obj, [
            AUDIO_SOURCE_PLAYBACK_DURATION_PROPERTY, 'originalFilePath',
            'TrimBegin', 'TrimEnd', 'FadeInDuration', 'FadeOutDuration', 'LoopBegin', 'LoopEnd',
        ])
    duration = get_audio_source_duration_seconds(properties)
    if duration is not None:
        return duration
    # 回退：用 TrimBegin / TrimEnd 的绝对位置换算播放区间
    file_path = properties.get('originalFilePath') or get_source_absolute_path(obj)
    if not file_path or not os.path.exists(file_path):
        return 0.0
    with soundfile.SoundFile(file_path) as sound_file:
        total_frames = sound_file.frames
        sample_rate = sound_file.samplerate
    start_frame, end_frame = get_trimmed_frame_range(obj, total_frames, sample_rate, properties)
    return max(0.0, (end_frame - start_frame) / sample_rate) if sample_rate else 0.0


# 源文件里实际生效的采样区间：TrimBegin / TrimEnd 都是从头算起的绝对时间位置；
# TrimEnd ≤ 0（默认 -0.001）表示未设置，保留到文件末尾
def get_trimmed_frame_range(obj: WwiseObject, total_frames: int, sample_rate: int,
                            properties: dict = None) -> tuple:
    info = get_source_edit_info(obj, properties)
    if not info or not sample_rate:
        return 0, total_frames
    trim_begin = info[0] or 0.0
    trim_end = info[1] or 0.0
    start_frame = max(0, min(int(round(trim_begin * sample_rate)), total_frames))
    end_frame = total_frames if trim_end <= 0 else int(round(trim_end * sample_rate))
    end_frame = max(start_frame, min(end_frame, total_frames))
    return start_frame, end_frame


# 按 Source Editor 的裁剪区间测量音频：返回 (响度, 时长秒)，只统计 TrimBegin~TrimEnd 之间的样本
# properties 传批量取回的分析属性时不再发起 WAAPI 查询；裁剪区间内只打开文件一次
def measure_trimmed_audio(obj: WwiseObject, standard=None, properties: dict = None) -> tuple:
    if standard is None:
        standard = audio_utils.LoudnessStandard.RMS
    if not properties:
        properties = get_source_analysis_properties([obj]).get(obj.id, {})
    file_path = properties.get('originalFilePath') or get_source_absolute_path(obj)
    if not file_path or not os.path.exists(file_path):
        return audio_utils.MIN_LOUDNESS_DB, 0.0
    with soundfile.SoundFile(file_path) as sound_file:
        total_frames = sound_file.frames
        sample_rate = sound_file.samplerate
        start_frame, end_frame = get_trimmed_frame_range(obj, total_frames, sample_rate, properties)
        duration = max(0.0, (end_frame - start_frame) / sample_rate) if sample_rate else 0.0
        if end_frame - start_frame <= 0:
            return audio_utils.MIN_LOUDNESS_DB, 0.0
        # 短音频一次读入内存算响度；长音频退回流式读取，避免内存占用失控
        if end_frame - start_frame <= IN_MEMORY_MEASURE_FRAME_LIMIT:
            sound_file.seek(start_frame)
            trimmed = sound_file.read(end_frame - start_frame, dtype='float64', always_2d=True)
            loudness = audio_utils.calculate_loudness_by_standard_from_data(trimmed, sample_rate, standard)
            return loudness, duration
    loudness = audio_utils.calculate_loudness_by_standard(file_path, standard, start_frame, end_frame)
    return loudness, duration


# 按裁剪区间测量音频响度（只统计 TrimBegin~TrimEnd 之间的样本）
def calculate_trimmed_loudness(obj: WwiseObject, standard=None) -> float:
    return measure_trimmed_audio(obj, standard)[0]


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


# 改写 Source Editor 的裁剪区间与淡变：TrimBegin / TrimEnd 都是从头算起的绝对时间位置（秒）；
# 传 None 的项保持不变，循环设置不动。current 传入已读到的裁剪信息可省一次查询；
# 只把真正变化的属性合并进一次 object.set（Wwise 首次设置 TrimEnd 会做一次较重的处理，重复写同值没有意义）
def set_source_trim_range(obj: WwiseObject, trim_begin=None, trim_end=None,
                          fade_in=None, fade_out=None, current=None) -> bool:
    if obj.type != WwiseObjectType.AudioSource:
        return False
    if current is None:
        current = get_source_edit_info(obj)
    updates = {}
    for name, value, old_value in (
        ('TrimBegin', trim_begin, current[0] if current else None),
        ('TrimEnd', trim_end, current[1] if current else None),
        ('FadeInDuration', fade_in, current[2] if current else None),
        ('FadeOutDuration', fade_out, current[3] if current else None),
    ):
        if value is None:
            continue
        if isinstance(old_value, (int, float)) and abs(float(value) - float(old_value)) <= 1e-6:
            continue
        updates[name] = float(value)
    if not updates:
        return True
    return waapi_utils.set_object_property_values(obj, updates)


# 将Source Editor里编辑的信息写入源文件中
def apply_source_edits(obj: WwiseObject) -> bool:
    modified = False
    if obj.type == WwiseObjectType.Sound:
        for child in waapi_utils.get_child_objects(obj):
            modified |= apply_source_edits(child)
        return modified
    elif obj.type != WwiseObjectType.AudioSource:
        return False
    source_path = get_source_absolute_path(obj)
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
    # 清空裁剪与淡变：Trim/Loop 回到 -1，Fade 回到 0
    modified |= set_source_edit_info(obj, -1, -1, 0, 0, -1, -1)
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
    sources = [
        source for source in waapi_utils.get_child_objects(sound)
        if source.type == WwiseObjectType.AudioSource
    ]
    properties_by_id = waapi_utils.get_objects_properties(
        sources,
        ['originalFilePath', localization_utils.AUDIO_SOURCE_LANGUAGE_PROPERTY],
    )
    modified = False
    for source in sources:
        properties = properties_by_id.get(source.id)
        language = localization_utils.get_sound_language(source, properties)
        original_wave_path = get_source_absolute_path(source, properties)
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
    original_path = get_source_absolute_path(sound)
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
        if wwise_compat.is_hierarchy_root_name(parent_name):
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
def add_silence(sound: WwiseObject, duration: float, language: str) -> bool:
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


# 为语音添加正弦波占位源（Wwise Sine 插件）
def add_sine(sound: WwiseObject, duration: float, language: str, frequency: float = 1000.0) -> bool:
    version = project_utils.get_project_version()
    if version <= 2021:
        Logger().warning('Wwise Sine 占位源需要 Wwise 2022 及以上版本')
        return False
    return waapi_utils.add_sine(sound, duration, language, frequency=frequency)


# 批量添加静音占位源：assignments 为 [(Sound, 缺失语言列表)]
def add_silence_batch(assignments: list[tuple[WwiseObject, list[str]]], duration: float) -> bool:
    return waapi_utils.add_silence_batch(assignments, duration)


# 批量添加正弦波占位源：assignments 为 [(Sound, 缺失语言列表)]
def add_sine_batch(assignments: list[tuple[WwiseObject, list[str]]], duration: float,
                   frequency: float = 1000.0) -> bool:
    version = project_utils.get_project_version()
    if version <= 2021:
        Logger().warning('Wwise Sine 占位源需要 Wwise 2022 及以上版本')
        return False
    return waapi_utils.add_sine_batch(assignments, duration, frequency=frequency)
