"""Tests for utils/remap.py."""
from voiceover_edit.utils.remap import locate, remap_words, build_accumulator, remap_time


def test_locate_inside_clip():
    clips = [(1.0, 3.0), (5.0, 8.0)]
    assert locate(2.0, clips) == 0
    assert locate(6.0, clips) == 1


def test_locate_snap_to_nearest():
    clips = [(1.0, 3.0), (5.0, 8.0)]
    # t=4.0 is in the gap; closer to clip 1 start (5.0) than clip 0 end (3.0)
    assert locate(4.0, clips) == 0  # 4.0-3.0=1.0 vs 5.0-4.0=1.0, tie goes to first
    assert locate(4.5, clips) == 1  # 4.5-3.0=1.5 vs 5.0-4.5=0.5


def test_locate_before_first():
    clips = [(2.0, 4.0)]
    assert locate(0.5, clips) == 0


def test_locate_after_last():
    clips = [(2.0, 4.0)]
    assert locate(10.0, clips) == 0


def test_accumulator():
    clips = [(1.0, 3.0), (5.0, 8.0)]
    acc = build_accumulator(clips)
    assert acc == [0.0, 2.0]  # first clip is 2s, second starts at offset 2s


def test_remap_time_clamp():
    clips = [(1.0, 3.0), (5.0, 8.0)]
    acc = build_accumulator(clips)
    # Inside clip 0
    assert abs(remap_time(2.0, 0, clips, acc) - 1.0) < 1e-9
    # Before clip 0 start, clamped
    assert abs(remap_time(0.5, 0, clips, acc) - 0.0) < 1e-9


def test_remap_words_basic():
    clips = [(0.0, 2.0), (4.0, 6.0)]
    words = [
        {"start": 0.5, "end": 1.0, "word": "hello"},
        {"start": 4.5, "end": 5.0, "word": "world"},
    ]
    result = remap_words(words, clips)
    assert len(result) == 2
    assert result[0]["word"] == "hello"
    assert result[0]["start"] == 0.5  # within first clip, offset 0
    assert result[1]["word"] == "world"
    assert result[1]["start"] == 2.5  # 4.5 -> acc[1]=2.0 + (4.5-4.0)=0.5


def test_remap_words_snap():
    clips = [(0.0, 2.0), (4.0, 6.0)]
    # Word midpoint 3.0 is in the gap, snaps to clip 0 (closer to 2.0)
    words = [{"start": 2.5, "end": 3.5, "word": "gap"}]
    result = remap_words(words, clips)
    assert len(result) == 1  # never drops words
    assert result[0]["source_start"] == 2.5


def test_remap_empty():
    assert remap_words([], [(0.0, 1.0)]) == []
    assert remap_words([{"start": 0, "end": 1, "word": "x"}], []) == []
