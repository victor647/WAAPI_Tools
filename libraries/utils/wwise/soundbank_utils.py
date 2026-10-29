import os
from libraries.utils import io_utils
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import common_utils, audio_source_utils, event_utils, localization_utils, project_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType


# Bank 名称上的 Event / Media 拆分后缀
EVENT_BANK_SUFFIX = '_Event'
MEDIA_BANK_SUFFIX = '_Media'
PARENT_STREAMING_CACHE_KEY = '_parent_is_streaming_enabled'


# 去掉拆分后缀后的 Bank 显示名（拆分 Event/Media 的工程在表格中不显示后缀）
def get_bank_display_name(bank_name: str) -> str:
    for suffix in (EVENT_BANK_SUFFIX, MEDIA_BANK_SUFFIX):
        if bank_name.endswith(suffix):
            return bank_name[: -len(suffix)]
    return bank_name


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

# 计算多个Bank合计大小（MB；非 Bank 对象会被忽略）
def get_total_bank_size(banks: list) -> tuple:
    return get_total_media_size([bank for bank in banks if bank.type == WwiseObjectType.SoundBank])


# 跨多个对象增量统计媒体大小的容器：GUI 用 batch processor 逐个对象 accumulate，
# 全部累加完成后调用 finish 汇总（含对缺失 wem 的一次生成尝试）
class MediaSizeStatistics:
    def __init__(self):
        self.total_wav_size = 0.0
        self.total_memory_wem_size = 0.0
        self.total_stream_wem_size = 0.0
        self.used_files: list = []
        self.seen_sources: set = set()
        self.seen_walked: set = set()
        self.seen_wems: set = set()
        self.sources_to_convert: list = []
        self.result = None

    # 累加单个对象子树；多个对象共用一个实例时自动跨对象去重
    def accumulate(self, obj) -> None:
        self.total_wav_size, self.total_memory_wem_size, self.total_stream_wem_size, self.used_files = (
            _accumulate_media_size(obj, self.total_wav_size, self.total_memory_wem_size, self.total_stream_wem_size,
                                   self.used_files, self.seen_sources, self.seen_walked, self.sources_to_convert, self.seen_wems))

    # 汇总为 MB 并返回 (原始wav, 内存wem, 流式wem, 用到的源文件列表)；重复调用只计算一次
    def finish(self) -> tuple:
        if self.result is None:
            if self.sources_to_convert:
                self.total_memory_wem_size, self.total_stream_wem_size = _convert_missing_wem_sources(
                    self.sources_to_convert, self.total_memory_wem_size, self.total_stream_wem_size, self.seen_wems)
            self.result = (round(self.total_wav_size / 1024, 2), round(self.total_memory_wem_size / 1024, 2),
                           round(self.total_stream_wem_size / 1024, 2), self.used_files)
        return self.result


# 统计任意对象列表的音频媒体资源总大小（MB）：SoundBank 按 media 包含展开，
# Event 按播放目标展开，其余对象递归其子对象中的 AudioFileSource；wav 与 wem 均按文件路径去重
def get_total_media_size(objects: list) -> tuple:
    statistics = MediaSizeStatistics()
    for obj in objects:
        statistics.accumulate(obj)
    return statistics.finish()


# 单个对象子树独立的媒体大小统计（KB；不做跨对象去重、不触发缺失 wem 转码）
# 返回 (wavKB, 内存wemKB, 流式wemKB, 文件列表, 流式源文件列表, 非流式源文件列表)
def get_object_media_size(obj: WwiseObject) -> tuple:
    stream_files, memory_files = [], []
    total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files = (
        _accumulate_media_size(obj, 0.0, 0.0, 0.0, [], set(), set(), None, set(),
                               stream_file_paths=stream_files, memory_file_paths=memory_files)
    )
    return (total_wav_size, total_memory_wem_size, total_stream_wem_size,
            used_files, stream_files, memory_files)


