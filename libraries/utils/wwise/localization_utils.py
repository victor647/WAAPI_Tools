from libraries.utils import user_config
from libraries.utils.wwise import audio_source_utils, event_utils, waapi_utils
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

# 尝试导入当前所有语音资源的本地化文件
def localize_languages(sound: WwiseObject):
    if sound.type != WwiseObjectType.Sound:
        return False
    sources = waapi_utils.get_child_objects(sound)
    if len(sources) == 0:
        return False
    existing_wav_path, existing_language = get_wave_path_for_any_existing_language(sound)
    imported = False
    for language in get_all_language_names():
        if language != existing_language:
            new_wav_path = existing_wav_path.replace(existing_language, language)
            source = waapi_utils.import_audio_file(new_wav_path, sound, language)
            if source:
                imported = True
    return imported

# 为语音对象的参考语言创建静音
def import_silence_for_ref_language(sound: WwiseObject):
    if sound.type != WwiseObjectType.Sound:
        return False
    ref_language = get_reference_language_name()
    source_path = get_wave_path_for_language(sound, ref_language)
    if not source_path:
        return audio_source_utils.add_silence(sound, 2, ref_language)
    return False

# 为语音对象的所有未导入语言创建静音
def import_silence_for_all_languages(sound: WwiseObject):
    if sound.type != WwiseObjectType.Sound:
        return False
    added = False
    for language in get_all_language_names():
        source_path = get_wave_path_for_language(sound, language)
        if not source_path:
            added |= audio_source_utils.add_silence(sound, 2, language)
    return added
