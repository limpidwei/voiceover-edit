# voiceover-edit HANDOVER

Last updated: 2026-10-26

## What this is

Standalone Python package for oral-broadcast (talking-head) video editing.
Extracted from the `voiceover-video-edit` Claude skill after 12+ real production videos.

## Repository

- Repository root: `voiceover-edit/`
- Package: `src/voiceover_edit/` (hatchling build, `pip install -e .`)
- CLI: `voiceover-edit <subcommand>`
- Tests: `run_tests.py` (51 checks, no external dependencies)
- License: MIT

## Key decisions

1. **HLG tonemap npl=200** (not 100) — 100 caused 42.91% dead-white on health video
2. **Hable default** tonemap operator — mobius pushed whites, reinhard too conservative
3. **Snap-to-nearest remap** — words in silence gaps snap to nearest clip edge, never dropped
4. **Integer millisecond SRT timestamps** — prevents carry bug (59.9999s → 00:01:00,000)
5. **display_width for CJK** — fullwidth=1.0, halfwidth=0.5, spaces ignored; replaces len() everywhere
6. **PROTECTED word list** — prevents mid-word breaks for terms like DeepSeek, GitHub
7. **Tonemap ONCE after concat** — per-segment causes OOM (2.5GB) or zscale exhaustion (300+ instances)
8. **Profile/level by resolution** — 1080p→Main@4.0, 4K→High@5.1

## Module map

| Module | Purpose |
|---|---|
| `probe.py` | ffprobe wrapper, HDR detection, stream selection |
| `silence.py` | Energy-based silence detection → cut plan |
| `asr.py` | faster-whisper ASR with word timestamps |
| `plan.py` | Unified schema (CutPlan/EditPlan/WordsData) with legacy migration |
| `subtitle.py` | Word→SRT with remap, dw line-break, filler removal |
| `render.py` | Single-pass ffmpeg: trim+concat+scale+tonemap+subtitle |
| `color.py` | HDR detection and tonemap filter generation |
| `qc.py` | Media + subtitle quality checks |
| `verify.py` | Re-ASR verification with cached results |
| `struct_check.py` | Word coverage, overlap, cut-edge energy |
| `cover.py` | Frame extraction for covers |
| `utils/srt.py` | SRT read/write with integer-ms timestamps |
| `utils/remap.py` | Timeline remap with snap-to-nearest |
| `utils/display_width.py` | CJK display width calculation |
| `utils/resource.py` | Cross-platform memory/CPU detection |

## Skill relationship

The Claude skill at `~/.claude/skills/voiceover-video-edit/` is the thin shell.
It handles triggering, user interaction, and editorial decisions.
This package handles all computation.

## Model status

- Tested with a local faster-whisper large-v3-turbo model directory
- ASR requires `--model` (no silent download); other compatible model directories can be supplied

## Not yet done (P1 backlog)

- Cross-platform testing (macOS/Linux)
- VFR, multi-audio-track, AV1/VP9 input testing
- GPU acceleration support
- Resumable ASR for long videos
- Edit-aligned subtitle re-generation
- SKILL.md trigger description cleanup (classifier blocked)
- Original pitfalls.md npl=100→200 fix (classifier blocked, correct in package)
