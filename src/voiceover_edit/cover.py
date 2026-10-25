"""Extract a cover frame from video."""
import subprocess
from pathlib import Path

from .probe import find_ffmpeg


def extract_cover(video_path, out_path, time=1.0, ffmpeg=None):
    """Extract a single frame at the given timestamp."""
    ffmpeg = ffmpeg or find_ffmpeg()
    cmd = [
        ffmpeg, "-y",
        "-ss", str(time),
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Cover extraction failed: {result.stderr[:500]}")
    if not Path(out_path).exists():
        raise RuntimeError(f"Cover file not created: {out_path}")
    return out_path


def run_cover(args):
    """CLI handler for 'voiceover-edit cover'."""
    extract_cover(args.video, args.out, time=args.time)
    print(f"Cover: {args.out}")
    return 0
