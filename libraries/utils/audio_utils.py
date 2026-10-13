import os.path
import soundfile
import math
import numpy
from enum import Enum

from libraries.utils import user_config

# RMS 响度的下限（无信号时的返回值）
MIN_LOUDNESS_DB = -96

# 响度分析默认的 buffer 大小（采样点数）
LOUDNESS_BUFFER_SAMPLES = 1024

# 响度分析时视为静音的响度门限（dBFS）
LOUDNESS_SILENCE_THRESHOLD_DB = -60

# LUFS（ITU-R BS.1770 综合响度）的常量
LUFS_OFFSET = -0.691
LUFS_ABSOLUTE_GATE = -70.0
LUFS_RELATIVE_GATE = -10.0
LUFS_SHORT_BLOCK_SECONDS = 0.4
LUFS_SHORT_BLOCK_OVERLAP = 0.75

# K 加权用频域卷积实现时预留的滤波器尾部长度：两级 biquad 的冲激响应在这个长度内已衰减到
# 远低于静音门限，尾部之外的循环卷积污染会被丢弃。高采样率下衰减更慢，按时间兜底。
K_WEIGHTING_TAIL_SAMPLES = 8192
K_WEIGHTING_TAIL_SECONDS = 0.2

# 多声道能量权重（BS.1770 表 3）：左/右/中为 1，环绕为 1.41，LFE 不计入
LUFS_SURROUND_WEIGHT = 1.41


# 响度标准
class LoudnessStandard(Enum):
    RMS = 'rms'
    LUFS = 'lufs'

    @property
    def unit(self) -> str:
        return 'dBFS' if self == LoudnessStandard.RMS else 'LUFS'


# 按指定的响度标准测量音频；start_frame / end_frame 限定统计的采样区间
def calculate_loudness_by_standard(file_path, standard: LoudnessStandard = LoudnessStandard.RMS,
                                   start_frame: int = 0, end_frame: int = None) -> float:
    if standard == LoudnessStandard.LUFS:
        return calculate_lufs(file_path, start_frame, end_frame)
    return calculate_loudness(file_path, threshold_db=LOUDNESS_SILENCE_THRESHOLD_DB,
                              start_frame=start_frame, end_frame=end_frame)


# 把统计区间收敛到文件的合法采样范围内
def clamp_frame_range(total_frames: int, start_frame: int = 0, end_frame: int = None) -> tuple:
    start = max(0, min(int(start_frame or 0), total_frames))
    end = total_frames if end_frame is None else max(0, min(int(end_frame), total_frames))
    return start, end


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
                       buffer_samples: int = None, start_frame: int = 0, end_frame: int = None):
    # 分块大小可在「设置 - 工具行为」里配置，未显式传入时读配置
    if buffer_samples is None:
        buffer_samples = user_config.get_tool_loudness_buffer_samples()
    if threshold_db is None:
        return _calculate_overall_loudness(file_path, block_size, start_frame, end_frame)
    return _calculate_buffered_loudness(
        file_path, block_size, threshold_db, buffer_samples, start_frame, end_frame)


# 计算一段音频数据的 RMS 响度（dBFS）
# threshold_db 为空时统计整段数据；否则按 buffer_samples 分块剔除静音 buffer 后再取平均
def calculate_loudness_from_data(audio_data, block_size: int = 65536, threshold_db: float = None,
                                 buffer_samples: int = None) -> float:
    data = numpy.asarray(audio_data, dtype="float64")
    if data.size == 0:
        return MIN_LOUDNESS_DB
    if threshold_db is None:
        return _power_to_decibel(numpy.sum(data ** 2) / data.size)
    return _buffered_loudness_from_data(data, threshold_db, buffer_samples, block_size)


# 按指定响度标准测量已读取到内存的音频数据（裁剪区间由调用方先切好）
def calculate_loudness_by_standard_from_data(audio_data, sample_rate: int,
                                             standard: LoudnessStandard = LoudnessStandard.RMS) -> float:
    if standard == LoudnessStandard.LUFS:
        return calculate_lufs_from_data(audio_data, sample_rate)
    return calculate_loudness_from_data(audio_data, threshold_db=LOUDNESS_SILENCE_THRESHOLD_DB)


