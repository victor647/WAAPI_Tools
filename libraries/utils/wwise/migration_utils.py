import os
from libraries.utils import io_utils
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import project_utils, waapi_utils
from libraries.multi_thread import batch_processor
from libraries.wwise_object import WwiseObject, WwiseObjectType


# 从FMOD导出的json导入Event
def import_fmod_events():
    selection = waapi_utils.get_selected_objects()
    if len(selection) == 0:
        Logger().warning('导入失败，请在Wwise工程中选择一个对象作为导入资源的父级！')
        return
    json = io_utils.import_from_json()
    if json is None:
        return
    batch_processor.create_async(
        json,
        lambda index, event: import_fmod_event(event, selection[0]),
        '从FMOD导入事件',
    )

def import_fmod_event(event: dict, work_unit: WwiseObject) -> bool:
    event_name = event['name']
    existing_event = waapi_utils.find_object_by_name_and_type(event_name, WwiseObjectType.Event)
    if existing_event:
        print(f'Existing event [{event_name}] found, will not import.')
        return False
    tracks = event['tracks']
    if len(tracks) > 1:
        root = waapi_utils.create_child_object(event_name, WwiseObjectType.BlendContainer, work_unit)
        if not root:
            print(f'Create blend container failed: {event_name}')
            return False
        waapi_utils.set_object_property(root, 'Volume', event['volume'])
        for i in range(len(tracks)):
            import_fmod_track(tracks[i], i, root)
    elif len(tracks) == 1:
        root = import_fmod_track(tracks[0], 0, work_unit)
        waapi_utils.rename_object(root, event_name)
    else:
        return False
    for marker in event['markers']:
        import_fmod_marker(marker, root)
    import_fmod_effect(event['effects'], root)
    # event_utils.create_play_event(root)
    if root:
        print(f'Import FMOD event [{event_name}] success!')
        return True
    else:
        print(f'Import FMOD event [{event_name}] failed!')
        return False

def import_fmod_track(track: dict, index: int, parent: WwiseObject) -> WwiseObject:
    if not parent:
        return WwiseObject()
    instrument = None
    base_volume = track['volume']
    for clip in track['clips']:
        if clip['instrument'] == {}:
            continue
        clip_start = clip['startTime']
        fade_in = clip['fadeInTime'] if 'fadeInTime' in clip else 0
        fade_out = clip['fadeOutTime'] if 'fadeOutTime' in clip else 0
        instrument = import_fmod_instrument(clip['instrument'], parent, index, fade_in, fade_out, base_volume)
        waapi_utils.set_object_property(instrument, 'InitialDelay', clip_start)
        index += 1
    return instrument

def import_fmod_instrument(instrument: dict, parent: WwiseObject, index: int, fade_in: float, fade_out: float, base_volume: float) -> WwiseObject:
    instrument_type = instrument.type
    if instrument_type == 'multi':
        return import_fmod_random_container(instrument, f'Layer{index+1}', parent, fade_in, fade_out, base_volume)
    if instrument_type == 'single':
        return import_single_sound(instrument, parent, fade_in, fade_out, base_volume)
    return WwiseObject()

# 从FMOD导入RandomContainer
def import_fmod_random_container(instrument: dict, node_name: str, parent: WwiseObject, fade_in: float, fade_out: float, base_volume: float) -> WwiseObject:
    if not parent:
        return WwiseObject()
    container = waapi_utils.create_child_object(node_name, WwiseObjectType.RandomContainer, parent)
    if not container:
        print(f'Create random container failed: {node_name}')
        return WwiseObject()
    playlist = instrument['playList']
    play_mode = playlist['playMode']
    waapi_utils.set_object_property(container, 'Pitch', instrument['pitch'])
    waapi_utils.set_object_property(container, 'Volume', instrument['volume'] + base_volume)
    waapi_utils.set_object_property(container, 'PlayMechanismLoop', instrument['loop'])
    children = []
    for item in playlist['items']:
        if item.type == 'single':
            children.append(import_single_sound(item, container, fade_in, fade_out, base_volume))

    if play_mode == 'Random':
        waapi_utils.set_object_property(container, 'RandomOrSequence', 1)
        waapi_utils.set_object_property(container, 'NormalOrShuffle', 1)
    elif play_mode == 'Shuffle':
        waapi_utils.set_object_property(container, 'RandomOrSequence', 1)
        waapi_utils.set_object_property(container, 'NormalOrShuffle', 0)
    elif play_mode == 'SequenceLocal':
        waapi_utils.set_object_property(container, 'RandomOrSequence', 0)
        waapi_utils.set_sequence_container_playlist(container, children)
    elif play_mode == 'SequenceGlobal':
        waapi_utils.set_object_property(container, 'RandomOrSequence', 0)
        waapi_utils.set_sequence_container_playlist(container, children)
    return container

