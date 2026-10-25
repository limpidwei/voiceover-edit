"""Media probe: ffprobe wrapper for metadata extraction."""
import json
import shutil
import subprocess
import sys
from pathlib import Path


def find_ffprobe(config_bin_dir=""):
    """Resolve ffprobe binary path. Priority: config > PATH."""
    if config_bin_dir:
        p = Path(config_bin_dir) / ("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
        if p.is_file():
            return str(p)
    found = shutil.which("ffprobe")
    if found:
        return found
    raise FileNotFoundError(
        "ffprobe not found. Install ffmpeg or set [ffmpeg] bin_dir in config.toml."
    )


def find_ffmpeg(config_bin_dir=""):
    """Resolve ffmpeg binary path. Priority: config > PATH."""
    if config_bin_dir:
        p = Path(config_bin_dir) / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
        if p.is_file():
            return str(p)
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise FileNotFoundError(
        "ffmpeg not found. Install ffmpeg or set [ffmpeg] bin_dir in config.toml."
    )


def probe(path, ffprobe=None):
    """Run ffprobe and return parsed JSON metadata."""
    ffprobe = ffprobe or find_ffprobe()
    cmd = [
        ffprobe, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}: {r.stderr.strip()}")
    return json.loads(r.stdout)


def is_hdr(info):
    """Detect HDR from ffprobe output. Returns 'hlg', 'pq', or None."""
    for s in info.get("streams", []):
        if s.get("codec_type") != "video":
            continue
        transfer = s.get("color_transfer", "")
        if transfer == "arib-std-b67":
            return "hlg"
        if transfer == "smpte2084":
            return "pq"
        tags = s.get("side_data_list", [])
        for sd in tags:
            if "mastering" in sd.get("side_data_type", "").lower():
                return "pq"
    return None


def video_stream(info):
    """Return first video stream dict, or None."""
    for s in info.get("streams", []):
        if s.get("codec_type") == "video":
            return s
    return None


def audio_stream_index(info):
    """Return the index of the first audio stream suitable for voice.

    iPhone recordings may have multiple audio tracks; prefer the one
    with the most channels, falling back to the first audio stream.
    """
    audio_streams = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    if not audio_streams:
        return None
    best = max(audio_streams, key=lambda s: int(s.get("channels", 0)))
    return int(best["index"])


def resolution(info):
    """Return (width, height) of the first video stream."""
    vs = video_stream(info)
    if not vs:
        return None
    return int(vs["width"]), int(vs["height"])


def profile_level(width, height):
    """Choose H.264 profile and level by resolution.

    1080p and below -> Main@4.0
    Above 1080p (4K) -> High@5.1
    """
    pixels = width * height
    if pixels <= 1920 * 1080:
        return "main", "4.0"
    return "high", "5.1"
