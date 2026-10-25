# voiceover-edit

Talking-head video editing pipeline: silence removal, word-level ASR subtitles, HDR tone-mapping, and single-pass rendering.

Designed for vertical (9:16) oral-broadcast videos destined for platforms like Xiaohongshu, Douyin, and YouTube Shorts.

## Features

- **Silence detection** - energy-based pause detection with configurable thresholds
- **ASR with word timestamps** - faster-whisper integration, model-agnostic registry
- **Subtitle generation** - CJK display-width aware line breaking, filler removal, remap to edited timeline
- **Single-pass rendering** - trim + concat + scale + HDR-to-SDR + subtitles in one ffmpeg command
- **HDR safety** - auto-detect HLG/PQ/SDR, Hable tone-mapping by default, trial-frame validation
- **Quality checks** - media parameter validation, subtitle-speech alignment, cut-edge energy verification
- **Structured plan** - JSON-based edit plan with schema validation, reproducible builds

## Requirements

- Python >= 3.10
- ffmpeg + ffprobe on PATH
- (Optional) faster-whisper for ASR: `pip install voiceover-edit[asr]`

## Install

```bash
pip install -e .
# or with ASR support:
pip install -e ".[asr]"
```

## Quick start

```bash
# Detect silences and build a cut plan
voiceover-edit silence --input video.mov --plan cut_plan.json

# Run ASR with word timestamps
voiceover-edit asr --input video.mov --model /path/to/fw-large-v3-turbo --words words.json

# Generate subtitles from words + plan
voiceover-edit subtitle --plan cut_plan.json --words words.json --srt subs.srt

# Render final video (single-pass)
voiceover-edit render --plan edit_plan.json --out final.mp4

# Quality check
voiceover-edit qc --video final.mp4 --srt subs.srt --timeline 95.2
```

## Supported input

| Property | Tested | Untested (contributions welcome) |
|---|---|---|
| Container | MOV, MP4 | MKV, WebM, AVI |
| Video codec | H.264, HEVC (8/10-bit) | AV1, VP9 |
| Color space | SDR (BT.709), HLG (BT.2020) | PQ/HDR10 |
| Aspect ratio | 9:16 vertical | 16:9, 1:1 |
| Audio | AAC stereo/mono | Opus, FLAC |
| Frame rate | 24/25/30/60 CFR | VFR |

## Configuration

Copy `config.example.toml` to `config.toml` and adjust paths:

```toml
[models]
default = "/path/to/faster-whisper-model"

[ffmpeg]
# Leave empty to use PATH
bin_dir = ""

[render]
crf = 17
preset = "slow"
```

## License

MIT
