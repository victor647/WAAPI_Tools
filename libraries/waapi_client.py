# JSON/dict 层 WAAPI：入参出参均为 dict 或原生值；供 MCP 与 WAAPI 门面共用。
import os.path
from waapi import WaapiClient
from libraries.singleton import Singleton
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import project_utils

RETURN_FIELDS = {'return': ['id', 'name', 'type', 'path']}

class WAAPIClient(metaclass=Singleton):

    def __init__(self, port: int=8080):
        self.client: WaapiClient = None
        self.port = port
        self.connect()

    # 获取Waapi客户端
    def connect(self) -> WaapiClient:
        if not self.client:
            self.client = WaapiClient(url=f'ws://127.0.0.1:{self.port}/waapi')
        return self.client

    # 关闭Waapi客户端连接
    def disconnect(self):
        if not self.client:
            return
        try:
            self.client.disconnect()
            self.client = None
        except Exception as e:
            Logger().error(f"WAAPI - Error closing WAAPI client: {e}")
            self.client = None

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
            return None
        try:
            get_args = {}
            if project_utils.get_project_version() > 2020:
                get_args['waql'] = 'from type Project'
            else:
                get_args['from'] = {'ofType': ['Project']}
            get_args['options'] = {'return': [property_name]}
            result = self.client.call('ak.wwise.core.object.get', get_args)
            if result:
                return result['return'][0][property_name]

            Logger().error(f'WAAPI - Cannot find property named [{property_name}] in project!')
            return None
        except Exception as e:
            Logger().error(str(e))
            return None

    # 获取对象的属性
    def get_object_property(self, obj: dict, property_name: str):
        if not self.client or not obj:
            return None
        try:
            get_args = {}
            project_ver = project_utils.get_project_version()
            if project_ver > 2020:
                get_args ['waql'] = f'from object \"{obj["id"]}\"'
            else:
                 get_args['from'] = {'id': [obj["id"]]}
            get_args['options'] = {'return': [property_name]}
            result = self.client.call('ak.wwise.core.object.get', get_args)
            if not result or result['return'][0] == {}:
                # 2020之前的版本，引用类对象需要添加@
                if project_ver < 2020 and property_name[0] != '@':
                    return self.get_object_property(obj, f'@{property_name}')
                Logger().error(f"WAAPI - Cannot find property named [{property_name}] in {obj.get('type')} [{obj.get('path')}]!")
                return None
            return_obj = result['return'][0]
            return return_obj[property_name] if property_name in return_obj else None
        except Exception as e:
            Logger().error(str(e))
            return None


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
            if project_utils.get_project_version() > 2020:
                get_args ['waql'] = f'from object \"{path}\"'
            else:
                get_args['from'] = {'path': [path]}
                get_args['transform'] = [{'select': ['referencesTo']}]
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
            if project_utils.get_project_version() > 2020:
                get_args ['waql'] = f'from object \"{obj_id}\" select referencesTo'
            else:
                get_args['from'] = {'id': [obj_id]}
                get_args['transform'] = [{'select': ['referencesTo']}]
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
            if project_utils.get_project_version() > 2020:
                get_args['waql'] = f'from type AudioFileSource where originalRelativeFilePath = "{original_relative_path}"'
            else:
                get_args['from'] = {'ofType': ['AudioFileSource']}
                get_args['transform'] = [{'where': ['originalRelativeFilePath:matches', original_relative_path]}]
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
            if project_utils.get_project_version() > 2020:
                get_args ['waql'] = f'from object \"{obj_id}\" select parent'
            else:
                get_args['from'] = {'id': [obj_id]}
                get_args['transform'] = [{'select': ['parent']}]
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
            get_args = {}
            obj_id = obj["id"]
            if project_utils.get_project_version() > 2020:
                get_args ['waql'] = f'from object \"{obj_id}\" select ancestors'
            else:
                get_args['from'] = {'id': [obj_id]}
                get_args['transform'] = [{'select': ['ancestors']}]
            get_args['options'] = RETURN_FIELDS
            result = self.client.call('ak.wwise.core.object.get', get_args)
            return list(result['return']) if result else []
        except Exception as e:
            Logger().error(str(e))
            return []

    # 获取一个对象递归下层的所有子对象
    def get_child_objects(self, obj: dict, include_descendants=False) -> list[dict]:
        if not self.client or not obj:
            return []
        try:
            children = []
            index = 0
            interval = 500
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
                if cur_range_result and len(cur_range_result['return']) > 0:
                    children += list(cur_range_result['return'])
                    index += 1
                else:
                    break
            return children
        except Exception as e:
            Logger().error(str(e))
            return []

    # 获取特定类型的全部子对象（child_type 为 Wwise API 类型字符串，如 Sound、GameParameter）
    def get_descendants_of_type(self, obj: dict, child_type: str) -> list[dict]:
        if not self.client or not obj:
            return []
        try:
            get_args = {}
            obj_id = obj["id"]
            if project_utils.get_project_version() > 2020:
                get_args ['waql'] = f'from object \"{obj_id}\" select descendants where type = \"{child_type}\"'
            else:
                get_args['from'] = {'id': [obj_id]}
                get_args['transform'] = [
                        {'select': ['descendants']},
                        {'where': [f'type:{child_type}']}
                    ]
            get_args['options'] = RETURN_FIELDS
            result = self.client.call('ak.wwise.core.object.get', get_args)
            if not result or not result.get('return'):
                return []
            return list(result['return'])
        except Exception as e:
            Logger().error(str(e))
            return []

    # 获取整个Wwise工程所有对象
    def get_global_objects(self) -> list[dict]:
        if not self.client:
            return []
        try:
            global_objects = []
            objects_type = (
                'WorkUnit', 'ActorMixer', 'Folder', 'SwitchContainer', 'BlendContainer', 'RandomSequenceContainer',
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
            if project_utils.get_project_version() > 2020:
                get_args ['waql'] = f'from object \"{obj_id}\"'
            else:
                 get_args['from'] = {'id': [obj_id]}
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
            if project_utils.get_project_version() > 2020:
                get_args ['waql'] = f'from object \"{path}\"'
            else:
                 get_args['from'] = {'path': [path]}
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
            if project_utils.get_project_version() > 2020:
                get_args ['waql'] = f'from type {obj_type} where name: \"*{obj_name}\"'
            else:
                get_args['from'] = {'ofType': [obj_type]}
                get_args['transform'] = [{'where': ['name:matches', obj_name]}]
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
            get_args = {}
            if project_utils.get_project_version() > 2020:
                get_args ['waql'] = f'from search \"{obj_name}\"'
            else:
                 get_args['from'] = {'search': [obj_name]}
            get_args['options'] = RETURN_FIELDS
            result = self.client.call('ak.wwise.core.object.get', get_args)
            if result is None or len(result['return']) == 0:
                return []
            if not exact_match:
                return list(result['return'])
            matching_objects = []
            for raw in result['return']:
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
            get_args = {}
            if project_utils.get_project_version() > 2020:
                get_args ['waql'] = f'from type {obj_type}'
            else:
                 get_args['from'] = {'ofType': [obj_type]}
            get_args['options'] = RETURN_FIELDS
            result = self.client.call('ak.wwise.core.object.get', get_args)
            if not result or not result.get('return'):
                return []
            return list(result['return'])
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
                default_path = '\\Master-Mixer Hierarchy\\Default Work Unit\\Master Audio Bus'
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
                default_path = '\\Interactive Music Hierarchy\\Default Work Unit'
            else:
                default_path = '\\Actor-Mixer Hierarchy\\Default Work Unit'
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
            # 新版Wwise可以直接通过Set创建
            if project_utils.get_project_version() > 2020:
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
            else:
                create_args = {
                    'parent': parent_path,
                    'type': obj_type,
                    'name': obj_name
                }
                result_obj = self.client.call('ak.wwise.core.object.create', create_args)
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

    # 为声音创建静音源插件
    def add_silence(self, obj: dict, length: int, language='SFX') -> bool:
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
        if not self.client or len(objects) == 0:
            return False
        try:
            obj_ids = [obj["id"] for obj in objects]
            execute_args = {
                'command': command,
                'objects': obj_ids
            }
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
        self.client.call('ak.wwise.core.undo.beginGroup')
        Logger().debug(f'WAAPI - Begin undo group [{action}]')
        return True

    # 结束记录操作
    def end_undo_group(self, action: str) -> bool:
        if not self.client:
            return False
        try:
            end_args = {'displayName': 'WAAPI - ' + action}
            self.client.call('ak.wwise.core.undo.endGroup', end_args)
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