# 按“逐个对象节点累加”的方式统计某个根对象的媒体大小：
# 只有 AudioSource / SoundBank / Event 这几类会贡献媒体，容器等节点不重复计入子节点内容，
# 因此把一棵树展开成节点逐个 accumulate 的结果与递归统计一致
class MediaSizeNodeStatistics:
    def __init__(self):
        self.stream_file_paths: list = []
        self.memory_file_paths: list = []
        self.used_files: list = []
        self._totals = [0.0, 0.0, 0.0]
        self.seen_sources: set = set()
        self.seen_walked: set = set()
        self.seen_wems: set = set()

    # 累加单个节点的媒体（容器类节点忽略，其子节点会各自贡献）
    # only_language 传具体语言名时只统计该语言的源，与主窗口的语言筛选口径一致
    def accumulate(self, obj, source_properties_by_id: dict = None,
                   only_language: str = None, xml_index=None) -> None:
        if not obj or obj.type not in (WwiseObjectType.AudioSource, WwiseObjectType.SoundBank, WwiseObjectType.Event):
            return
        wav, memory, stream, used_files = _accumulate_media_size(
            obj, self._totals[0], self._totals[1], self._totals[2], self.used_files,
            self.seen_sources, self.seen_walked, None, self.seen_wems,
            self.stream_file_paths, self.memory_file_paths, source_properties_by_id, only_language,
            xml_index=xml_index)
        self._totals = [wav, memory, stream]
        self.used_files = used_files

    # 与 get_object_media_size 相同的返回结构
    def finish(self) -> tuple:
        return (self._totals[0], self._totals[1], self._totals[2],
                self.used_files, self.stream_file_paths, self.memory_file_paths)


# 传统方式获取Bank大小（KB 累加，供工程检查等按单个 Bank 调用）
def get_bank_size(bank: WwiseObject, total_wav_size: float, total_memory_wem_size: float, total_stream_wem_size: float, used_files: list) -> tuple:
    if bank.type != WwiseObjectType.SoundBank:
        return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files
    return _accumulate_media_size(bank, total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files, set(), set(), None, set())


# 从已取回的属性里读音频源语言名（批量预取过就不用再查一次）
def _language_from_properties(source_properties: dict = None) -> str:
    value = (source_properties or {}).get('audioSource:language')
    if isinstance(value, dict):
        return value.get('name') or None
    if isinstance(value, str):
        return value or None
    return None


