"""Structural integrity check: word coverage, overlap, cut-edge energy."""
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from .plan import CutPlan, WordsData
from .probe import find_ffmpeg


def check_word_coverage(plan_words, raw_words):
    plan_chars = Counter("".join(w.get("word", w.get("w", "")) for w in plan_words))
    raw_chars = Counter("".join(w.get("word", w.get("w", "")) for w in raw_words))
    missing = raw_chars - plan_chars
    extra = plan_chars - raw_chars
    return {"missing_chars": dict(missing) if missing else {}, "extra_chars": dict(extra) if extra else {}, "pass": not missing}


def check_overlap(words):
    overlaps = []
    for i in range(len(words) - 1):
        e = float(words[i].get("end", words[i].get("e", 0)))
        s_next = float(words[i + 1].get("start", words[i + 1].get("s", 0)))
        if e > s_next + 0.01:
            overlaps.append({"index": i, "gap": round(s_next - e, 3)})
    return {"overlaps": overlaps, "pass": len(overlaps) == 0}


def check_cut_edge_energy(video_path, keep, window=0.15, threshold=-40):
    ffmpeg = find_ffmpeg()
    issues = []
    for i, (s, e) in enumerate(keep):
        for label, t in [("start", s), ("end", e)]:
            if t < 0.1:
                continue
            t0 = max(0, t - window)
            t1 = t + window
            cmd = [
                ffmpeg, "-i", str(video_path),
                "-ss", str(t0), "-to", str(t1),
                "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
                "-f", "null", "-",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            rms_vals = re.findall(r"RMS_level=(-?[\d.]+)", result.stderr)
            if rms_vals:
                rms = max(float(v) for v in rms_vals)
                if rms > threshold:
                    issues.append({"segment": i, "edge": label, "time": t, "rms": rms})
    return {"edge_issues": issues, "pass": len(issues) == 0}


def run_struct_check(args):
    """CLI handler for 'voiceover-edit struct-check'."""
    cut_plan = CutPlan.from_file(args.plan)
    keep = cut_plan.flat_clips(0)
    words_data = WordsData.from_file(args.words)

    results = {}
    if args.raw_words:
        raw_data = WordsData.from_file(args.raw_words)
        results["coverage"] = check_word_coverage(words_data.words, raw_data.words)
    else:
        results["coverage"] = {"missing_chars": {}, "extra_chars": {}, "pass": True, "skipped": "no --raw-words provided"}
    results["overlap"] = check_overlap(words_data.words)
    results["cut_edge"] = check_cut_edge_energy(args.video, keep)
    results["pass"] = all(r.get("pass", True) for r in results.values())

    Path(args.report).write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if results["pass"]:
        print("Struct check PASS")
        return 0
    print("Struct check FAIL")
    for key, val in results.items():
        if isinstance(val, dict) and not val.get("pass", True):
            print(f"  {key}: FAIL")
    return 1
