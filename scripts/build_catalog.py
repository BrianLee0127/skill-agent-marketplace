#!/usr/bin/env python3
"""Rebuild README.md and docs/index.html from the plugins' skill/agent/command files."""
import json, html, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GH = "https://github.com/BrianLee0127/skill-agent-marketplace"
GROUPS = {"design-skills": "External tools", "team-toolkit": "My own"}
DEFAULT_CATEGORY = "Others"


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
    cat_map = {}
    cat_file = ROOT / "categories.json"
    if cat_file.exists():
        cat_map = {k: v for k, v in json.loads(cat_file.read_text()).items() if not k.startswith("_")}

    items = []
    for entry in mp["plugins"]:
        pdir = ROOT / entry["source"].lstrip("./")
        group = GROUPS.get(entry["name"], "My own")
        for sk in sorted((pdir / "skills").glob("*/SKILL.md")):
            fm = frontmatter(sk)
            name = fm.get("name", sk.parent.name)
            items.append({
                "group": group, "plugin": entry["name"], "kind": "skill",
                "category": fm.get("category") or cat_map.get(name) or cat_map.get(sk.parent.name) or DEFAULT_CATEGORY,
                "name": name,
                "description": fm.get("description", ""),
                "path": str(sk.parent.relative_to(ROOT)),
            })
        for kind in ("agents", "commands"):
            for f in sorted((pdir / kind).glob("*.md")):
                if f.name == "README.md":
                    continue
                fm = frontmatter(f)
                name = fm.get("name", f.stem)
                items.append({
                    "group": group, "plugin": entry["name"], "kind": kind[:-1],
                    "category": fm.get("category") or cat_map.get(name) or DEFAULT_CATEGORY,
                    "name": name,
                    "description": fm.get("description", ""),
                    "path": str(f.relative_to(ROOT)),
                })
    return mp, items


