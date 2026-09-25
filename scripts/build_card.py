"""Builds the profile card SVGs (dark + light) into assets/.

The ASCII art is read from assets/ascii.txt (57 rows x 110 cols, with a
per-character color index 0-9 in assets/ascii_levels.txt) and rendered in
muted, desaturated tints: light-on-dark in dark mode, dark-on-light in light.

Run:  python scripts/build_card.py
"""
import html
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

W, H = 1060, 420
ART_X, ART_W, ART_H = 40, 333, 358
PANEL_X = 420
ICON_X = PANEL_X
LABEL_X = PANEL_X + 34
VALUE_X = 582
RIGHT = W - 30

FONT = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"


def font_face():
    """Embed JetBrains Mono so it renders anywhere (GitHub blocks web fonts in images)."""
    import base64
    css = ""
    for weight in (400, 700):
        data = base64.b64encode((ASSETS / "fonts" / f"JetBrainsMono-{weight}.woff2").read_bytes()).decode()
        css += (f"@font-face{{font-family:'JetBrains Mono';font-weight:{weight};"
                f"src:url(data:font/woff2;base64,{data}) format('woff2')}}")
    return css

THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", art="#f0f6fc", text="#e6edf3",
                 label="#4fae2c", accent="#b8ea2b", rule="#21262d", muted="#6e7681",
                 tints=["#6b7591", "#8f82ad", "#8a88b3", "#a598c2", "#8b9cc4",
                        "#9fb8d3", "#9cc0c8", "#9cc4b4", "#b5c79a", "#d6c89c"]),
    "light": dict(bg="#ffffff", border="#d0d7de", art="#1f2328", text="#1f2328",
                  label="#2f7d14", accent="#5f8a00", rule="#d8dee4", muted="#8c959f",
                  art_weight=700,
                  tints=["#5f6883", "#52487a", "#484878", "#54457f", "#3a4a78",
                         "#1f4c7a", "#125a63", "#135a40", "#3f5a12", "#6b4f06"]),
}

ICONS = {
    "term": '<rect x="0.8" y="1.5" width="10.4" height="9" rx="1.2"/><path d="M3 4.6 5.2 6.8 3 9"/><line x1="6.2" y1="9" x2="9" y2="9"/>',
    "user": '<circle cx="6" cy="4.1" r="2.3"/><path d="M1.6 11c0-2.7 1.9-4.3 4.4-4.3s4.4 1.6 4.4 4.3"/>',
    "role": '<rect x="1.3" y="4.3" width="9.4" height="6.2" rx="1"/><path d="M4.2 4.3V3.1a1 1 0 0 1 1-1h1.6a1 1 0 0 1 1 1v1.2"/><line x1="1.3" y1="7.4" x2="10.7" y2="7.4"/>',
    "code": '<path d="M4.3 3.2 1 6.9l3.3 3.7"/><path d="M7.7 3.2 11 6.9l-3.3 3.7"/>',
    "music": '<circle cx="3" cy="9.6" r="1.5"/><circle cx="8.6" cy="8.1" r="1.5"/><path d="M4.5 9.6V2.4L10.1 1.4v6.7"/>',
    "mail": '<rect x="1" y="2.8" width="10" height="7.4" rx="1"/><path d="M1.3 3.4 6 7.3l4.7-3.9"/>',
    "chat": '<rect x="1" y="2.1" width="10" height="6.6" rx="1.7"/><path d="M4 8.7v2.2l2.4-2.2"/>',
    "link": '<path d="M5 7 7 5"/><rect x="1.3" y="5.6" width="4" height="2.2" rx="1.1" transform="rotate(-45 3.3 6.7)"/><rect x="6.7" y="1.2" width="4" height="2.2" rx="1.1" transform="rotate(-45 8.7 2.3)"/>',
}

ROWS = [
    ("user", "Name:", "sai"),
    ("role", "Role:", "Data Scientist, WebDev, GameDev, UI/UX Designer"),
    ("code", "Languages:", "JavaScript, Python, CSS, React, HTML, SQL"),
    ("music", "Music:", "Producer, Mixer, Recorder, Enthusiast"),
]
CONTACT = [
    ("mail", "Email:", "carlosyminoza@gmail.com"),
    ("chat", "Discord:", "carlosss.mxn"),
    ("link", "LinkedIn:", "linkedin.com/in/cminoza-sai"),
]


