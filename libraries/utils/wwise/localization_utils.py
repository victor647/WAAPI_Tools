import os

from data import project_conventions, user_config
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import audio_source_utils, event_utils, project_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType

# 非本地化语言名：语言筛选时这类对象始终保留
SFX_LANGUAGE_NAME = 'SFX'
AUDIO_SOURCE_LANGUAGE_PROPERTY = 'audioSource:language'


# 获取音频源文件语言
def get_sound_language(source: WwiseObject, properties: dict = None):
    if source.type != WwiseObjectType.AudioSource and source.type != WwiseObjectType.Sound:
        return SFX_LANGUAGE_NAME
    # audioSource:language 属于 AudioFileSource；对 Sound 需取其首个音频源子对象查询
    if source.type == WwiseObjectType.Sound:
        for child in waapi_utils.get_child_objects(source):
            if child.type == WwiseObjectType.AudioSource:
                source = child
                break
        else:
            return SFX_LANGUAGE_NAME
    language_value = (
        properties.get(AUDIO_SOURCE_LANGUAGE_PROPERTY)
        if properties is not None else waapi_utils.get_object_property(source, AUDIO_SOURCE_LANGUAGE_PROPERTY)
    )
    language = WwiseObject(language_value) if isinstance(language_value, dict) else None
    if language is None:
        return SFX_LANGUAGE_NAME
    return language.name


# 批量获取 Sound / AudioFileSource 的语言；Sound 采用首个 AudioFileSource 的语言
def get_sound_languages(objects: list[WwiseObject]) -> dict[str, str]:
    source_by_object_id = {}
    sources_by_id = {}
    languages_by_id = {obj.id: SFX_LANGUAGE_NAME for obj in objects if obj and obj.id}
    for obj in objects:
        if not obj or not obj.id:
            continue
        object_type = (obj.wwise_dict or {}).get('type')
        if object_type == WwiseObjectType.AudioSource.value:
            source = obj
        elif object_type == WwiseObjectType.Sound.value:
            source = next(
                (child for child in waapi_utils.get_child_objects(obj)
                 if (child.wwise_dict or {}).get('type') == WwiseObjectType.AudioSource.value),
                None,
            )
        else:
            continue
        if source:
            source_by_object_id[obj.id] = source
            sources_by_id[source.id] = source

    properties_by_id = waapi_utils.get_objects_properties(
        list(sources_by_id.values()), [AUDIO_SOURCE_LANGUAGE_PROPERTY])
    for object_id, source in source_by_object_id.items():
        properties = properties_by_id.get(source.id)
        if properties is not None:
            languages_by_id[object_id] = get_sound_language(source, properties)
        else:
            languages_by_id[object_id] = get_sound_language(source)
    return languages_by_id


# 「按当前语言筛选」时该对象是否应被排除：SFX 等非本地化对象始终保留，只排除其它语言的本地化对象
def is_filtered_out_by_language(obj: WwiseObject, active_language: str, language: str = None) -> bool:
    if language is None:
        language = get_sound_language(obj)
    if language == SFX_LANGUAGE_NAME:
        return False
    return language != active_language

# 获取工程参考语言名（getProjectInfo 的 referenceLanguageId 对应的语言名）
def get_default_language():
    language_id = waapi_utils.get_project_info('referenceLanguageId')
    language = waapi_utils.get_full_info_from_obj_id(language_id)
    return language.name if language else ''


# 参考语言名：设置里勾选「参考语言使用工程默认」时取工程参考语言，否则用手填值
def get_reference_language_name() -> str:
    if user_config.get_reference_language_use_default():
        return get_default_language()
    return user_config.get_configured_reference_language()

# 获取当前语言
def get_current_language():
    language_id = waapi_utils.get_project_info('currentLanguageId')
    language = waapi_utils.get_full_info_from_obj_id(language_id)
    return language.name if language else get_default_language()