def build_readme(mp, items):
    lines = [
        "# Skill & Agent Marketplace",
        "",
        f"Claude Code plugin marketplace. {len(items)} items.",
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
    for group in dict.fromkeys(i["group"] for i in items):
        lines += [f"## {group}", ""]
        gitems = [i for i in items if i["group"] == group]
        for cat in sorted(dict.fromkeys(i["category"] for i in gitems)):
            lines += [f"### {cat}", "", "| Type | Name | What it does |", "|---|---|---|"]
            for i in [x for x in gitems if x["category"] == cat]:
                lines.append(f"| {i['kind']} | [{i['name']}]({i['path']}) | {i['description'][:170]} |")
            lines.append("")
    lines += ["## Updating (maintainer)", "", "Run `./sync.sh` to publish changes and rebuild this catalog.",
              "", "Set a skill's category with `category: ...` in its SKILL.md frontmatter, or in `categories.json`.", ""]
    (ROOT / "README.md").write_text("\n".join(lines))


def build_html(items):
    data = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
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
  .sub { color:var(--dim); margin-top:6px; font-size:14px; }
  code { background:var(--card); padding:2px 7px; border-radius:6px; font-size:13px; }
  input {
    width:100%; margin:24px 0 20px; padding:14px 18px; font-size:16px;
    background:var(--card); border:1px solid var(--line); border-radius:12px; color:var(--text); outline:none;
  }
  input:focus { border-color:var(--accent); }
  .crumbs { margin-bottom:18px; font-size:14px; color:var(--dim); min-height:20px; }
  .crumbs a { color:var(--accent); text-decoration:none; cursor:pointer; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:14px; }
  .folder, .card {
    background:var(--card); border:1px solid var(--line); border-radius:14px; padding:20px;
    color:inherit; text-decoration:none; display:block; cursor:pointer;
    transition:border-color .2s, transform .2s;
  }
  .folder:hover, .card:hover { border-color:var(--accent); transform:translateY(-2px); }
  .folder .ico { font-size:30px; }
  .folder h3 { margin-top:10px; font-size:18px; }
  .folder p { color:var(--dim); font-size:13.5px; margin-top:4px; }
  .kind, .plug {
    display:inline-block; font-size:11px; text-transform:uppercase; letter-spacing:.06em;
    padding:3px 9px; border-radius:999px; margin-right:6px;
  }
  .kind { background:rgba(77,163,255,.14); color:var(--accent); }
  .plug { background:rgba(255,255,255,.06); color:var(--dim); }
  .card h3 { margin-top:10px; font-size:16.5px; }
  .card p { margin-top:6px; font-size:13.5px; color:var(--dim); }
  .none { color:var(--dim); margin-top:20px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Skill Catalog</h1>
  <p class="sub">Install via <code>/plugin marketplace add BrianLee0127/skill-agent-marketplace</code></p>
  <input id="q" type="search" placeholder="Search all skills..." />
  <div class="crumbs" id="crumbs"></div>
  <div class="grid" id="grid"></div>
  <p class="none" id="none" style="display:none">Nothing here yet.</p>
</div>
<script>
const DATA = __DATA__;
const GH = "__GH__";
const ICONS = { "External tools": "\\uD83D\\uDCE6", "My own": "\\uD83D\\uDEE0\\uFE0F",
  "UI & Design": "\\uD83C\\uDFA8", "Backend": "\\u2699\\uFE0F", "MCP & Tools": "\\uD83D\\uDD0C", "Others": "\\uD83D\\uDCC1" };
const CAT_ORDER = ["UI & Design", "Backend", "MCP & Tools", "Others"];
const GROUP_LIST = ["External tools", "My own"];
const grid = document.getElementById("grid"), crumbs = document.getElementById("crumbs"),
      none = document.getElementById("none"), q = document.getElementById("q");

function esc(s){ const d = document.createElement("span"); d.textContent = s; return d.innerHTML; }
function state(){
  const h = decodeURIComponent(location.hash.replace(/^#\\/?/, ""));
  const [g, c] = h.split("/");
  return { g: g || null, c: c || null };
}
function folder(icon, title, sub, href){
  return '<a class="folder" href="' + href + '"><span class="ico">' + icon + "</span><h3>" +
    esc(title) + "</h3><p>" + esc(sub) + "</p></a>";
}
function card(i){
  return '<a class="card" href="' + GH + "/tree/main/" + i.path + '" target="_blank" rel="noopener">' +
    '<span class="kind">' + esc(i.kind) + '</span><span class="plug">' + esc(i.plugin) + "</span>" +
    "<h3>" + esc(i.name) + "</h3><p>" + esc(i.description.slice(0, 220)) + "</p></a>";
}
function render(){
  const t = q.value.trim().toLowerCase();
  let out = "", crumbHtml = "";
  if (t) {
    const hits = DATA.filter(i => (i.name + " " + i.description + " " + i.category + " " + i.plugin).toLowerCase().includes(t));
    out = hits.map(card).join("");
    crumbHtml = 'Search results (' + hits.length + ') \\u00b7 <a href="#" onclick="q.value=\\'\\';render();return false;">clear</a>';
  } else {
    const { g, c } = state();
    if (!g) {
      const groups = [...new Set([...GROUP_LIST, ...DATA.map(i => i.group)])];
      out = groups.map(gr => {
        const n = DATA.filter(i => i.group === gr).length;
        return folder(ICONS[gr] || "\\uD83D\\uDCC1", gr, n + " items", "#" + encodeURIComponent(gr));
      }).join("");
    } else if (!c) {
      crumbHtml = '<a href="#">All</a> \\u203a ' + esc(g);
      const cats = [...new Set(DATA.filter(i => i.group === g).map(i => i.category))]
        .sort((a, b) => (CAT_ORDER.indexOf(a) + 99) - (CAT_ORDER.indexOf(b) + 99));
      out = cats.map(cat => {
        const n = DATA.filter(i => i.group === g && i.category === cat).length;
        return folder(ICONS[cat] || "\\uD83D\\uDCC1", cat, n + " items", "#" + encodeURIComponent(g) + "/" + encodeURIComponent(cat));
      }).join("");
    } else {
      crumbHtml = '<a href="#">All</a> \\u203a <a href="#' + encodeURIComponent(g) + '">' + esc(g) + "</a> \\u203a " + esc(c);
      out = DATA.filter(i => i.group === g && i.category === c).map(card).join("");
    }
  }
  grid.innerHTML = out;
  crumbs.innerHTML = crumbHtml;
  none.style.display = out ? "none" : "block";
}
window.addEventListener("hashchange", render);
q.addEventListener("input", render);
render();
</script>
</body>
</html>
"""
    (ROOT / "docs/index.html").write_text(page.replace("__DATA__", data).replace("__GH__", GH))


mp, items = collect()
build_readme(mp, items)
build_html(items)
print(f"Catalog rebuilt: {len(items)} items")
