# Pitfalls & Lessons Learned

Battle-tested knowledge from 12+ real oral-broadcast video edits.
Organized by pipeline stage. Each entry has: symptom, root cause, fix.

## HDR / Color (highest priority)

### 1. iPhone HDR video looks washed-out when processed as SDR
- **Symptom**: Grey, low-contrast, pale skin in output
- **Cause**: iPhone defaults to HLG HDR (`color_transfer=arib-std-b67`, `bt2020`)
- **Fix**: Detect via ffprobe, apply tonemap filter before encoding

### 2. Tonemap npl value matters - HLG needs 200, not 100
- **Symptom**: 42.91% dead-white pixels
- **Cause**: `npl=100` is too low for HLG content
- **Fix**: `color.py` defaults to `npl=200` for HLG, `npl=100` for PQ

### 3. Tonemap placement: ONCE after concat, never per-segment
- **Symptom A**: OOM kill with many segments at 4K
- **Symptom B**: zscale instance exhaustion after 300+ instances
- **Fix**: Each segment only trims+scales. Tonemap runs once after concat.

### 4. Output must explicitly tag bt709
- **Symptom**: Player double-converts SDR content tagged as HDR
- **Fix**: Always add `-color_primaries bt709 -color_trc bt709 -colorspace bt709`

### 5. Must use gbrpf32le intermediate format
- **Symptom**: Banding, color shifts in tonemap output
- **Fix**: `format=gbrpf32le` before zscale+tonemap chain

## Silence Detection & Cut Points

### 6. Never use ASR word timestamps for cut points
- **Symptom**: Subtitles don't match audio (the #1 user complaint)
- **Cause**: ASR word timestamps drift 0.3-0.5s on sentence-initial words
- **Fix**: Energy-based silence detection, decoupled from ASR

### 7. Adjacent sentences must share the same silence block
- **Symptom**: Same audio plays twice in output
- **Fix**: `build_keep()` walks silence blocks sequentially

## Subtitles

### 8. Use display_width, never len(), for CJK line breaking
- **Symptom**: Bizarre line breaks with mixed CJK/Latin text
- **Fix**: `display_width()` fullwidth=1.0, halfwidth=0.5, spaces ignored

### 9. Subtitle timestamps MUST be remapped after silence removal
- **Symptom**: Subtitles progressively lag behind audio
- **Fix**: `remap_words()` maps every word through keep segments

### 10. SRT timestamp carry bug
- **Symptom**: `00:00:60,000` instead of `00:01:00,000`
- **Fix**: Integer millisecond arithmetic with divmod chain

### 11. Words in removed gaps must snap, not drop
- **Symptom**: Missing words in subtitle output
- **Fix**: Snap-to-nearest clip edge instead of returning None

### 12. PROTECTED words must not be split mid-word
- **Symptom**: "Deep" on one line, "Seek" on the next
- **Fix**: PROTECTED word list + scoring-based break points

## Encoding & Compatibility

### 13. Profile/level must match output resolution
- **Symptom**: Plays on PC, won't open on iPhone
- **Fix**: 1080p -> Main@4.0, 4K -> High@5.1

### 14. Filter complex exceeds Windows 32K command line limit
- **Symptom**: WinError 206 within 24s of launch
- **Fix**: Write filter to file, use `-filter_complex_script`

### 15. iPhone multi-track MOV: must use absolute stream index
- **Symptom**: `no decoder found for: none`
- **Fix**: `audio_stream_index()` picks best track by channel count

## Memory & Resources

### 16. ASR must be serial - no concurrent heavy jobs
- **Symptom**: mkl_malloc failure, process killed
- **Fix**: `adaptive_threads()` checks available memory

## Schema & Data Flow

### 17. Plan schema split: input vs inputs, s/e/w vs start/end/word
- **Symptom**: KeyError, empty output, silent data loss
- **Fix**: `plan.py` `from_dict()` migrates legacy formats automatically