# 获取全部语言名称
def get_all_language_names():
    language_names = []
    language_list = waapi_utils.get_language_list()
    for language in language_list:
        name = language.name
        if name != SFX_LANGUAGE_NAME and name != 'External' and name != 'Mixed':
            language_names.append(name)
    return language_names


# 递归下级对象：若存在任一Sound的language不是SFX，则视为本地化
def is_localized(root: WwiseObject) -> bool:
    if not root or not root.id:
        return False

    sounds_by_id = {}
    visited_roots = set()

    def collect_sounds(obj: WwiseObject) -> None:
        if not obj or not obj.id or obj.id in visited_roots:
            return
        visited_roots.add(obj.id)
        if obj.type == WwiseObjectType.Event:
            for target in event_utils.get_event_targets(obj):
                collect_sounds(target)
            return
        if obj.type == WwiseObjectType.Sound:
            sounds_by_id[obj.id] = obj
            return
        descendants = waapi_utils.get_child_objects(obj, include_descendants=True)
        for descendant in descendants:
            if descendant.type == WwiseObjectType.Event:
                collect_sounds(descendant)
            elif descendant.type == WwiseObjectType.Sound:
                sounds_by_id[descendant.id] = descendant

    collect_sounds(root)

    languages_by_id = get_sound_languages(list(sounds_by_id.values()))
    return any(language != SFX_LANGUAGE_NAME for language in languages_by_id.values())

# 获取语音对象下某个语言的样本路径
def get_wave_path_for_language(sound: WwiseObject, language:str):
    sources = [
        source for source in waapi_utils.get_child_objects(sound)
        if source.type == WwiseObjectType.AudioSource
    ]
    properties_by_id = waapi_utils.get_objects_properties(
        sources,
        ['originalFilePath', AUDIO_SOURCE_LANGUAGE_PROPERTY],
    )
    for source in sources:
        properties = properties_by_id.get(source.id)
        source_language = get_sound_language(source, properties)
        if source_language == language:
            return audio_source_utils.get_source_absolute_path(source, properties)
    return None

# 获取已有语言的源文件路径
def get_wave_path_for_any_existing_language(sound: WwiseObject):
    sources = [
        source for source in waapi_utils.get_child_objects(sound)
        if source.type == WwiseObjectType.AudioSource
    ]
    properties_by_id = waapi_utils.get_objects_properties(
        sources,
        ['originalFilePath', AUDIO_SOURCE_LANGUAGE_PROPERTY],
    )
    for source in sources:
        properties = properties_by_id.get(source.id)
        source_path = audio_source_utils.get_source_absolute_path(source, properties)
        if source_path:
            language = get_sound_language(source, properties)
            return source_path, language
    return None, None

# 获取 Sound 下所有 AudioFileSource 已占用的语言，用于跳过已有资源
def get_existing_source_languages(sound: WwiseObject) -> set[str]:
    sources = [
        source for source in waapi_utils.get_child_objects(sound)
        if source.type == WwiseObjectType.AudioSource
    ]
    return set(get_sound_languages(sources).values())

# 本地化导入的语言范围跟随高级筛选：全部语言补齐所有语言，当前语言只补当前语言
def get_localization_import_languages() -> list[str]:
    if user_config.get_advanced_filter_settings().get("language_filter") != "active":
        return get_all_language_names()
    language = get_current_language()
    return [language] if language else []

# 按目标语言生成导入路径：默认只替换语言子目录，工程规范要求时再替换文件名
def get_localized_wav_path(existing_wav_path: str, existing_language: str, target_language: str) -> str:
    directory, file_name = os.path.split(existing_wav_path)
    directory = directory.replace(existing_language, target_language)
    if project_conventions.use_language_in_file_name():
        file_name = file_name.replace(existing_language, target_language)
    return os.path.join(directory, file_name)

