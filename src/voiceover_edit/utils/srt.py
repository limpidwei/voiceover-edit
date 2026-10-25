"""SRT reading, writing, and timestamp formatting."""
import re
from dataclasses import dataclass


@dataclass
class SrtEntry:
    index: int
    start: float
    end: float
    text: str


def ts(value):
    """Format seconds as SRT timestamp: HH:MM:SS,mmm.

    Uses integer millisecond arithmetic to avoid float carry bugs.
    """
    value = max(0.0, value)
    ms = int(round(value * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_ts(text):
    """Parse SRT timestamp to seconds."""
    m = re.match(r"(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})", text.strip())
    if not m:
        raise ValueError(f"Bad SRT timestamp: {text!r}")
    h, mi, s, ms = (int(x) for x in m.groups())
    return h * 3600 + mi * 60 + s + ms / 1000


def read_srt(path):
    """Parse an SRT file into a list of SrtEntry."""
    text = open(path, encoding="utf-8-sig").read()
    entries = []
    for block in re.split(r"\n\n+", text.strip()):
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        idx = int(lines[0].strip())
        times = lines[1].strip()
        start_str, end_str = times.split("-->")
        entries.append(SrtEntry(
            index=idx,
            start=parse_ts(start_str),
            end=parse_ts(end_str),
            text="\n".join(lines[2:]),
        ))
    return entries


def write_srt(entries, path):
    """Write a list of SrtEntry to an SRT file."""
    blocks = []
    for i, e in enumerate(entries, 1):
        blocks.append(f"{i}\n{ts(e.start)} --> {ts(e.end)}\n{e.text}")
    open(path, "w", encoding="utf-8-sig").write("\n\n".join(blocks) + "\n")