# 递归累加对象子树内的媒体资源：SoundBank 按 media 包含展开、Event 按播放目标展开、
# AudioFileSource 统计源文件大小，其余类型逐级下钻子对象
# only_language 传具体语言名时只统计该语言的源（SFX 等非本地化源始终保留），不传则全语言统计
def _accumulate_media_size(obj, total_wav_size: float, total_memory_wem_size: float, total_stream_wem_size: float,
                           used_files: list, seen_sources: set, seen_walked: set,
                           sources_to_convert: list = None, seen_wems: set = None,
                           stream_file_paths: list = None, memory_file_paths: list = None,
                           source_properties_by_id: dict = None, only_language: str = None,
                           xml_index=None) -> tuple:
    if not obj or not obj.id:
        return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files
    if seen_wems is None:
        seen_wems = set()
    if obj.type == WwiseObjectType.AudioSource:
        if obj.id in seen_sources:
            return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files
        seen_sources.add(obj.id)
        source_properties = (source_properties_by_id or {}).get(obj.id)
        if source_properties is None:
            source_properties = waapi_utils.get_object_properties(obj, [
                'originalFilePath', 'originalWavFilePath', 'convertedWemFilePath',
            ])
        # 语言筛选（口径与主窗口「高级筛选 → 语言筛选」一致）：非当前语言的本地化源直接跳过
        if only_language and localization_utils.is_filtered_out_by_language(
                obj, only_language, _language_from_properties(source_properties)):
            return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files
        wav_path = audio_source_utils.get_source_absolute_path(obj, source_properties)
        # 部分层级（如 Music Track 下的源）读不到 sound: 前缀属性时退回原始属性
        if not wav_path:
            wav_path = source_properties.get('originalWavFilePath')
        if not wav_path or not os.path.exists(wav_path):
            # 原始文件缺失时整条源跳过（无法确定其 wem 的归属）
            return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files
        wem_path = source_properties.get('convertedWemFilePath')
        needs_stream_info = (
            stream_file_paths is not None
            or memory_file_paths is not None
            or (wem_path and os.path.exists(wem_path))
        )
        is_streaming = False
        if needs_stream_info:
            if PARENT_STREAMING_CACHE_KEY in source_properties:
                is_streaming = source_properties[PARENT_STREAMING_CACHE_KEY]
            else:
                parent = waapi_utils.get_parent_object(obj)
                parent_properties = (
                    waapi_utils.get_object_properties(parent, ['IsStreamingEnabled'])
                    if parent and parent.is_valid else {}
                )
                is_streaming = parent_properties.get('IsStreamingEnabled', False)
        # 同一 wav 被多个源引用时，原始大小只累加一次
        if wav_path not in used_files:
            used_files.append(wav_path)
            wav_size = os.path.getsize(wav_path) / 1024
            total_wav_size += wav_size
            Logger().debug(f'{wav_path} has size of {wav_size}KB')
            if stream_file_paths is not None or memory_file_paths is not None:
                bucket = stream_file_paths if is_streaming else memory_file_paths
                if bucket is not None and wav_path not in bucket:
                    bucket.append(wav_path)
        wem_counted = False
        if wem_path and os.path.exists(wem_path):
            # 同一 wem 被多个源引用时，压缩大小只累加一次
            if wem_path in seen_wems:
                return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files
            seen_wems.add(wem_path)
            wem_size = os.path.getsize(wem_path) / 1024
            if is_streaming:
                total_stream_wem_size += wem_size
            else:
                total_memory_wem_size += wem_size
            Logger().debug(f'{wem_path} has size of {wem_size}KB')
            wem_counted = True
        if not wem_counted and xml_index is not None:
            xml_entries = xml_index.lookup(
                [
                    source_properties.get('originalFilePath') or "",
                    source_properties.get('originalRelativeFilePath') or "",
                    wav_path,
                ],
                _language_from_properties(source_properties) or only_language or "",
            )
            if xml_entries:
                wem_counted = True
                for xml_size, xml_streaming, xml_path in xml_entries:
                    if xml_path in seen_wems:
                        continue
                    seen_wems.add(xml_path)
                    wem_size = xml_size / 1024
                    if xml_streaming:
                        total_stream_wem_size += wem_size
                    else:
                        total_memory_wem_size += wem_size
                    Logger().debug(f'{xml_path} has size of {wem_size}KB (SoundBanksInfo.xml)')
        if not wem_counted and sources_to_convert is not None:
            # 尚未转码的源先记录下来，遍历结束后统一调用 convert 尝试生成一次 wem
            sources_to_convert.append(obj)
        return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files
    if obj.id in seen_walked:
        return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files
    seen_walked.add(obj.id)
    if obj.type == WwiseObjectType.SoundBank:
        for inclusion in waapi_utils.get_bank_inclusions(obj):
            if 'media' not in inclusion['filter']:
                continue
            inclusion_obj = waapi_utils.get_full_info_from_obj_id(inclusion['object'])
            total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files = (
                _accumulate_media_size(inclusion_obj, total_wav_size, total_memory_wem_size, total_stream_wem_size,
                                       used_files, seen_sources, seen_walked, sources_to_convert, seen_wems,
                                       stream_file_paths, memory_file_paths, source_properties_by_id, only_language,
                                       xml_index))
        return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files
    if obj.type == WwiseObjectType.Event:
        for target in event_utils.get_event_targets(obj):
            total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files = (
                _accumulate_media_size(target, total_wav_size, total_memory_wem_size, total_stream_wem_size,
                                       used_files, seen_sources, seen_walked, sources_to_convert, seen_wems,
                                       stream_file_paths, memory_file_paths, source_properties_by_id, only_language,
                                       xml_index))
        return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files
    for child in waapi_utils.get_child_objects(obj):
        total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files = (
            _accumulate_media_size(child, total_wav_size, total_memory_wem_size, total_stream_wem_size,
                                   used_files, seen_sources, seen_walked, sources_to_convert, seen_wems,
                                   stream_file_paths, memory_file_paths, source_properties_by_id, only_language,
                                   xml_index))
    return total_wav_size, total_memory_wem_size, total_stream_wem_size, used_files