# 尝试导入当前所有语音资源的本地化文件
def localize_languages(sound: WwiseObject):
    if sound.type != WwiseObjectType.Sound:
        return False
    existing_languages = get_existing_source_languages(sound)
    if not existing_languages:
        return False
    existing_wav_path, existing_language = get_wave_path_for_any_existing_language(sound)
    if not existing_wav_path or not existing_language:
        return False
    imported = False
    for language in get_localization_import_languages():
        if language in existing_languages:
            continue
        new_wav_path = get_localized_wav_path(existing_wav_path, existing_language, language)
        source = waapi_utils.import_audio_file(new_wav_path, sound, language)
        if source:
            imported = True
    return imported

# 按名称取工程语言对象（SFX 也在语言列表里）
def get_language_object(language_name: str) -> WwiseObject:
    if not language_name:
        return WwiseObject()
    for language in waapi_utils.get_language_list():
        if language.name == language_name:
            return language
    return WwiseObject()


# 读取 Sound 下所有 AudioSource 的语言与文件路径
def get_audio_source_infos(sound: WwiseObject) -> list[dict]:
    sources = [
        source for source in waapi_utils.get_child_objects(sound)
        if source.type == WwiseObjectType.AudioSource
    ]
    if not sources:
        return []
    properties_by_id = waapi_utils.get_objects_properties(
        sources, ['originalFilePath', 'originalWavFilePath', AUDIO_SOURCE_LANGUAGE_PROPERTY]
    )
    infos = []
    for source in sources:
        properties = properties_by_id.get(source.id, {})
        original_path = properties.get('originalFilePath') or ''
        wav_path = properties.get('originalWavFilePath') or ''
        path = original_path if original_path and os.path.exists(original_path) else (wav_path or original_path)
        infos.append({
            'source': source,
            'language': get_sound_language(source, properties),
            'path': path,
        })
    return infos


# 选择转换时保留的源：优先参考语言，其次 SFX，最后任意有文件的源
def choose_audio_source_info(infos: list[dict], preferred_language: str):
    for info in infos:
        if info['language'] == preferred_language and info['path']:
            return info
    for info in infos:
        if info['language'] == SFX_LANGUAGE_NAME and info['path']:
            return info
    for info in infos:
        if info['path']:
            return info
    for info in infos:
        if info['language'] == preferred_language:
            return info
    return infos[0] if infos else None


# 从 SFX/其它语言的源路径，定位参考语言目录下的同名文件
def resolve_voice_language_path(source_path: str, language: str) -> str:
    if not source_path or not language:
        return ''
    originals_folder = project_utils.get_originals_folder()
    file_name = os.path.basename(source_path).lower()
    language_roots = [
        os.path.join(originals_folder, 'Voices', language),
        os.path.join(originals_folder, language),
    ]
    # 源文件已经在目标语言目录下时直接使用，避免同名文件搜索产生歧义
    source_abs = os.path.abspath(source_path)
    for root in language_roots:
        try:
            if os.path.commonpath([os.path.abspath(root), source_abs]) == os.path.abspath(root):
                return source_path
        except ValueError:
            continue
    # 先按「只替换语言层级目录」映射，保留 SFX 路径下的所有子目录
    sfx_root = os.path.join(originals_folder, SFX_LANGUAGE_NAME)
    relative_path = os.path.relpath(source_path, sfx_root)
    if not relative_path.startswith('..'):
        for root in language_roots:
            candidate = os.path.join(root, relative_path)
            if os.path.isfile(candidate):
                return candidate
    matches = []
    for root in language_roots:
        if not os.path.isdir(root):
            continue
        for current_root, _dirs, files in os.walk(root):
            if any(name.lower() == file_name for name in files):
                matches.append(os.path.join(current_root, os.path.basename(source_path)))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        # 优先用 SFX 目录下的相对路径消歧
        if not relative_path.startswith('..'):
            for root in language_roots:
                candidate = os.path.join(root, relative_path)
                if os.path.isfile(candidate):
                    return candidate
        Logger().warning(
            f'[{os.path.basename(source_path)}] 在参考语言目录 {language} 下找到多个同名文件，无法确定要导入哪一个'
        )
        return ''
    # 语言目录没有同名文件时，返回原文件路径，由 Wwise 按 originalsSubFolder 复制到目标语言目录
    return source_path if os.path.isfile(source_path) else ''


