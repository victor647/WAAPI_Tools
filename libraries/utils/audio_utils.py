import os.path
import soundfile
import math
import numpy

# RMS 响度的下限（无信号时的返回值）
MIN_LOUDNESS_DB = -96

# 响度分析默认的 buffer 大小（采样点数）
LOUDNESS_BUFFER_SAMPLES = 1024

# 响度分析时视为静音的响度门限（dBFS）
LOUDNESS_SILENCE_THRESHOLD_DB = -60


# 由平均功率换算 RMS 响度（dBFS）
def _power_to_decibel(power: float) -> float:
    if power <= 0:
        return MIN_LOUDNESS_DB
    return 10 * math.log10(power)


# 由平方和与采样数换算 RMS 响度（dBFS）
def _rms_to_decibel(sum_sq: float, count: int) -> float:
    if count == 0:
        return MIN_LOUDNESS_DB
    return _power_to_decibel(sum_sq / count)


# 计算音频的RMS；threshold_db 为空时统计整段音频，否则按 buffer 门限求平均响度
def calculate_loudness(file_path, block_size=65536, threshold_db: float = None,
                       buffer_samples: int = LOUDNESS_BUFFER_SAMPLES):
    if threshold_db is None:
        return _calculate_overall_loudness(file_path, block_size)
    return _calculate_buffered_loudness(file_path, block_size, threshold_db, buffer_samples)


# 计算一段音频数据的 RMS 响度（dBFS）
def calculate_loudness_from_data(audio_data) -> float:
    data = numpy.asarray(audio_data, dtype="float64")
    if data.size == 0:
        return MIN_LOUDNESS_DB
    return _power_to_decibel(numpy.sum(data ** 2) / data.size)


# 整段 RMS：跳过完全静音的读取块，避免静音部分拉低音量
def _calculate_overall_loudness(file_path, block_size: int) -> float:
    sum_sq = 0.0
    count = 0
    with soundfile.SoundFile(file_path) as f:
        for block in f.blocks(blocksize=block_size, dtype="float32"):
            value = numpy.sum(block ** 2)
            if value > 0:
                sum_sq += value
                count += block.size
    return _rms_to_decibel(sum_sq, count)


# 按 buffer 门限求平均响度：每 buffer_samples 个采样点（各声道对齐）单独求功率，
# 剔除响度低于 threshold_db 的静音 buffer，再对保留 buffer 的功率取平均并换算成响度
def _calculate_buffered_loudness(file_path, block_size: int, threshold_db: float, buffer_samples: int) -> float:
    buffer_power = []
    pending = numpy.empty(0, dtype="float32")
    with soundfile.SoundFile(file_path) as f:
        buffer_size = max(1, buffer_samples * max(1, f.channels))
        for block in f.blocks(blocksize=block_size, dtype="float32"):
            data = block.reshape(-1)
            if pending.size > 0:
                data = numpy.concatenate((pending, data))
            full_size = data.size - data.size % buffer_size
            for start in range(0, full_size, buffer_size):
                chunk = data[start:start + buffer_size]
                buffer_power.append(numpy.sum(chunk ** 2) / chunk.size)
            pending = data[full_size:]
    if pending.size > 0:
        # 末尾不足一个 buffer 的采样点单独统计
        buffer_power.append(numpy.sum(pending ** 2) / pending.size)
    kept = [power for power in buffer_power if _power_to_decibel(power) >= threshold_db]
    if not kept:
        return MIN_LOUDNESS_DB
    return _power_to_decibel(sum(kept) / len(kept))

# 把分贝转换成0-1的值
def decibel_to_linear(decibel: float) -> float:
    return min(1.0, pow(10, (decibel / 20)))

# 检测音频文件是否完全是静音
def is_sound_completely_silent(file_path: str) -> bool:
    if not os.path.exists(file_path):
        return False
    sound_file = soundfile.SoundFile(file=file_path)
    if not sound_file:
        return True
    sound_file.seek(0)
    audio_data = sound_file.read()
    if not audio_data.any():
        return True
    return get_sound_frame_max_amp(audio_data) == 0

# 寻找下一个间隔
def find_next_silence(audio_data, threshold: float, samples_per_frame: int, gap_min_samples: int, frame_begin_sample=0) -> tuple:
    silence_start_sample = -1
    silence_end_sample = 0
    while frame_begin_sample < len(audio_data):
        frame_end_sample = frame_begin_sample + samples_per_frame
        frame_data = audio_data[frame_begin_sample:frame_end_sample]
        max_amp = get_sound_frame_max_amp(frame_data)

        # 静音开始
        if silence_start_sample == -1:
            if max_amp < threshold:
                silence_start_sample = frame_begin_sample
        # 静音结束
        elif max_amp > threshold:
            # 时间不满最短间隔，重新计算
            if frame_begin_sample - silence_start_sample < gap_min_samples:
                silence_start_sample = -1
            else:
                silence_end_sample = frame_begin_sample
                break
        frame_begin_sample = frame_end_sample
    return silence_start_sample, silence_end_sample

# 在指定路径创建静音文件
def create_silence_audio_file(path: str, duration: float=1, sample_rate=44100) -> bool:
    if os.path.exists(path):
        return False
    num_samples = int(duration * sample_rate)
    silence_data = numpy.zeros(num_samples, dtype='float32')
    soundfile.write(path, silence_data, sample_rate)
    return True

# 获取音频静音部分长度（以采样窗口为单位）
def get_silence_duration_frames(audio_data, samples_per_frame: int, threshold: float, direction_tail: bool) -> int:
    silence_frames = 0
    while True:
        if len(audio_data) < samples_per_frame:
            return silence_frames
        if direction_tail:
            frame_data = audio_data[-samples_per_frame:]
        else:
            frame_data = audio_data[:samples_per_frame]
        if get_sound_frame_max_amp(frame_data) > threshold:
            return silence_frames
        silence_frames += 1
        if direction_tail:
            audio_data = audio_data[:-samples_per_frame]
        else:
            audio_data = audio_data[samples_per_frame:]


# 仅统计尾部连续静音的窗口数（音尾分析）
def get_tail_silence_duration_frames(audio_data, samples_per_frame: int, threshold: float) -> int:
    return get_silence_duration_frames(audio_data, samples_per_frame, threshold, True)


# 获取一个采样窗口的最大振幅
def get_sound_frame_max_amp(frame_data) -> float:
    if len(frame_data.shape) > 1:
        # 把交络波形转换成每个通道单独的数组
        return max(abs(frame_data.T[0]))
    else:
        return max(abs(frame_data))

# 淡入淡出，1为淡入，-1为淡出
def fade(audio_data, duration_samples: int, fade_direction: int):
    duration_samples = round(duration_samples)
    if duration_samples > len(audio_data):
        return
    for index in range(duration_samples):
        audio_data[fade_direction * index] *= index / duration_samples

# 裁剪音频数据
def trim(audio_data, start_samples: int, end_samples: int):
    start_samples = round(start_samples)
    end_samples = round(end_samples)
    if end_samples == 0:
        audio_data = audio_data[start_samples:]
    elif start_samples == 0:
        audio_data = audio_data[:end_samples]
    else:
        audio_data = audio_data[start_samples:end_samples]
    return audio_data
