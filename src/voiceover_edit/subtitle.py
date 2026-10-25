"""Generate subtitles: remap words through keep plan, line-break, output SRT.

Ported from build_subtitles.py (the best tested implementation).
Key upgrades over the original skill scripts:
- display_width (dw) everywhere, never len()
- PROTECTED word list prevents mid-word breaks
- Punctuation-preferred break points with balance scoring
- Snap-to-nearest remap (never drops words)
- Overlap clamping and minimum duration enforcement
- Proper ts() using integer millisecond arithmetic
"""
import re
import unicodedata
from pathlib import Path

from opencc import OpenCC

from .plan import EditPlan, WordsData
from .utils.display_width import display_width as dw
from .utils.remap import remap_words
from .utils.srt import SrtEntry, ts, write_srt

FILLERS = {"嗯", "呃", "啊", "欸"}
PUNCT = "，。？！、；：,.!?;:"
PROTECTED = (
    "开源", "思维", "为什么", "年轻人", "反馈", "产品", "项目", "用户", "需求",
    "系统", "市场", "技术", "客户", "资料", "知识产权", "上下文", "开发者",
    "自动", "考公", "考研", "教资", "宣发", "闭门造车",
    "DeepSeek", "GitHub", "token", "AI", "ChatGPT", "OpenAI",
)


def clean(text, cc):
    """Normalize: t2s, strip ellipsis, unify punctuation, collapse repeats."""
    text = cc.convert(text).replace("...", "").replace("…", "")
    text = text.replace(",", "，").replace("?", "？").replace("!", "！")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([，。？！、；：])\1+", r"\1", text)
    return text.strip(" " + PUNCT)


def smart_join(tokens):
    """Join tokens with space only between ASCII alphanumeric pairs."""
    text = ""
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if text and text[-1].isascii() and token[0].isascii() and text[-1].isalnum() and token[0].isalnum():
            text += " "
        text += token
    return text


def wrap(text, max_width=12, protected=PROTECTED):
    """Break text into at most 2 lines, each <= max_width display width.

    Scoring: prefer punctuation breaks > balanced width > avoid PROTECTED splits.
    Raises AssertionError if no valid break exists.
    """
    if dw(text) <= max_width:
        return [text]

    def splits_protected(index):
        for term in protected:
            start = text.find(term)
            while start >= 0:
                if start < index < start + len(term):
                    return True
                start = text.find(term, start + 1)
        return False

    candidates = []
    for i in range(1, len(text)):
        left, right = text[:i].strip(), text[i:].strip()
        if not left or not right:
            continue
        if splits_protected(i):
            continue
        if text[i - 1].isascii() and text[i].isascii() and text[i - 1].isalnum() and text[i].isalnum():
            continue
        left = left.rstrip(PUNCT)
        right = right.lstrip(PUNCT + " ")
        if not left or not right or dw(left) > max_width or dw(right) > max_width:
            continue
        preferred = text[i - 1] in PUNCT or text[i].isspace()
        candidates.append((not preferred, abs(dw(left) - dw(right)), left, right))
    if not candidates:
        raise AssertionError(f"Cannot wrap within 2x{max_width}: {text} ({dw(text)})")
    _, _, left, right = min(candidates)
    return [left, right]


def build_subtitle(
    words_data,
    plan,
    max_width=12,
    max_lines=2,
    protected=PROTECTED,
):
    """Build subtitle cues from WordsData + EditPlan.

    Returns list of SrtEntry.
    """
    cc = OpenCC("t2s")
    clips = plan.flat_clips(0) if hasattr(plan, "flat_clips") else [(s, e) for s, e in plan]
    timeline = sum(e - s for s, e in clips)

    content_deletions = getattr(plan, "content_deletions", []) or []
    word_replacements = getattr(plan, "word_replacements", {}) or {}
    phrase_replacements = getattr(plan, "phrase_replacements", {}) or {}
    force_break_after = getattr(plan, "force_break_after", []) or []

    def is_deleted(mid):
        return any(item["source_start"] <= mid < item["source_end"] for item in content_deletions)

    # Filter: remove fillers, deleted content; apply word replacements
    filtered = []
    for w in words_data.words:
        mid = (w["start"] + w["end"]) / 2
        if is_deleted(mid):
            continue
        token = w["word"].strip()
        if token.strip(PUNCT) in FILLERS:
            continue
        token = word_replacements.get(token, token)
        filtered.append({"start": w["start"], "end": w["end"], "word": token})

    # Remap through keep plan
    remapped = remap_words(filtered, clips)
    if not remapped:
        return []

    # Group into cues by segment boundaries and punctuation
    cues = []
    current = []

    def flush():
        nonlocal current
        if not current:
            return
        text = clean(smart_join([w["word"] for w in current]), cc)
        for old, new in phrase_replacements.items():
            text = text.replace(old, new)
        if text and text not in FILLERS:
            start_t = current[0]["start"]
            end_t = min(current[-1]["end"], timeline)
            if cues and cues[-1]["text"] == text and abs(cues[-1]["start"] - start_t) < 1.5:
                cues[-1] = {**cues[-1], "end": max(cues[-1]["end"], end_t)}
            else:
                cues.append({"start": start_t, "end": end_t, "text": text})
        current = []

    for word in remapped:
        if current:
            trial = smart_join([w["word"] for w in current] + [word["word"]])
            if dw(clean(trial, cc)) > max_width * max_lines:
                flush()
        current.append(word)
        raw_text = smart_join([w["word"] for w in current])
        text = clean(raw_text, cc)
        last = raw_text.strip()[-1:]
        if any(text.endswith(phrase) for phrase in force_break_after):
            flush()
        elif last in "。？！？；!" and dw(text) >= 6:
            flush()
        elif last in "，,：" and dw(text) >= 10:
            flush()
    flush()

    # Sort and fix timing
    cues.sort(key=lambda c: c["start"])
    for i, cue in enumerate(cues):
        if cue["end"] - cue["start"] < 0.4:
            limit = cues[i + 1]["start"] if i + 1 < len(cues) else timeline
            cue["end"] = min(cue["start"] + 0.4, limit, timeline)
        if i and cue["start"] < cues[i - 1]["end"]:
            cues[i - 1]["end"] = cue["start"]

    # Wrap lines and validate
    entries = []
    for i, cue in enumerate(cues):
        lines = wrap(cue["text"], max_width, protected)
        assert len(lines) <= max_lines and all(dw(ln) <= max_width for ln in lines)
        assert cue["end"] > cue["start"], cue
        entries.append(SrtEntry(
            index=i + 1,
            start=cue["start"],
            end=cue["end"],
            text="\n".join(lines),
        ))

    if entries:
        assert entries[-1].end <= timeline + 0.001

    return entries


def run_subtitle(args):
    """CLI handler for 'voiceover-edit subtitle'."""
    plan = EditPlan.from_file(args.plan)
    words_data = WordsData.from_file(args.words)
    entries = build_subtitle(words_data, plan)
    write_srt(entries, args.srt)
    print(f"Subtitles: {len(entries)} cues")
    return 0