def icon(name, x, y, c):
    return (f'<g transform="translate({x},{y - 12}) scale(1.4)" fill="none" stroke="{c["accent"]}" '
            f'stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>')


def art(c, data):
    """Returns (svg, css). Each glyph takes its own muted color from the photo, quantized to a small palette."""
    chars, colors = data["chars"], data["colors"]
    n = len(chars)
    pitch = ART_H / n
    fs = pitch * 0.98
    y0 = (H - ART_H) / 2
    classes = {}

    def cls(hex_):
        return classes.setdefault(hex_, f"c{len(classes)}")

    out = []
    for i, (row, row_c) in enumerate(zip(chars, colors)):
        spans, cur, buf = [], None, ""
        for ch, col in zip(row, row_c):
            if ch == " ":
                col = cur if cur is not None else col
            if col != cur and buf:
                spans.append((cur, buf)); buf = ""
            cur = col; buf += ch
        spans.append((cur, buf))
        body = "".join(
            f'<tspan class="{cls(col)}">{html.escape(t).replace(" ", "&#160;")}</tspan>' for col, t in spans)
        y = y0 + pitch * (i + 0.8)
        out.append(f'<text x="{ART_X}" y="{y:.2f}" font-size="{fs:.2f}" font-weight="{c.get("art_weight", 400)}" '
                   f'textLength="{ART_W}" xml:space="preserve">{body}</text>')
    css = "".join(f".{k}{{fill:{h}}}" for h, k in classes.items())
    return "\n".join(out), css


TITLE = "c4rlosst@github"
TITLE_W = len(TITLE) * 22 * 0.6  # monospace advance at 22px
TYPE_SECONDS = 9


def build(theme, data):
    c = THEMES[theme]
    art_svg, art_css = art(c, data[theme])
    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             f'role="img" aria-label="sai (c4rlosst) profile card" font-family="{FONT}">')
    p.append(f'<style>{font_face()}'
             + art_css +
             f'.k{{font-size:16px;font-weight:700;fill:{c["label"]}}}'
             f'.v{{font-size:15px;fill:{c["text"]}}}'
             f'.h{{font-size:22px;font-weight:700;fill:{c["accent"]}}}'
             f'.s{{font-size:17px;font-weight:700;fill:{c["accent"]}}}'
             f'.ty{{animation:tyclip {TYPE_SECONDS}s linear infinite}}'
             f'.cur{{animation:tymove {TYPE_SECONDS}s linear infinite}}'
             f'.cur rect{{animation:blink 1s steps(1) infinite}}'
             f'@keyframes tyclip{{'
             f'0%{{clip-path:inset(0 100% 0 0);animation-timing-function:steps({len(TITLE)},end)}}'
             f'25%,70%{{clip-path:inset(0 0 0 0);animation-timing-function:steps({len(TITLE)},end)}}'
             f'95%,100%{{clip-path:inset(0 100% 0 0)}}}}'
             f'@keyframes tymove{{'
             f'0%{{transform:translateX(0);animation-timing-function:steps({len(TITLE)},end)}}'
             f'25%,70%{{transform:translateX({TITLE_W:.1f}px);animation-timing-function:steps({len(TITLE)},end)}}'
             f'95%,100%{{transform:translateX(0)}}}}'
             f'@keyframes blink{{50%{{opacity:0}}}}'
             f'@media (prefers-reduced-motion:reduce){{.ty,.cur,.cur rect{{animation:none}}.cur{{display:none}}}}'
             f'</style>')
    p.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{c["bg"]}" stroke="{c["border"]}"/>')
    p.append(art_svg)

    y = 58
    p.append(icon("term", ICON_X, y, c))
    p.append(f'<text class="h ty" x="{LABEL_X}" y="{y}">{TITLE}</text>')
    p.append(f'<g class="cur"><rect x="{LABEL_X}" y="{y - 19}" width="9" height="24" fill="{c["accent"]}"/></g>')
    p.append(f'<line x1="{PANEL_X}" y1="80" x2="{RIGHT}" y2="80" stroke="{c["rule"]}"/>')

    y = 118
    for ic, k, v in ROWS:
        p.append(icon(ic, ICON_X, y, c))
        p.append(f'<text class="k" x="{LABEL_X}" y="{y}">{k}</text>')
        p.append(f'<text class="v" x="{VALUE_X}" y="{y}">{html.escape(v)}</text>')
        y += 34

    p.append(f'<line x1="{PANEL_X}" y1="{y - 12}" x2="{RIGHT}" y2="{y - 12}" stroke="{c["rule"]}"/>')
    y += 24
    p.append(f'<text class="s" x="{PANEL_X}" y="{y}">Contact</text>')
    y += 34
    for ic, k, v in CONTACT:
        p.append(icon(ic, ICON_X, y, c))
        p.append(f'<text class="k" x="{LABEL_X}" y="{y}">{k}</text>')
        p.append(f'<text class="v" x="{VALUE_X}" y="{y}">{html.escape(v)}</text>')
        y += 34
    p.append("</svg>")
    return "\n".join(p)