# 用 ak.wwise.core.audio.convert 为未转码的源生成一次 wem 后补充压缩大小（该接口需 Wwise 2024 及以上版本）
def _convert_missing_wem_sources(sources: list, total_memory_wem_size: float, total_stream_wem_size: float, seen_wems: set) -> tuple:
    if project_utils.get_project_version() < 2024:
        Logger().warning(f'当前 Wwise 版本不支持WAAPI转码（需 2024 及以上），跳过 {len(sources)} 个未转码源的 wem 生成')
        return total_memory_wem_size, total_stream_wem_size
    # 当前平台作为与 convertedWemFilePath 一致的转码上下文
    platform_name = project_utils.get_current_platform_name()
    if not platform_name:
        Logger().warning('无法确定当前平台，跳过未转码源的 wem 生成')
        return total_memory_wem_size, total_stream_wem_size
    # 按源所属语言分组转码，保证每个源只按自己的语言生成
    language_sources_map = {}
    for source in sources:
        language_sources_map.setdefault(localization_utils.get_sound_language(source), []).append(source)
    languages = sorted(language_sources_map)
    Logger().info(f'检测到 {len(sources)} 个源缺少 wem，尝试用 ak.wwise.core.audio.convert 生成一次（平台: {platform_name}，语言: {", ".join(languages)}）')
    for language in languages:
        result = waapi_utils.convert_audio_objects(language_sources_map[language], [platform_name], [language])
        for error in (result or {}).get('errors') or []:
            Logger().error(str(error))
    # 生成成功后重新读取每个源的 wem 路径并累加压缩大小
    parent_by_source_id = {}
    unique_parents = {}
    for source in sources:
        parent = waapi_utils.get_parent_object(source)
        if parent and parent.is_valid:
            parent_by_source_id[source.id] = parent
            unique_parents[parent.id] = parent
    properties_by_id = waapi_utils.get_objects_properties(
        sources + list(unique_parents.values()),
        ['convertedWemFilePath', 'IsStreamingEnabled'],
    )
    for source in sources:
        wem_path = properties_by_id.get(source.id, {}).get('convertedWemFilePath')
        if not wem_path or not os.path.exists(wem_path):
            continue
        if wem_path in seen_wems:
            continue
        seen_wems.add(wem_path)
        wem_size = os.path.getsize(wem_path) / 1024
        parent = parent_by_source_id.get(source.id)
        is_streaming = properties_by_id.get(parent.id, {}).get('IsStreamingEnabled') if parent else False
        if is_streaming:
            total_stream_wem_size += wem_size
        else:
            total_memory_wem_size += wem_size
        Logger().debug(f'{wem_path} has size of {wem_size}KB')
    return total_memory_wem_size, total_stream_wem_size


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


# 生成 Event 与包含它的 SoundBank 的对应关系（Event id -> Bank 名称列表，按 Bank 顺序去重）
def build_event_bank_map() -> dict:
    event_bank_map = {}
    all_banks = waapi_utils.find_all_objects_by_type(WwiseObjectType.SoundBank)
    for bank in all_banks:
        for inclusion in waapi_utils.get_bank_inclusions(bank):
            obj = waapi_utils.get_full_info_from_obj_id(inclusion.get('object'))
            if not obj or not obj.is_valid:
                continue
            # 直接包含 Event，或包含 Event 上级的 Folder/WorkUnit 时都要算出其中的 Event
            if obj.type == WwiseObjectType.Event:
                events = [obj]
            elif obj.path.startswith('\\Events'):
                events = waapi_utils.get_descendants_of_type(obj, WwiseObjectType.Event)
            else:
                continue
            for event in events:
                bank_names = event_bank_map.setdefault(event.id, [])
                if bank.name not in bank_names:
                    bank_names.append(bank.name)
    return event_bank_map
