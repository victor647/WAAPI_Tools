import os
import xml.etree.ElementTree as ET

from libraries.utils.log_utils import Logger
from libraries.utils.wwise import waapi_utils
from libraries.wwise_object import WwiseObject

# 可能带 ActiveSourceList 的对象类型
OWNER_TAGS = {
    'Sound', 'AudioFileSource', 'ActorMixer', 'PropertyContainer', 'RandomSequenceContainer', 'SwitchContainer',
    'BlendContainer', 'MusicSegment', 'MusicTrack',
}

# WorkUnit 缓存：{文件路径: {'mtime': 修改时间, 'actives': {对象ID: [活跃源ID]}}}
_cache: dict = {}


# 读取某个 WorkUnit 里所有对象的 ActiveSourceList：{"in use" 的源是 Wwise 真正会播放的那些}
def get_active_source_ids(workunit_path: str) -> dict:
    if not workunit_path or not os.path.isfile(workunit_path):
        return {}
    try:
        mtime = os.path.getmtime(workunit_path)
    except OSError:
        return {}
    cached = _cache.get(workunit_path)
    if cached and cached.get('mtime') == mtime:
        return cached['actives']
    try:
        actives = _parse_active_source_lists(workunit_path)
    except Exception as error:
        Logger().error(f'解析 WorkUnit 失败：{workunit_path} ({error})')
        return {}
    _cache[workunit_path] = {'mtime': mtime, 'actives': actives}
    return actives


# 流式解析 .wwu（36MB 文件约 1.7 秒），取出每个对象的 ActiveSourceList 成员 ID
def _parse_active_source_lists(workunit_path: str) -> dict:
    actives: dict = {}
    owner_stack: list = []
    active_owner = None
    for event, elem in ET.iterparse(workunit_path, events=('start', 'end')):
        if event == 'start':
            if elem.tag in OWNER_TAGS:
                owner_stack.append((elem.tag, elem.get('ID')))
            elif elem.tag == 'ActiveSourceList':
                active_owner = owner_stack[-1][1] if owner_stack else None
            continue
        if elem.tag == 'ActiveSourceList':
            if active_owner:
                actives.setdefault(active_owner, [])
                actives[active_owner].extend(child.get('ID') for child in elem)
            active_owner = None
            elem.clear()
        elif elem.tag in OWNER_TAGS:
            if owner_stack and owner_stack[-1][0] == elem.tag:
                owner_stack.pop()
            elem.clear()
    return actives


# 清空缓存（工程改动后需要重扫时调用）
def clear_cache() -> None:
    _cache.clear()


# 取某个对象所在 WorkUnit 里该对象的活跃源 ID 集合（取不到返回空集合）
# workunit_path 已由调用方批量取到时直接传入，省掉一次 WAAPI 往返
def get_active_source_ids_for_object(obj: WwiseObject, workunit_path: str = None) -> set:
    path = workunit_path or waapi_utils.get_object_property(obj, 'workUnit.filePath')
    if not path:
        return set()
    return {source_id for source_id in get_active_source_ids(path).get(obj.id, []) if source_id}
