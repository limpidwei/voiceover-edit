"""Quality-check rendered video and subtitles."""
import json
from pathlib import Path

from .probe import find_ffprobe, probe, video_stream
from .utils.display_width import display_width
from .utils.srt import read_srt


def run_qc(args):
    """CLI handler for 'voiceover-edit qc'."""
    ffprobe = find_ffprobe()
    info = probe(args.video, ffprobe=ffprobe)
    v = video_stream(info)
    a_list = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    timeline = args.timeline
    issues = []

    # Video checks
    if not v:
        issues.append("FATAL: no video stream")
    else:
        w, h = int(v["width"]), int(v["height"])
        if v.get("codec_name") != "h264":
            issues.append(f"codec: expected h264, got {v.get('codec_name')}")
        if v.get("pix_fmt") != "yuv420p":
            issues.append(f"pix_fmt: expected yuv420p, got {v.get('pix_fmt')}")

        # Profile/level
        pixels = w * h
        expected_profile = "High" if pixels > 1920 * 1080 else "Main"
        actual_profile = v.get("profile", "")
        if expected_profile.lower() not in actual_profile.lower():
            issues.append(f"profile: expected {expected_profile}, got {actual_profile}")

        # Color space - must be SDR bt709
        ct = v.get("color_transfer", "")
        cp = v.get("color_primaries", "")
        if "bt2020" in cp or "arib-std-b67" in ct or "smpte2084" in ct:
            issues.append(f"HDR not tone-mapped: transfer={ct}, primaries={cp}")

    # Audio checks
    if not a_list:
        issues.append("WARNING: no audio stream")
    else:
        a = a_list[0]
        sr = int(a.get("sample_rate", 0))
        if sr < 44100:
            issues.append(f"audio sample_rate: {sr} < 44100")

    # Duration
    dur = float(info["format"]["duration"])
    if abs(dur - timeline) > 2.0:
        issues.append(f"duration mismatch: video={dur:.1f}s, expected={timeline:.1f}s")

    # Subtitle checks
    if args.srt and Path(args.srt).exists():
        cues = read_srt(args.srt)
        if not cues:
            issues.append("WARNING: empty SRT")
        else:
            for i, cue in enumerate(cues):
                lines = cue.text.split("\n")
                for ln in lines:
                    if display_width(ln) > 12.01:
                        issues.append(f"subtitle {i+1}: line too wide ({display_width(ln):.1f}): {ln!r}")
                if len(lines) > 2:
                    issues.append(f"subtitle {i+1}: >2 lines")
                if cue.end > timeline + 0.5:
                    issues.append(f"subtitle {i+1}: ends at {cue.end:.3f} beyond timeline {timeline:.1f}")
            for i in range(len(cues) - 1):
                if cues[i].end > cues[i + 1].start + 0.01:
                    issues.append(f"subtitle overlap: {i+1} ends {cues[i].end:.3f}, "
                                  f"{i+2} starts {cues[i+1].start:.3f}")

    # Report
    report = {
        "video": args.video,
        "pass": len(issues) == 0,
        "issues": issues,
    }
    Path(args.report).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if issues:
        print(f"QC FAIL: {len(issues)} issues")
        for iss in issues:
            print(f"  - {iss}")
        return 1
    print("QC PASS")
    return 0