# K 加权滤波器系数：BS.1770 给出的两级 IIR（高架 + 高通），用双线性变换在任意采样率上重新推导
def _k_weighting_coefficients(sample_rate: int) -> tuple:
    # 第一级：高频架式提升
    shelf_f0 = 1681.974450955533
    shelf_gain = 3.999843853973347
    shelf_q = 0.7071752369554196
    k = math.tan(math.pi * shelf_f0 / sample_rate)
    vh = 10 ** (shelf_gain / 20)
    vb = vh ** 0.4996667741545416
    a0 = 1.0 + k / shelf_q + k * k
    shelf = (
        (vh + vb * k / shelf_q + k * k) / a0,
        2.0 * (k * k - vh) / a0,
        (vh - vb * k / shelf_q + k * k) / a0,
        2.0 * (k * k - 1.0) / a0,
        (1.0 - k / shelf_q + k * k) / a0,
    )
    # 第二级：高通（去掉低频）
    highpass_f0 = 38.13547087602444
    highpass_q = 0.5003270373238773
    k = math.tan(math.pi * highpass_f0 / sample_rate)
    a0 = 1.0 + k / highpass_q + k * k
    highpass = (
        1.0,
        -2.0,
        1.0,
        2.0 * (k * k - 1.0) / a0,
        (1.0 - k / highpass_q + k * k) / a0,
    )
    return shelf, highpass


# 取不小于 target 的「5 平滑」长度：pocketfft 对只含 2/3/5 因子的长度最快，比硬取 2 的幂省算力
def _next_fast_length(target: int) -> int:
    if target <= 16:
        return 16
    length = target
    while True:
        remainder = length
        for factor in (2, 3, 5):
            while remainder % factor == 0:
                remainder //= factor
        if remainder == 1:
            return length
        length += 1


# 单个 biquad 在给定频率上的响应
def _biquad_response(coefficients, z) -> object:
    b0, b1, b2, a1, a2 = coefficients
    return (b0 + b1 * z + b2 * z ** 2) / (1.0 + a1 * z + a2 * z ** 2)


# 两级 biquad 的 K 加权：把两段频响相乘后一次变换完成（级联的频响相乘，结果与逐级滤波一致）；
# 频域滤波等价于零相位滤波，FFT 长度只需盖住「信号 + 滤波器尾部」
def _apply_k_weighting(data, sample_rate: int) -> object:
    length = data.shape[0]
    tail_samples = max(K_WEIGHTING_TAIL_SAMPLES, int(K_WEIGHTING_TAIL_SECONDS * sample_rate))
    spectrum_len = _next_fast_length(length + tail_samples)
    frequencies = numpy.fft.rfftfreq(spectrum_len, d=1.0 / sample_rate)
    z = numpy.exp(-2j * numpy.pi * frequencies / sample_rate)
    shelf, highpass = _k_weighting_coefficients(sample_rate)
    response = _biquad_response(shelf, z) * _biquad_response(highpass, z)
    spectrum = numpy.fft.rfft(data, n=spectrum_len, axis=0)
    filtered = numpy.fft.irfft(spectrum * response[:, None], n=spectrum_len, axis=0)
    return filtered[:length]


# 计算音频的 LUFS（ITU-R BS.1770 综合响度）：K 加权 + 400ms 分块 + 两级门限
def calculate_lufs(file_path, start_frame: int = 0, end_frame: int = None) -> float:
    with soundfile.SoundFile(file_path) as f:
        sample_rate = f.samplerate
        start_frame, end_frame = clamp_frame_range(f.frames, start_frame, end_frame)
        if end_frame - start_frame <= 0:
            return MIN_LOUDNESS_DB
        f.seek(start_frame)
        data = f.read(end_frame - start_frame, dtype="float64", always_2d=True)
    return calculate_lufs_from_data(data, sample_rate)


# 计算已读取到内存的音频数据的 LUFS（调用方负责先按裁剪区间切好）
def calculate_lufs_from_data(audio_data, sample_rate: int) -> float:
    data = numpy.asarray(audio_data, dtype="float64")
    if data.size == 0:
        return MIN_LOUDNESS_DB
    weighted = _apply_k_weighting(data, sample_rate)
    return _gated_lufs(_short_term_block_powers(weighted, sample_rate))


# 400ms 分块（75% 重叠）的能量序列；短于一个分块时整段作为一个分块
def _short_term_block_powers(weighted, sample_rate: int) -> list:
    weights = _channel_weights(max(1, weighted.shape[1]))
    block_size = max(1, int(round(LUFS_SHORT_BLOCK_SECONDS * sample_rate)))
    hop_size = max(1, int(round(block_size * (1.0 - LUFS_SHORT_BLOCK_OVERLAP))))
    if weighted.shape[0] < block_size:
        # 短于一个 400ms 分块（短语音、音效）：整段当作一个分块，
        # 否则一个分块都凑不齐，会被误判成「无信号」
        return [_block_power(weighted, weights)]
    return [_block_power(weighted[start:start + block_size], weights)
            for start in range(0, weighted.shape[0] - block_size + 1, hop_size)]


