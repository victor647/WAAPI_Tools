import os
import xml.etree.ElementTree as ET

from libraries.utils.log_utils import Logger
from libraries.utils.wwise import project_utils
from libraries.wwise_object import WwiseObject


# 插件参数里代表「Quality」的属性名（不同 Format 叫法不同）
QUALITY_PROPERTY_NAMES = ('QualityFactor', 'Quality')
# 采样率属性名（值可能是 Wwise 的枚举值，也可能是具体 Hz）
SAMPLE_RATE_PROPERTY_NAME = 'SampleRate'

# 采样率属性里几个自动档的枚举值显示名；其余值按具体 Hz 原样显示
SAMPLE_RATE_LABELS = {
    '0': 'As Input',
    '1': 'Auto Low',
    '2': 'Auto Medium',
    '3': 'Auto High',
}

# WorkUnit 缓存：{文件路径: {'mtime': 修改时间, 'conversions': {对象ID: {平台: {'format', 'quality'}}}}}
_cache: dict = {}


# 采样率显示文本：0/1/2/3 是自动档枚举，其余（如 44100）按原值显示
def sample_rate_text(value) -> str:
    text = '' if value is None else str(value).strip()
    return SAMPLE_RATE_LABELS.get(text, text)


# 对象所在 WorkUnit 文件：从对象路径逐级向上找第一个存在的 .wwu
def find_workunit_path(obj: WwiseObject) -> str:
    project_dir = project_utils.get_project_directory()
    parts = [part for part in (obj.path or "").replace("/", "\\").split("\\") if part]
    if not project_dir or not parts:
        return ""
    for depth in range(len(parts) - 1, 0, -1):
        candidate = os.path.join(project_dir, *parts[:depth]) + ".wwu"
        if os.path.isfile(candidate):
            return candidate
    return ""


# 批量读取 Conversion ShareSet 的插件信息：
# {对象ID: {'format': Format, 'quality': Quality, 'sample_rate': 采样率}}
# 这三个参数 WAAPI 的 object.get 拿不到（或拿不到平台维度），只能从工程 WorkUnit（.wwu）读
def get_conversion_settings(conversions: list, platform: str) -> dict:
    ids_by_file: dict = {}
    conversion_by_id = {}
    for obj in conversions:
        if not obj or not obj.id:
            continue
        conversion_by_id[obj.id] = obj
        workunit_path = find_workunit_path(obj)
        if workunit_path:
            ids_by_file.setdefault(workunit_path, set()).add(obj.id)

    result = {object_id: {} for object_id in conversion_by_id}
    for workunit_path, object_ids in ids_by_file.items():
        parsed = _parse_conversions(workunit_path)
        for object_id in object_ids:
            info = parsed.get(object_id, {})
            plugin = dict((info.get('formats') or {}).get(platform) or {})
            if plugin:
                sample_rate = (info.get('sample_rate') or {}).get(platform) \
                    or (info.get('sample_rate') or {}).get('') or ''
                plugin['sample_rate'] = sample_rate
            result[object_id] = plugin
    return result


# 清空缓存（工程改动后需要重扫时调用）
def clear_cache() -> None:
    _cache.clear()


# 解析 .wwu 里的 Conversion 插件定义，结果按文件路径 + 修改时间缓存
def _parse_conversions(workunit_path: str) -> dict:
    try:
        mtime = os.path.getmtime(workunit_path)
    except OSError:
        return {}
    cached = _cache.get(workunit_path)
    if cached and cached.get('mtime') == mtime:
        return cached['conversions']
    try:
        conversions = _read_conversion_plugins(workunit_path)
    except Exception as error:
        Logger().error(f'解析 Conversion 设置失败：{workunit_path} ({error})')
        return {}
    _cache[workunit_path] = {'mtime': mtime, 'conversions': conversions}
    return conversions


# 流式读取单个 Conversion：
#   PropertyList/Property(SampleRate)                 -> 采样率（可能带平台 ValueList）
#   ConversionPluginInfo(Platform)/ConversionPlugin   -> Format(PluginName) + Quality 属性
def _read_conversion_plugins(workunit_path: str) -> dict:
    conversions: dict = {}
    current_id = None
    current_platform = None
    in_plugin = False
    for event, elem in ET.iterparse(workunit_path, events=('start', 'end')):
        if event == 'start':
            if elem.tag == 'Conversion':
                current_id = elem.get('ID')
                conversions.setdefault(current_id, {'formats': {}, 'sample_rate': {}})
            elif elem.tag == 'ConversionPluginInfo':
                current_platform = elem.get('Platform')
            elif elem.tag == 'ConversionPlugin':
                in_plugin = True
            continue
        if elem.tag == 'Property':
            if current_id and not in_plugin and elem.get('Name') == SAMPLE_RATE_PROPERTY_NAME:
                conversions[current_id]['sample_rate'].update(_platform_values(elem))
                elem.clear()
        elif elem.tag == 'ConversionPlugin':
            if current_id and current_platform:
                quality = ''
                for prop in elem.findall('./PropertyList/Property'):
                    if prop.get('Name') in QUALITY_PROPERTY_NAMES:
                        quality = prop.get('Value') or ''
                        break
                conversions[current_id]['formats'][current_platform] = {
                    'format': elem.get('PluginName') or '',
                    'quality': quality,
                }
            in_plugin = False
            elem.clear()
        elif elem.tag == 'ConversionPluginInfo':
            current_platform = None
        elif elem.tag == 'Conversion':
            current_id = None
            current_platform = None
            in_plugin = False
            elem.clear()
    return conversions


# 属性值可能是「按平台的 ValueList」，也可能只有一个 Value 属性；空平台键表示无平台维度的默认值
def _platform_values(prop) -> dict:
    values = {
        child.get('Platform') or '': (child.text or '').strip()
        for child in prop.findall('./ValueList/Value')
    }
    if not values and prop.get('Value') is not None:
        values[''] = (prop.get('Value') or '').strip()
    return values
