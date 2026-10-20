"""Render the profile card (light.svg, dark.svg).

    python3 build.py                       # redraw with today's uptime
    GH_TOKEN=... python3 build.py          # also refresh GitHub stats
    python3 build.py --portrait avatar.jpg # rebuild portrait.txt (needs Pillow)

Stdlib only, except --portrait. Without GH_TOKEN the last stats in stats.json are reused.
"""

import datetime as dt
import json
import os
import sys
import time
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
LOGIN = "miyazaki-yg"
BIRTH = dt.date(2002, 9, 15)
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

PROFILE = [
    ("Status", "●|Running (stable)"),
    ("OS", "Yash Gupta"),
    ("Uptime", None),
    ("Host", "Bangalore, IN"),
    ("Kernel", "Data Engineer @ Lokal"),
    ("Environment", "Cursor, Claude, Codex (CCC)"),
    ("Tools", "GCP, AWS, BigQuery, Docker, Git, Airflow"),
    ("Languages.Programming", "Python, SQL"),
    ("Languages.Real", "English, Hindi"),
    ("Focus", "Data Architecture, Data Pipelines, Agentic Workflows"),
    ("Interests", "Optimisation, Designing Systems"),
    ("Hobbies", "Gaming, Chess, Modding"),
]
CONTACT = [
    ("Email", "yash.gupta@getlokalapp.com"),
    ("Website", "buildwithmiyazaki.dev"),
    ("LinkedIn", "in/yashgupta7337"),
    ("Discord", "yash1509"),
]
QUOTE = [
    "// Live as brave men; and if fortune is adverse,",
    "// front its blows with brave hearts. - Horace",
]

THEMES = {
    "light": dict(bg="#f6f8fa", border="#d0d7de", key="#a371f7", val="#0d2b45", dot="#afb8c1",
                  rule="#57606a", ink="#24292f", comment="#a0aab4", ok="#3fb950", add="#1a7f37", rem="#cf222e",
                  shades=[("dots", "#24292f"), ("dither", "#24292f"), ("solid", "#24292f")]),
    "dark": dict(bg="#161b22", border="#30363d", key="#d2a8ff", val="#e6edf3", dot="#484f58",
                 rule="#8b949e", ink="#e6edf3", comment="#6e7681", ok="#3fb950", add="#3fb950", rem="#f85149",
                 shades=[("solid", "#d0d7de"), ("dither", "#8b949e"), ("solid", "#30363d")]),
}

WIDTH, HEIGHT = 1200, 800
CELL = 9                # portrait cell size, px
TEXT_X, TEXT_Y = 546, 52
LINE_H, CHARS = 30, 64  # text rows: line height and width in characters
FONT = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"


# ---------- uptime ----------

def uptime(today):
    y = today.year - BIRTH.year
    m = today.month - BIRTH.month
    d = today.day - BIRTH.day
    if d < 0:
        m -= 1
        prev = today.replace(day=1) - dt.timedelta(days=1)
        d += prev.day
    if m < 0:
        y -= 1
        m += 12
    plural = lambda n, w: f"{n} {w}" + ("" if n == 1 else "s")
    return f"{plural(y, 'year')}, {plural(m, 'month')}, {plural(d, 'day')}"


# ---------- GitHub stats ----------

def gh(path, token, body=None):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.loads(r.read() or b"null")


def fetch_stats(token):
    q = """query($login:String!){user(login:$login){
      repositories(ownerAffiliations:OWNER,first:100){nodes{nameWithOwner}}
      repositoriesContributedTo(first:100,includeUserRepositories:true,
        contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){nodes{nameWithOwner}}}}"""
    _, res = gh("/graphql", token, {"query": q, "variables": {"login": LOGIN}})
    user = res["data"]["user"]
    owned = {n["nameWithOwner"] for n in user["repositories"]["nodes"]}
    contributed = {n["nameWithOwner"] for n in user["repositoriesContributedTo"]["nodes"]}

    commits = adds = dels = 0
    for repo in sorted(owned | contributed):
        for _ in range(6):  # GitHub answers 202 while it computes the stats
            status, data = gh(f"/repos/{repo}/stats/contributors", token)
            if status == 200:
                break
            time.sleep(5)
        for c in data or []:
            if (c.get("author") or {}).get("login") == LOGIN:
                commits += c["total"]
                adds += sum(w["a"] for w in c["weeks"])
                dels += sum(w["d"] for w in c["weeks"])

    count = lambda q: gh(f"/search/issues?per_page=1&q={q}", token)[1]["total_count"]
    return dict(
        repos=len(owned), contributed=len(contributed - owned),
        prs=count(f"author:{LOGIN}+is:pr"), merged=count(f"author:{LOGIN}+is:pr+is:merged"),
        commits=commits, additions=adds, deletions=dels,
    )


