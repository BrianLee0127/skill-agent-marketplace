# Skill & Agent Marketplace

Claude Code plugin marketplace. 13 items across 2 plugins.

Browse the catalog: https://brianlee0127.github.io/skill-agent-marketplace/

## Install

```
/plugin marketplace add BrianLee0127/skill-agent-marketplace
```

Then run `/plugin` and install the plugin you want.

## Plugin: design-skills

Design skill pack: premium frontend taste, brand kits, image-gen direction, redesign workflows

| Skill | What it does |
|---|---|
| [brandkit](design-skills/skills/brandkit) | Premium brand-kit image generation skill for creating high-end brand-guidelines boards, logo systems, identity decks, and visual-world presentations. Trained for minimalist, cinema |
| [design-taste-frontend](design-skills/skills/design-taste-frontend) | Anti-slop frontend skill for landing pages, portfolios, and redesigns. The agent reads the brief, infers the right design direction, and ships interfaces that do not look templated |
| [design-taste-frontend-v1](design-skills/skills/design-taste-frontend-v1) | The original v1 taste-skill, preserved for projects depending on its exact behavior. The current default is `design-taste-frontend` (v2 experimental), which is a substantial rewrit |
| [full-output-enforcement](design-skills/skills/full-output-enforcement) | Overrides default LLM truncation behavior. Enforces complete code generation, bans placeholder patterns, and handles token-limit splits cleanly. Apply to any task requiring exhaust |
| [gpt-taste](design-skills/skills/gpt-taste) | Elite UX/UI & Advanced GSAP Motion Engineer. Enforces Python-driven true randomization for layout variance, strict AIDA page structure, wide editorial typography (bans 6-line wraps |
| [high-end-visual-design](design-skills/skills/high-end-visual-design) | Teaches the AI to design like a high-end agency. Defines the exact fonts, spacing, shadows, card structures, and animations that make a website feel expensive. Blocks all the commo |
| [image-to-code](design-skills/skills/image-to-code) | Elite website image-to-code skill for Codex. For visually important web tasks, it must first generate the design image(s) itself, deeply analyze them, then implement the website to |
| [imagegen-frontend-mobile](design-skills/skills/imagegen-frontend-mobile) | Elite mobile app image-generation skill for creating premium, app-native screen concepts and flows. Designed for iOS, Android, and cross-platform mobile products. Prioritizes clean |
| [imagegen-frontend-web](design-skills/skills/imagegen-frontend-web) | Elite frontend image-direction skill for generating premium, conversion-aware website design references. CRITICAL OUTPUT RULE — generate ONE separate horizontal image FOR EVERY sec |
| [industrial-brutalist-ui](design-skills/skills/industrial-brutalist-ui) | Raw mechanical interfaces fusing Swiss typographic print with military terminal aesthetics. Rigid grids, extreme type scale contrast, utilitarian color, analog degradation effects. |
| [minimalist-ui](design-skills/skills/minimalist-ui) | Clean editorial-style interfaces. Warm monochrome palette, typographic contrast, flat bento grids, muted pastels. No gradients, no heavy shadows. |
| [redesign-existing-projects](design-skills/skills/redesign-existing-projects) | Upgrades existing websites and apps to premium quality. Audits current design, identifies generic AI patterns, and applies high-end design standards without breaking functionality. |
| [stitch-design-taste](design-skills/skills/stitch-design-taste) | Semantic Design System Skill for Google Stitch. Generates agent-friendly DESIGN.md files that enforce premium, anti-generic UI standards — strict typography, calibrated color, asym |

## Plugin: team-toolkit

Skills, agents, and commands created by the team

Nothing here yet.

## Updating (maintainer)

Run `./sync.sh` to publish skill changes and rebuild this catalog.
