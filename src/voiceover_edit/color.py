"""HDR detection and tone-mapping filter generation.

Battle-tested rules from pitfalls.md:
- tonemap ONCE after concat, never per-segment (zscale instance limit)
- hable is default; mobius better for face closeups but pushes highlights
- npl=100 caused 42.91% dead-white on HLG content; use npl=200 minimum
- always assert bt709 on output
- must pass through gbrpf32le for correct tonemap math
"""

TONEMAP_OPERATORS = {
    "hable": "tonemap=hable:desat=0",
    "mobius": "tonemap=mobius:param=0.3:desat=0",
    "reinhard": "tonemap=reinhard:desat=0",
}

DEFAULT_NPL = {"hlg": 200, "pq": 100}


def tonemap_filter(hdr_type, operator="hable", npl=None):
    """Build the full tonemap filter chain for ffmpeg filter_complex.

    Args:
        hdr_type: 'hlg' or 'pq' (from probe.is_hdr)
        operator: 'hable', 'mobius', or 'reinhard'
        npl: nominal peak luminance override (default: 200 for HLG, 100 for PQ)

    Returns:
        Filter string to insert into filter_complex.
    """
    if operator not in TONEMAP_OPERATORS:
        raise ValueError(f"Unknown tonemap operator: {operator}. Use: {list(TONEMAP_OPERATORS)}")
    if npl is None:
        npl = DEFAULT_NPL.get(hdr_type, 200)

    if hdr_type == "hlg":
        zscale_in = f"zscale=tin=arib-std-b67:pin=bt2020:t=linear:npl={npl}"
    else:
        zscale_in = f"zscale=tin=smpte2084:pin=bt2020:t=linear:npl={npl}"

    parts = [
        zscale_in,
        "format=gbrpf32le",
        TONEMAP_OPERATORS[operator],
        "zscale=p=bt709:t=bt709:m=bt709:r=tv",
        "format=yuv420p",
    ]
    return ",".join(parts)


def needs_tonemap(probe_info):
    """Check ffprobe info dict. Returns (needs: bool, hdr_type: str|None)."""
    from . import probe
    hdr_type = probe.is_hdr(probe_info)
    return hdr_type is not None, hdr_type
