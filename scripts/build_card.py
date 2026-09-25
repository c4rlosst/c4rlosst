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

W, H = 1100, 420
ART_X, ART_W, ART_H = 32, 400, 358
PANEL_X = 474
ICON_X = PANEL_X
LABEL_X = PANEL_X + 34
VALUE_X = 636
RIGHT = W - 30

FONT = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace"

THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", art="#f0f6fc", text="#e6edf3",
                 label="#79c0ff", accent="#56d364", rule="#21262d", muted="#6e7681",
                 tints=["#6b7591", "#8f82ad", "#8a88b3", "#a598c2", "#8b9cc4",
                        "#9fb8d3", "#9cc0c8", "#9cc4b4", "#b5c79a", "#d6c89c"]),
    "light": dict(bg="#ffffff", border="#d0d7de", art="#1f2328", text="#1f2328",
                  label="#0969da", accent="#1a7f37", rule="#d8dee4", muted="#8c959f",
                  tints=["#2b3040", "#3a3050", "#33334f", "#43385a", "#2f3a58",
                         "#4f6f92", "#5a8d96", "#5f9a82", "#8aa060", "#a88f4a"]),
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


RAMP = " .:-=+*#%@"


def art(c, ascii_rows, levels, invert=False):
    n, cols = len(ascii_rows), len(ascii_rows[0])
    pitch = ART_H / n
    fs = pitch * 0.98
    y0 = (H - ART_H) / 2
    out = []
    for i, (row, lv) in enumerate(zip(ascii_rows, levels)):
        if invert:
            row = row.translate(str.maketrans(RAMP, RAMP[::-1]))
        spans, cur, buf = [], None, ""
        for ch, l in zip(row, lv):
            if ch == " ":
                l = cur if cur is not None else l
            if l != cur and buf:
                spans.append((cur, buf)); buf = ""
            cur = l; buf += ch
        spans.append((cur, buf))
        body = "".join(
            f'<tspan class="a{l}">{html.escape(t).replace(" ", "&#160;")}</tspan>' for l, t in spans)
        y = y0 + pitch * (i + 0.8)
        out.append(f'<text x="{ART_X}" y="{y:.2f}" font-size="{fs:.2f}" textLength="{ART_W}" '
                   f'xml:space="preserve">{body}</text>')
    return "\n".join(out)


def build(theme, ascii_rows, levels):
    c = THEMES[theme]
    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             f'role="img" aria-label="sai (c4rlosst) profile card" font-family="{FONT}">')
    p.append(f'<style>'
             + "".join(f".a{i}{{fill:{t}}}" for i, t in enumerate(c["tints"])) +
             f'.k{{font-size:16px;font-weight:700;fill:{c["label"]}}}'
             f'.v{{font-size:15px;fill:{c["text"]}}}'
             f'.h{{font-size:22px;font-weight:700;fill:{c["accent"]}}}'
             f'.s{{font-size:17px;font-weight:700;fill:{c["accent"]}}}'
             f'</style>')
    p.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{c["bg"]}" stroke="{c["border"]}"/>')
    p.append(art(c, ascii_rows, levels, invert=theme == "light"))

    y = 58
    p.append(icon("term", ICON_X, y, c))
    p.append(f'<text class="h" x="{LABEL_X}" y="{y}">c4rlosst@github</text>')
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


def main():
    ascii_rows = (ASSETS / "ascii.txt").read_text(encoding="utf8").split("\n")
    levels = (ASSETS / "ascii_levels.txt").read_text(encoding="utf8").split("\n")
    ascii_rows = [r for r in ascii_rows if r != ""]
    levels = [r for r in levels if r != ""]
    assert len(ascii_rows) == len(levels)
    for theme in THEMES:
        (ASSETS / f"profile-card-{theme}.svg").write_text(build(theme, ascii_rows, levels), encoding="utf8")
        print("wrote", f"profile-card-{theme}.svg")


if __name__ == "__main__":
    main()




