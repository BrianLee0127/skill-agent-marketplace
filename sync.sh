#!/bin/zsh
# Sync live Claude skills into the marketplace and publish.
# Usage: ~/skill-agent-marketplace/sync.sh
set -e
cd "$(dirname "$0")"

echo "Pulling latest from GitHub ..."
git pull --rebase

# Warn if the repo has skills that are missing locally (e.g. created on another PC)
for name in $(ls design-skills/skills 2>/dev/null); do
  if [ ! -e "$HOME/.claude/skills/$name" ]; then
    echo "WARNING: skill '$name' exists in the repo but not in ~/.claude/skills."
    echo "Syncing now would DELETE it. Copy it to ~/.claude/skills first, or ask Claude to 'pull marketplace skills'."
    exit 1
  fi
done

echo "Copying skills from ~/.claude/skills ..."
rm -rf design-skills/skills
cp -RL "$HOME/.claude/skills/" design-skills/skills/

echo "Rebuilding catalog ..."
python3 scripts/build_catalog.py

if git status --porcelain | grep -q .; then
  NEW_VERSION=$(python3 - <<'EOF'
import json
p = "design-skills/.claude-plugin/plugin.json"
d = json.load(open(p))
major, minor, patch = d["version"].split(".")
d["version"] = f"{major}.{minor}.{int(patch) + 1}"
json.dump(d, open(p, "w"), indent=2)
print(d["version"])
EOF
)
  git add -A
  git commit -m "Sync skills (v$NEW_VERSION)"
  git push
  echo "Published v$NEW_VERSION. Team can update via /plugin."
else
  echo "No changes found. Nothing to publish."
fi