# 取音频文件在 Originals 下相对于语言层级的子目录（用于 Wwise 导入时保留目录结构）
def get_originals_subfolder(source_path: str) -> str:
    if not source_path:
        return ''
    originals_folder = os.path.abspath(project_utils.get_originals_folder())
    relative_dir = os.path.relpath(os.path.dirname(os.path.abspath(source_path)), originals_folder)
    if relative_dir == '.' or relative_dir.startswith('..') or os.path.isabs(relative_dir):
        return ''
    parts = relative_dir.split(os.sep)
    if parts[0].lower() == SFX_LANGUAGE_NAME.lower():
        parts = parts[1:]
    elif parts[0].lower() == 'voices':
        parts = parts[2:]
    else:
        parts = parts[1:]
    return os.path.join(*parts) if parts else ''


# 判断 Sound 当前属于 Voice 还是 Sound：优先 IsVoice，取不到时按源语言推断
def get_sound_category(sound: WwiseObject) -> tuple[str, bool | None]:
    if sound.has_property('IsVoice'):
        is_voice = waapi_utils.get_object_property(sound, 'IsVoice')
        if is_voice is not None:
            is_voice = bool(is_voice)
            return ('Voice' if is_voice else 'Sound'), is_voice
    infos = get_audio_source_infos(sound)
    if infos:
        all_sfx = all(info['language'] == SFX_LANGUAGE_NAME for info in infos)
        return ('Sound' if all_sfx else 'Voice'), None
    return '', None


# 把一个 Sound 清理成只保留目标语言的单个音频源；无法直接改语言时退回重新导入
def convert_sound_source_language(sound: WwiseObject, target_language_name: str,
                                  preferred_language_name: str, is_voice: bool,
                                  current_is_voice: bool | None = None) -> bool:
    if sound.type != WwiseObjectType.Sound:
        return False
    if not get_language_object(target_language_name):
        Logger().warning(f'[{sound.name}] 找不到目标语言：{target_language_name}')
        return False
    infos = get_audio_source_infos(sound)
    keep = choose_audio_source_info(infos, preferred_language_name)
    if keep is None:
        Logger().warning(f'[{sound.name}] 没有可转换的 AudioSource')
        return False
    desired_is_voice = bool(is_voice)
    original_is_voice = current_is_voice
    if original_is_voice is None and sound.has_property('IsVoice'):
        original_is_voice = waapi_utils.get_object_property(sound, 'IsVoice')

    def set_is_voice(value):
        if not sound.has_property('IsVoice'):
            return True
        return waapi_utils.set_object_property(sound, 'IsVoice', bool(value))

    def restore_is_voice():
        if original_is_voice is not None and bool(original_is_voice) != desired_is_voice:
            set_is_voice(original_is_voice)

    if keep['language'] == target_language_name:
        for info in infos:
            if info['source'].id != keep['source'].id:
                waapi_utils.delete_object(info['source'])
    else:
        edit_info = audio_source_utils.get_source_edit_info(keep['source'])
        source_path = keep['path']
        if not source_path:
            restore_is_voice()
            Logger().warning(f'[{sound.name}] 保留源没有文件路径，无法导入 {target_language_name}')
            return False
        # 目标为 Sound 时必须先取消 Voice；目标为 Voice 且当前仍是 Voice 时也先临时取消，
        # 否则 Wwise 不允许在 Voice 上再挂新的语言源。
        if not desired_is_voice or bool(original_is_voice):
            if not set_is_voice(False):
                Logger().warning(f'[{sound.name}] 临时取消 IsVoice 失败，继续尝试导入')
        source_name = os.path.splitext(os.path.basename(source_path))[0]
        originals_subfolder = get_originals_subfolder(source_path)
        new_source = waapi_utils.import_audio_source(
            sound, source_path, target_language_name, source_name=source_name,
            originals_subfolder=originals_subfolder,
        )
        if not new_source:
            restore_is_voice()
            Logger().warning(f'[{sound.name}] 导入 {target_language_name} 失败：{source_path}')
            return False
        if edit_info and not audio_source_utils.set_source_edit_info(new_source, *edit_info):
            Logger().warning(f'[{sound.name}] 已导入 {target_language_name}，但 Source Editor 参数复制失败')
        for info in infos:
            waapi_utils.delete_object(info['source'])
        if new_source.name and new_source.name != source_name:
            waapi_utils.rename_object(new_source, source_name)
    if original_is_voice is None or bool(original_is_voice) != desired_is_voice:
        if not set_is_voice(desired_is_voice):
            Logger().warning(f'[{sound.name}] 语言已处理，但 IsVoice 设置失败')
    return True


