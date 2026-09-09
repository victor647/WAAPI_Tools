from libraries.waapi_client import WAAPIClient
from libraries.wwise_object import WwiseObject, WwiseObjectType



def _dict_to_wobj(d: dict) -> WwiseObject:
    return WwiseObject(d) if d and d.get("id") else WwiseObject({})


def _dict_list_to_wobjs(items: list) -> list[WwiseObject]:
    return [WwiseObject(x) for x in items] if items else []


def close_client():
    WAAPIClient().disconnect()


# region Query
def get_authoring_info(property_name: str) -> dict:
    return WAAPIClient().get_authoring_info(property_name)


def get_project_info(property_name: str) -> dict:
    return WAAPIClient().get_project_info(property_name)


def get_project_property(property_name: str):
    return WAAPIClient().get_project_property(property_name)


def get_object_property(obj: WwiseObject, property_name: str):
    return WAAPIClient().get_object_property(obj.wwise_dict, property_name)


def get_object_properties(obj: WwiseObject, property_names: list) -> dict:
    return WAAPIClient().get_object_properties(obj.wwise_dict, property_names)


def get_property_and_reference_names(obj: WwiseObject) -> list[str]:
    return WAAPIClient().get_property_and_reference_names(obj.wwise_dict)


def paste_object_property(source_obj: WwiseObject, target_objects: list[WwiseObject], property_name: str) -> bool:
    return WAAPIClient().paste_object_property(source_obj.wwise_dict, [t.wwise_dict for t in target_objects], property_name)


def get_selected_objects() -> list[WwiseObject]:
    return _dict_list_to_wobjs(WAAPIClient().get_selected_objects())


def get_object_from_path(path: str) -> WwiseObject:
    return _dict_to_wobj(WAAPIClient().get_object_from_path(path))


def get_object_references(obj: WwiseObject) -> list[WwiseObject]:
    return _dict_list_to_wobjs(WAAPIClient().get_object_references(obj.wwise_dict))


def find_audio_sources_by_original_path(original_relative_path: str) -> list[WwiseObject]:
    return _dict_list_to_wobjs(WAAPIClient().find_audio_sources_by_original_path(original_relative_path))


def get_parent_object(obj: WwiseObject) -> WwiseObject:
    return _dict_to_wobj(WAAPIClient().get_parent_object(obj.wwise_dict))


def get_ancestor_objects(obj: WwiseObject) -> list[WwiseObject]:
    return _dict_list_to_wobjs(WAAPIClient().get_ancestor_objects(obj.wwise_dict))


def get_child_objects(obj: WwiseObject, include_descendants=False) -> list[WwiseObject]:
    return _dict_list_to_wobjs(WAAPIClient().get_child_objects(obj.wwise_dict, include_descendants=include_descendants))


def get_descendants_of_type(obj: WwiseObject, child_type: WwiseObjectType) -> list[WwiseObject]:
    return _dict_list_to_wobjs(WAAPIClient().get_descendants_of_type(obj.wwise_dict, child_type.value))


def get_global_objects() -> list[WwiseObject]:
    return _dict_list_to_wobjs(WAAPIClient().get_global_objects())


def get_full_info_from_obj_id(obj_id) -> WwiseObject:
    return _dict_to_wobj(WAAPIClient().get_full_info_from_obj_id(obj_id))


def find_object_by_path(path: str) -> WwiseObject:
    return _dict_to_wobj(WAAPIClient().find_object_by_path(path))


def find_object_by_name_and_type(obj_name: str, obj_type: WwiseObjectType, exact_match=True) -> WwiseObject:
    return _dict_to_wobj(WAAPIClient().find_object_by_name_and_type(obj_name, obj_type.value, exact_match=exact_match))


def find_all_objects_by_name(obj_name: str, exact_match: bool) -> list[WwiseObject]:
    return _dict_list_to_wobjs(WAAPIClient().find_all_objects_by_name(obj_name, exact_match))


def find_all_objects_by_type(obj_type: WwiseObjectType) -> list[WwiseObject]:
    return _dict_list_to_wobjs(WAAPIClient().find_all_objects_by_type(obj_type.value))


# endregion Query

# region CommonOperation
def create_object_at_default_location(obj_name: str, obj_type: WwiseObjectType) -> WwiseObject:
    return _dict_to_wobj(WAAPIClient().create_object_at_default_location(obj_name, obj_type.value))


def create_child_object(obj_name: str, obj_type: WwiseObjectType, parent_obj: WwiseObject, on_name_conflict="fail") -> WwiseObject:
    return _dict_to_wobj(WAAPIClient().create_child_object(obj_name, obj_type.value, parent_obj.wwise_dict, on_name_conflict=on_name_conflict))


def create_object_by_path(obj_path: str, obj_type: str, on_name_conflict='fail') -> WwiseObject:
    return _dict_to_wobj(WAAPIClient().create_object_by_path(obj_path, obj_type, on_name_conflict=on_name_conflict))


def move_object(obj: WwiseObject, new_parent: WwiseObject) -> bool:
    return WAAPIClient().move_object(obj.wwise_dict, new_parent.wwise_dict)


def copy_object(obj: WwiseObject, parent: WwiseObject) -> WwiseObject:
    return _dict_to_wobj(WAAPIClient().copy_object(obj.wwise_dict, parent.wwise_dict))


