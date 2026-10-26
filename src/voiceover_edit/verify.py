"""Verify subtitles by re-running ASR on the rendered video and comparing."""
import hashlib
import json
import os
from pathlib import Path

from .utils.srt import read_srt


def _cache_key(video_path, model_path, prompt="", language="zh"):
    """Build a cache key from video mtime + model + params."""
    stat = Path(video_path).stat()
    raw = f"{video_path}:{stat.st_mtime}:{stat.st_size}:{model_path}:{prompt}:{language}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_path(video_path, model_path, prompt="", language="zh"):
    cache_dir = Path(video_path).parent / ".voiceover_cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir / f"verify_{_cache_key(video_path, model_path)}.json"


def verify_srt(video_path, srt_path, model_path, prompt="", language="zh"):
    """Compare SRT cues against fresh ASR. Returns (score, details)."""
    cache = _cache_path(video_path, model_path, prompt, language)
    if cache.exists():
        asr_words = json.loads(cache.read_text(encoding="utf-8"))
    else:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise RuntimeError("faster-whisper required for verify")

        os.environ.setdefault("OMP_NUM_THREADS", "4")
        model = WhisperModel(model_path, device="auto", compute_type="int8")
        segments, _ = model.transcribe(
            video_path, language=language,
            word_timestamps=True, initial_prompt=prompt or None,
            vad_filter=True,
        )
        asr_words = []
        for seg in segments:
            if not seg.words:
                continue
            for w in seg.words:
                text = w.word.strip()
                if text:
                    asr_words.append({"s": round(w.start, 3), "e": round(w.end, 3), "w": text})
        cache.write_text(json.dumps(asr_words, ensure_ascii=False), encoding="utf-8")

    cues = read_srt(srt_path)
    srt_text = "".join(c.text.replace("\n", "") for c in cues)
    asr_text = "".join(w["word"] for w in asr_words)

    # Character overlap score
    from collections import Counter
    srt_counts = Counter(srt_text)
    asr_counts = Counter(asr_text)
    overlap = sum((srt_counts & asr_counts).values())
    total = max(sum(srt_counts.values()), sum(asr_counts.values()), 1)
    score = overlap / total

    return score, {
        "srt_chars": len(srt_text),
        "asr_chars": len(asr_text),
        "overlap_chars": overlap,
        "score": round(score, 4),
        "asr_word_count": len(asr_words),
    }


def run_verify(args):
    """CLI handler for 'voiceover-edit verify'."""
    score, details = verify_srt(args.video, args.srt, args.model, prompt=args.prompt)
    print(f"Verify score: {score:.2%}")
    print(json.dumps(details, indent=2))
    threshold = 0.80
    if score < threshold:
        print(f"WARN: score {score:.2%} < {threshold:.0%} threshold")
        return 1
    return 0
