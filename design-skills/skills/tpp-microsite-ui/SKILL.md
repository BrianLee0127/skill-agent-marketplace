---
name: tpp-microsite-ui
description: TyrePlus/Michelin TPP microsite UI design template for ASP.NET Core MVC + Bootstrap 5. Green/yellow/blue brand tokens, gradient CTAs, form-section cards, 5-step wizard with stepper + summary sidebar, status badges, Leaflet outlet picker, Tom Select/Flatpickr conventions, Razor + virtual-directory-safe URL rules. Use when building or restyling a Webmax microsite so it matches the TPP RHP look-and-feel.
---

# TPP Microsite UI Design Template

You are building UI for a Webmax microsite that must match the TyrePlus/Michelin RHP warranty microsite look-and-feel. Stack: ASP.NET Core 8 MVC (Razor views, no SPA), Bootstrap 5.1 (local under `wwwroot/lib`), jQuery 3.6, Bootstrap Icons (CDN), Tom Select 2.3.1 (CDN), Flatpickr (CDN, per page), Leaflet 1.9.4 (CDN, per page). No build step, no JS modules.

Detailed component CSS/markup excerpts live in [references/components.md](references/components.md) — load it when implementing a specific component (wizard, modals, badges, map picker, etc.).

## 1. Design tokens (put in `:root` of `wwwroot/css/site.css`)

