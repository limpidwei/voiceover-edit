"""Tests for utils/display_width.py."""
from voiceover_edit.utils.display_width import display_width


def test_pure_cjk():
    assert display_width("你好") == 2.0  # two CJK chars


def test_pure_ascii():
    assert display_width("hello") == 2.5  # 5 half-width chars


def test_mixed():
    assert display_width("你好world") == 4.5  # 2 + 2.5


def test_spaces_ignored():
    assert display_width("你 好") == 2.0


def test_empty():
    assert display_width("") == 0.0


def test_fullwidth_latin():
    assert display_width("Ａ") == 1.0  # fullwidth A
