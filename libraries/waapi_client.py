# JSON/dict 层 WAAPI：入参出参均为 dict 或原生值；供 MCP 与 WAAPI 门面共用。
import os.path
import threading
import time
from waapi import WaapiClient
from libraries.singleton import Singleton
from libraries.utils.log_utils import Logger
from libraries.utils import user_config
from libraries.utils.wwise import project_utils, wwise_compat

RETURN_FIELDS = {'return': ['id', 'name', 'type', 'path']}


# waapi-client 0.8.1 的 _WampCallbackHandler 只把 kwargs 交给订阅回调，
# 会丢掉 WAMP 事件的位置参数（commands.executed 的 payload 就是位置参数）。
# 在项目侧补一层转发，避免升级依赖前订阅回调拿不到 payload。
def _patch_waapi_subscription_args() -> None:
    try:
        from waapi.wamp.async_decoupled_client import _WampCallbackHandler
    except Exception:
        return
    if getattr(_WampCallbackHandler, "_toolkit_args_patched", False):
        return

    def patched_call(self, *args, **kwargs):
        if not (self._callback and callable(self._callback)):
            return

        def invoke():
            try:
                if args:
                    self._callback(*args, **kwargs)
                else:
                    self._callback(**kwargs)
            except Exception:
                # 回调线程一旦抛异常会退出，后续订阅事件全部静默丢失
                Logger().exception('WAAPI 订阅回调异常')

        self._executor.execute(invoke, {})

    _WampCallbackHandler.__call__ = patched_call
    _WampCallbackHandler._toolkit_args_patched = True


_patch_waapi_subscription_args()


# 日志用的参数摘要：长字符串/大列表只留长度，避免一行日志爆长
def _summarize_value(value, depth: int = 0) -> str:
    if isinstance(value, str):
        return value if len(value) <= 80 else value[:60] + f"...({len(value)}字符)"
    if isinstance(value, dict):
        if depth >= 2:
            return "{...}"
        items = list(value.items())[:8]
        body = ", ".join(f"{key}={_summarize_value(item, depth + 1)}" for key, item in items)
        suffix = f", ...共{len(value)}项" if len(value) > len(items) else ""
        return "{" + body + suffix + "}"
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        if len(items) <= 6:
            return "[" + ", ".join(_summarize_value(item, depth + 1) for item in items) + "]"
        return f"[{len(items)}项：{', '.join(_summarize_value(i, depth + 1) for i in items[:3])}, ...]"
    return str(value)


def _describe_call_args(args: tuple, kwargs: dict) -> str:
    parts = [_summarize_value(value) for value in args if value is not None]
    parts.extend(f"{key}={_summarize_value(value)}" for key, value in kwargs.items())
    return " ".join(parts)


def _describe_call_result(result) -> str:
    if result is None:
        return "None"
    if isinstance(result, list):
        return f"{len(result)} 条"
    if isinstance(result, dict):
        body = ", ".join(f"{key}={_summarize_value(value, 1)}" for key, value in list(result.items())[:6])
        return "{" + body + "}"
    return _summarize_value(result)