# 转为 Voice：尝试把音频导入工程的所有语言，并标记为 Voice
def convert_to_voice(sound: WwiseObject) -> bool:
    category, current_is_voice = get_sound_category(sound)
    if category == 'Voice':
        Logger().warning(f'[{sound.name}] 对象本来就是 Voice，已跳过')
        return False
    if sound.type != WwiseObjectType.Sound:
        return False
    languages = get_all_language_names()
    if not languages:
        Logger().warning(f'[{sound.name}] 工程没有可用语言，无法转为 Voice')
        return False
    infos = get_audio_source_infos(sound)
    if not infos:
        Logger().warning(f'[{sound.name}] 没有可转换的 AudioSource')
        return False

    existing_by_language = {}
    for info in infos:
        existing_by_language.setdefault(info['language'], info)
    source_info = next(
        (info for info in infos if info['language'] == SFX_LANGUAGE_NAME and info['path']),
        None,
    )
    if source_info is None:
        source_info = next((info for info in infos if info['path']), None)
    if source_info is None:
        Logger().warning(f'[{sound.name}] 没有带文件路径的 AudioSource')
        return False
    source_path = source_info['path']
    edit_info = audio_source_utils.get_source_edit_info(source_info['source'])

    original_is_voice = current_is_voice
    if original_is_voice is None and sound.has_property('IsVoice'):
        original_is_voice = waapi_utils.get_object_property(sound, 'IsVoice')

    def set_is_voice(value):
        if not sound.has_property('IsVoice'):
            return True
        return waapi_utils.set_object_property(sound, 'IsVoice', bool(value))

    if bool(original_is_voice):
        set_is_voice(False)

    keep_ids = set()
    new_sources = []
    failed_languages = []
    for language in languages:
        existing = existing_by_language.get(language)
        if existing and existing['path']:
            keep_ids.add(existing['source'].id)
            continue
        language_source_path = resolve_voice_language_path(source_path, language)
        if not language_source_path:
            failed_languages.append(language)
            Logger().warning(f'[{sound.name}] 找不到 {language} 的源文件：{source_path}')
            continue
        desired_name = os.path.splitext(os.path.basename(language_source_path))[0]
        new_source = waapi_utils.import_audio_source(
            sound, language_source_path, language,
            source_name=f'{desired_name}_{language}',
            originals_subfolder=get_originals_subfolder(language_source_path),
        )
        if not new_source:
            failed_languages.append(language)
            Logger().warning(f'[{sound.name}] 导入 {language} 失败：{language_source_path}')
            continue
        if edit_info and not audio_source_utils.set_source_edit_info(new_source, *edit_info):
            Logger().warning(f'[{sound.name}] {language} 已导入，但 Source Editor 参数复制失败')
        new_sources.append(new_source)
        keep_ids.add(new_source.id)

    if not keep_ids:
        if bool(original_is_voice):
            set_is_voice(True)
        Logger().warning(f'[{sound.name}] 所有语言导入失败，已保留原对象')
        return False

    for info in infos:
        if info['source'].id not in keep_ids:
            waapi_utils.delete_object(info['source'])
    if not set_is_voice(True):
        Logger().warning(f'[{sound.name}] 语言已导入，但 IsVoice 设置失败')
    if failed_languages:
        Logger().warning(
            f'[{sound.name}] 转为 Voice 完成，但以下语言导入失败：' + '、'.join(failed_languages)
        )
    else:
        Logger().info(
            f'[{sound.name}] 已转为 Voice：导入 {len(new_sources)} 个语言，'
            f'保留 {len(keep_ids) - len(new_sources)} 个已有语言'
        )
    return True