```css
:root {
    --tp-green: #009944;  --tp-green-light: #00b550;  --tp-green-dark: #007a36;
    --tp-green-glow: rgba(0, 153, 68, 0.25);
    --tp-yellow: #FFE500; --tp-yellow-light: #fff176; --tp-yellow-dark: #e6cf00;
    --tp-blue: #004f9f;   --tp-blue-light: #1a6fbf;   --tp-blue-dark: #003d7a;
    --tp-dark: #0f1114;   --tp-dark-card: #1a1d23;
    --tp-gray-50: #fafafa;  --tp-gray-100: #f5f5f5; --tp-gray-200: #eeeeee;
    --tp-gray-300: #e0e0e0; --tp-gray-400: #bdbdbd; --tp-gray-500: #9e9e9e; --tp-gray-600: #757575;
    --tp-text: #1a1a2e;   --tp-text-secondary: #64748b;  --tp-white: #ffffff;
    --tp-radius-sm: 8px;  --tp-radius: 12px;  --tp-radius-lg: 16px;  --tp-radius-xl: 24px;
    --tp-shadow-xs: 0 1px 2px rgba(0,0,0,0.05);
    --tp-shadow-sm: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
    --tp-shadow:    0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
    --tp-shadow-md: 0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.05);
    --tp-shadow-lg: 0 20px 25px -5px rgba(0,0,0,0.08), 0 8px 10px -6px rgba(0,0,0,0.04);
    --tp-shadow-green: 0 4px 14px rgba(0, 153, 68, 0.3);
    --tp-transition:        all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    --tp-transition-fast:   all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    --tp-transition-bounce: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

Base: `html { font-size: 14px }` → `16px` at ≥768px (fluid rem scale). Font is **Inter** (Google Fonts, weights 300–900). Body background is a subtle green-tinted vertical gradient: `linear-gradient(180deg, #f0f7f2 0%, var(--tp-gray-50) 30%, var(--tp-gray-50) 70%, #f0f7f2 100%)`. Links: blue, hover green. `::selection` green/white. `html, body { max-width: 100vw; overflow-x: hidden; }`.

**Signature gradients** (reuse verbatim):

| Purpose | Value |
|---|---|
| Green CTA | `linear-gradient(135deg, var(--tp-green) 0%, var(--tp-green-light) 100%)` |
| Green CTA hover | `linear-gradient(135deg, var(--tp-green-dark) 0%, var(--tp-green) 100%)` |
| Blue CTA / header | `linear-gradient(135deg, var(--tp-blue-dark) 0%, var(--tp-blue) 50%, var(--tp-blue-light) 100%)` |
| Yellow CTA | `linear-gradient(135deg, var(--tp-yellow) 0%, var(--tp-yellow-light) 100%)` |
| Card accent bar / section underline | `linear-gradient(90deg, var(--tp-green), var(--tp-yellow))` |
| Footer top bar | `linear-gradient(90deg, var(--tp-green), var(--tp-yellow), var(--tp-green))` |

**Radius scale:** 8px controls/buttons/alerts · 12px cards · 16px hero/modals · 999px/50px pills · 50% icon circles.
**Labels:** `0.82rem`, weight 600, uppercase, letter-spacing 0.3px, `var(--tp-text-secondary)`. Required fields get `.required::after { content: " *"; color: #dc3545; }`.

## 2. Layout shell rules

- Sticky navbar `navbar navbar-expand-lg navbar-tp sticky-top` with dual logos (TyrePlus 60px | separator | Michelin 96px), Bootstrap-Icons nav links, and a `d-lg-none` compact action group pinned with `ms-auto` so mobile logout stays on the brand row. Navbar gains `.scrolled` (shrink/shadow) past 20px scroll.
- Flash messages: `TempData["Success"]` / `TempData["Error"]` rendered as dismissible Bootstrap alerts with `bi-check-circle-fill` / `bi-exclamation-triangle-fill` at the top of `<main>`.
- 4-column dark footer `.footer-tp` with tri-color `.footer-green-bar` on top, uppercase micro-headings, chevron link lists, WhatsApp/tel/mailto contact icons in green.
- **Virtual-directory safety (IIS)**: never hard-code `/images/...` or `/Controller/Action` anywhere, including JS. Always `~/` + tag helpers, `@Url.Action(...)`, `@Url.Content("~/...")`. No `UsePathBase`.
- Session-timeout UX (authenticated pages only): 30-min idle timer matching `Program.cs` `IdleTimeout`, reset on click/keydown/touchstart, plus 401 interception on both jQuery ajax and patched `window.fetch` → redirect to a SessionTimeout page (centered card, red-tinted 80px `bi-clock-history` circle, `btn-tp-green btn-lg px-5` re-login).
- `asp-append-version="true"` on all first-party static assets.

## 3. Core components (recipes in references/components.md)

- **Buttons**: `.btn-tp-green` (gradient + sheen sweep `::after`, hover `translateY(-2px)`), `.btn-tp-yellow` (forward navigation / claim CTA, dark text, weight 700), `.btn-tp-outline` (2px green border, wipe-fill `::before` on hover), `.btn-tp-blue`. Semantics: **green = confirm/primary, yellow = next/forward, outline = back/secondary, blue = informational**. Global focus ring: `0 0 0 3px var(--tp-green-glow)`.
- **Cards**: `.card-tp` — white, 12px radius, hover lifts `-6px` and reveals a 3px green→yellow top accent bar. `.form-section` + `.form-section-header` (green gradient, uppercase 0.85rem) + `.form-section-body` (1.5rem padding) is the dominant page container.
- **Section headings**: `.section-header` with 48px green→yellow underline that grows to 80px on hover.
- **Wizard (5-step)**: `.wizard-stepper` circles (38px, active = green + glow ring + scale 1.1, completed = check icon) + `.wizard-step-line` progress fill; panels slide with `.wizard-from-right/left` + `.wizard-sliding-in` (400ms); invalid step triggers `.wizard-shake`. Desktop: sticky summary sidebar (`top: 90px`) with `.summary-row` items that highlight green when active. Mobile: fixed bottom bar with pill tabs + step dots, `body { padding-bottom: 64px }` under 992px.
- **Forms**: 1.5px borders, green focus; readonly inputs tinted inline (`background: var(--tp-gray-50); color: var(--tp-text-secondary)`); derived values rendered as **chips** (`.vehicle-info-chip` label/value stack) with a hidden input carrying the posted value; AI/OCR-filled fields get `.ai-filled` (green border + tint) + `.ai-highlight` pulse; dashed-border dropzone with `.dragover`/`.has-file` states.
- **Modals**: centered, `border-0 shadow`, borderless header/footer; confirm = `btn-tp-green`, compact yes/no = `modal-sm` 14px radius, big icon, `flex-fill` footer buttons; success modals use `data-bs-backdrop="static"`; large form modals go full-screen under 576px with sticky footer and 16px inputs (iOS zoom guard).
- **Badges**: `.badge-status` dot-prefixed pills (active green / pending orange pulsing / expired grey / rejected red / claimed blue); status colors = tinted background (≈12% alpha) + saturated text; `.tyre-badge` numeric green squares; `.outlet-badge` uppercase pills.
- **Tables**: `.table-tp` — grey uppercase 0.72rem headers, green-tinted row hover; below `md`, swap tables for card lists (`d-none d-md-block` + mobile cards).
- **Toasts**: no library — fixed top-right dismissible alerts auto-closed after 6s. Button-busy idiom: disable + swap innerHTML to `spinner-border spinner-border-sm` + restore in `finally`.
- **Hero**: pure-image banner in `.hero-banner` (16px radius, `line-height: 0`), no text overlay. Home action row: gradient `.action-card` tiles with watermark icon, glassy icon square, arrow that slides right on hover.
- **Scroll reveal**: `.fade-in-up/left/right`, `.scale-in` + `.delay-1..4`, activated by IntersectionObserver adding `.visible`.

## 4. Third-party library conventions

- **Tom Select**: global `initTpSearchableSelect(selectEl, options)` wrapper in `site.js` (destroys existing instance, sensible defaults, graceful fallback to native select). Inside overflow containers always pass `dropdownParent: 'body'` and declare `.ts-dropdown { z-index: 9999 !important; }`. After silent `setValue(v, true)` always call `.close()` then `.blur()`. Init only when the containing step/panel is visible (TS can't measure hidden elements); pair with a document-level delegated `change` listener so callbacks survive destroy/recreate.
- **Flatpickr**: visible `dd/MM/yyyy` text input (`dateFormat: 'd/m/Y'`, `allowInput: true`) + hidden ISO input for model binding. Build the ISO string from local date parts — **never `toISOString()`** (timezone drift). Rehydrate with `el._flatpickr.setDate(d, false)`.
- **Leaflet**: OSM tiles, Malaysia default view `[4.2, 108.5], 6`. Markers are teardrop `divIcon`s carrying the brand logo (green ring TyrePlus, blue ring Michelin). No radius circles — proximity shown as "X.X km away" + `fitBounds(..., { padding: [30,30], maxZoom: 13 })`. Defer map init until its panel is visible, then `invalidateSize()`. Picker layout: 380px map left / 340px scrollable list right, stacked under 768px; selected item = green tint, 4px left border, "✓ Selected" pill.

## 5. JS & Razor conventions

- Page logic lives inline in `@section Scripts { }` so Razor can interpolate `@Url.Action`. `site.js` holds only cross-page helpers.
- Page-local CSS in one `<style>` block near the top of the view; **double the `@` in Razor files** (`@@media`, `@@keyframes`) — but single `@` in plain `.css` files.
- Validation: sweep `[required]` in the active panel, message from `data-msg`, write into nearest `.invalid-feedback`, clear on next `input` (`{ once: true }`), shake panel + focus first invalid. TomSelect fields toggle a sibling message div and mark `.ts-wrapper.is-invalid`.
- State wiring via `data-*` attributes (`data-tyre`, `data-field`, `data-summary`, `data-msg`), read back with attribute selectors — no inline JSON.
- Fetch: `await fetch('@Url.Action("Action","Controller")')`; JSON or FormData bodies; responses `{ success, message, ... }`; wrap in try/catch/finally and restore button state. Anti-forgery: `@Html.AntiForgeryToken()` in the form, forwarded as `RequestVerificationToken` **header** on AJAX.
- Escape all JS-built HTML through a `div.textContent`-based `escHtml` helper. Debounce search inputs 400ms / min 2 chars.

## 6. File layout

```
src/<App>.Web/
├─ Views/Shared/_Layout.cshtml       # shell: navbar, flash, footer, timeout script
├─ Views/<Feature>/<Page>.cshtml     # partials prefixed "_"
└─ wwwroot/
   ├─ css/site.css                   # THE design system, sectioned /* ===== Name ===== */
   ├─ js/site.js                     # global helpers only
   ├─ images/  documents/  lib/      # LibMan-vendored bootstrap/jquery
```

Class naming: `tp-` prefix for tokens/buttons, component-name prefixes elsewhere (`wizard-*`, `summary-*`, `outlet-picker-*`, `action-card-*`, `chip-*`).

## 7. Known gotchas (fix, don't copy)

1. In plain `.css` files use single `@keyframes` — the original leaked a Razor `@@keyframes` into `site.css`, killing the shake animation.
2. Pick ONE body font declaration (Inter) — the original had a dead Segoe UI declaration overridden by an inline style.
3. Define every class you reference (the original's `.invoice-upload-hero` was used but never defined).
4. Print styles: hide `.navbar-tp, .footer-tp, .btn`, flatten card shadows.
