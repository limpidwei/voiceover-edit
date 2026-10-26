#!/usr/bin/env python3
"""Self-contained smoke test: run with PYTHONPATH=src py -3.12 run_tests.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

passed, failed = 0, 0

def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {name}")

print("=== srt ===")
from voiceover_edit.utils.srt import ts, parse_ts
check("ts(0)", ts(0) == "00:00:00,000")
check("ts carry", ts(59.9999) == "00:01:00,000")
check("ts hour", ts(3661.5) == "01:01:01,500")
check("ts negative", ts(-1) == "00:00:00,000")
check("parse_ts dot", abs(parse_ts("01:02:03.456") - 3723.456) < 0.001)
check("roundtrip", abs(parse_ts(ts(65.123)) - 65.123) < 0.002)

print("=== display_width ===")
from voiceover_edit.utils.display_width import display_width as dw
check("cjk", dw("你好") == 2.0)
check("ascii", dw("hello") == 2.5)
check("mixed", dw("你好world") == 4.5)
check("spaces", dw("你 好") == 2.0)
check("empty", dw("") == 0.0)

print("=== remap ===")
from voiceover_edit.utils.remap import locate, remap_words, build_accumulator, remap_time
clips = [(1.0, 3.0), (5.0, 8.0)]
check("locate inside", locate(2.0, clips) == 0)
check("locate snap", locate(4.5, clips) == 1)
check("locate before", locate(0.5, [(2.0, 4.0)]) == 0)
acc = build_accumulator(clips)
check("acc", acc == [0.0, 2.0])
check("remap_time", abs(remap_time(2.0, 0, clips, acc) - 1.0) < 1e-9)
words = [{"start":0.5,"end":1.0,"word":"hi"},{"start":4.5,"end":5.0,"word":"there"}]
r = remap_words(words, [(0.0,2.0),(4.0,6.0)])
check("remap count", len(r) == 2)
check("remap word", r[1]["word"] == "there")
check("remap start", abs(r[1]["start"] - 2.5) < 0.01)
check("remap snap", len(remap_words([{"start":2.5,"end":3.5,"word":"gap"}], [(0.0,2.0),(4.0,6.0)])) == 1)
check("remap empty", remap_words([], [(0,1)]) == [])

print("=== plan ===")
from voiceover_edit.plan import CutPlan, EditPlan, WordsData
p = CutPlan.from_dict({"input":"test.mp4","keep":[[0.0,1.5],[3.0,5.0]],"duration":6.0})
check("legacy input", p.inputs == ["test.mp4"])
check("flat_clips", p.flat_clips(0) == [(0.0,1.5),(3.0,5.0)])
try:
    p.validate()
    check("validate ok", True)
except Exception:
    check("validate ok", False)
ep = EditPlan.from_dict({"input":"a.mp4","keep":[[0,1],[2,3]],"hdr":True,"astream":"0:1"})
check("hdr->tonemap", ep.tonemap == True)
check("astream->audio_stream", ep.audio_stream == "0:1")
wd = WordsData.from_dict({"duration":5,"segments":[],"words":[{"s":0.1,"e":0.5,"w":"hi"}]})
check("s->start", wd.words[0]["start"] == 0.1)
check("w->word", wd.words[0]["word"] == "hi")

print("=== color ===")
from voiceover_edit.color import tonemap_filter
tf = tonemap_filter("hlg", "hable")
check("hable filter", "tonemap=hable" in tf)
check("npl 200", "npl=200" in tf)
check("gbrpf32le", "gbrpf32le" in tf)
tf2 = tonemap_filter("pq", "mobius")
check("mobius", "mobius" in tf2)
check("smpte2084", "smpte2084" in tf2)

print("=== probe ===")
from voiceover_edit.probe import profile_level, is_hdr
check("1080p", profile_level(1920,1080) == ("main","4.0"))
check("4k", profile_level(3840,2160) == ("high","5.1"))
check("no hdr", is_hdr({"streams":[]}) is None)

print("=== imports ===")
try:
    from voiceover_edit import probe, silence, plan, subtitle, render, qc, verify, struct_check, cover, color
    from voiceover_edit.utils import srt, remap, display_width, resource
    check("all imports", True)
except Exception as exc:
    print(f"  import error: {exc}")
    check("all imports", False)

print("=== cli dispatch ===")
from voiceover_edit.__main__ import main
rc = main(["--help"])
check("cli help", rc is None or rc == 0)
for cmd in ["silence", "asr", "subtitle", "render", "qc", "probe", "verify", "struct-check", "cover"]:
    try:
        main([cmd, "--help"])
        check(f"cli {cmd}", True)
    except SystemExit:
        check(f"cli {cmd}", True)
    except Exception as exc:
        print(f"  {cmd}: {exc}")
        check(f"cli {cmd}", False)

print(f"\n{'='*40}")
print(f"PASSED: {passed}  FAILED: {failed}")
sys.exit(1 if failed else 0)