def load_stats():
    path = ROOT / "stats.json"
    token = os.environ.get("GH_TOKEN")
    if token:
        stats = fetch_stats(token)
        path.write_text(json.dumps(stats, indent=2) + "\n")
        return stats
    return json.loads(path.read_text()) if path.exists() else None


# ---------- portrait ----------

def build_portrait(src):
    """Quantise the avatar to a grid of 0 (empty) .. 3 (solid) and save portrait.txt."""
    from PIL import Image, ImageOps

    im = ImageOps.autocontrast(Image.open(src).convert("L"), cutoff=1)
    w, h = im.size
    cols, rows = 56, 74
    crop_w = int(h * cols / rows)
    left = (w - crop_w) // 2 + 4
    im = im.crop((left, 0, left + crop_w, h))

    # the flat backdrop: flood fill from the border, so the white face and hair stay
    bg = Image.new("L", im.size, 0)
    seen, stack = set(), [(x, y) for x in range(im.width) for y in (0, im.height - 1)]
    stack += [(x, y) for y in range(im.height) for x in (0, im.width - 1)]
    ref = im.getpixel((2, 2))
    while stack:
        p = stack.pop()
        if p in seen or not (0 <= p[0] < im.width and 0 <= p[1] < im.height):
            continue
        seen.add(p)
        if abs(im.getpixel(p) - ref) <= 10:
            bg.putpixel(p, 255)
            x, y = p
            stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]

    lum = im.resize((cols, rows), Image.Resampling.BOX)
    back = bg.resize((cols, rows), Image.Resampling.BOX)
    out = []
    for y in range(rows):
        row = ""
        for x in range(cols):
            v, b = lum.getpixel((x, y)), back.getpixel((x, y))
            if b > 150:
                row += "0"
            elif v < 70:
                row += "3"
            elif v < 170:
                row += "2"
            else:
                row += "1"
        out.append(row)
    (ROOT / "portrait.txt").write_text("\n".join(out) + "\n")


def patterns(t):
    out = []
    for i, (kind, c) in enumerate(t["shades"]):
        if kind == "dots":
            out.append(f'<pattern id="s{i + 1}" width="4" height="4" patternUnits="userSpaceOnUse">'
                       f'<rect width="1.4" height="1.4" fill="{c}" opacity=".55"/>'
                       f'<rect x="2" y="2" width="1.4" height="1.4" fill="{c}" opacity=".55"/></pattern>')
        elif kind == "dither":
            out.append(f'<pattern id="s{i + 1}" width="3" height="3" patternUnits="userSpaceOnUse">'
                       f'<rect width="3" height="3" fill="{c}" opacity=".35"/><rect width="1.5" height="1.5" fill="{c}"/>'
                       f'<rect x="1.5" y="1.5" width="1.5" height="1.5" fill="{c}"/></pattern>')
    return "\n".join(out)


def portrait_svg(t):
    rows = (ROOT / "portrait.txt").read_text().split()
    top = (HEIGHT - len(rows) * CELL) // 2 + 10
    left = 30
    fill = {str(i + 1): c if kind == "solid" else f"url(#s{i + 1})" for i, (kind, c) in enumerate(t["shades"])}
    parts = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):  # merge runs of the same shade into one bar
            end = x
            while end < len(row) and row[end] == row[x]:
                end += 1
            if row[x] != "0":
                parts.append(f'<rect x="{left + x * CELL}" y="{top + y * CELL}" '
                             f'width="{(end - x) * CELL}" height="{CELL - 1}" fill="{fill[row[x]]}"/>')
            x = end
    return "\n".join(parts)


