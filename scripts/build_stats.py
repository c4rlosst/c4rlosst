"""Builds assets/stats-{dark,light}.svg from the GitHub GraphQL API.

Run:  GH_TOKEN=... python scripts/build_stats.py [username]
"""
import collections
import datetime
import html
import json
import os
import pathlib
import sys
import urllib.request

from build_contributions import FONT, font_face

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
USER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GH_USER", "c4rlosst")

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

SHIFT = 48  # content is laid out on a 262px canvas, then moved up now the title row is gone
W, H = 1100, 262 - SHIFT + 12
PAD = 32
LW = W - PAD - 660  # width of the languages bar
POP_SLOT = 1.5      # seconds each tile gets in the pop cycle

THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", text="#e6edf3", muted="#8b949e", accent="#b8ea2b",
                 track="#161b22", label="#4fae2c",
                 langs=["#b8ea2b", "#4fae2c", "#79c0ff", "#9cc4b4", "#d6c89c", "#a598c2"]),
    "light": dict(bg="#ffffff", border="#d0d7de", text="#1f2328", muted="#656d76", accent="#5f8a00",
                  track="#eaeef2", label="#2f7d14",
                  langs=["#5f8a00", "#2f7d14", "#0969da", "#2f7358", "#86691f", "#66508a"]),
}


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
    return data["data"]["user"]


def streaks(cal):
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    # current streak: today may still be empty, so allow it
    cur = 0
    for d in reversed(days):
        if d["contributionCount"]:
            cur += 1
        elif d["date"] == datetime.date.today().isoformat():
            continue
        else:
            break
    return cur, longest


def summarize(u):
    cal = u["contributionsCollection"]["contributionCalendar"]
    cur, longest = streaks(cal)
    sizes = collections.Counter()
    stars = 0
    for repo in u["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        for e in repo["languages"]["edges"]:
            sizes[e["node"]["name"]] += e["size"]
    total = sum(sizes.values()) or 1
    top = [(n, s / total) for n, s in sizes.most_common(6)]
    return dict(
        tiles=[
            ("Contributions", f'{cal["totalContributions"]:,}', "last 12 months"),
            ("Commits", f'{u["contributionsCollection"]["totalCommitContributions"]:,}', "last 12 months"),
            ("Pull requests", f'{u["pullRequests"]["totalCount"]:,}', "all time"),
            ("Repositories", f'{u["repositories"]["totalCount"]:,}', "owned"),
            ("Stars earned", f"{stars:,}", "across repos"),
            ("Current streak", f"{cur}d", f"longest {longest}d"),
        ],
        langs=top,
    )


def build(theme, s):
    c = THEMES[theme]
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'role="img" aria-label="{USER} GitHub stats" font-family="{FONT}">',
         f'<style>{font_face()}'
         f'.ttl{{font-size:17px;font-weight:700;fill:{c["accent"]}}}'
         f'.lab{{font-size:12px;fill:{c["muted"]}}}'
         f'.val{{font-size:30px;font-weight:700;fill:{c["accent"]}}}'
         f'.sub{{font-size:11px;fill:{c["muted"]}}}'
         f'.ln{{font-size:13px;fill:{c["text"]}}}'
         f'.pc{{font-size:13px;fill:{c["muted"]}}}'
         f'.bar{{transform-box:fill-box;transform-origin:left center;animation:grow 1.4s cubic-bezier(.2,.7,.2,1) both}}'
         f'@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}'
         f'.tile{{animation:rise .6s cubic-bezier(.2,.7,.2,1) both}}'
         f'.val{{transform-box:fill-box;transform-origin:left center;animation:pop {POP_SLOT * 6}s ease-in-out infinite}}'
         f'@keyframes rise{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}'
         f'@keyframes pop{{0%,16%,100%{{transform:scale(1);filter:none}}'
         f'6%{{transform:scale(1.12);filter:drop-shadow(0 0 7px {c["accent"]})}}}}'
         f'.shine{{animation:shine 5s ease-in-out 2s infinite}}'
         f'@keyframes shine{{from{{transform:translateX(-90px)}}to{{transform:translateX({LW + 90}px)}}}}'
         f'@media (prefers-reduced-motion:reduce){{.bar,.tile,.val,.shine{{animation:none}}.shine{{display:none}}}}'
         f'</style>',
         f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{c["bg"]}"/>',
         f'<g transform="translate(0,-{SHIFT})">']

    # tile grid (3 columns x 2 rows)
    colw, rowh, x0, y0 = 190, 100, PAD, 92
    for i, (label, value, sub) in enumerate(s["tiles"]):
        x = x0 + (i % 3) * colw
        y = y0 + (i // 3) * rowh
        rise = 0.08 * i
        pop = 1.4 + POP_SLOT * i
        p.append(f'<g class="tile" style="animation-delay:{rise:.2f}s">')
        p.append(f'<text class="lab" x="{x}" y="{y}">{html.escape(label)}</text>')
        p.append(f'<text class="val" x="{x}" y="{y + 36}" style="animation-delay:{pop:.2f}s">{html.escape(value)}</text>')
        p.append(f'<text class="sub" x="{x}" y="{y + 56}">{html.escape(sub)}</text>')
        p.append("</g>")

    # languages
    lx, lw = 660, W - PAD - 660
    p.append(f'<text class="lab" x="{lx}" y="92">Top languages</text>')
    p.append('<linearGradient id="sh"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
             '<stop offset=".5" stop-color="#fff" stop-opacity=".45"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    p.append(f'<clipPath id="bc"><rect x="{lx}" y="104" width="{lw}" height="12" rx="6"/></clipPath>')
    p.append(f'<rect x="{lx}" y="104" width="{lw}" height="12" rx="6" fill="{c["track"]}"/>')
    p.append('<g clip-path="url(#bc)"><g class="bar">')
    x = lx
    for i, (name, frac) in enumerate(s["langs"]):
        w = lw * frac
        p.append(f'<rect x="{x:.1f}" y="104" width="{w + .5:.1f}" height="12" fill="{c["langs"][i % 6]}"/>')
        x += w
    p.append("</g>")
    p.append(f'<g class="shine"><rect x="{lx}" y="104" width="90" height="12" fill="url(#sh)"/></g></g>')
    for i, (name, frac) in enumerate(s["langs"]):
        col, row = i % 2, i // 2
        gx = lx + col * (lw / 2)
        gy = 148 + row * 34
        p.append(f'<circle cx="{gx + 5}" cy="{gy - 4}" r="5" fill="{c["langs"][i % 6]}"/>')
        p.append(f'<text class="ln" x="{gx + 18}" y="{gy}">{html.escape(name)}</text>')
        p.append(f'<text class="pc" x="{gx + lw / 2 - 16}" y="{gy}" text-anchor="end">{frac * 100:.1f}%</text>')
    p.append("</g></svg>")
    return "\n".join(p)


def main():
    s = summarize(fetch())
    ASSETS.mkdir(exist_ok=True)
    for theme in THEMES:
        (ASSETS / f"stats-{theme}.svg").write_text(build(theme, s), encoding="utf8")
        print("wrote", f"stats-{theme}.svg")
    print(s["tiles"], [(n, round(f, 3)) for n, f in s["langs"]])


if __name__ == "__main__":
    main()

