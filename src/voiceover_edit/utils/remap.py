"""Timeline remap: map source timestamps through keep segments.

Uses snap-to-nearest (not exact match) for words whose ASR midpoint
drifted into removed silence — pitfalls.md item 19.
"""


def build_accumulator(clips):
    """Pre-compute timeline offsets for each clip."""
    acc = []
    total = 0.0
    for start, end in clips:
        acc.append(total)
        total += end - start
    return acc


def locate(t, clips):
    """Find which clip a source timestamp belongs to.

    Snap-to-nearest: if t falls in a gap, returns the clip whose
    edge is closest. Never returns None.
    """
    for i, (start, end) in enumerate(clips):
        if start <= t <= end:
            return i
    return min(range(len(clips)),
               key=lambda i: min(abs(t - clips[i][0]), abs(t - clips[i][1])))


def remap_time(t, clip_idx, clips, acc):
    """Map a single source timestamp to the output timeline."""
    start, end = clips[clip_idx]
    clamped = min(max(t, start), end)
    return acc[clip_idx] + clamped - start


def remap_word(word, clips, acc):
    """Remap one word dict. Input keys: start, end, word."""
    mid = (word["start"] + word["end"]) / 2
    i = locate(mid, clips)
    return {
        "start": round(remap_time(word["start"], i, clips, acc), 3),
        "end": round(remap_time(word["end"], i, clips, acc), 3),
        "word": word["word"],
        "source_start": word["start"],
        "source_end": word["end"],
    }


def remap_words(words, clips):
    """Remap a list of word dicts through keep segments.

    Args:
        words: list of {start, end, word}
        clips: list of (start, end) tuples

    Returns remapped words; never drops words (snaps to nearest clip).
    """
    if not clips or not words:
        return []
    acc = build_accumulator(clips)
    return [remap_word(w, clips, acc) for w in words]