# ---------- text ----------

def span(text, color):
    return f'<tspan fill="{color}">{escape(text)}</tspan>'


def kv(key, value, t, value_spans=None, value_len=None):
    """'. Key: ..... value' padded to CHARS wide."""
    head = f". {key}: "
    vlen = value_len if value_len is not None else len(value)
    dots = "." * max(1, CHARS - len(head) - vlen - 1)
    k = span(". ", t["dot"]) + span(".", t["ink"]).join(span(p, t["key"]) for p in key.split(".")) + span(": ", t["ink"])
    return k + span(dots + " ", t["dot"]) + (value_spans or span(value, t["val"]))


def half(key, value, width, t):
    head = f"{key}: "
    dots = "." * max(1, width - len(head) - len(value) - 1)
    return span(key, t["key"]) + span(": ", t["ink"]) + span(dots + " ", t["dot"]) + span(value, t["val"])


def heading(title, t):
    lead = f"- {title} " if title != "github@" + LOGIN else f"{title} "
    return span(lead, t["ink"]) + span("─" * (CHARS - len(lead) - 3) + "-—-", t["rule"])


def lines(t, today, stats):
    out = [heading("github@" + LOGIN, t)]
    for key, value in PROFILE:
        if key == "Uptime":
            value = uptime(today)
        if value.startswith("●|"):
            text = value[2:]
            out.append(kv(key, text, t, span("● ", t["ok"]) + span(text, t["val"]), len(text) + 2))
        else:
            out.append(kv(key, value, t))
    out.append(heading("Contact", t))
    out += [kv(k, v, t) for k, v in CONTACT]
    if stats:
        out.append(heading("GitHub Stats", t))
        left = 29
        repos = f"{stats['repos']} {{Contributed: {stats['contributed']}}}"
        out.append(span(". ", t["dot"]) + half("Repos", repos, left, t) + span(" | ", t["ink"])
                   + half("PRs", f"{stats['prs']}", CHARS - left - 5, t))
        out.append(span(". ", t["dot"]) + half("Commits", f"{stats['commits']:,}", left, t) + span(" | ", t["ink"])
                   + half("Merged PRs", f"{stats['merged']}", CHARS - left - 5, t))
        net = f"{stats['additions'] - stats['deletions']:,}"
        add, rem = f"{stats['additions']:,}++", f"{stats['deletions']:,}--"
        vlen = len(net) + len(add) + len(rem) + 7
        out.append(kv("Lines of Code", "", t, span(net + " ( ", t["val"]) + span(add, t["add"])
                      + span(", ", t["val"]) + span(rem, t["rem"]) + span(" )", t["val"]), vlen))
    out.append(span(" " * 3 + "─" * (CHARS - 6) + "-—-", t["rule"]))
    out += [span(q.rjust(CHARS), t["comment"]) for q in QUOTE]
    return out


def render(theme, today, stats):
    t = THEMES[theme]
    rows = lines(t, today, stats)
    text = "\n".join(f'<text x="{TEXT_X}" y="{TEXT_Y + i * LINE_H}">{r}</text>' for i, r in enumerate(rows))
    height = max(HEIGHT, TEXT_Y + len(rows) * LINE_H)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" font-family="{FONT}" font-size="16px">
<defs>
{patterns(t)}
</defs>
<style>text {{ white-space: pre; }}</style>
<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="12" fill="{t['bg']}" stroke="{t['border']}"/>
{portrait_svg(t)}
{text}
</svg>
"""


def main():
    if "--portrait" in sys.argv:
        build_portrait(sys.argv[sys.argv.index("--portrait") + 1])
    today = dt.datetime.now(IST).date()
    stats = load_stats()
    for theme in THEMES:
        (ROOT / f"{theme}.svg").write_text(render(theme, today, stats))


if __name__ == "__main__":
    main()
