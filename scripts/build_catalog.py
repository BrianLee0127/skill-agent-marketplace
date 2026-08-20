#!/usr/bin/env python3
"""Rebuild README.md and docs/index.html from the plugins' skill/agent/command files."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GH = "https://github.com/BrianLee0127/skill-agent-marketplace"
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
    mp = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    cat_file = ROOT / "categories.json"
    cat_map = {}
    if cat_file.exists():
        cat_map = {k: v for k, v in json.loads(cat_file.read_text(encoding="utf-8")).items() if not k.startswith("_")}

    packages, items = [], []
    for entry in mp["plugins"]:
        pdir = ROOT / entry["source"].lstrip("./")
        packages.append({"name": entry["name"], "description": entry["description"]})
        for sk in sorted((pdir / "skills").glob("*/SKILL.md")):
            fm = frontmatter(sk)
            name = fm.get("name", sk.parent.name)
            items.append({
                "pkg": entry["name"], "kind": "skill",
                "folder": fm.get("category") or cat_map.get(name) or cat_map.get(sk.parent.name) or DEFAULT_CATEGORY,
                "name": name,
                "description": fm.get("description", ""),
                "path": str(sk.parent.relative_to(ROOT)),
            })
        for kind, folder in (("agents", "Agents"), ("commands", "Commands")):
            for f in sorted((pdir / kind).glob("*.md")):
                if f.name == "README.md":
                    continue
                fm = frontmatter(f)
                items.append({
                    "pkg": entry["name"], "kind": kind[:-1], "folder": folder,
                    "name": fm.get("name", f.stem),
                    "description": fm.get("description", ""),
                    "path": str(f.relative_to(ROOT)),
                })
    return packages, items


def build_readme(packages, items):
    lines = [
        "# Skill & Agent Marketplace",
        "",
        f"Claude Code plugin marketplace. {len(items)} items across {len(packages)} packages.",
        "",
        "Browse the catalog: https://brianlee0127.github.io/skill-agent-marketplace/",
        "",
        "## Install",
        "",
        "```",
        "/plugin marketplace add BrianLee0127/skill-agent-marketplace",
        "```",
        "",
        "Then run `/plugin` and install the package you want. Installing a package gives you everything inside it.",
        "",
        "## Adding your own skills",
        "",
        "See [CONTRIBUTING.md](CONTRIBUTING.md) for exactly where to put a new skill/agent/command and how to publish it.",
        "",
    ]
    for p in packages:
        pitems = [i for i in items if i["pkg"] == p["name"]]
        lines += [f"## Package: {p['name']}", "", p["description"], "",
                  f"Install: `/plugin` then choose **{p['name']}**", ""]
        if not pitems:
            lines += ["Nothing here yet.", ""]
            continue
        for folder in dict.fromkeys(i["folder"] for i in pitems):
            lines += [f"### {folder}", "", "| Type | Name | What it does |", "|---|---|---|"]
            for i in [x for x in pitems if x["folder"] == folder]:
                lines.append(f"| {i['kind']} | [{i['name']}]({i['path']}) | {i['description'][:170]} |")
            lines.append("")
    lines += ["## Updating (maintainer)", "", "Run `./sync.sh` to publish changes and rebuild this catalog.",
              "", "Set a skill's folder with `category: ...` in its SKILL.md frontmatter, or in `categories.json`.", ""]
    (ROOT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def build_html(packages, items):
    data = json.dumps({"packages": packages, "items": items}, ensure_ascii=False).replace("</", "<\\/")
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
  .crumbs a { color:var(--accent); text-decoration:none; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:14px; }
  .folder, .card, .pkg {
    background:var(--card); border:1px solid var(--line); border-radius:14px; padding:20px;
    color:inherit; text-decoration:none; display:block; cursor:pointer;
    transition:border-color .2s, transform .2s;
  }
  .folder:hover, .card:hover, .pkg:hover { border-color:var(--accent); transform:translateY(-2px); }
  .pkg { grid-column: 1 / -1; }
  .pkg .ico, .folder .ico { font-size:30px; }
  .pkg h3 { margin-top:10px; font-size:20px; }
  .pkg .desc { color:var(--dim); font-size:14px; margin-top:4px; }
  .pkg .inst {
    margin-top:14px; padding:10px 14px; border-radius:10px; font-size:13px;
    background:rgba(77,163,255,.1); color:var(--accent); font-family:ui-monospace,monospace;
  }
  .pkg .count { float:right; color:var(--dim); font-size:13px; }
  .folder h3 { margin-top:10px; font-size:18px; }
  .folder p { color:var(--dim); font-size:13.5px; margin-top:4px; }
  .kind {
    display:inline-block; font-size:11px; text-transform:uppercase; letter-spacing:.06em;
    padding:3px 9px; border-radius:999px; background:rgba(77,163,255,.14); color:var(--accent);
  }
  .card h3 { margin-top:10px; font-size:16.5px; }
  .card p { margin-top:6px; font-size:13.5px; color:var(--dim); }
  .none { color:var(--dim); margin-top:20px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Skill Catalog</h1>
  <p class="sub">Add the marketplace once: <code>/plugin marketplace add BrianLee0127/skill-agent-marketplace</code></p>
  <input id="q" type="search" placeholder="Search everything..." />
  <div class="crumbs" id="crumbs"></div>
  <div class="grid" id="grid"></div>
  <p class="none" id="none" style="display:none">Nothing here yet.</p>
</div>
<script>
const DATA = __DATA__;
const GH = "__GH__";
const ICONS = { "ui-design-skills": "\\uD83C\\uDFA8", "design-skills": "\\uD83C\\uDFA8", "team-toolkit": "\\uD83D\\uDEE0\\uFE0F",
  "UI & Design": "\\uD83C\\uDFA8", "Backend": "\\u2699\\uFE0F", "MCP & Tools": "\\uD83D\\uDD0C",
  "Others": "\\uD83D\\uDCC1", "Agents": "\\uD83E\\uDD16", "Commands": "\\u2328\\uFE0F" };
const FOLDER_ORDER = ["UI & Design", "Backend", "MCP & Tools", "Others", "Agents", "Commands"];
const grid = document.getElementById("grid"), crumbs = document.getElementById("crumbs"),
      none = document.getElementById("none"), q = document.getElementById("q");

function esc(s){ const d = document.createElement("span"); d.textContent = s; return d.innerHTML; }
function state(){
  const h = decodeURIComponent(location.hash.replace(/^#\\/?/, ""));
  const [p, f] = h.split("/");
  return { p: p || null, f: f || null };
}
function pkgCard(p){
  const n = DATA.items.filter(i => i.pkg === p.name).length;
  return '<a class="pkg" href="#' + encodeURIComponent(p.name) + '">' +
    '<span class="count">' + n + (n === 1 ? " item" : " items") + '</span>' +
    '<span class="ico">' + (ICONS[p.name] || "\\uD83D\\uDCE6") + "</span>" +
    "<h3>" + esc(p.name) + '</h3><p class="desc">' + esc(p.description) + "</p>" +
    '<div class="inst">Install: /plugin \\u2192 install ' + esc(p.name) + "</div></a>";
}
function folderCard(pkg, f){
  const n = DATA.items.filter(i => i.pkg === pkg && i.folder === f).length;
  return '<a class="folder" href="#' + encodeURIComponent(pkg) + "/" + encodeURIComponent(f) + '">' +
    '<span class="ico">' + (ICONS[f] || "\\uD83D\\uDCC1") + "</span><h3>" + esc(f) + "</h3><p>" +
    n + (n === 1 ? " item" : " items") + "</p></a>";
}
function card(i){
  return '<a class="card" href="' + GH + "/tree/main/" + i.path + '" target="_blank" rel="noopener">' +
    '<span class="kind">' + esc(i.kind) + "</span>" +
    "<h3>" + esc(i.name) + "</h3><p>" + esc(i.description.slice(0, 220)) + "</p></a>";
}
function render(){
  const t = q.value.trim().toLowerCase();
  let out = "", crumbHtml = "";
  if (t) {
    const hits = DATA.items.filter(i => (i.name + " " + i.description + " " + i.folder + " " + i.pkg).toLowerCase().includes(t));
    out = hits.map(card).join("");
    crumbHtml = "Search results (" + hits.length + ")";
  } else {
    const { p, f } = state();
    if (!p) {
      out = DATA.packages.map(pkgCard).join("");
    } else if (!f) {
      crumbHtml = '<a href="#">All packages</a> \\u203a ' + esc(p);
      const folders = [...new Set(DATA.items.filter(i => i.pkg === p).map(i => i.folder))]
        .sort((a, b) => (FOLDER_ORDER.indexOf(a) + 99) - (FOLDER_ORDER.indexOf(b) + 99));
      out = folders.map(fo => folderCard(p, fo)).join("");
    } else {
      crumbHtml = '<a href="#">All packages</a> \\u203a <a href="#' + encodeURIComponent(p) + '">' + esc(p) + "</a> \\u203a " + esc(f);
      out = DATA.items.filter(i => i.pkg === p && i.folder === f).map(card).join("");
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
    (ROOT / "docs/index.html").write_text(page.replace("__DATA__", data).replace("__GH__", GH), encoding="utf-8")


packages, items = collect()
build_readme(packages, items)
build_html(packages, items)
print(f"Catalog rebuilt: {len(items)} items in {len(packages)} packages")
