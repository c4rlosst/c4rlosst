"""Builds assets/contributions-{dark,light}.svg from the GitHub GraphQL API.

Needs GH_TOKEN (a token for the profile owner). Private contributions are
included in the counts when "Include private contributions on my profile" is
enabled in GitHub's profile settings and the token belongs to that account.

Run:  GH_TOKEN=... python scripts/build_contributions.py [username]
"""
import datetime
import json
import html
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
USER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GH_USER", "c4rlosst")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
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
    "dark": dict(bg="#0d1117", border="#30363d", text="#e6edf3", muted="#8b949e", accent="#b8ea2b",
                 cells=["#161b22", "#22470f", "#38801a", "#6fbb2a", "#b8ea2b"]),
    "light": dict(bg="#ffffff", border="#d0d7de", text="#1f2328", muted="#656d76", accent="#5f8a00",
                  cells=["#ebedf0", "#d6efa3", "#a9dc4c", "#63a21e", "#2f6f0e"]),
}

CELL, GAP, PAD_X, TOP = 12, 3, 32, 78
MORPH_PERIOD = 18  # Hold the heatmap, rise into a skyline, then settle back.
STEP = CELL + GAP


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}", "User-Agent": "profile-card"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def build(theme, cal):
    c = THEMES[theme]
    weeks = cal["weeks"]
    W = PAD_X * 2 + len(weeks) * STEP - GAP
    H = TOP + 7 * STEP + 44
    # All faces keep their identity as their geometry moves between views.
    # CSS path interpolation works inside GitHub's script-free SVG images.
    styles = [font_face(),
              '.month{animation:labels 18s ease-in-out infinite}',
              '@keyframes labels{0%,22%,94%,100%{opacity:1}38%,78%{opacity:0}}']
    faces, static = [], []
    max_count = max((d['contributionCount'] for w in weeks for d in w['contributionDays']), default=0)

    def path(points):
        return 'M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in points) + ' Z'

    def project(x, y, height=0):
        # A shallow isometric camera fits the skyline into the original card.
        return (PAD_X + 36 + x * .89 - y * .38,
                TOP + 8 + x * .065 + y * .48 - height)

    def shade(color, factor):
        return '#' + ''.join(f'{round(int(color[i:i + 2], 16) * factor):02x}' for i in (1, 3, 5))

    for wi, week in enumerate(weeks):
        for day in week['contributionDays']:
            row = datetime.date.fromisoformat(day['date']).isoweekday() % 7
            x, y = wi * STEP, row * STEP
            n = day['contributionCount']
            level = LEVELS[day['contributionLevel']]
            color = c['cells'][level]
            height = 2 + 42 * (n / max_count) ** .7 if n and max_count else 1
            flat = [(PAD_X + x, TOP + y), (PAD_X + x + CELL, TOP + y),
                    (PAD_X + x + CELL, TOP + y + CELL), (PAD_X + x, TOP + y + CELL)]
            base = [project(x, y), project(x + CELL, y),
                    project(x + CELL, y + CELL), project(x, y + CELL)]
            roof = [project(x, y, height), project(x + CELL, y, height),
                    project(x + CELL, y + CELL, height), project(x, y + CELL, height)]
            title = html.escape(f"{n} contribution{'s' if n != 1 else ''} on {day['date']}")
            static.append(f'<rect x="{PAD_X + x}" y="{TOP + y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}"><title>{title}</title></rect>')
            # The wave delays each week's rise while keeping one shared loop.
            rise = 30 + wi / max(1, len(weeks) - 1) * 10
            settle = 80 + wi / max(1, len(weeks) - 1) * 10
            shapes = [
                ('left', [flat[3], flat[2], flat[2], flat[3]], [roof[3], roof[2], base[2], base[3]], shade(color, .66)),
                ('right', [flat[1], flat[2], flat[2], flat[1]], [roof[1], roof[2], base[2], base[1]], shade(color, .82)),
                ('top', flat, roof, color),
            ]
            day_faces = []
            for face, start, end, fill in shapes:
                name = f'd{wi}_{row}_{face}'
                flat_path, raised_path = path(start), path(end)
                styles.append(f"@keyframes {name}{{0%,22%,100%{{d:path('{flat_path}')}}"
                              f"{rise:.2f}%,{settle:.2f}%{{d:path('{raised_path}')}}"
                              f"96%{{d:path('{flat_path}')}}}}")
                day_faces.append(f'<path d="{flat_path}" fill="{fill}" style="animation:{name} {MORPH_PERIOD}s ease-in-out infinite"><title>{title}</title></path>')
            faces.append((x * .065 + y * .48, ''.join(day_faces)))
    styles.append('.static{display:none}@media(prefers-reduced-motion:reduce){.scene{display:none}.static{display:inline}.month{animation:none}}')
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'role="img" aria-label="{html.escape(USER, quote=True)} contribution heatmap and animated skyline" font-family="{FONT}">',
         '<desc>A year of GitHub contributions. The heatmap rises into a skyline; taller buildings indicate more contributions. Reduced motion shows the flat heatmap.</desc>',
         '<style>' + ''.join(styles) + '</style>',
         f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{c["bg"]}" stroke="{c["border"]}"/>',
         f'<text x="{PAD_X}" y="40" font-size="17" font-weight="700" fill="{c["accent"]}">Contributions</text>',
         f'<text x="{W - PAD_X}" y="40" font-size="14" text-anchor="end" fill="{c["muted"]}">'
         f'{cal["totalContributions"]:,} in the last year</text>']
    # month labels: one per month change, dropping any label that would collide with the next one
    marks, last_month = [], None
    for wi, week in enumerate(weeks):
        month = datetime.date.fromisoformat(week["contributionDays"][0]["date"]).strftime("%b")
        if month != last_month and wi < len(weeks) - 2:
            marks.append((wi, month))
        last_month = month
    marks = [m for i, m in enumerate(marks) if i + 1 == len(marks) or marks[i + 1][0] - m[0] >= 3]
    for wi, month in marks:
        p.append(f'<text class="month" x="{PAD_X + wi * STEP}" y="{TOP - 10}" font-size="11" fill="{c["muted"]}">{month}</text>')
    p.append('<g class="scene">' + ''.join(markup for _, markup in sorted(faces, key=lambda face: face[0])) + '</g>')
    p.append('<g class="static">' + ''.join(static) + '</g>')
    ly = H - 22
    lx = W - PAD_X - 5 * STEP - 30
    p.append(f'<text x="{lx - 8}" y="{ly + 10}" font-size="11" text-anchor="end" fill="{c["muted"]}">Less</text>')
    for i, col in enumerate(c["cells"]):
        p.append(f'<rect x="{lx + i * STEP}" y="{ly}" width="{CELL}" height="{CELL}" rx="2.5" fill="{col}"/>')
    p.append(f'<text x="{lx + 5 * STEP + 4}" y="{ly + 10}" font-size="11" fill="{c["muted"]}">More</text>')
    p.append("</svg>")
    return "\n".join(p)


def main():
    cal = fetch()
    ASSETS.mkdir(exist_ok=True)
    for theme in THEMES:
        (ASSETS / f"contributions-{theme}.svg").write_text(build(theme, cal), encoding="utf8")
        print("wrote", f"contributions-{theme}.svg", "-", cal["totalContributions"], "contributions")


if __name__ == "__main__":
    main()