def rename_object(obj: WwiseObject, new_name: str) -> bool:
    return WAAPIClient().rename_object(obj.wwise_dict, new_name)


def set_object_property(obj: WwiseObject, property_name: str, value, platform=None) -> bool:
    return WAAPIClient().set_object_property(obj.wwise_dict, property_name, value, platform=platform)


def set_object_reference(obj: WwiseObject, reference_type: str, value: WwiseObject) -> bool:
    return WAAPIClient().set_object_reference(obj.wwise_dict, reference_type, value.wwise_dict)


def set_object_notes(obj: WwiseObject, notes: str) -> bool:
    return WAAPIClient().set_object_notes(obj.wwise_dict, notes)


def delete_object(obj: WwiseObject) -> bool:
    return WAAPIClient().delete_object(obj.wwise_dict)


# endregion CommonOperation

# region LogicContainer
def set_sequence_container_playlist(container: WwiseObject, playlist: list[WwiseObject]) -> bool:
    return WAAPIClient().set_sequence_container_playlist(container.wwise_dict, [x.wwise_dict for x in playlist])


def get_switch_mappings(container: WwiseObject) -> list:
    return WAAPIClient().get_switch_mappings(container.wwise_dict)


def assign_switch_mapping(target: WwiseObject, switch_obj: WwiseObject) -> bool:
    return WAAPIClient().assign_switch_mapping(target.wwise_dict, switch_obj.wwise_dict)


def remove_switch_mappings(obj: WwiseObject) -> bool:
    return WAAPIClient().remove_switch_mappings(obj.wwise_dict)


# endregion LogicContainer

# region AudioSource
def import_audio_file(wave_path: str, sound: WwiseObject, language='SFX') -> WwiseObject:
    return _dict_to_wobj(WAAPIClient().import_audio_file(wave_path, sound.wwise_dict, language=language))


def convert_audio_objects(objects: list, platforms: list, languages: list) -> dict:
    return WAAPIClient().convert_audio_objects([obj.id for obj in objects], platforms, languages)


def add_silence(obj: WwiseObject, length: int, language='SFX') -> bool:
    return WAAPIClient().add_silence(obj.wwise_dict, length, language=language)


def get_default_audio_source(sound: WwiseObject) -> WwiseObject:
    return _dict_to_wobj(WAAPIClient().get_default_audio_source(sound.wwise_dict))


# endregion AudioSource

# region SoundBank
def get_bank_inclusions(bank: WwiseObject) -> list:
    return WAAPIClient().get_bank_inclusions(bank.wwise_dict)


def clear_bank_inclusions(bank: WwiseObject) -> bool:
    return WAAPIClient().clear_bank_inclusions(bank.wwise_dict)


def set_bank_inclusion(bank: WwiseObject, inclusion: dict, replace: bool, inclusion_type=None) -> bool:
    return WAAPIClient().set_bank_inclusion(bank.wwise_dict, inclusion, replace, inclusion_type=inclusion_type)


def set_bank_inclusion_object(
    bank: WwiseObject, included_obj: WwiseObject, replace: bool, inclusion_type=None
) -> bool:
    """将 SoundBank 的包含项设为指定对象（WwiseObject 在内部转为 id）。"""
    return WAAPIClient().set_bank_inclusion(
        bank.wwise_dict, {"object": included_obj.id}, replace, inclusion_type=inclusion_type
    )


# endregion SoundBank

# region GameSync
def add_rtpc(target_obj: WwiseObject, rtpc_obj: WwiseObject, target_property: str, points: list) -> bool:
    return WAAPIClient().add_rtpc(target_obj.wwise_dict, rtpc_obj.wwise_dict, target_property, points)


def clear_slots(obj: WwiseObject, slot_name: str) -> bool:
    return WAAPIClient().clear_slots(obj.wwise_dict, slot_name)


# endregion GameSync

# region Mixing
def add_effect(obj: WwiseObject, share_set_name: str) -> bool:
    return WAAPIClient().add_effect(obj.wwise_dict, share_set_name)


# endregion Mixing

# region Localization
def get_language_list() -> list:
    return WAAPIClient().get_language_list()


# endregion Localization

# region Playback
def play_sound_in_transport(obj: WwiseObject) -> int:
    return WAAPIClient().play_sound_in_transport(obj.wwise_dict)


def stop_sound_in_transport(transport_id: int) -> bool:
    return WAAPIClient().stop_sound_in_transport(transport_id)


def destroy_transport(transport_id: int) -> bool:
    return WAAPIClient().destroy_transport(transport_id)


# endregion Playback

# region UICommand
def execute_ui_command(objects: list, command: str) -> bool:
    return WAAPIClient().execute_ui_command([o.wwise_dict for o in objects], command)


def select_objects_in_wwise(objects: list) -> bool:
    return WAAPIClient().select_objects_in_wwise([o.wwise_dict for o in objects])


def bring_wwise_to_foreground() -> bool:
    return WAAPIClient().bring_wwise_to_foreground()


def begin_undo_group(action: str) -> bool:
    return WAAPIClient().begin_undo_group(action)


def end_undo_group(action: str) -> bool:
    return WAAPIClient().end_undo_group(action)


def undo() -> bool:
    return WAAPIClient().undo()


def redo() -> bool:
    return WAAPIClient().redo()


def add_to_source_control(file_path: str) -> bool:
    return WAAPIClient().add_to_source_control(file_path)


# endregion UICommand
