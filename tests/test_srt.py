"""Tests for utils/srt.py."""
from voiceover_edit.utils.srt import ts, parse_ts, SrtEntry


def test_ts_zero():
    assert ts(0.0) == "00:00:00,000"


def test_ts_normal():
    assert ts(65.123) == "00:01:05,123"


def test_ts_carry():
    # This was a bug in the old 02b script: ms=1000 should carry to seconds
    assert ts(59.9999) == "00:01:00,000"


def test_ts_hour():
    assert ts(3661.5) == "01:01:01,500"


def test_ts_negative_clamps():
    assert ts(-1.0) == "00:00:00,000"


def test_parse_ts_roundtrip():
    for val in [0.0, 1.234, 65.5, 3661.999]:
        formatted = ts(val)
        parsed = parse_ts(formatted)
        assert abs(parsed - val) < 0.002, f"Roundtrip failed for {val}: {formatted} -> {parsed}"


def test_parse_ts_dot_separator():
    assert parse_ts("01:02:03.456") == 3723.456
