"""ASR via faster-whisper with word-level timestamps."""
import json
import os
from pathlib import Path


def _ensure_fw():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper not installed. Run: pip install voiceover-edit[asr]")


def run_asr(args):
    """CLI handler for 'voiceover-edit asr'."""
    WhisperModel = _ensure_fw()

    os.environ.setdefault("OMP_NUM_THREADS", "4")

    model = WhisperModel(
        args.model,
        device="auto",
        compute_type="int8",
    )
    segments, info = model.transcribe(
        args.input,
        language=args.language,
        word_timestamps=True,
        initial_prompt=args.prompt or None,
        vad_filter=True,
    )

    words = []
    for seg in segments:
        if not seg.words:
            continue
        for w in seg.words:
            text = w.word.strip()
            if not text:
                continue
            words.append({
                "start": round(w.start, 3),
                "end": round(w.end, 3),
                "word": text,
            })

    out = {"duration": info.duration, "segments": [], "words": words}
    Path(args.words).write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"ASR: {len(words)} words, language={info.language}, prob={info.language_probability:.2f}")

    if args.srt:
        from .utils.srt import SrtEntry, write_srt
        entries = [SrtEntry(i + 1, w["start"], w["end"], w["word"])
                  for i, w in enumerate(words)]
        write_srt(entries, args.srt)
        print(f"Raw SRT: {args.srt}")

    return 0
