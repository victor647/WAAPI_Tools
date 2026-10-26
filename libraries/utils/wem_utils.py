import struct
from dataclasses import dataclass
from pathlib import Path


HEADER_READ_SIZE = 8192

FORMAT_NAMES = {
    0x0001: "PCM",
    0x0069: "IMA ADPCM",
    0x0161: "XWMA",
    0x0162: "XWMA",
    0x0165: "XMA2",
    0x0166: "XMA2",
    0xAAC0: "AAC",
    0xFFF0: "DSP",
    0xFFFB: "HEVAG",
    0xFFFC: "ATRAC9",
    0xFFFE: "PCM",
    0xFFFF: "Vorbis",
    0x3039: "OpusNX",
    0x3040: "Opus",
    0x3041: "OpusWEM",
    0x8311: "PTADPCM",
}


@dataclass
class WemInfo:
    path: Path
    size_bytes: int | None = None
    format_tag: int | None = None
    codec: str = "-"
    channels: int | None = None
    sample_rate: int | None = None
    duration_seconds: float | None = None


def _read_u16(data: bytes, offset: int, endian: str) -> int:
    return struct.unpack_from(f"{endian}H", data, offset)[0]


def _read_u32(data: bytes, offset: int, endian: str) -> int:
    return struct.unpack_from(f"{endian}I", data, offset)[0]


def _codec_name(format_tag: int, channels: int, extra_size: int, block_size: int) -> str:
    if format_tag == 0x0002:
        if extra_size == 0x0C + channels * 0x2E:
            return "DSP"
        if block_size == 0x104 * channels:
            return "PTADPCM"
        return "IMA ADPCM"
    return FORMAT_NAMES.get(format_tag, f"未知 (0x{format_tag:04X})")


# 读取 wem 的 RIFF 头，不加载音频数据
def read_wem_info(path: str | Path) -> WemInfo:
    file_path = Path(path)
    info = WemInfo(path=file_path)
    try:
        info.size_bytes = file_path.stat().st_size
        with file_path.open("rb") as file:
            header = file.read(HEADER_READ_SIZE)
    except OSError:
        return info

    if len(header) < 12 or header[:4] not in (b"RIFF", b"RIFX") or header[8:12] != b"WAVE":
        return info

    endian = "<" if header[:4] == b"RIFF" else ">"
    fmt_data = b""
    data_offset = 0
    data_size = 0
    offset = 12
    while offset + 8 <= len(header):
        chunk_id = header[offset:offset + 4]
        chunk_size = _read_u32(header, offset + 4, endian)
        payload_offset = offset + 8
        payload = header[payload_offset:payload_offset + chunk_size]
        if chunk_id == b"fmt ":
            fmt_data = payload
        elif chunk_id == b"data":
            data_offset = payload_offset
            data_size = chunk_size
        if fmt_data and data_offset:
            break
        offset = payload_offset + chunk_size + (chunk_size & 1)

    if len(fmt_data) < 16:
        return info
    info.format_tag = _read_u16(fmt_data, 0, endian)
    info.channels = _read_u16(fmt_data, 2, endian)
    info.sample_rate = _read_u32(fmt_data, 4, endian)
    block_size = _read_u16(fmt_data, 0x0C, endian)
    extra_size = _read_u16(fmt_data, 0x10, endian) if len(fmt_data) >= 0x12 else 0
    info.codec = _codec_name(info.format_tag, info.channels, extra_size, block_size)

    total_frames = None
    if len(fmt_data) >= 0x1C:
        if info.codec in ("Opus", "OpusNX", "OpusWEM"):
            total_frames = _read_u32(fmt_data, 0x18, endian)
        elif info.codec == "Vorbis" and extra_size >= 0x30:
            total_frames = _read_u32(fmt_data, 0x18, endian)
    if total_frames and info.sample_rate:
        info.duration_seconds = total_frames / info.sample_rate
    elif info.codec == "PCM" and block_size and data_size and info.sample_rate:
        info.duration_seconds = (data_size / block_size) / info.sample_rate

    # 极少数被插件替换成 Ogg Opus 的 wem
    if info.format_tag == 0xFFFE and data_offset and data_offset + 4 <= len(header):
        if header[data_offset:data_offset + 4] == b"OggS":
            info.codec = "Opus"

    return info


def format_file_size(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "-"
    if size_bytes < 1024:
        return f"{size_bytes}B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"


def format_duration(duration_seconds: float | None) -> str:
    if duration_seconds is None:
        return "-"
    if duration_seconds < 60:
        return f"{duration_seconds:.2f} s"
    minutes, seconds = divmod(duration_seconds, 60)
    return f"{int(minutes)}:{seconds:05.2f}"