MARQUEE_ITEMS = ["JAVASCRIPT", "PYTHON", "CSS", "REACT", "HTML", "SQL"]
MARQUEE_H, MARQUEE_FS, MARQUEE_SECONDS = 48, 15, 40


def build_marquee(theme):
    """Scrolling ticker; pure CSS animation, which GitHub renders inside <img>."""
    c = THEMES[theme]
    adv = MARQUEE_FS * 0.6
    sep = "   ·   "
    n = 0
    seg = []
    while True:  # repeat the item list until one segment is wider than the card
        for item in MARQUEE_ITEMS:
            seg.append((item + sep, n % 2))
            n += 1
        if sum(len(t) for t, _ in seg) * adv >= W and n % 2 == 0:
            break
    chars = sum(len(t) for t, _ in seg)
    seg_w = chars * adv
    spans = "".join(f'<tspan class="m{i}">{html.escape(t)}</tspan>' for t, i in seg)
    y = MARQUEE_H / 2 + MARQUEE_FS * 0.35
    dur = MARQUEE_SECONDS * seg_w / 1100
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {MARQUEE_H}" width="{W}" height="{MARQUEE_H}" role="img" aria-label="JavaScript, Python, CSS, React, HTML, SQL" font-family="{FONT}">
<style>{font_face()}
.m0{{fill:{c["accent"]}}}.m1{{fill:{c["label"]}}}
.t{{font-size:{MARQUEE_FS}px;font-weight:700;letter-spacing:0}}
.belt{{animation:slide {dur:.1f}s linear infinite}}
@keyframes slide{{from{{transform:translateX(0)}}to{{transform:translateX(-{seg_w:.1f}px)}}}}
@media (prefers-reduced-motion:reduce){{.belt{{animation:none}}}}
</style>
<defs>
<clipPath id="r"><rect x="0.5" y="0.5" width="{W - 1}" height="{MARQUEE_H - 1}" rx="12"/></clipPath>
<linearGradient id="f" x1="0" x2="1"><stop offset="0" stop-color="{c["bg"]}"/><stop offset=".06" stop-color="{c["bg"]}" stop-opacity="0"/><stop offset=".94" stop-color="{c["bg"]}" stop-opacity="0"/><stop offset="1" stop-color="{c["bg"]}"/></linearGradient>
</defs>
<rect x="0.5" y="0.5" width="{W - 1}" height="{MARQUEE_H - 1}" rx="12" fill="{c["bg"]}"/>
<g clip-path="url(#r)">
<g class="belt">
<text class="t" x="0" y="{y:.1f}" textLength="{seg_w:.1f}" xml:space="preserve">{spans}</text>
<text class="t" x="{seg_w:.1f}" y="{y:.1f}" textLength="{seg_w:.1f}" xml:space="preserve">{spans}</text>
<text class="t" x="{2 * seg_w:.1f}" y="{y:.1f}" textLength="{seg_w:.1f}" xml:space="preserve">{spans}</text>
</g>
<rect width="{W}" height="{MARQUEE_H}" fill="url(#f)"/>
</g>
</svg>"""


def main():
    import json
    data = json.loads((ASSETS / "ascii_data.json").read_text(encoding="utf8"))
    for theme in THEMES:
        (ASSETS / f"profile-card-{theme}.svg").write_text(build(theme, data), encoding="utf8")
        print("wrote", f"profile-card-{theme}.svg")
        (ASSETS / f"marquee-{theme}.svg").write_text(build_marquee(theme), encoding="utf8")
        print("wrote", f"marquee-{theme}.svg")


if __name__ == "__main__":
    main()
