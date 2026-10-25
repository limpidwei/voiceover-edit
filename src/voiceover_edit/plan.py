"""Unified plan schema: CutPlan, EditPlan, WordsData.

Resolves the schema split between scripts:
- 01 outputs {input, keep} (single input, flat keep)
- 03 consumes {inputs, keep} (multi-input, nested keep)
- 02b outputs words with {start, end, word}
- 09 consumes words with segment structure
"""
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CutPlan:
    """Output of silence detection."""
    inputs: list[str]
    keep: list[list[list[float]]]  # keep[input_idx] = [[start, end], ...]
    duration: list[float] = field(default_factory=list)

    @classmethod
    def from_file(cls, path):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, d):
        if "input" in d and "inputs" not in d:
            inputs = [d["input"]]
            keep_raw = d["keep"]
            if keep_raw and isinstance(keep_raw[0], (list, tuple)) and len(keep_raw[0]) == 2 and isinstance(keep_raw[0][0], (int, float)):
                keep = [keep_raw]
            else:
                keep = keep_raw
        else:
            inputs = d["inputs"]
            keep = d["keep"]
        normalized = []
        for per_input in keep:
            if per_input and isinstance(per_input[0], (int, float)):
                normalized.append([per_input])
            else:
                normalized.append([list(seg) for seg in per_input])
        duration = d.get("duration", [])
        if isinstance(duration, (int, float)):
            duration = [duration]
        return cls(inputs=inputs, keep=normalized, duration=duration)

    def flat_clips(self, input_idx=0):
        return [tuple(seg) for seg in self.keep[input_idx]]

    def validate(self):
        errors = []
        for i, segments in enumerate(self.keep):
            for j, seg in enumerate(segments):
                if len(seg) != 2:
                    errors.append(f"keep[{i}][{j}]: expected [start, end], got {seg}")
                elif seg[0] < 0:
                    errors.append(f"keep[{i}][{j}]: negative start {seg[0]}")
                elif seg[1] <= seg[0]:
                    errors.append(f"keep[{i}][{j}]: end <= start")
                if j > 0 and seg[0] < segments[j - 1][1] - 1e-9:
                    errors.append(f"keep[{i}][{j}]: overlaps previous segment")
        if errors:
            raise ValueError("CutPlan validation failed:\n" + "\n".join(errors))


@dataclass
class EditPlan:
    """Rendering plan consumed by the renderer."""
    inputs: list[str]
    keep: list[list[list[float]]]
    srt: str = ""
    scale: list[int] = field(default_factory=list)
    tonemap: bool = False
    tonemap_op: str = "hable"
    audio_stream: str = "a"
    crf: int = 17
    preset: str = "slow"
    fps: int = 30
    content_deletions: list[dict] = field(default_factory=list)
    word_replacements: dict = field(default_factory=dict)
    phrase_replacements: dict = field(default_factory=dict)
    force_break_after: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, d):
        if "input" in d and "inputs" not in d:
            d["inputs"] = [d.pop("input")]
        if "hdr" in d and "tonemap" not in d:
            d["tonemap"] = d.pop("hdr")
        if "astream" in d and "audio_stream" not in d:
            d["audio_stream"] = d.pop("astream")
        keep = d.get("keep", [])
        if keep and isinstance(keep[0], (list, tuple)) and keep[0] and isinstance(keep[0][0], (int, float)):
            keep = [keep]
        return cls(
            inputs=d.get("inputs", []),
            keep=keep,
            srt=d.get("srt", ""),
            scale=d.get("scale", []),
            tonemap=d.get("tonemap", False),
            tonemap_op=d.get("tonemap_op", "hable"),
            audio_stream=str(d.get("audio_stream", d.get("astream", "a"))),
            crf=d.get("crf", 17),
            preset=d.get("preset", "slow"),
            fps=d.get("fps", 30),
            content_deletions=d.get("content_deletions", []),
            word_replacements=d.get("word_replacements", {}),
            phrase_replacements=d.get("phrase_replacements", {}),
            force_break_after=d.get("force_break_after", []),
        )


@dataclass
class WordsData:
    """ASR output: segments + word-level timestamps."""
    duration: float
    segments: list[dict]
    words: list[dict]

    @classmethod
    def from_file(cls, path):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, d):
        words = d.get("words", [])
        migrated = []
        for w in words:
            if "s" in w and "start" not in w:
                migrated.append({"start": w["s"], "end": w["e"], "word": w["w"]})
            else:
                migrated.append(w)
        return cls(
            duration=d.get("duration", 0),
            segments=d.get("segments", []),
            words=migrated,
        )

    def validate(self):
        errors = []
        for i, w in enumerate(self.words):
            for key in ("start", "end", "word"):
                if key not in w:
                    errors.append(f"words[{i}]: missing '{key}'")
            if "start" in w and "end" in w and w["end"] < w["start"]:
                errors.append(f"words[{i}]: end < start")
        if self.words and self.duration > 0:
            last_end = self.words[-1].get("end", 0)
            if last_end > self.duration + 0.5:
                errors.append(f"last word end {last_end} exceeds duration {self.duration}")
        if errors:
            raise ValueError("WordsData validation failed:\n" + "\n".join(errors))
