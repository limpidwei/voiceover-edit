"""Silence detection via ffmpeg silencedetect, builds cut plan."""
import json
import re
import subprocess
from pathlib import Path

from .probe import find_ffmpeg, probe as run_probe


def _media_duration(path, ffprobe=None):
    """Get duration in seconds from ffprobe."""
    info = run_probe(path, ffprobe=ffprobe)
    return float(info["format"]["duration"])


def detect_silences(path, noise="-35dB", min_duration=0.45, ffmpeg=None):
    """Return list of (start, end) silence intervals."""
    ffmpeg = ffmpeg or find_ffmpeg()
    cmd = [
        ffmpeg, "-i", str(path), "-af",
        f"silencedetect=noise={noise}:d={min_duration}",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    stderr = result.stderr
    starts = [float(m.group(1)) for m in re.finditer(r"silence_start: ([\d.]+)", stderr)]
    ends = [float(m.group(1)) for m in re.finditer(r"silence_end: ([\d.]+)", stderr)]
    silences = list(zip(starts, ends[:len(starts)]))
    if len(starts) > len(ends):
        dur = _media_duration(path)
        silences.append((starts[-1], dur))
    return silences


def build_keep(duration, silences, pad=0.18):
    """Build keep segments from silence intervals."""
    keep = []
    cursor = 0.0
    for s_start, s_end in silences:
        seg_start = cursor
        seg_end = s_start + pad
        if seg_end > seg_start + 0.05:
            keep.append([round(seg_start, 3), round(seg_end, 3)])
        cursor = max(cursor, s_end - pad)
    if cursor < duration - 0.05:
        keep.append([round(cursor, 3), round(duration, 3)])
    return keep


def build_cut_plan(path, noise="-35dB", min_duration=0.45, pad=0.18, ffmpeg=None):
    """Full pipeline: detect silences -> keep segments -> CutPlan dict."""
    path = Path(path)
    dur = _media_duration(path)
    silences = detect_silences(path, noise=noise, min_duration=min_duration, ffmpeg=ffmpeg)
    keep = build_keep(dur, silences, pad=pad)
    return {
        "inputs": [str(path.resolve())],
        "keep": [keep],
        "duration": [dur],
    }


def run_silence(args):
    """CLI handler for 'voiceover-edit silence'."""
    plan = build_cut_plan(
        args.input, noise=args.noise, min_duration=args.min_duration, pad=args.pad,
    )
    keep = plan["keep"][0]
    dur = plan["duration"][0]
    Path(args.plan).write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Detected silences, {len(keep)} keep segments, "
          f"output ~{sum(e-s for s,e in keep):.1f}s from {dur:.1f}s source")
    return 0