# 转为 Sound：保留参考语言的音频文件并转为 SFX，其他语言清空，同时取消 Voice 标记
def convert_to_sound(sound: WwiseObject) -> bool:
    category, current_is_voice = get_sound_category(sound)
    if category == 'Sound':
        Logger().warning(f'[{sound.name}] 对象本来就是 Sound，已跳过')
        return False
    reference_language = get_reference_language_name() or get_default_language()
    if not reference_language:
        Logger().warning(f'[{sound.name}] 无法读取工程参考语言')
        return False
    return convert_sound_source_language(
        sound, SFX_LANGUAGE_NAME, reference_language, False, current_is_voice
    )

# 为语音对象的参考语言创建静音
def import_silence_for_ref_language(sound: WwiseObject):
    if sound.type != WwiseObjectType.Sound:
        return False
    ref_language = get_reference_language_name()
    source_path = get_wave_path_for_language(sound, ref_language)
    if not source_path:
        return audio_source_utils.add_silence(sound, user_config.get_tool_silence_duration(), ref_language)
    return False

# 为语音对象的所有未导入语言创建静音
def import_silence_for_all_languages(sound: WwiseObject):
    if sound.type != WwiseObjectType.Sound:
        return False
    added = False
    for language in get_all_language_names():
        source_path = get_wave_path_for_language(sound, language)
        if not source_path:
            added |= audio_source_utils.add_silence(sound, user_config.get_tool_silence_duration(), language)
    return added


# 用静音填补空缺：语言范围跟随高级筛选的语言选项
# 「只显示当前语言」只补当前语言；「全部语言」补齐全部未导入语言
def fill_silence(sound: WwiseObject):
    if sound.type != WwiseObjectType.Sound:
        return False
    if user_config.get_advanced_filter_settings().get("language_filter") != "active":
        return import_silence_for_all_languages(sound)
    language = get_current_language()
    if not language or get_wave_path_for_language(sound, language):
        return False
    return audio_source_utils.add_silence(sound, user_config.get_tool_silence_duration(), language)


# 为所有未导入语言创建正弦波占位源
def import_sine_for_all_languages(sound: WwiseObject):
    if sound.type != WwiseObjectType.Sound:
        return False
    frequency = user_config.get_tool_sine_frequency()
    added = False
    for language in get_all_language_names():
        if not get_wave_path_for_language(sound, language):
            added |= audio_source_utils.add_sine(
                sound, user_config.get_tool_silence_duration(), language, frequency
            )
    return added


# 用正弦波填补空缺：语言范围跟随高级筛选的语言选项
def fill_sine(sound: WwiseObject):
    if sound.type != WwiseObjectType.Sound:
        return False
    if user_config.get_advanced_filter_settings().get("language_filter") != "active":
        return import_sine_for_all_languages(sound)
    language = get_current_language()
    if not language or get_wave_path_for_language(sound, language):
        return False
    return audio_source_utils.add_sine(
        sound,
        user_config.get_tool_silence_duration(),
        language,
        user_config.get_tool_sine_frequency(),
    )
