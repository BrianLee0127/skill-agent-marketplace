# How to add skills, agents & commands

This repo is a Claude Code **plugin marketplace**. This guide shows exactly where to put new
things and how to publish them. (This file is safe to edit — it is **not** auto-generated.)

## Folder layout

```
skill-agent-marketplace/
├── .claude-plugin/marketplace.json   ← the catalog: lists which plugins exist
├── design-skills/                    ← a PLUGIN (the downloaded design pack)
│   ├── .claude-plugin/plugin.json    ← plugin name + version
│   └── skills/<skill-name>/SKILL.md  ← one folder per skill
├── team-toolkit/                     ← a PLUGIN for your own creations
│   ├── .claude-plugin/plugin.json
│   ├── skills/<skill-name>/SKILL.md  ← your skills go here
│   ├── agents/<agent-name>.md        ← your agents go here
│   └── commands/<command-name>.md    ← your slash commands go here
├── categories.json                   ← maps a skill → a catalog folder (UI only)
├── sync.sh                           ← publishes changes (see "Publishing")
└── scripts/build_catalog.py          ← regenerates README + the web catalog
```

> **Golden rule:** a plugin must contain at least one real skill/agent/command. An **empty
> plugin breaks the whole marketplace load** — that's the bug that once made it "unable to use."
> Don't list a plugin in `marketplace.json` until it has content.

## Add a new SKILL

1. Create a folder: `team-toolkit/skills/<your-skill-name>/`
2. Inside it, create `SKILL.md` starting with this frontmatter:
   ```markdown
   ---
   name: your-skill-name
   description: One line explaining WHEN Claude should use this skill.
   category: UI & Design        # optional — which catalog folder (see categories below)
   ---

   # Your Skill Title

   The full instructions Claude should follow when this skill is invoked...
   ```
   - `name` must match the folder name (kebab-case).
   - `description` is what Claude reads to decide when to use it — make it specific.
3. (Optional) Put a **category** in the frontmatter so it files into the right catalog folder:
   `UI & Design`, `Backend`, `MCP & Tools`, or `Others`. No category = "Others".
4. Publish (see below).

## Add a new AGENT

Create `team-toolkit/agents/<agent-name>.md`:
```markdown
---
name: my-agent
description: What this agent specializes in.
tools: ["*"]        # or a specific list
---

System prompt / instructions for the agent...
```
Do **not** leave a stray `README.md` in `agents/` — Claude Code tries to load every `.md` there
as an agent, and a non-agent file will break loading. Use `.gitkeep` for empty folders.

## Add a new COMMAND (slash command)

Create `team-toolkit/commands/<command-name>.md`. The filename becomes the command
(`/<command-name>`). Same caution: only real command files in `commands/`.

## Add a whole new PACKAGE (a separate installable pack)

1. Make `newpack/.claude-plugin/plugin.json`:
   ```json
   { "name": "newpack", "description": "What it is", "version": "1.0.0", "author": { "name": "Brian Lee" } }
   ```
2. Add its skills/agents/commands (at least one!).
3. Add it to `.claude-plugin/marketplace.json` under `plugins`:
   ```json
   { "name": "newpack", "source": "./newpack", "description": "What it is" }
   ```
4. Publish.

## Categories (catalog folders — cosmetic only)

The web catalog groups skills into folders. A skill's folder comes from, in order:
1. `category:` in its `SKILL.md` frontmatter, else
2. an entry in `categories.json` (`"skill-name": "UI & Design"`), else
3. "Others".

Changing a category never moves files — it only changes how the catalog displays.

## Publishing (making your team see the change)

From the repo root:
```
./sync.sh
```
That script: pulls latest, copies your live `~/.claude/skills` into `design-skills`, rebuilds the
README + web catalog, bumps the version, commits, and pushes. **Or just tell Claude "sync marketplace"**
and it runs for you.

If you only edited `team-toolkit` (not the design pack), you can instead just:
```
python3 scripts/build_catalog.py && git add -A && git commit -m "add skill X" && git push
```

Your teammates then run `/plugin` → **Update** to pull the new version.

## Quick checklist when adding a skill

- [ ] Folder + `SKILL.md` with `name` + `description` frontmatter
- [ ] `name` matches folder, kebab-case
- [ ] (optional) `category` set
- [ ] Plugin it lives in is listed in `marketplace.json` and is **not empty**
- [ ] Ran `./sync.sh` (or `build_catalog.py` + commit + push)
- [ ] Team runs `/plugin` → Update
