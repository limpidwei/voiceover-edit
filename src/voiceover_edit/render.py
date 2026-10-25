"""Single-pass render: trim + concat + scale + HDR-to-SDR + subtitles + encode."""
import subprocess
import tempfile
from pathlib import Path

from .color import tonemap_filter, needs_tonemap
from .plan import EditPlan
from .probe import find_ffmpeg, find_ffprobe, probe, video_stream, resolution
from .utils.resource import adaptive_threads


def _profile_level(width, height):
    pixels = width * height
    if pixels > 1920 * 1080:
        return "high", "5.1"
    return "main", "4.0"


def _build_filter_complex(ep, inputs_info, target_w, target_h, srt_path=None):
    """Build the filter_complex string for single-pass render."""
    parts = []
    seg_labels = []
    seg_idx = 0

    for i, segments in enumerate(ep.keep):
        info = inputs_info[i]
        needs_tm, hdr = needs_tonemap(info)
        src_w, src_h = resolution(info)

        for j, seg in enumerate(segments):
            s, e = seg[0], seg[1]

            # Trim
            audio_sel = f"{i}:{ep.audio_stream}" if ep.audio_stream.isdigit() else f"{i}:a"
            parts.append(f"[{i}:v]trim=start={s}:end={e},setpts=PTS-STARTPTS[tv{seg_idx}];")
            parts.append(f"[{audio_sel}]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[ta{seg_idx}];")

            # Scale if needed (no tonemap per-segment; tonemap after concat)
            if src_w != target_w or src_h != target_h:
                parts.append(
                    f"[tv{seg_idx}]scale={target_w}:{target_h}:flags=lanczos[vm{seg_idx}];"
                )
                seg_labels.append((f"vm{seg_idx}", f"ta{seg_idx}"))
            else:
                seg_labels.append((f"tv{seg_idx}", f"ta{seg_idx}"))

            seg_idx += 1

    n = len(seg_labels)
    if n == 0:
        raise RuntimeError("No segments to render")

    concat_in = "".join(f"[{v}][{a}]" for v, a in seg_labels)
    parts.append(f"{concat_in}concat=n={n}:v=1:a=1[cv][ca];")

    # Tonemap ONCE after concat (per pitfalls.md)
    out_v = "cv"
    if ep.tonemap:
        tm = tonemap_filter(hdr or "hlg", operator=ep.tonemap_op)
        parts.append(f"[cv]{tm}[tm];")
        out_v = "tm"

    # Subtitle burn-in
    actual_srt = srt_path or ep.srt
    if actual_srt:
        esc_path = str(actual_srt).replace("\\", "/").replace(":", r"\:")
        style = "FontName=Noto Sans CJK SC,FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=0,MarginV=35"
        parts.append(f"[{out_v}]subtitles='{esc_path}':force_style='{style}'[vout]")
        out_v = "vout"

    fc = "\n".join(parts)
    if fc.endswith(";"):
        fc = fc[:-1]

    return fc, out_v


def run_render(args):
    """CLI handler for 'voiceover-edit render'."""
    ep = EditPlan.from_file(args.plan)
    ffmpeg = find_ffmpeg()
    ffprobe = find_ffprobe()

    inputs_info = [probe_media(p, ffprobe) for p in ep.inputs]

    first_w, first_h = resolution(inputs_info[0])
    if ep.scale:
        target_w, target_h = ep.scale
    elif args.preview:
        scale = 540 / max(first_w, first_h)
        target_w = int(first_w * scale) // 2 * 2
        target_h = int(first_h * scale) // 2 * 2
    else:
        target_w, target_h = first_w, first_h

    srt_path = getattr(args, "srt", None)
    fc, out_v = _build_filter_complex(ep, inputs_info, target_w, target_h, srt_path=srt_path)

    fc_file = Path(tempfile.mktemp(suffix=".txt"))
    fc_file.write_text(fc, encoding="utf-8")

    profile, level = _profile_level(target_w, target_h)
    threads = adaptive_threads()
    crf = 23 if args.preview else ep.crf
    preset = "veryfast" if args.preview else ep.preset

    cmd = [ffmpeg, "-y"]
    for p in ep.inputs:
        cmd.extend(["-i", p])
    cmd.extend([
        "-filter_complex_script", str(fc_file),
        "-map", f"[{out_v}]", "-map", "[ca]",
        "-c:v", "libx264", "-profile:v", profile, "-level", level,
        "-crf", str(crf), "-preset", preset,
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-threads", str(threads),
        "-movflags", "+faststart",
        str(args.out),
    ])

    total_segs = sum(len(segs) for segs in ep.keep)
    print(f"Rendering {total_segs} segments -> {target_w}x{target_h} "
          f"({profile}@{level}, crf={crf}, threads={threads})")

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    fc_file.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"ffmpeg failed:\n{result.stderr[-2000:]}")
        return 1

    out_info = probe(args.out, ffprobe)
    v = video_stream(out_info)
    if v:
        assert v.get("pix_fmt") == "yuv420p", f"Bad pix_fmt: {v.get('pix_fmt')}"
        cs = v.get("color_space", "")
        if cs and cs != "unknown":
            assert "bt709" in cs, f"Not bt709: {cs}"

    dur = float(out_info["format"]["duration"])
    expected = sum(seg[1] - seg[0] for segs in ep.keep for seg in segs)
    print(f"Output: {args.out} ({dur:.1f}s, expected ~{expected:.1f}s)")
    return 0
