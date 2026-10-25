"""Tests for HDR/color utilities."""
from voiceover_edit.color import tonemap_filter, TONEMAP_OPERATORS, DEFAULT_NPL


def test_hlg_produces_chain():
    chain = tonemap_filter("hlg")
    assert "tonemap=hable" in chain
    assert "bt709" in chain
    assert "yuv420p" in chain
    assert "gbrpf32le" in chain
    assert "arib-std-b67" in chain


def test_pq_produces_chain():
    chain = tonemap_filter("pq")
    assert "tonemap=hable" in chain
    assert "smpte2084" in chain


def test_mobius_operator():
    chain = tonemap_filter("hlg", operator="mobius")
    assert "tonemap=mobius" in chain


def test_custom_npl():
    chain = tonemap_filter("hlg", npl=300)
    assert "npl=300" in chain


def test_default_npl_hlg():
    assert DEFAULT_NPL["hlg"] == 200


def test_all_operators_valid():
    for op in TONEMAP_OPERATORS:
        chain = tonemap_filter("hlg", operator=op)
        assert "tonemap=" in chain
