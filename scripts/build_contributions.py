"""Builds assets/contributions-{dark,light}.svg from the GitHub GraphQL API.

Needs GH_TOKEN (a token for the profile owner). Private contributions are
included in the counts when "Include private contributions on my profile" is
enabled in GitHub's profile settings and the token belongs to that account.

Run:  GH_TOKEN=... python scripts/build_contributions.py [username]
"""
import datetime
import json
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
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'role="img" aria-label="{USER} contribution graph" font-family="{FONT}">',
         f'<style>{font_face()}</style>',
         f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{c["bg"]}" stroke="{c["border"]}"/>',
         f'<text x="{PAD_X}" y="40" font-size="17" font-weight="700" fill="{c["accent"]}">Contributions</text>',
         f'<text x="{W - PAD_X}" y="40" font-size="14" text-anchor="end" fill="{c["muted"]}">'
         f'{cal["totalContributions"]:,} in the last year</text>']
    last_month = None
    for wi, week in enumerate(weeks):
        x = PAD_X + wi * STEP
        first = week["contributionDays"][0]["date"]
        month = datetime.date.fromisoformat(first).strftime("%b")
        if month != last_month and wi < len(weeks) - 2:
            p.append(f'<text x="{x}" y="{TOP - 10}" font-size="11" fill="{c["muted"]}">{month}</text>')
        last_month = month
        for d in week["contributionDays"]:
            y = TOP + datetime.date.fromisoformat(d["date"]).isoweekday() % 7 * STEP
            n = d["contributionCount"]
            p.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                     f'fill="{c["cells"][LEVELS[d["contributionLevel"]]]}"><title>{n} on {d["date"]}</title></rect>')
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


