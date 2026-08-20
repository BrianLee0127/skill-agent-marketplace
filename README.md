# Skill & Agent Marketplace

Claude Code plugin marketplace. 14 items across 2 packages.

Browse the catalog: https://brianlee0127.github.io/skill-agent-marketplace/

## Install

```
/plugin marketplace add BrianLee0127/skill-agent-marketplace
```

Then run `/plugin` and install the package you want. Installing a package gives you everything inside it.

## Adding your own skills

See [CONTRIBUTING.md](CONTRIBUTING.md) for exactly where to put a new skill/agent/command and how to publish it.

## Package: design-skills

Design skill pack: premium frontend taste, brand kits, image-gen direction, redesign workflows

Install: `/plugin` then choose **design-skills**

### UI & Design

| Type | Name | What it does |
|---|---|---|
| skill | [brandkit](design-skills/skills/brandkit) | Premium brand-kit image generation skill for creating high-end brand-guidelines boards, logo systems, identity decks, and visual-world presentations. Trained for minimali |
| skill | [design-taste-frontend](design-skills/skills/design-taste-frontend) | Anti-slop frontend skill for landing pages, portfolios, and redesigns. The agent reads the brief, infers the right design direction, and ships interfaces that do not look |
| skill | [design-taste-frontend-v1](design-skills/skills/design-taste-frontend-v1) | The original v1 taste-skill, preserved for projects depending on its exact behavior. The current default is `design-taste-frontend` (v2 experimental), which is a substant |
| skill | [gpt-taste](design-skills/skills/gpt-taste) | Elite UX/UI & Advanced GSAP Motion Engineer. Enforces Python-driven true randomization for layout variance, strict AIDA page structure, wide editorial typography (bans 6- |
| skill | [high-end-visual-design](design-skills/skills/high-end-visual-design) | Teaches the AI to design like a high-end agency. Defines the exact fonts, spacing, shadows, card structures, and animations that make a website feel expensive. Blocks all |
| skill | [image-to-code](design-skills/skills/image-to-code) | Elite website image-to-code skill for Codex. For visually important web tasks, it must first generate the design image(s) itself, deeply analyze them, then implement the  |
| skill | [imagegen-frontend-mobile](design-skills/skills/imagegen-frontend-mobile) | Elite mobile app image-generation skill for creating premium, app-native screen concepts and flows. Designed for iOS, Android, and cross-platform mobile products. Priorit |
| skill | [imagegen-frontend-web](design-skills/skills/imagegen-frontend-web) | Elite frontend image-direction skill for generating premium, conversion-aware website design references. CRITICAL OUTPUT RULE — generate ONE separate horizontal image FOR |
| skill | [industrial-brutalist-ui](design-skills/skills/industrial-brutalist-ui) | Raw mechanical interfaces fusing Swiss typographic print with military terminal aesthetics. Rigid grids, extreme type scale contrast, utilitarian color, analog degradatio |
| skill | [minimalist-ui](design-skills/skills/minimalist-ui) | Clean editorial-style interfaces. Warm monochrome palette, typographic contrast, flat bento grids, muted pastels. No gradients, no heavy shadows. |
| skill | [redesign-existing-projects](design-skills/skills/redesign-existing-projects) | Upgrades existing websites and apps to premium quality. Audits current design, identifies generic AI patterns, and applies high-end design standards without breaking func |
| skill | [stitch-design-taste](design-skills/skills/stitch-design-taste) | Semantic Design System Skill for Google Stitch. Generates agent-friendly DESIGN.md files that enforce premium, anti-generic UI standards — strict typography, calibrated c |

### Others

| Type | Name | What it does |
|---|---|---|
| skill | [full-output-enforcement](design-skills/skills/full-output-enforcement) | Overrides default LLM truncation behavior. Enforces complete code generation, bans placeholder patterns, and handles token-limit splits cleanly. Apply to any task requiri |

## Package: team-toolkit

Skills, agents, and commands created by the team

Install: `/plugin` then choose **team-toolkit**

### UI & Design

| Type | Name | What it does |
|---|---|---|
| skill | [tpp-microsite-ui](team-toolkit/skills/tpp-microsite-ui) | TyrePlus/Michelin TPP microsite UI design template for ASP.NET Core MVC + Bootstrap 5. Green/yellow/blue brand tokens, gradient CTAs, form-section cards, 5-step wizard wi |

## Updating (maintainer)

Run `./sync.sh` to publish changes and rebuild this catalog.

Set a skill's folder with `category: ...` in its SKILL.md frontmatter, or in `categories.json`.
