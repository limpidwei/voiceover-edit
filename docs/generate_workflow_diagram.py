"""Regenerate the Chinese and English pipeline diagrams using only the standard library."""
from html import escape
from pathlib import Path


NODE_LAYOUT = [
    (30, 110, "probe", "#4361ee", False),
    (280, 110, "silence", "#3a0ca3", False),
    (530, 110, "asr", "#7209b7", False),
    (780, 110, "plan", "#f72585", False),
    (30, 270, "subtitle", "#4cc9f0", False),
    (280, 270, "color", "#e76f51", False),
    (530, 270, "render", "#06d6a0", False),
    (780, 270, "qc", "#ffd166", True),
    (30, 430, "cover", "#118ab2", False),
    (280, 430, "verify", "#ef476f", False),
    (530, 430, "struct-check", "#fca311", True),
]

COPY = {
    "zh": {
        "title": "voiceover-edit 工作流管线",
        "subtitle": "从素材到可发布成品的完整工作流",
        "stages": ("① 理解素材", "② 生成成片", "③ 验证交付"),
        "nodes": {
            "probe": ("素材探测", "probe"),
            "silence": ("静音检测", "silence"),
            "asr": ("语音识别", "asr"),
            "plan": ("剪辑计划", "plan"),
            "subtitle": ("字幕生成", "subtitle + remap"),
            "color": ("HDR 色彩映射", "color (tonemap)"),
            "render": ("单代渲染", "render"),
            "qc": ("质量检查", "qc"),
            "cover": ("封面制作", "cover"),
            "verify": ("字幕回归验证", "verify"),
            "struct-check": ("结构检查", "struct-check"),
        },
        "feedback": "验证不通过 → 回到对应阶段修复",
        "output": "交付物",
        "artifacts": "成片 MP4 + SRT 字幕 + 封面",
        "review": "自动检查后，再由人工观看验收",
        "principles_title": "核心原则",
        "principles": "音频能量定切点 · 显示宽度定断行 · 整数毫秒定时间 · 自动检查与人工验收分层",
        "history": "12+ 真实项目复盘 → 17 个陷阱 → 11 项核心修复 → 自动化回归测试",
    },
    "en": {
        "title": "voiceover-edit Pipeline",
        "subtitle": "From raw footage to publishable deliverables",
        "stages": ("1. Understand inputs", "2. Build the video", "3. Verify and deliver"),
        "nodes": {
            "probe": ("Probe media", "probe"),
            "silence": ("Detect silences", "silence"),
            "asr": ("Transcribe speech", "asr"),
            "plan": ("Build edit plan", "plan"),
            "subtitle": ("Generate subtitles", "subtitle + remap"),
            "color": ("Map HDR color", "color (tonemap)"),
            "render": ("Render once", "render"),
            "qc": ("Check quality", "qc"),
            "cover": ("Extract cover", "cover"),
            "verify": ("Verify subtitles", "verify"),
            "struct-check": ("Check structure", "struct-check"),
        },
        "feedback": "Failed checks → return to the relevant stage",
        "output": "Deliverables",
        "artifacts": "Video MP4 + SRT subtitles + cover",
        "review": "Automated checks + human review",
        "principles_title": "Core principles",
        "principles": "Cut by audio energy · Break lines by display width · Use integer milliseconds · Keep human review",
        "history": "12+ real projects → 17 pitfalls → 11 core fixes → Automated regression tests",
    },
}

ARROWS = [
    '<line x1="230" y1="150" x2="278" y2="150"/>',
    '<line x1="480" y1="150" x2="528" y2="150"/>',
    '<line x1="730" y1="150" x2="778" y2="150"/>',
    '<path d="M 880 190 Q 880 230 550 230 Q 220 230 130 268"/>',
    '<line x1="230" y1="310" x2="278" y2="310"/>',
    '<line x1="480" y1="310" x2="528" y2="310"/>',
    '<line x1="730" y1="310" x2="778" y2="310"/>',
    '<path d="M 850 350 Q 850 390 600 390 Q 480 390 430 428"/>',
    '<path d="M 900 350 Q 900 400 750 400 Q 680 400 660 428"/>',
    '<path d="M 580 350 Q 400 390 180 428" stroke-dasharray="6,4"/>',
]


def text(x, y, value, size=12, color="#555", weight="normal"):
    return (
        f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" '
        f'fill="{color}" font-weight="{weight}">{escape(value)}</text>'
    )


def build_svg(language):
    copy = COPY[language]
    stage_one, stage_two, stage_three = copy["stages"]
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 750" '
        'font-family="Segoe UI,Microsoft YaHei,sans-serif">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="7" refX="9" '
        'refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill="#555"/>'
        '</marker></defs>',
        '<rect width="1100" height="750" fill="#fafafa" rx="8"/>',
        text(550, 45, copy["title"], 24, "#1a1a2e", "bold"),
        text(550, 70, copy["subtitle"], 14, "#777"),
        text(130, 95, stage_one, 12, "#777"),
        text(630, 255, stage_two, 12, "#777"),
        text(550, 415, stage_three, 12, "#777"),
    ]

    for x, y, key, color, dark in NODE_LAYOUT:
        title, command = copy["nodes"][key]
        parts.append(f'<rect x="{x}" y="{y}" width="200" height="80" rx="12" fill="{color}"/>')
        parts.append(text(x + 100, y + 35, title, 14 if language == "en" else 15, "#333" if dark else "white", "bold"))
        parts.append(text(x + 100, y + 59, command, 12, "#555" if dark else "#ffffffdd"))

    parts.extend(f'<g stroke="#555" stroke-width="2" fill="none" marker-end="url(#arrow)">{arrow}</g>' for arrow in ARROWS)
    parts.extend([
        '<path d="M 380 510 Q 380 560 200 560 Q 50 560 50 350 Q 50 230 80 192" '
        'stroke="#ef476f" stroke-width="2" fill="none" marker-end="url(#arrow)" stroke-dasharray="8,4"/>',
        text(310, 585, copy["feedback"], 12, "#ef476f"),
        '<rect x="780" y="430" width="260" height="80" rx="12" fill="white" stroke="#06d6a0" stroke-width="2.5"/>',
        text(910, 458, copy["output"], 14, "#059669", "bold"),
        text(910, 480, copy["artifacts"], 11),
        text(910, 498, copy["review"], 11),
        '<line x1="730" y1="470" x2="778" y2="470" stroke="#06d6a0" stroke-width="2" marker-end="url(#arrow)"/>',
        '<path d="M 480 500 Q 510 540 570 550 L 780 550 Q 850 550 850 512" '
        'stroke="#06d6a0" stroke-width="2" fill="none" marker-end="url(#arrow)"/>',
        '<rect x="80" y="610" width="940" height="55" rx="10" fill="#f0f0f0" stroke="#ddd"/>',
        text(550, 633, copy["principles_title"], 13, "#444", "bold"),
        text(550, 654, copy["principles"], 12, "#666"),
        '<rect x="80" y="680" width="940" height="25" rx="4" fill="#e8e8e8"/>',
        text(550, 698, copy["history"], 11),
        '</svg>',
    ])
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    for language, filename in (("zh", "workflow_pipeline.svg"), ("en", "workflow_pipeline.en.svg")):
        output = Path(__file__).with_name(filename)
        output.write_text(build_svg(language), encoding="utf-8")
        print(f"Saved: {output}")
