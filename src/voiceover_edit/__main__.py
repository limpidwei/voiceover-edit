"""CLI entry point."""
import argparse
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="voiceover-edit",
        description="Talking-head video editing pipeline.",
    )
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("silence", help="Detect silences and build cut plan")
    p.add_argument("--input", required=True, help="Source video/audio file")
    p.add_argument("--plan", required=True, help="Output cut_plan.json path")
    p.add_argument("--noise", default="-35dB")
    p.add_argument("--min-duration", type=float, default=0.45)
    p.add_argument("--pad", type=float, default=0.18)

    p = sub.add_parser("asr", help="Run ASR with word-level timestamps")
    p.add_argument("--input", required=True)
    p.add_argument("--model", required=True, help="Path to faster-whisper model directory")
    p.add_argument("--words", required=True, help="Output words.json path")
    p.add_argument("--srt", help="Optional direct SRT output")
    p.add_argument("--prompt", default="")
    p.add_argument("--language", default="zh")

    p = sub.add_parser("subtitle", help="Generate subtitles from words + plan")
    p.add_argument("--plan", required=True)
    p.add_argument("--words", required=True)
    p.add_argument("--srt", required=True)
    p.add_argument("--transcript", help="Optional transcript output")

    p = sub.add_parser("render", help="Single-pass render from edit plan")
    p.add_argument("--plan", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--srt", help="SRT file for subtitle burn-in")
    p.add_argument("--preview", action="store_true")

    p = sub.add_parser("qc", help="Quality-check final video + subtitles")
    p.add_argument("--video", required=True)
    p.add_argument("--srt", required=True)
    p.add_argument("--timeline", type=float, required=True)
    p.add_argument("--report", default="qc_report.json")

    p = sub.add_parser("probe", help="Probe media file properties")
    p.add_argument("--input", required=True)

    p = sub.add_parser("verify", help="Verify subtitles against video audio")
    p.add_argument("--video", required=True)
    p.add_argument("--srt", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--prompt", default="")

    p = sub.add_parser("struct-check", help="Structural integrity check")
    p.add_argument("--plan", required=True)
    p.add_argument("--words", required=True)
    p.add_argument("--raw-words", help="Original ASR words.json for coverage comparison")
    p.add_argument("--video", required=True)
    p.add_argument("--report", default="struct_report.json")

    p = sub.add_parser("cover", help="Extract cover frame")
    p.add_argument("--video", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--time", type=float, default=1.0)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    dispatch = {
        "silence": lambda: __import__("voiceover_edit.silence", fromlist=["run_silence"]).run_silence,
        "asr": lambda: __import__("voiceover_edit.asr", fromlist=["run_asr"]).run_asr,
        "subtitle": lambda: __import__("voiceover_edit.subtitle", fromlist=["run_subtitle"]).run_subtitle,
        "render": lambda: __import__("voiceover_edit.render", fromlist=["run_render"]).run_render,
        "qc": lambda: __import__("voiceover_edit.qc", fromlist=["run_qc"]).run_qc,
        "probe": lambda: __import__("voiceover_edit.probe", fromlist=["run_probe"]).run_probe,
        "verify": lambda: __import__("voiceover_edit.verify", fromlist=["run_verify"]).run_verify,
        "struct-check": lambda: __import__("voiceover_edit.struct_check", fromlist=["run_struct_check"]).run_struct_check,
        "cover": lambda: __import__("voiceover_edit.cover", fromlist=["run_cover"]).run_cover,
    }
    handler = dispatch[args.command]()
    return handler(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