# 从FMOD导入单个音效
def import_single_sound(instrument: dict, parent: WwiseObject, fade_in: float, fade_out: float, base_volume: float) -> WwiseObject:
    if not parent:
        return WwiseObject()
    asset_path = instrument['asset']
    sound_name = asset_path.split('/')[-1][:-4]
    sound = waapi_utils.create_child_object(sound_name, WwiseObjectType.Sound, parent, 'rename')
    if not sound:
        print(f'Create sound failed: {sound_name}')
        return WwiseObject()
    asset_path = str(os.path.join(project_utils.get_originals_folder(), 'SFX', asset_path))
    waapi_utils.set_object_property(sound, 'IsLoopingEnabled', 0)
    waapi_utils.set_object_property(sound, 'Pitch', instrument['pitch'])
    waapi_utils.set_object_property(sound, 'Volume', instrument['volume'] + base_volume)
    source = waapi_utils.import_audio_file(asset_path, sound)
    if source:
        waapi_utils.set_object_property(source, 'FadeInDuration', fade_in)
        waapi_utils.set_object_property(source, 'FadeOutDuration', fade_out)
        if 'trimBegin' in instrument:
            waapi_utils.set_object_property(source, 'TrimBegin', instrument['trimBegin'])
        if 'trimEnd' in instrument:
            waapi_utils.set_object_property(source, 'TrimEnd', instrument['trimEnd'])
    return sound

# 导入FMOD中的Marker
def import_fmod_marker(marker: dict, root: WwiseObject):
    if marker.type == 'LoopRegion':
        loop_entry = marker['position']
        loop_exit = loop_entry + marker['length']
        if root.type == WwiseObjectType.Sound:
            import_loop_status(root, loop_entry, loop_exit)
        else:
            instruments = waapi_utils.get_child_objects(root)
            for instrument in instruments:
                import_loop_status(instrument, loop_entry, loop_exit)

# 导入FMOD中的loop设置
def import_loop_status(instrument: WwiseObject, loop_entry: float, loop_exit: float):
    delay = waapi_utils.get_object_property(instrument, 'InitialDelay')
    if loop_entry <= delay <= loop_exit:
        if instrument.type == WwiseObjectType.RandomContainer:
            waapi_utils.set_object_property(instrument, 'PlayMechanismLoop', True)
        else:
            waapi_utils.set_object_property(instrument, 'IsLoopingEnabled', True)

# 导入FMOD中的3D设置
def import_fmod_effect(effects, root):
    for effect in effects:
        if effect == 'SpatialiserEffect':
            waapi_utils.set_object_property(root, '3DSpatialization', 1)

# 从FMOD导出的json导入Preset
def import_fmod_presets():
    state_root = waapi_utils.find_object_by_path('\\States\\Default Work Unit')
    switch_root = waapi_utils.find_object_by_path('\\Switches\\Default Work Unit')
    rtpc_root = waapi_utils.find_object_by_path('\\Game Parameters\\Default Work Unit')
    json = io_utils.import_from_json()
    if json is None:
        return
    for preset in json:
        preset_name = preset.name
        preset_type = preset.type
        if preset_type == 'Label':
            if preset['isGlobal']:
                state = waapi_utils.create_child_object(preset_name, WwiseObjectType.StateGroup, state_root)
                if state:
                    print(f'StateGroup created: {preset_name}')
                    for label in preset['labels']:
                        waapi_utils.create_child_object(label, WwiseObjectType.StateValue, state)
            else:
                switch = waapi_utils.create_child_object(preset_name, WwiseObjectType.SwitchGroup, switch_root)
                if switch:
                    print(f'SwitchGroup created: {preset_name}')
                    for label in preset['labels']:
                        waapi_utils.create_child_object(label, WwiseObjectType.SwitchValue, switch)
        else:
            rtpc = waapi_utils.create_child_object(preset_name, WwiseObjectType.RTPC, rtpc_root)
            if rtpc:
                min_value = preset['minValue']
                max_value = preset['maxValue']
                waapi_utils.set_object_property(rtpc, 'InitialValue', preset['initValue'])
                waapi_utils.set_object_property(rtpc, 'Min', min_value)
                waapi_utils.set_object_property(rtpc, 'Max', max_value)
                slew_rate = preset['slewRateUp']
                if slew_rate > 0:
                    waapi_utils.set_object_property(rtpc, 'RTPCRamping', 1)
                    waapi_utils.set_object_property(rtpc, 'SlewRateUp', slew_rate)
                    waapi_utils.set_object_property(rtpc, 'SlewRateDown', preset['slewRateDown'] if 'slewRateDown' in preset else slew_rate)
                if preset_type == 'BuiltInDistance':
                    waapi_utils.set_object_property(rtpc, 'BindToBuiltInParam', 1)
                print(f'RTPC created: {preset_name} ({min_value}-{max_value})')

