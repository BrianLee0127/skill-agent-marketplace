#!/usr/bin/env python3
"""Rebuild README.md and docs/index.html from the plugins' skill/agent/command files."""
import json, html, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GH = "https://github.com/BrianLee0127/skill-agent-marketplace"


def frontmatter(path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def collect():
    mp = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    plugins = []
    for entry in mp["plugins"]:
        pdir = ROOT / entry["source"].lstrip("./")
        skills = []
        for sk in sorted((pdir / "skills").glob("*/SKILL.md")):
            fm = frontmatter(sk)
            skills.append({
                "name": fm.get("name", sk.parent.name),
                "description": fm.get("description", ""),
                "path": str(sk.parent.relative_to(ROOT)),
            })
        extras = []
        for kind in ("agents", "commands"):
            for f in sorted((pdir / kind).glob("*.md")):
                if f.name == "README.md":
                    continue
                fm = frontmatter(f)
                extras.append({
                    "kind": kind[:-1],
                    "name": fm.get("name", f.stem),
                    "description": fm.get("description", ""),
                    "path": str(f.relative_to(ROOT)),
                })
        plugins.append({**entry, "skills": skills, "extras": extras})
    return plugins


def build_readme(plugins):
    total = sum(len(p["skills"]) + len(p["extras"]) for p in plugins)
    lines = [
        "# Skill & Agent Marketplace",
        "",
        f"Claude Code plugin marketplace. {total} items across {len(plugins)} plugins.",
        "",
        "Browse the catalog: https://brianlee0127.github.io/skill-agent-marketplace/",
        "",
        "## Install",
        "",
        "```",
        "/plugin marketplace add BrianLee0127/skill-agent-marketplace",
        "```",
        "",
        "Then run `/plugin` and install the plugin you want.",
        "",
    ]
    for p in plugins:
        lines += [f"## Plugin: {p['name']}", "", p["description"], ""]
        if p["skills"]:
            lines += ["| Skill | What it does |", "|---|---|"]
            for s in p["skills"]:
                desc = s["description"][:180]
                lines.append(f"| [{s['name']}]({s['path']}) | {desc} |")
            lines.append("")
        if p["extras"]:
            lines += ["| Type | Name | What it does |", "|---|---|---|"]
            for e in p["extras"]:
                lines.append(f"| {e['kind']} | [{e['name']}]({e['path']}) | {e['description'][:180]} |")
            lines.append("")
        if not p["skills"] and not p["extras"]:
            lines += ["Nothing here yet.", ""]
    lines += ["## Updating (maintainer)", "", "Run `./sync.sh` to publish skill changes and rebuild this catalog.", ""]
    (ROOT / "README.md").write_text("\n".join(lines))


def build_html(plugins):
    cards = []
    for p in plugins:
        items = ([{**s, "kind": "skill"} for s in p["skills"]] + p["extras"])
        for it in items:
            cards.append(
                '<a class="card" data-text="{search}" href="{gh}/tree/main/{path}" target="_blank" rel="noopener">'
                '<span class="kind">{kind}</span><span class="plug">{plug}</span>'
                "<h3>{name}</h3><p>{desc}</p></a>".format(
                    search=html.escape((it["name"] + " " + it["description"] + " " + p["name"]).lower(), quote=True),
                    gh=GH, path=it["path"], kind=it["kind"], plug=p["name"],
                    name=html.escape(it["name"]), desc=html.escape(it["description"][:220]),
                )
            )
    page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Skill Catalog</title>
<style>
  :root { --bg:#101214; --card:#191d21; --line:#2a3037; --text:#e8eaed; --dim:#9aa3ad; --accent:#4da3ff; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:system-ui,-apple-system,sans-serif; line-height:1.5; }
  .wrap { max-width:1100px; margin:0 auto; padding:40px 20px 80px; }
  h1 { font-size:clamp(26px,4vw,38px); letter-spacing:-0.02em; }
  .sub { color:var(--dim); margin-top:6px; }
  input {
    width:100%; margin:26px 0 30px; padding:14px 18px; font-size:16px;
    background:var(--card); border:1px solid var(--line); border-radius:12px; color:var(--text); outline:none;
  }
  input:focus { border-color:var(--accent); }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(290px,1fr)); gap:14px; }
  .card {
    display:block; background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:18px; color:inherit; text-decoration:none; transition:border-color .2s, transform .2s;
  }
  .card:hover { border-color:var(--accent); transform:translateY(-2px); }
  .kind, .plug {
    display:inline-block; font-size:11px; text-transform:uppercase; letter-spacing:.06em;
    padding:3px 9px; border-radius:999px; margin-right:6px;
  }
  .kind { background:rgba(77,163,255,.14); color:var(--accent); }
  .plug { background:rgba(255,255,255,.06); color:var(--dim); }
  h3 { margin-top:10px; font-size:17px; }
  .card p { margin-top:6px; font-size:13.5px; color:var(--dim); }
  .none { color:var(--dim); display:none; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Skill Catalog</h1>
  <p class="sub">Click any card to view it on GitHub. Install via <code>/plugin marketplace add BrianLee0127/skill-agent-marketplace</code></p>
  <input id="q" type="search" placeholder="Search skills..." />
  <div class="grid" id="grid">__CARDS__</div>
  <p class="none" id="none">No match found.</p>
</div>
<script>
  const q = document.getElementById("q"), cards = [...document.querySelectorAll(".card")];
  q.addEventListener("input", () => {
    const t = q.value.trim().toLowerCase();
    let shown = 0;
    cards.forEach(c => { const hit = !t || c.dataset.text.includes(t); c.style.display = hit ? "" : "none"; if (hit) shown++; });
    document.getElementById("none").style.display = shown ? "none" : "block";
  });
</script>
</body>
</html>
"""
    (ROOT / "docs/index.html").write_text(page.replace("__CARDS__", "\n".join(cards)))


plugins = collect()
build_readme(plugins)
build_html(plugins)
print(f"Catalog rebuilt: {sum(len(p['skills']) + len(p['extras']) for p in plugins)} items")