class WAAPIClient(metaclass=Singleton):

    # 已经创建过的实例；未连接成功（构造抛异常）时返回 None，
    # 供关闭连接、查询连接状态等场景使用，避免再次触发构造与连接异常
    @classmethod
    def get_existing(cls) -> "WAAPIClient | None":
        return cls._instances.get(cls)

    def __init__(self, port: int=8080):
        self.client: WaapiClient = None
        self.port = port
        # 是否已经处于撤销组内（Wwise 不支持撤销组嵌套，嵌套时要复用外层组）
        self.undo_group_open = False
        # 底层 websocket 客户端不支持并发调用；界面线程、批处理线程与 AI 线程共用同一连接
        self._call_lock = threading.RLock()
        self.connect()

    # 获取Waapi客户端
    def connect(self) -> WaapiClient:
        if not self.client:
            self.client = WaapiClient(url=f'ws://127.0.0.1:{self.port}/waapi')
            self._lock_client_calls()
        return self.client

    # 串行化 WAAPI 调用，避免多线程并发使用同一 websocket 导致的原生崩溃
    def _lock_client_calls(self) -> None:
        original_call = self.client.call
        lock = self._call_lock

        def locked_call(*args, **kwargs):
            topic = str(args[0]) if args else "?"
            # 明细日志关闭时不构造参数/结果摘要，省掉每条调用的字符串拼装
            detailed = Logger().detail_on()
            summary = _describe_call_args(args[1:], kwargs) if detailed else ""
            started = time.perf_counter()
            failure = None
            with lock:
                try:
                    result = original_call(*args, **kwargs)
                except Exception as e:
                    failure = e
                    result = None
            elapsed_ms = (time.perf_counter() - started) * 1000
            if failure is not None:
                # 记录失败调用的主题、参数与耗时，便于对着日志排查
                if not summary:
                    summary = _describe_call_args(args[1:], kwargs)
                Logger().trace(f"WAAPI 失败 {topic} {summary} [{elapsed_ms:.0f}ms] "
                               f"{type(failure).__name__}: {failure}", console=False)
                raise failure
            if detailed:
                Logger().trace(
                    f"WAAPI {topic} {summary} [{elapsed_ms:.0f}ms] -> {_describe_call_result(result)}",
                    console=False, detail=True)
            return result

        self.client.call = locked_call

    # 订阅 WAAPI 主题；回调可能在工作线程触发，调用方需自行切回 GUI 线程
    def subscribe_topic(self, topic: str, callback, options: dict = None):
        if not self.client:
            return None
        try:
            with self._call_lock:
                return self.client.subscribe(topic, callback, options or {})
        except Exception as e:
            Logger().error(str(e))
            return None

    # 取消订阅
    def unsubscribe_topic(self, event_handler) -> bool:
        if not self.client or event_handler is None:
            return False
        try:
            with self._call_lock:
                return self.client.unsubscribe(event_handler)
        except Exception as e:
            Logger().error(str(e))
            return False

    # 关闭Waapi客户端连接
    # graceful=False 用于应用退出：不等待 WAMP GOODBYE 握手（该等待无超时），
    # 也不与仍在进行的 WAAPI 调用并发操作原生连接，交给进程退出直接回收。
    def disconnect(self, timeout: float = 2.0, graceful: bool = True):
        if not self.client:
            return
        client = self.client
        self.client = None
        if not graceful:
            Logger().debug("WAAPI - 应用退出，跳过优雅断开（连接随进程退出回收）")
            return

        def _close():
            # autobahn 客户端不支持并发访问：与在途 WAAPI 调用共用同一把锁串行化
            with self._call_lock:
                client.disconnect()

        try:
            # WaapiClient.disconnect() 内部会同步等待 WAMP GOODBYE 握手与线程 join（无超时），
            # 若 Wwise 繁忙或连接半开会长时间卡住；放到守护线程里限时等待
            closer = threading.Thread(target=_close, daemon=True)
            closer.start()
            closer.join(timeout=timeout)
            if closer.is_alive():
                Logger().warning("WAAPI 断开超时，已放弃等待（进程退出时自动回收连接）")
                # 清理线程可能还占着旧锁：换一把新锁，避免后续 WAAPI 调用被永久阻塞；
                # 旧连接只由该线程持有，新连接会创建全新的 socket，不与它共享原生状态
                self._call_lock = threading.RLock()
        except Exception as e:
            Logger().error(f"WAAPI - Error closing WAAPI client: {e}")

    # 是否已经连接
    def is_connected(self):
        return self.client and self.client.is_connected()

    # region Query
    # 获取Wwise软件相关信息
    def get_authoring_info(self, property_name: str) -> dict:
        if not self.client:
            return {}
        try:
            result = self.client.call('ak.wwise.core.getInfo')
            if not result:
                return {}
            return result[property_name]
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 获取工程全局信息
    def get_project_info(self, property_name: str) -> dict:
        if not self.client:
            return {}
        try:
            result = self.client.call('ak.wwise.core.getProjectInfo')
            if not result:
                return {}
            return result[property_name]
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 获取工程全局属性
    def get_project_property(self, property_name: str):
        if not self.client:
            return ""
        try:
            get_args = {}
            get_args['waql'] = 'from type Project'
            get_args['options'] = {'return': [property_name]}
            result = self.client.call('ak.wwise.core.object.get', get_args)
            if result:
                return result['return'][0][property_name]

            Logger().error(f'WAAPI - Cannot find property named [{property_name}] in project!')
            return ""
        except Exception as e:
            Logger().error(str(e))
            return ""

    # 获取对象的属性
    def get_object_property(self, obj: dict, property_name: str, platform=None):
        if not self.client or not obj:
            return None
        try:
            get_args = {}
            get_args ['waql'] = f'from object \"{obj["id"]}\"'
            options = {'return': [property_name]}
            if platform:
                options['platform'] = platform
            get_args['options'] = options
            result = self.client.call('ak.wwise.core.object.get', get_args)
            if not result or result['return'][0] == {}:
                Logger().error(f"WAAPI - Cannot find property named [{property_name}] in {obj.get('type')} [{obj.get('path')}]!")
                return None
            return_obj = result['return'][0]
            return return_obj[property_name] if property_name in return_obj else None
        except Exception as e:
            Logger().error(str(e))
            return None

    # 一次读取对象的多个属性；对象类型上不存在的属性不会出现在结果中
    def get_object_properties(self, obj: dict, property_names: list, platform=None) -> dict:
        if not self.client or not obj or not property_names:
            return {}
        try:
            get_args = {}
            get_args['waql'] = f'from object \"{obj["id"]}\"'
            options = {'return': property_names}
            if platform:
                options['platform'] = platform
            get_args['options'] = options
            result = self.client.call('ak.wwise.core.object.get', get_args)
            if not result or not result.get('return'):
                return {}
            found = result['return'][0] or {}
            return {name: found[name] for name in property_names if name in found}
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 一次读取多个对象的多个属性；返回 {对象ID: {属性名: 值}}，与 get_object_properties 同口径：
    # 只保留请求的属性，类型上不存在的属性不会出现在结果中。
    # 注意：from.id 只接受数组，传单个字符串会被 Wwise 判为参数非法。
    # 对象数超过「查询分页大小」设置时自动分批取回再合并，避免单次请求过大
    def get_objects_properties(self, objects: list[dict], property_names: list, platform=None) -> dict:
        object_ids = [obj["id"] for obj in objects if obj and obj.get("id")]
        if not self.client or not object_ids or not property_names:
            return {}
        # from.id 形式下 Wwise 不会自动带上 id，必须显式请求，否则结果无法按对象归位
        requested_names = list(dict.fromkeys(property_names))
        interval = max(1, user_config.get_tool_page_size())
        found: dict = {}
        for start in range(0, len(object_ids), interval):
            options = {'return': list(dict.fromkeys(['id', *requested_names]))}
            if platform:
                options['platform'] = platform
            get_args = {
                'from': {'id': object_ids[start:start + interval]},
                'options': options,
            }
            try:
                result = self.client.call('ak.wwise.core.object.get', get_args)
            except Exception as e:
                # 单批失败不影响其它批次，缺的属性由调用方按“取不到”处理
                Logger().error(str(e))
                continue
            for item in (result or {}).get('return') or []:
                if item.get('id'):
                    found[item['id']] = {name: item[name] for name in requested_names if name in item}
        return found

    # 当前对象类型上可用的属性与引用名称；object.get 的 return 只能使用此处列出的名称（见官方 ak.wwise.core.object.getPropertyAndReferenceNames）
    def get_property_and_reference_names(self, obj: dict) -> list[str]:
        if not self.client or not obj:
            return []
        try:
            result = self.client.call(
                "ak.wwise.core.object.getPropertyAndReferenceNames",
                {"object": obj["id"]},
            )
            if result and result.get("return") is not None:
                return list(result["return"])
            return []
        except Exception as e:
            Logger().error(str(e))
            return []


    # 将对象的某个属性复制到其他对象上
    def paste_object_property(self, source_obj: dict, target_objects: list[dict], property_name: str) -> bool:
        if not self.client or not source_obj or target_objects == []:
            return False
        try:
            target_ids = [t["id"] for t in target_objects]
            paste_args = {
                'source': source_obj["id"],
                'targets': target_ids,
                'inclusion': [property_name]
            }
            result = self.client.call('ak.wwise.core.object.pasteProperties', paste_args)
            return result is not None
        except Exception as e:
            Logger().error(str(e))
            return False

    # 获取选中的对象列表
    def get_selected_objects(self) -> list[dict]:
        if not self.client:
            return []
        try:
            get_args = {'options': RETURN_FIELDS}
            result = self.client.call('ak.wwise.ui.getSelectedObjects', get_args)
            return list(result['objects']) if result else []
        except Exception as e:
            Logger().error(str(e))
            return []

    # 根据路径查找对象
    def get_object_from_path(self, path: str) -> dict:
        if not self.client:
            return {}
        try:
            get_args = {}
            get_args ['waql'] = f'from object \"{path}\"'
            get_args['options'] = RETURN_FIELDS
            result = self.client.call('ak.wwise.core.object.get', get_args)
            if not result or not result.get('return'):
                return {}
            ret = result['return']
            if isinstance(ret, list):
                return ret[0] if len(ret) > 0 else {}
            return ret
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 获取一个对象所有的引用
    def get_object_references(self, obj: dict) -> list[dict]:
        if not self.client or not obj:
            return []
        try:
            get_args = {}
            obj_id = obj["id"]
            get_args ['waql'] = f'from object \"{obj_id}\" select referencesTo'
            get_args['options'] = RETURN_FIELDS
            result = self.client.call('ak.wwise.core.object.get', get_args)
            if not result or not result.get('return'):
                return []
            return list(result['return'])
        except Exception as e:
            Logger().error(str(e))
            return []

    # AudioFileSource 无法用 referencesTo 反查引用，按源文件相对路径反查所有使用同一源文件的对象
    def find_audio_sources_by_original_path(self, original_relative_path: str) -> list[dict]:
        if not self.client or not original_relative_path:
            return []
        try:
            get_args = {}
            get_args['waql'] = f'from type AudioFileSource where originalRelativeFilePath = "{original_relative_path}"'
            get_args['options'] = RETURN_FIELDS
            result = self.client.call('ak.wwise.core.object.get', get_args)
            if not result or not result.get('return'):
                return []
            return list(result['return'])
        except Exception as e:
            Logger().error(str(e))
            return []

    # 获取一个对象直属上层的对象
    def get_parent_object(self, obj: dict) -> dict:
        if not self.client or not obj:
            return {}
        try:
            get_args = {}
            obj_id = obj["id"]
            get_args ['waql'] = f'from object \"{obj_id}\" select parent'
            get_args['options'] = RETURN_FIELDS
            result = self.client.call('ak.wwise.core.object.get', get_args)
            parents = result['return']
            return parents[0] if len(parents) > 0 else {}
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 获取一个对象递归上层的所有对象
    def get_ancestor_objects(self, obj: dict) -> list[dict]:
        if not self.client or not obj:
            return []
        try:
            obj_id = obj["id"]
            return self._paged_object_query({'waql': f'from object \"{obj_id}\" select ancestors'})
        except Exception as e:
            Logger().error(str(e))
            return []

    # 获取一个对象递归下层的所有子对象
    def get_child_objects(self, obj: dict, include_descendants=False) -> list[dict]:
        if not self.client or not obj:
            return []
        try:
            children = []
            seen_ids: set = set()
            index = 0
            interval = user_config.get_tool_page_size()
            while True:
                get_args = {
                    'from': {'id': [obj["id"]]},
                    'transform': [
                        {'select': ['descendants' if include_descendants else 'children']},
                        {'range': [index * interval, interval]}
                    ],
                    'options': RETURN_FIELDS
                }
                cur_range_result = self.client.call('ak.wwise.core.object.get', get_args)
                page = list(cur_range_result['return']) if cur_range_result and cur_range_result.get('return') else []
                new_items = [item for item in page if item.get('id') not in seen_ids]
                if new_items:
                    seen_ids.update(item.get('id') for item in new_items)
                    children += new_items
                # 不满一页说明已经取完；去重后没有新对象则覆盖 range 被忽略、反复返回同一批的情况
                if len(page) < interval or not new_items:
                    break
                index += 1
            return children
        except Exception as e:
            Logger().error(str(e))
            return []

    # 一次读取多个对象的直接子对象：按容器 ID 分块查询，结果带 parent 便于按父级归组
    def get_children_of_objects(self, objects: list[dict], return_fields: list = None) -> list[dict]:
        object_ids = [obj["id"] for obj in objects if obj and obj.get("id")]
        if not self.client or not object_ids:
            return []
        interval = max(1, user_config.get_tool_page_size())
        requested_fields = list(dict.fromkeys(['parent', *(return_fields or [])]))
        children: list[dict] = []
        seen_ids: set = set()
        fallback_logged = False
        for start in range(0, len(object_ids), interval):
            chunk = object_ids[start:start + interval]
            chunk_set = set(chunk)
            chunk_children: list[dict] = []
            try:
                chunk_children = self._paged_object_query({
                    'from': {'id': chunk},
                    'transform': [{'select': ['children']}],
                }, return_fields=requested_fields)
            except Exception as e:
                Logger().error(str(e))
            # 批量 children 查询失效时退回逐个容器读取，保证结果完整
            has_chunk_child = any(
                ((item.get('parent') or {}).get('id') in chunk_set)
                for item in chunk_children
            )
            if not has_chunk_child:
                if not fallback_logged:
                    Logger().warning(
                        f'批量读取子对象失败，改为逐个读取（首批 {len(chunk)} 个容器）'
                    )
                    fallback_logged = True
                chunk_children = []
                for object_id in chunk:
                    for item in self.get_child_objects({'id': object_id}):
                        item['parent'] = {'id': object_id}
                        chunk_children.append(item)
            for item in chunk_children:
                if item.get('id') and item['id'] not in seen_ids:
                    seen_ids.add(item['id'])
                    children.append(item)
        return children

    # 获取指定类型的全部子对象（child_type 可为类型的字符串或字符串列表）
    def get_descendants_of_type(self, obj: dict, child_type, return_fields: list = None) -> list[dict]:
        if not self.client or not obj:
            return []
        types = [child_type] if isinstance(child_type, str) else [t for t in child_type if t]
        if not types:
            return []
        obj_id = obj["id"]
        try:
            condition = ' or '.join(f'type = "{child_type_name}"' for child_type_name in types)
            waql = f'from object \"{obj_id}\" select descendants where {condition}'
            return self._paged_object_query({'waql': waql}, return_fields=return_fields)
        except Exception as e:
            Logger().error(str(e))
            return []

    # 一次批量查询多个根对象的全部后代（可按类型过滤）：按分页大小分块，避免逐对象各查一次
    def get_descendants_of_objects(self, objects: list[dict], child_types=None, return_fields: list = None) -> list[dict]:
        object_ids = [obj["id"] for obj in objects if obj and obj.get("id")]
        if not self.client or not object_ids:
            return []
        if isinstance(child_types, str):
            child_types = [child_types]
        types = {(item.value if hasattr(item, 'value') else str(item)) for item in (child_types or []) if item}
        interval = max(1, user_config.get_tool_page_size())
        found: list[dict] = []
        seen_ids: set = set()
        for start in range(0, len(object_ids), interval):
            chunk = object_ids[start:start + interval]
            chunk_set = set(chunk)
            try:
                items = self._paged_object_query(
                    {'from': {'id': chunk}, 'transform': [{'select': ['descendants']}]},
                    return_fields=return_fields,
                )
            except Exception as e:
                Logger().error(str(e))
                items = []
            # 该版本不支持批量 select descendants 时会原样返回根对象，退回逐个查询保证结果完整
            if any(item.get('id') in chunk_set for item in items):
                items = []
                for object_id in chunk:
                    if types:
                        items.extend(self.get_descendants_of_type({'id': object_id}, list(types),
                                                                  return_fields=return_fields))
                    else:
                        items.extend(self.get_child_objects({'id': object_id}, include_descendants=True))
            for item in items:
                item_id = item.get('id')
                if not item_id or item_id in seen_ids:
                    continue
                if types and item.get('type') not in types:
                    continue
                seen_ids.add(item_id)
                found.append(item)
        return found

    # 按配置的分页大小执行 object.get，直到取完（range 被忽略时靠去重保护退出）
    # 分页范围必须放在 transform 步骤里：部分 Wwise 版本（如 2023.1）不接受顶层 range，会直接报错
    def _paged_object_query(self, base_args: dict, return_fields: list = None) -> list[dict]:
        objects: list[dict] = []
        seen_ids: set = set()
        interval = user_config.get_tool_page_size()
        index = 0
        requested_fields = list(dict.fromkeys([
            *RETURN_FIELDS['return'],
            *(return_fields or []),
        ]))
        while True:
            get_args = dict(base_args)
            get_args['options'] = {'return': requested_fields}
            # 已有 transform 步骤的查询（如后代回退查询）在其后追加分页范围，不要覆盖
            get_args['transform'] = list(base_args.get('transform') or []) + [{'range': [index * interval, interval]}]
            result = self.client.call('ak.wwise.core.object.get', get_args)
            page = list(result['return']) if result and result.get('return') else []
            new_items = [item for item in page if item.get('id') not in seen_ids]
            for item in new_items:
                seen_ids.add(item.get('id'))
            objects += new_items
            if len(page) < interval or not new_items:
                break
            index += 1
        return objects

    # 通用 WAQL 查询入口：只读，等价于 ak.wwise.core.object.get + waql
    def get_objects_by_waql(self, waql: str, return_fields: list = None) -> list[dict]:
        if not self.client or not (waql or "").strip():
            return []
        # 通用查询是逃生口：不再额外吞异常。底层 WAMP 错误由 waapi-client 记录（通常返回 None），
        # 若底层选择抛出，异常会原样传给调用方。
        return self._paged_object_query({'waql': str(waql).strip()}, return_fields=return_fields)

    # 获取整个Wwise工程所有对象
    def get_global_objects(self) -> list[dict]:
        if not self.client:
            return []
        try:
            global_objects = []
            property_container_type = wwise_compat.default_property_container_type()
            objects_type = (
                'WorkUnit', property_container_type, 'Folder', 'SwitchContainer', 'BlendContainer',
                'RandomSequenceContainer',
                'Sound', 'Event', 'AuxBus', 'Bus', 'SoundBank', 'StateGroup', 'SwitchGroup', 'GameParameter',
                'MusicSwitchContainer', 'MusicPlaylistContainer', 'MusicSegment', 'MusicTrack',
            )
            for obj_type in objects_type:
                results = self.find_all_objects_by_type(obj_type)
                global_objects += results
            return global_objects
        except Exception as e:
            Logger().error(str(e))
            return []

    # 通过guid获取对象完整信息
    def get_full_info_from_obj_id(self, obj_id) -> dict:
        if not self.client or not obj_id:
            return {}
        try:
            get_args = {}
            get_args ['waql'] = f'from object \"{obj_id}\"'
            get_args['options'] = RETURN_FIELDS
            return_obj = self.client.call('ak.wwise.core.object.get', get_args)
            if not return_obj or len(return_obj['return']) == 0:
                return {}
            return return_obj['return'][0]
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 从路径获取对象
    def find_object_by_path(self, path: str) -> dict:
        if not self.client:
            return {}
        try:
            get_args = {}
            get_args ['waql'] = f'from object \"{path}\"'
            get_args['options'] = RETURN_FIELDS
            return_obj = self.client.call('ak.wwise.core.object.get', get_args)
            if not return_obj or len(return_obj['return']) == 0:
                return {}
            return return_obj['return'][0]
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 从名称和类型获取对象（obj_type 为 Wwise API 类型字符串）
    def find_object_by_name_and_type(self, obj_name: str, obj_type: str, exact_match=True) -> dict:
        if not self.client:
            return {}
        try:
            get_args = {}
            get_args ['waql'] = f'from type {obj_type} where name: \"*{obj_name}\"'
            get_args['options'] = RETURN_FIELDS
            return_obj = self.client.call('ak.wwise.core.object.get', get_args)
            if return_obj is None or len(return_obj['return']) == 0:
                return {}
            # 可模糊查找
            if not exact_match:
                return return_obj['return'][0]
            # 仅查找名称完全一致的对象
            for raw in return_obj['return']:
                if raw.get('name') == obj_name:
                    return raw
            return {}
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 查找所有符合名称的对象
    def find_all_objects_by_name(self, obj_name: str, exact_match: bool) -> list[dict]:
        if not self.client:
            return []
        try:
            found = self._paged_object_query({'waql': f'from search \"{obj_name}\"'})
            if not found:
                return []
            if not exact_match:
                return found
            matching_objects = []
            for raw in found:
                if raw.get('name') == obj_name:
                    matching_objects.append(raw)
            return matching_objects
        except Exception as e:
            Logger().error(str(e))
            return []

    # 查找所有特定类型的对象（obj_type 为 Wwise API 类型字符串）
    def find_all_objects_by_type(self, obj_type: str) -> list[dict]:
        if not self.client:
            return []
        try:
            return self._paged_object_query({'waql': f'from type {obj_type}'})
        except Exception as e:
            Logger().error(str(e))
            return []
    # endregion Query

    # region CommonOperation
    # 在对应类别的默认Work Unit下创建对象（obj_type 为 Wwise API 类型字符串）
    def create_object_at_default_location(self, obj_name: str, obj_type: str) -> dict:
        if not self.client:
            return {}
        try:
            if obj_type == 'Bus':
                default_path = wwise_compat.default_bus_path()
            elif obj_type == 'Event':
                default_path = '\\Events\\Default Work Unit'
            elif obj_type == 'SwitchGroup':
                default_path = '\\Switches\\Default Work Unit'
            elif obj_type == 'StateGroup':
                default_path = '\\States\\Default Work Unit'
            elif obj_type == 'GameParameter':
                default_path = '\\Game Parameters\\Default Work Unit'
            elif obj_type == 'Trigger':
                default_path = '\\Triggers\\Default Work Unit'
            elif obj_type == 'Attenuation':
                default_path = '\\Attenuations\\Default Work Unit'
            elif obj_type == 'Conversion':
                default_path = '\\Conversion Settings\\Default Work Unit'
            elif 'Music' in obj_type:
                default_path = wwise_compat.default_music_work_unit()
            else:
                default_path = wwise_compat.default_audio_work_unit()
            create_args = {
                'parent': default_path,
                'type': obj_type,
                'name': obj_name,
                'onNameConflict': 'replace'
            }
            result_obj = self.client.call('ak.wwise.core.object.create', create_args)
            if result_obj:
                result_obj = self.get_full_info_from_obj_id(result_obj['id'])
                Logger().debug(f"WAAPI - {obj_type} [{obj_name}] created under default path [{default_path}]")
            return result_obj
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 在指定对象的下级创建一个新的对象（obj_type 为 Wwise API 类型字符串）
    def create_child_object(self, obj_name: str, obj_type: str,parent_obj: dict, on_name_conflict="fail") -> dict:
        if not self.client or not parent_obj:
            return {}
        try:
            create_args = {
                'parent': parent_obj["id"],
                'type': obj_type,
                'name': obj_name,
                'onNameConflict': on_name_conflict
            }
            result_obj = self.client.call('ak.wwise.core.object.create', create_args)
            if result_obj:
                result_obj = self.get_full_info_from_obj_id(result_obj['id'])
                Logger().debug(f"WAAPI - {obj_type} [{obj_name}] created under [{parent_obj.get('path', '')}]")
            return result_obj
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 在指定路径下创建一个新的对象
    def create_object_by_path(self, obj_path: str, obj_type: str, on_name_conflict='fail') -> dict:
        if not self.client:
            return {}
        try:
            parent_path = os.path.dirname(obj_path)
            obj_name = os.path.basename(obj_path)
            # Wwise 2021+ 通过 object.set 创建
            create_args = {
                'objects': [
                    {
                        'object': f'\\{parent_path}',
                        'children': [
                            {
                                'type': obj_type,
                                'name': obj_name,
                            }
                        ]
                    }
                ],
                'onNameConflict': on_name_conflict
            }
            result_obj = self.client.call('ak.wwise.core.object.set', create_args)
            if result_obj:
                result_obj = self.get_full_info_from_obj_id(result_obj['objects'][0]['children'][0]['id'])
                Logger().debug(f"WAAPI - {obj_type} [{obj_path}] created")
            return result_obj
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 移动对象到新的路径
    def move_object(self, obj: dict, new_parent: dict) -> bool:
        if not self.client or not obj or not new_parent:
            return False
        try:
            move_args = {
                'object': obj["id"],
                'parent': new_parent["id"],
                'onNameConflict': 'replace'
            }
            self.client.call('ak.wwise.core.object.move', move_args)
            return True
        except Exception as e:
            Logger().error(str(e))
            return False

    # 复制对象到某个对象下面
    def copy_object(self, obj: dict, parent: dict) -> dict:
        if not self.client or not obj or not parent:
            return {}
        try:
            copy_args = {
                'object': obj["id"],
                'parent': parent["id"],
                'onNameConflict': 'rename'
            }
            result = self.client.call('ak.wwise.core.object.copy', copy_args, RETURN_FIELDS)
            result = self.get_full_info_from_obj_id(result['id'])
            if not result:
                Logger().error(f'WAAPI - Copy {obj} to {parent} failed!')
            return result
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 给一个对象重命名
    def rename_object(self, obj: dict, new_name: str) -> bool:
        if not self.client or not obj:
            return False
        if new_name == obj.get('name'):
            return True
        try:
            rename_args = {
                'object': obj["id"],
                'value': new_name
            }
            self.client.call('ak.wwise.core.object.setName', rename_args)
            Logger().debug(f"WAAPI - {obj.get('type')} [{obj.get('name')}] renamed to [{new_name}]")
            return True
        except Exception as e:
            Logger().error(str(e))
            return False

    # 设置对象的属性
    def set_object_property(self, obj: dict, property_name: str, value, platform=None) -> bool:
        if not self.client or not obj:
            return False
        try:
            set_args = {
                'object': obj["id"],
                'property': property_name,
                'value': value
            }
            if platform:
                set_args['platform'] = platform
            result = self.client.call('ak.wwise.core.object.setProperty', set_args) == {}
            if result:
                Logger().debug(f"WAAPI - {obj.get('type')} [{obj.get('name')}] property of {property_name} set to [{value}]")
            else:
                Logger().error(f"WAAPI - {obj.get('type')} [{obj.get('name')}]: Cannot set property of {property_name} to [{value}]!")
            return result
        except Exception as e:
            Logger().error(str(e))
            return False

    # 查询属性/引用在指定平台上是否仍链接到默认值；旧版本不支持时返回 None
    def get_object_property_linked(self, obj: dict, property_name: str, platform: str) -> bool | None:
        if not self.client or not obj or not property_name or not platform:
            return None
        try:
            result = self.client.call('ak.wwise.core.object.isLinked', {
                'object': obj["id"],
                'property': property_name,
                'platform': platform,
            })
            return bool((result or {}).get('linked'))
        except Exception as e:
            Logger().debug(
                f"WAAPI - 无法读取 {property_name} 在平台 [{platform}] 的链接状态：{e}"
            )
            return None

    # 设置属性/引用在某个平台上的链接状态；先 unlink 后再用 set_object_property(platform=...) 才能只改该平台
    def set_object_property_linked(self, obj: dict, property_name: str, platform: str, linked: bool) -> bool:
        if not self.client or not obj or not platform:
            return False
        try:
            set_args = {
                'object': obj["id"],
                'property': property_name,
                'platform': platform,
                'linked': linked,
            }
            result = self.client.call('ak.wwise.core.object.setLinked', set_args) == {}
            if result:
                Logger().debug(
                    f"WAAPI - {obj.get('type')} [{obj.get('name')}] property {property_name} "
                    f"on platform [{platform}] linked set to [{linked}]"
                )
            else:
                Logger().error(
                    f"WAAPI - {obj.get('type')} [{obj.get('name')}]: Cannot set link state of "
                    f"{property_name} on platform [{platform}]!"
                )
            return result
        except Exception as e:
            Logger().error(str(e))
            return False

    def set_objects_property_values(self, assignments: list[tuple[dict, object]], property_name: str) -> bool:
        if not self.client or not assignments:
            return False
        try:
            set_args = {
                'objects': [
                    {
                        'object': obj['id'],
                        f'@{property_name}': value
                    }
                    for obj, value in assignments
                ]
            }
            result = self.client.call('ak.wwise.core.object.set', set_args)
            if result is None:
                Logger().error(f"WAAPI - Cannot set {property_name} on {len(assignments)} objects!")
                return False
            Logger().debug(f"WAAPI - Set {property_name} on {len(assignments)} objects")
            return True
        except Exception as e:
            Logger().error(str(e))
            return False

    # 一次给单个对象设置多个属性（属性名 -> 值）；任一属性不可写时整批失败，由调用方逐个重试
    def set_object_property_values(self, obj: dict, property_values: dict) -> bool:
        if not self.client or not obj or not property_values:
            return False
        try:
            entry = {'object': obj["id"]}
            entry.update({f'@{name}': value for name, value in property_values.items()})
            result = self.client.call('ak.wwise.core.object.set', {'objects': [entry]})
            if result is None:
                Logger().error(
                    f"WAAPI - Cannot set {len(property_values)} properties on {obj.get('name')}!"
                )
                return False
            Logger().debug(
                f"WAAPI - Set {len(property_values)} properties on {obj.get('name')}"
            )
            return True
        except Exception as e:
            Logger().error(str(e))
            return False

    # 设置对象的引用
    def set_object_reference(self, obj: dict, reference_type: str, value: dict) -> bool:
        if not self.client or not obj or not value:
            return False
        try:
            set_args = {
                'object': obj["id"],
                'reference': reference_type,
                'value': value["id"]
            }
            result = self.client.call('ak.wwise.core.object.setReference', set_args) == {}
            if result:
                Logger().debug(f"WAAPI - {obj.get('type')} [{obj.get('name')}] reference of {reference_type} set to [{value.get('name')}]")
            else:
                Logger().error(f"WAAPI - Set reference of {reference_type} [{value.get('name')}] failed for {obj.get('type')} [{obj.get('name')}] reference  set to ")
            return result
        except Exception as e:
            Logger().error(str(e))
            return False

    # 为对象设置备注
    def set_object_notes(self, obj: dict, notes: str) -> bool:
        if not self.client or not obj:
            return False
        try:
            set_args = {
                "object": obj["id"],
                "value": notes
            }
            result = self.client.call('ak.wwise.core.object.setNotes', set_args) == {}
            return result
        except Exception as e:
            Logger().error(str(e))
            return False

    # 删除一个对象
    def delete_object(self, obj: dict) -> bool:
        if not self.client or not obj:
            return False
        try:
            delete_args = {'object': obj["id"]}
            result = self.client.call('ak.wwise.core.object.delete', delete_args) == {}
            if result:
                Logger().debug(f"WAAPI - Deleted {obj.get('type')} [{obj.get('name')}]")
            else:
                Logger().error(f"WAAPI - Delete {obj.get('type')} [{obj.get('name')}] failed")
            return result
        except Exception as e:
            Logger().error(str(e))
            return False
    # endregion CommonOperation

    # region LogicContainer
    # 为顺序容器设置播放列表
    def set_sequence_container_playlist(self, container: dict, playlist: list[dict]) -> bool:
        if not self.client or not container:
            return False
        try:
            set_args = {
                'objects': [{
                    'object': container["id"],
                    '@Playlist': [item["id"] for item in playlist]
                }],
                'onNameConflict': 'merge',
                'listMode': 'replaceAll'
            }
            self.client.call('ak.wwise.core.object.set', set_args)
            return True
        except Exception as e:
            Logger().error(str(e))
            return False

    # 获取SwitchContainer的当前分配的对象
    def get_switch_mappings(self, container: dict) -> list:
        if not self.client or not container:
            return []
        if container.get('type') not in ('SwitchContainer', 'MusicSwitchContainer'):
            return []
        try:
            assign_args = {
                'id': container["id"]
            }
            options = RETURN_FIELDS
            result = self.client.call('ak.wwise.core.switchContainer.getAssignments', assign_args, options)
            return result['return'] if result else []
        except Exception as e:
            Logger().error(str(e))
            return []

    # 分配SwitchContainer的内容
    def assign_switch_mapping(self, target: dict, switch_obj: dict) -> bool:
        if isinstance(switch_obj, str):
            so = switch_obj
        elif not switch_obj:
            return False
        else:
            so = switch_obj["id"]
        if not self.client or not target or not so:
            return False
        try:
            state_or_switch = so
            assign_args = {
                'child': target["id"],
                'stateOrSwitch': state_or_switch
            }
            self.client.call('ak.wwise.core.switchContainer.addAssignment', assign_args)
            return True
        except Exception as e:
            Logger().error(str(e))
            return False

    # 删除Switch Container下面所有的分配
    def remove_switch_mappings(self, obj: dict) -> bool:
        if not self.client or not obj or obj.get('type') not in ('SwitchContainer', 'MusicSwitchContainer'):
            return False
        try:
            get_args = {'id': obj["id"]}
            results = self.client.call('ak.wwise.core.switchContainer.getAssignments', get_args)['return']
            for assignment in results:
                self.client.call('ak.wwise.core.switchContainer.removeAssignment', assignment)
            return True
        except Exception as e:
            Logger().error(str(e))
            return False
    # endregion LogicContainer

    # region AudioSource
    # 导入新的音频文件
    def import_audio_file(self, wave_path: str, sound: dict, language='SFX') -> dict:
        if not self.client or not sound:
            return {}
        if not os.path.exists(wave_path):
            Logger().warning(f'WAAPI - Import failed, file not found at {wave_path}')
            return {}
        try:
            import_args = {
                'importOperation': 'createNew',
                'default': {
                    'objectType': 'Sound',
                    'importLanguage': language
                },
                'imports': [
                    {
                        'audioFile': wave_path,
                        'importLocation': sound["id"],
                        'objectPath': '<Sound>' + sound.get('name', '')
                    },
                ],
                "autoAddToSourceControl": True,
            }
            result = self.client.call('ak.wwise.core.audio.import', import_args)
            if not result or not result.get('objects'):
                return {}
            return result['objects'][0]
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 在现有 Sound 下导入一个新的 AudioFileSource，并在导入时指定语言
    # audioSource:language 不是可写属性/引用，只能通过导入语言设置
    def import_audio_source(self, sound: dict, wave_path: str, language='SFX', source_name='',
                            originals_subfolder='') -> dict:
        if not self.client or not sound or not wave_path:
            return {}
        if not os.path.exists(wave_path):
            Logger().warning(f'WAAPI - Import failed, file not found at {wave_path}')
            return {}
        try:
            name = source_name or os.path.splitext(os.path.basename(wave_path))[0]
            import_file = {'audioFile': wave_path, 'language': language}
            if originals_subfolder:
                import_file['originalsSubFolder'] = originals_subfolder
            set_args = {
                'objects': [{
                    'object': sound["id"],
                    'children': [{
                        'type': 'AudioFileSource',
                        'name': name,
                        'import': {'files': [import_file]},
                    }],
                }],
                'onNameConflict': 'rename',
            }
            result = self.client.call('ak.wwise.core.object.set', set_args, RETURN_FIELDS)
            for parent in (result or {}).get('objects') or []:
                for child in parent.get('children') or []:
                    if not child.get('id'):
                        continue
                    logs = (child.get('import') or {}).get('logs') or []
                    errors = [
                        log for log in logs
                        if str(log.get('severity', '')).lower() in ('error', 'fatal error')
                    ]
                    if errors:
                        for log in errors:
                            Logger().error(f"WAAPI - Import {wave_path} failed: {log.get('message')}")
                        try:
                            self.client.call('ak.wwise.core.object.delete', {'object': child['id']})
                        except Exception:
                            pass
                        return {}
                    child.setdefault('type', 'AudioFileSource')
                    return child
            return {}
        except Exception as e:
            Logger().error(str(e))
            return {}

    # 为声音创建静音源插件
    def add_silence(self, obj: dict, length: float, language='SFX') -> bool:
        if not self.client or not obj:
            return False
        try:
            set_args = {
                'objects': [{
                    'object': obj["id"],
                    'children': [
                        {
                            'type': 'SourcePlugin',
                            'name': f'Silence_{language}' if language != 'SFX' else 'Silence',
                            'classId': 6619138,
                            '@Length': length
                        }
                    ]
                }]
            }
            if language != 'SFX':
                set_args['objects'][0]['children'][0]['language'] = language
            options = RETURN_FIELDS
            result = self.client.call('ak.wwise.core.object.set', set_args, options)
            return result is not None
        except Exception as e:
            Logger().error(str(e))
            return False

    # 把指定对象转码出 wem（ak.wwise.core.audio.convert，需 Wwise 2024 及以上版本）；
    # 返回 {"errors": [...]}，成功时 errors 为空列表
    def convert_audio_objects(self, objects: list, platforms: list, languages: list) -> dict:
        if not self.client or not objects or not platforms or not languages:
            return {}
        try:
            convert_args = {
                'objects': objects,
                'platforms': platforms,
                'languages': languages,
            }
            result = self.client.call('ak.wwise.core.audio.convert', convert_args)
            return result or {}
        except Exception as e:
            try:
                current_version = project_utils.get_project_version()
            except Exception:
                current_version = 0
            if current_version < 2024:
                version_text = current_version if current_version > 0 else '未知'
                Logger().error(f'ak.wwise.core.audio.convert 需要 Wwise 2024 及以上版本，当前版本 {version_text} 不支持该接口')
            else:
                Logger().error(str(e))
            return {}

    # 从Sound层级获取包含的AudioSource
    def get_default_audio_source(self, sound: dict) -> dict:
        if not self.client or not sound:
            return {}
        try:
            get_args = {
                'from': {'id': [sound["id"]]},
                'transform': [{'select': ['children']}],
                'options': RETURN_FIELDS
            }
            result = self.client.call('ak.wwise.core.object.get', get_args)
            if not result or not result.get('return'):
                return {}
            return result['return'][0]
        except Exception as e:
            Logger().error(str(e))
            return {}
    # endregion AudioSource

    # region SoundBank
    # 获取bank中的内容
    def get_bank_inclusions(self, bank: dict) -> list:
        if not self.client or not bank:
            return []
        try:
            get_args = {'soundbank': bank["id"]}
            result = self.client.call('ak.wwise.core.soundbank.getInclusions', get_args)
            return result['inclusions'] if result else []
        except Exception as e:
            Logger().error(str(e))
            return []

    # 清除Bank中所有内容
    def clear_bank_inclusions(self, bank: dict) -> bool:
        if not self.client or not bank:
            return False
        if bank.get('type') != 'SoundBank':
            return False
        try:
            set_args = {
                'soundbank': bank["id"],
                'operation': 'replace',
                'inclusions': []
            }
            self.client.call('ak.wwise.core.soundbank.setInclusions', set_args)
            return True
        except Exception as e:
            Logger().error(str(e))
            return False

    # 为SoundBank设置包含内容
    def set_bank_inclusion(self, bank: dict, inclusion: dict, replace: bool, inclusion_type=None) -> bool:
        if not self.client or not bank or not inclusion:
            return False
        try:
            if not inclusion_type:
                inclusion_type = ['events', 'structures', 'media']
            set_args = {
                'soundbank': bank["id"],
                'operation': 'replace' if replace else 'add',
                'inclusions': [
                    {
                        'object': inclusion['object'],
                        'filter': inclusion_type
                    }
                ]
            }
            self.client.call('ak.wwise.core.soundbank.setInclusions', set_args)
            return True
        except Exception as e:
            Logger().error(str(e))
            return False
    # endregion SoundBank

    # region GameSync
    # 为对象添加RTPC曲线
    def add_rtpc(self, target_obj: dict, rtpc_obj: dict, target_property: str, points: list) -> bool:
        if not self.client or not target_obj or not rtpc_obj:
            return False
        try:
            args = {
                'objects': [
                    {
                        'object': target_obj["id"],
                        '@RTPC': [
                            {
                                'type': 'RTPC',
                                'name': '',
                                '@Curve': {
                                    'type': 'Curve',
                                    'points': points
                                },
                                '@PropertyName': target_property,
                                '@ControlInput': rtpc_obj["id"]
                            }
                        ]
                    }
                ],
                'listMode': 'append'
            }
            result = self.client.call('ak.wwise.core.object.set', args)
            return result is not None
        except Exception as e:
            Logger().error(str(e))
            return False

    # 清除对象中的某个列表（如RTPC，Effects）
    def clear_slots(self, obj: dict, slot_name: str) -> bool:
        if not self.client or not obj:
            return False
        try:
            args = {
                'objects': [
                    {
                        'object': obj["id"],
                        slot_name: []
                    }
                ],
                'listMode': 'replaceAll'
            }
            result = self.client.call('ak.wwise.core.object.set', args)
            return result is not None
        except Exception as e:
            Logger().error(str(e))
            return False
    # endregion GameSync

    # region Mixing
    # 为对象添加RTPC曲线
    def add_effect(self, obj: dict, share_set_name: str) -> bool:
        if not self.client or not obj:
            return False
        try:
            args = {
                'objects': [
                    {
                        'object': obj["id"],
                        '@Effects': [
                            {
                                'type': 'EffectSlot',
                                'name': '',
                                '@Effect': {
                                    'type': 'Effect',
                                    'name': share_set_name
                                }
                            }
                        ]
                    }
                ]
            }
            result = self.client.call('ak.wwise.core.object.set', args)
            return result is not None
        except Exception as e:
            Logger().error(str(e))
            return False
    # endregion Mixing

    # region Localization
    # 获取所有的语言
    def get_language_list(self) -> list:
        if not self.client:
            return []
        try:
            args = {'from': {'ofType': ['Language']}}
            options = {'return': ['name']}
            result = self.client.call('ak.wwise.core.object.get', args, options)
            return result['return'] if result else []
        except Exception as e:
            Logger().error(str(e))
            return []
    # endregion Localization

    # region Playback
    # 播放音效，返回TransportID
    def play_sound_in_transport(self, obj: dict) -> int:
        if not self.client or not obj:
            return -1
        try:
            args = { "object": obj["id"] }
            result = self.client.call("ak.wwise.core.transport.create", args)
            if not result:
                return -1
            transport_id = result["transport"]
            args = {
                "transport": transport_id,
                "action": "play"
            }
            self.client.call("ak.wwise.core.transport.executeAction", args)
            return transport_id
        except Exception as e:
            Logger().error(str(e))
            return -1

    # 通过TransportID停止音效
    def stop_sound_in_transport(self, transport_id: int) -> bool:
        if not self.client:
            return False
        try:
            args = {
                "transport": transport_id,
                "action": "stop"
            }
            self.client.call("ak.wwise.core.transport.executeAction", args)
            return self.destroy_transport(transport_id)
        except Exception as e:
            Logger().error(str(e))
            return False

    # 回收Transport
    def destroy_transport(self, transport_id: int) -> bool:
        if not self.client:
            return False
        try:
            args = { "transport": transport_id }
            self.client.call("ak.wwise.core.transport.destroy", args)
            return True
        except Exception as e:
            Logger().error(str(e))
            return False
    # endregion Playback

    # region UICommand
    # 执行Wwise操作
    def execute_ui_command(self, objects: list, command: str) -> bool:
        if not self.client or not command:
            return False
        try:
            execute_args = {'command': command}
            # 有些命令不需要目标对象（如切换平台），此时不带 objects 字段
            obj_ids = [obj["id"] for obj in (objects or []) if obj and obj.get("id")]
            if obj_ids:
                execute_args['objects'] = obj_ids
            self.client.call('ak.wwise.ui.commands.execute', execute_args)
            return True
        except Exception as e:
            Logger().error(str(e))
            return False

    # 在Wwise里选中对象
    def select_objects_in_wwise(self, objects: list) -> bool:
        if not self.client:
            return False
        try:
            id_list = [obj["id"] for obj in objects]
            select_args = {
                'command': 'FindInProjectExplorerSyncGroup1',
                'objects': id_list
            }
            self.client.call('ak.wwise.ui.commands.execute', select_args)
            select_args = {
                'command': 'Inspect',
                'objects': id_list
            }
            self.client.call('ak.wwise.ui.commands.execute', select_args)
            return self.bring_wwise_to_foreground()
        except Exception as e:
            Logger().error(str(e))
            return False

    # 将Wwise窗口带到最前方
    def bring_wwise_to_foreground(self) -> bool:
        if not self.client:
            return False
        self.client.call('ak.wwise.ui.bringToForeground')
        return True

    # 开始记录操作
    def begin_undo_group(self, action: str) -> bool:
        if not self.client:
            return False
        # 已在撤销组内时不再嵌套开启，本次改动归入外层组（例如 AI 任务里触发的工具动作）
        if self.undo_group_open:
            Logger().debug(f'WAAPI - Undo group already open, join [{action}]')
            return False
        self.client.call('ak.wwise.core.undo.beginGroup')
        self.undo_group_open = True
        Logger().debug(f'WAAPI - Begin undo group [{action}]')
        return True

    # 结束记录操作
    def end_undo_group(self, action: str) -> bool:
        if not self.client or not self.undo_group_open:
            return False
        try:
            end_args = {'displayName': 'WAAPI - ' + action}
            self.client.call('ak.wwise.core.undo.endGroup', end_args)
            self.undo_group_open = False
            Logger().debug(f'WAAPI - End undo group [{action}]')
            return True
        except Exception as e:
            Logger().error(str(e))
            return False

    # 撤销操作
    def undo(self) -> bool:
        if not self.client:
            return False
        try:
            execute_args = {'command': 'Undo'}
            self.client.call('ak.wwise.ui.commands.execute', execute_args)
            return True
        except Exception as e:
            Logger().error(str(e))
            return False

    # 重做操作
    def redo(self) -> bool:
        if not self.client:
            return False
        try:
            execute_args = {'command': 'Redo'}
            self.client.call('ak.wwise.ui.commands.execute', execute_args)
            return True
        except Exception as e:
            Logger().error(str(e))
            return False

    # 保存工程：把 Wwise 内存里的改动写回工程文件
    def save_project(self) -> bool:
        if not self.client:
            return False
        try:
            result = self.client.call('ak.wwise.core.project.save', {})
            if result is None:
                Logger().error("WAAPI - 保存工程失败")
                return False
            Logger().debug("WAAPI - 工程已保存")
            return True
        except Exception as e:
            Logger().error(str(e))
            return False

    # 将文件添加到版本控制
    def add_to_source_control(self, file_path: str) -> bool:
        if not self.client:
            return False
        try:
            add_args = {'files': file_path}
            self.client.call('ak.wwise.core.sourceControl.add', add_args)
            return True
        except Exception as e:
            Logger().error(str(e))
            return False
    # endregion UICommand