# 一个分块的能量（先按声道求均方，再按声道权重加权平均）
def _block_power(block, weights) -> float:
    channel_power = numpy.mean(block ** 2, axis=0)
    return float(numpy.sum(channel_power * weights) / numpy.sum(weights))


# 各声道的能量权重：单/双声道为 1，5.1 及以上按 BS.1770 表 3（LFE 不参与）
def _channel_weights(channels: int) -> object:
    if channels <= 2:
        return numpy.ones(channels, dtype="float64")
    if channels >= 6:
        return numpy.array([1.0, 1.0, 1.0, 0.0, LUFS_SURROUND_WEIGHT, LUFS_SURROUND_WEIGHT] +
                           [1.0] * (channels - 6), dtype="float64")
    return numpy.ones(channels, dtype="float64")


# 对分块能量做门限处理，得到综合响度（LUFS）
def _gated_lufs(block_powers: list) -> float:
    if not block_powers:
        return MIN_LOUDNESS_DB
    absolute_kept = [power for power in block_powers
                     if _power_to_decibel(power) + LUFS_OFFSET >= LUFS_ABSOLUTE_GATE]
    if not absolute_kept:
        return MIN_LOUDNESS_DB
    absolute_mean = sum(absolute_kept) / len(absolute_kept)
    relative_gate = _power_to_decibel(absolute_mean) + LUFS_OFFSET + LUFS_RELATIVE_GATE
    kept = [power for power in absolute_kept if _power_to_decibel(power) + LUFS_OFFSET >= relative_gate]
    if not kept:
        return MIN_LOUDNESS_DB
    return _power_to_decibel(sum(kept) / len(kept)) + LUFS_OFFSET


# 整段 RMS：跳过完全静音的读取块，避免静音部分拉低音量
def _calculate_overall_loudness(file_path, block_size: int, start_frame: int = 0,
                                end_frame: int = None) -> float:
    sum_sq = 0.0
    count = 0
    with soundfile.SoundFile(file_path) as f:
        start_frame, end_frame = clamp_frame_range(f.frames, start_frame, end_frame)
        remaining = end_frame - start_frame
        if remaining <= 0:
            return MIN_LOUDNESS_DB
        f.seek(start_frame)
        for block in f.blocks(blocksize=block_size, frames=remaining, dtype="float32"):
            value = numpy.sum(block ** 2)
            if value > 0:
                sum_sq += value
                count += block.size
    return _rms_to_decibel(sum_sq, count)


# 按 buffer 门限求平均响度：每 buffer_samples 个采样点（各声道对齐）单独求功率，
# 剔除响度低于 threshold_db 的静音 buffer，再对保留 buffer 的功率取平均并换算成响度
def _calculate_buffered_loudness(file_path, block_size: int, threshold_db: float, buffer_samples: int,
                                 start_frame: int = 0, end_frame: int = None) -> float:
    with soundfile.SoundFile(file_path) as f:
        start_frame, end_frame = clamp_frame_range(f.frames, start_frame, end_frame)
        remaining = end_frame - start_frame
        if remaining <= 0:
            return MIN_LOUDNESS_DB
        f.seek(start_frame)
        buffer_size = max(1, buffer_samples * max(1, f.channels))
        blocks = f.blocks(blocksize=block_size, frames=remaining, dtype="float32")
        return _buffered_loudness_from_blocks(blocks, buffer_size, threshold_db)


# 内存数据的 buffer 门限平均响度：先按文件流式的 block_size 切块，再走同一套统计
def _buffered_loudness_from_data(data, threshold_db: float, buffer_samples: int = None,
                                 block_size: int = 65536) -> float:
    if buffer_samples is None:
        buffer_samples = user_config.get_tool_loudness_buffer_samples()
    channels = data.shape[1] if data.ndim > 1 else 1
    buffer_size = max(1, buffer_samples * max(1, channels))
    flat = data.reshape(-1)
    blocks = (flat[start:start + block_size] for start in range(0, flat.size, block_size))
    return _buffered_loudness_from_blocks(blocks, buffer_size, threshold_db)


# buffer 门限平均响度的共同实现：跨块拼接凑满一个 buffer，末尾不足一个 buffer 的单独统计
def _buffered_loudness_from_blocks(blocks, buffer_size: int, threshold_db: float) -> float:
    buffer_power = []
    pending = numpy.empty(0, dtype="float32")
    for block in blocks:
        chunk = numpy.asarray(block).reshape(-1)
        if pending.size > 0:
            chunk = numpy.concatenate((pending, chunk))
        full_size = chunk.size - chunk.size % buffer_size
        for offset in range(0, full_size, buffer_size):
            piece = chunk[offset:offset + buffer_size]
            buffer_power.append(numpy.sum(piece ** 2) / piece.size)
        pending = chunk[full_size:]
    if pending.size > 0:
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
