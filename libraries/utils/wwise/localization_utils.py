from libraries.utils.wwise import audio_source_utils, event_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType


# 获取音频源文件语言
def get_sound_language(source: WwiseObject):
    if source.type != WwiseObjectType.AudioSource and source.type != WwiseObjectType.Sound:
        return 'SFX'
    # audioSource:language 属于 AudioFileSource；对 Sound 需取其首个音频源子对象查询
    if source.type == WwiseObjectType.Sound:
        for child in waapi_utils.get_child_objects(source):
            if child.type == WwiseObjectType.AudioSource:
                source = child
                break
        else:
            return 'SFX'
    language = waapi_utils.get_object_property(source, 'audioSource:language')
    if language is None:
        return 'SFX'
    return language.name

# 获取默认语言
def get_default_language():
    return waapi_utils.get_project_property('DefaultLanguage')

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
        if name != 'SFX' and name != 'External' and name != 'Mixed':
            language_names.append(name)
    return language_names


# 递归下级对象：若存在任一Sound的language不是SFX，则视为本地化
def is_localized(root: WwiseObject) -> bool:
    if not root or not root.id:
        return False

    visited_containers: set[str] = set()

    def visit(obj: WwiseObject) -> bool:
        if not obj or not obj.id:
            return False

        if obj.type == WwiseObjectType.Sound:
            return get_sound_language(obj) != 'SFX'

        if obj.type == WwiseObjectType.Event:
            for target in event_utils.get_event_targets(obj):
                if visit(target):
                    return True
            return False

        if obj.id in visited_containers:
            return False
        visited_containers.add(obj.id)

        for child in waapi_utils.get_child_objects(obj):
            if visit(child):
                return True
        return False

    return visit(root)

# 获取语音对象下某个语言的样本路径
def get_wave_path_for_language(sound: WwiseObject, language:str):
    sources = waapi_utils.get_child_objects(sound)
    for source in sources:
        if source.type == WwiseObjectType.AudioSource:
            source_langauge = get_sound_language(source)
            if source_langauge == language:
                return audio_source_utils.get_source_file_path(source)
    return None

# 获取已有语言的源文件路径
def get_wave_path_for_any_existing_language(sound: WwiseObject):
    sources = waapi_utils.get_child_objects(sound)
    for source in sources:
        source_path = audio_source_utils.get_source_file_path(source)
        if source_path:
            language = get_sound_language(source)
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
    ref_language = get_default_language()
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
