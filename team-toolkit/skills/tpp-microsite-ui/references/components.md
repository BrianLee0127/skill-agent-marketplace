# TPP Microsite UI — Component Recipes

Copy-paste-grade CSS/markup for each component in the TPP RHP design system. All custom properties come from the `:root` token block in SKILL.md.

## Layout shell

### Head / CDN block

```html
<title>@ViewData["Title"] - <Brand> Microsite</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="~/lib/bootstrap/dist/css/bootstrap.min.css" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/css/tom-select.bootstrap5.min.css" />
<link rel="stylesheet" href="~/css/site.css" asp-append-version="true" />
```

Body font: `body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }` — declare it once in site.css.

### Navbar

```html
<nav class="navbar navbar-expand-lg navbar-tp sticky-top" id="mainNavbar">
  <div class="container">
    <a class="navbar-brand d-flex align-items-center gap-3" asp-controller="Home" asp-action="Index">
      <img src="~/images/brand-logo.png" alt="Brand" height="60" />
      <span class="brand-separator">|</span>
      <img src="~/images/partner-logo.png" alt="Partner" height="96" />
    </a>
    <!-- mobile-only compact action group: keeps logout on the brand row -->
    <div class="d-lg-none ms-auto me-2 d-flex align-items-center gap-2">
      <span class="navbar-mobile-phone small fw-semibold text-muted">
        <i class="bi bi-person-circle me-1"></i>@Context.Session.GetString("MobileNumber")
      </span>
      <a class="btn btn-tp-outline btn-sm" asp-controller="Auth" asp-action="Logout" aria-label="Logout">
        <i class="bi bi-box-arrow-right"></i>
      </a>
    </div>
    <button class="navbar-toggler border-0" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav ms-auto align-items-lg-center gap-1">
        <li class="nav-item"><a class="nav-link" asp-controller="X" asp-action="Y"><i class="bi bi-shield-plus me-1"></i>Register</a></li>
        <li class="nav-item ms-lg-2"><span class="nav-link nav-user"><i class="bi bi-person-circle me-1"></i>@Context.Session.GetString("MobileNumber")</span></li>
        <li class="nav-item"><a class="btn btn-tp-outline btn-sm" asp-controller="Auth" asp-action="Logout"><i class="bi bi-box-arrow-right me-1"></i>Logout</a></li>
      </ul>
    </div>
  </div>
</nav>
```

Mobile: hide `.navbar-mobile-phone` under 767px; shrink brand logos to 32px/50px; collapsed menu becomes a white rounded card. Shrink-on-scroll: `navbar.classList.toggle('scrolled', window.scrollY > 20)`.

Auth gating is session-based: `Context.Session.GetString("IsAuthenticated") == "true"`, role from `Session["UserRole"]`.

### Flash messages

```html
@if (TempData["Success"] != null) {
  <div class="alert alert-success alert-dismissible fade show" role="alert">
    <i class="bi bi-check-circle-fill me-2"></i>@TempData["Success"]
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  </div>
}
@* alert-danger + bi-exclamation-triangle-fill for TempData["Error"] *@
```

### Footer

```html
<footer class="footer-tp">
  <div class="footer-green-bar"></div> <!-- linear-gradient(90deg, green, yellow, green) -->
  <div class="container footer-content">
    <div class="row g-4">
      <div class="col-lg-4 col-md-6"><img src="~/images/brand-logo.png" height="28" style="filter: brightness(2);" /><p class="small" style="max-width:300px;">…</p></div>
      <div class="col-lg-2 col-md-6"><h6>Quick Links</h6>
        <ul class="list-unstyled">
          <li class="mb-2"><a href="…" target="_blank" rel="noopener"><i class="bi bi-chevron-right me-1" style="font-size:0.7rem;"></i>Terms &amp; Conditions</a></li>
        </ul></div>
      <div class="col-lg-3 col-md-6"><h6>Services</h6>…</div>
      <div class="col-lg-3 col-md-6"><h6>Contact</h6><!-- WhatsApp / tel: / mailto: green icons --></div>
    </div>
    <div class="footer-bottom text-center">&copy; @DateTime.Now.Year <Brand> &middot; All Rights Reserved</div>
  </div>
</footer>
```

### Session-timeout script (render only when authenticated)

```js
var TIMEOUT_URL = '@Url.Action("SessionTimeout", "Auth")';
var IDLE_LIMIT = 30 * 60 * 1000; // must match Program.cs IdleTimeout
var idleTimer, redirecting = false;
function goToTimeout() { if (redirecting) return; redirecting = true; window.location.href = TIMEOUT_URL; }
function resetIdle() { if (redirecting) return; if (idleTimer) clearTimeout(idleTimer); idleTimer = setTimeout(goToTimeout, IDLE_LIMIT); }
['click','keydown','touchstart'].forEach(evt => document.addEventListener(evt, resetIdle, { passive: true }));
resetIdle();
jQuery(document).ajaxError(function (e, xhr) { if (xhr && xhr.status === 401) goToTimeout(); });
var _fetch = window.fetch;
window.fetch = function () { return _fetch.apply(this, arguments).then(res => { if (res && res.status === 401) goToTimeout(); return res; }); };
```

## Buttons

```css
.btn-tp-green {
    background: linear-gradient(135deg, var(--tp-green) 0%, var(--tp-green-light) 100%);
    color: var(--tp-white); border: none; border-radius: var(--tp-radius-sm);
    font-weight: 600; font-size: 0.9rem; padding: 0.65rem 1.8rem;
    transition: var(--tp-transition); box-shadow: var(--tp-shadow-green);
    position: relative; overflow: hidden;
}
.btn-tp-green::after {          /* sheen sweep */
    content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: left 0.5s ease;
}
.btn-tp-green:hover { background: linear-gradient(135deg, var(--tp-green-dark) 0%, var(--tp-green) 100%);
    transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,153,68,0.4); }
.btn-tp-green:hover::after { left: 100%; }
.btn-tp-green:active { transform: translateY(0); }

.btn-tp-outline {               /* secondary — wipe-fill on hover */
    background: transparent; color: var(--tp-green); border: 2px solid var(--tp-green);
    border-radius: var(--tp-radius-sm); font-weight: 600; font-size: 0.9rem;
    padding: 0.55rem 1.8rem; transition: var(--tp-transition);
    position: relative; overflow: hidden; z-index: 1;
}
.btn-tp-outline::before { content: ''; position: absolute; top: 0; left: 0; width: 0; height: 100%;
    background: var(--tp-green); transition: width 0.3s ease; z-index: -1; }
.btn-tp-outline:hover { color: var(--tp-white); transform: translateY(-2px); }
.btn-tp-outline:hover::before { width: 100%; }

.btn-tp-yellow {                /* "Next" / forward-action accent */
    background: linear-gradient(135deg, var(--tp-yellow) 0%, var(--tp-yellow-light) 100%);
    color: var(--tp-dark); border: none; border-radius: var(--tp-radius-sm);
    font-weight: 700; font-size: 0.95rem; padding: 0.7rem 2rem;
    box-shadow: 0 4px 14px rgba(255,229,0,0.35);
}
.btn-tp-yellow:hover { transform: translateY(-2px) scale(1.02); box-shadow: 0 8px 25px rgba(255,229,0,0.45); }

/* .btn-tp-blue: same recipe, blue gradient + 0 4px 14px rgba(0,79,159,0.25) */

/* global focus ring */
.btn:focus, .btn:active:focus, .form-control:focus, .form-check-input:focus, .form-select:focus {
    box-shadow: 0 0 0 3px var(--tp-green-glow); border-color: var(--tp-green); outline: none;
}
```

## Cards & sections

```css
.card-tp {
    background: var(--tp-white); border: 1px solid rgba(0,0,0,0.04);
    border-radius: var(--tp-radius); box-shadow: var(--tp-shadow-sm);
    transition: var(--tp-transition); overflow: hidden; position: relative;
}
.card-tp::before {   /* green→yellow accent bar revealed on hover */
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, var(--tp-green), var(--tp-yellow));
    opacity: 0; transition: opacity 0.3s ease;
}
.card-tp:hover { box-shadow: var(--tp-shadow-lg); transform: translateY(-6px); border-color: transparent; }
.card-tp:hover::before { opacity: 1; }
.card-tp .card-header-tp {
    background: linear-gradient(135deg, var(--tp-green) 0%, var(--tp-green-light) 100%);
    color: var(--tp-white); font-weight: 600; padding: 0.85rem 1.25rem;
    font-size: 0.9rem; letter-spacing: 0.3px; border: none;
}
.card-tp .card-body { padding: 1.5rem; }

.form-section { background: var(--tp-white); border: 1px solid rgba(0,0,0,0.04);
    border-radius: var(--tp-radius); box-shadow: var(--tp-shadow-sm); margin-bottom: 1.5rem;
    overflow: hidden; transition: var(--tp-transition); }
.form-section:hover { box-shadow: var(--tp-shadow); }
.form-section-header {
    background: linear-gradient(135deg, var(--tp-green) 0%, var(--tp-green-light) 100%);
    color: var(--tp-white); font-weight: 600; padding: 0.7rem 1.25rem;
    font-size: 0.85rem; letter-spacing: 0.8px; text-transform: uppercase;
}
.form-section-body { padding: 1.5rem; background: var(--tp-white); }

.section-header { position: relative; margin-bottom: 2rem; padding-bottom: 0.85rem; color: var(--tp-text); }
.section-header::after { content: ''; position: absolute; bottom: 0; left: 0; width: 48px; height: 4px;
    background: linear-gradient(90deg, var(--tp-green), var(--tp-yellow)); border-radius: 2px; transition: width 0.3s ease; }
.section-header:hover::after { width: 80px; }
.section-header.text-center::after { left: 50%; transform: translateX(-50%); }
```

Markup: `<div class="form-section"><div class="form-section-header"><i class="bi bi-person-fill me-2"></i>YOUR INFORMATION</div><div class="form-section-body">…</div></div>`

## Wizard (multi-step)

### Stepper

```html
<div class="wizard-stepper mb-4">
  <div class="wizard-step active" data-step="1"><div class="wizard-step-circle">1</div><div class="wizard-step-label">INFO</div></div>
  <div class="wizard-step-line active"></div>
  <div class="wizard-step" data-step="2"><div class="wizard-step-circle">2</div><div class="wizard-step-label">VEHICLE</div></div>
  <div class="wizard-step-line"></div>
  <!-- … repeat per step … -->
</div>
```

```css
.wizard-stepper { display: flex; align-items: center; justify-content: center; gap: 0;
    padding: 1.25rem 1.5rem; background: var(--tp-white); border-radius: var(--tp-radius); box-shadow: var(--tp-shadow-sm); }
.wizard-step { display: flex; flex-direction: column; align-items: center; gap: 6px; flex-shrink: 0; cursor: default; }
.wizard-step-circle { width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center;
    justify-content: center; font-weight: 700; font-size: 0.9rem;
    background: var(--tp-gray-200); color: var(--tp-gray-500);
    transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); border: 2px solid transparent; }
.wizard-step.active .wizard-step-circle { background: var(--tp-green); color: white; border-color: var(--tp-green);
    box-shadow: 0 0 0 4px var(--tp-green-glow); transform: scale(1.1); }
.wizard-step.completed .wizard-step-circle { background: var(--tp-green); color: white; transform: scale(1); box-shadow: none; }
.wizard-step-label { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.8px;
    color: var(--tp-gray-400); text-transform: uppercase; transition: color 0.3s ease; }
.wizard-step.active .wizard-step-label { color: var(--tp-green); }
.wizard-step-line { flex: 1; height: 3px; background: var(--tp-gray-200); margin: 0 8px 22px;
    border-radius: 2px; position: relative; overflow: hidden; min-width: 30px; }
.wizard-step-line::after { content: ''; position: absolute; top: 0; left: 0; height: 100%; width: 0;
    background: var(--tp-green); border-radius: 2px; transition: width 0.5s cubic-bezier(0.4,0,0.2,1); }
.wizard-step-line.active::after { width: 100%; }
```

Completed circles get their number replaced with `<i class="bi bi-check2"></i>`.

### Panel transitions (container: `position: relative; overflow: hidden`)

```css
.wizard-panel { display: none; opacity: 0; transform: translateX(0); }
.wizard-panel.active { display: block; opacity: 1; }
.wizard-panel.wizard-ready { position: absolute; top: 0; left: 0; width: 100%; opacity: 0; z-index: 2; }
.wizard-panel.wizard-from-right { transform: translateX(60px); }
.wizard-panel.wizard-from-left  { transform: translateX(-60px); }
.wizard-panel.wizard-sliding-in { opacity: 1; transform: translateX(0);
    transition: opacity .4s cubic-bezier(.25,.46,.45,.94), transform .4s cubic-bezier(.25,.46,.45,.94); }
.wizard-panel.wizard-exit-left  { opacity: 0; transform: translateX(-40px); transition: opacity .3s ease-in, transform .3s ease-in; }
.wizard-panel.wizard-exit-right { opacity: 0; transform: translateX(40px);  transition: opacity .3s ease-in, transform .3s ease-in; }
.wizard-shake { animation: wizardShake 0.4s ease-in-out; }
@keyframes wizardShake { 0%,100%{transform:translateX(0)} 20%{transform:translateX(-8px)} 40%{transform:translateX(8px)} 60%{transform:translateX(-4px)} 80%{transform:translateX(4px)} }
```

(Single `@` in plain .css — double `@@` only inside Razor views.)

Navigation flow: `wizardNav(±1)` → `validateStep(current)` gate → `goToStep(n)` stages incoming panel (`.wizard-ready .wizard-from-right|left`), forces reflow (`nextPanel.offsetHeight`), swaps classes, finalizes after 400ms, then `updateStepper() / updateButtons() / updateSummary()`, smooth-scrolls to stepper, fires `onStepChanged(step)` hook (used for lazy TomSelect/Leaflet init).

### Nav row

```html
<div class="wizard-nav mt-4 mb-5">
  <button type="button" class="btn btn-tp-outline px-4" id="btnPrev" style="display:none;" onclick="wizardNav(-1)"><i class="bi bi-arrow-left me-1"></i>Back</button>
  <div class="flex-grow-1"></div>
  <button type="button" class="btn btn-tp-yellow px-5" id="btnNext" onclick="wizardNav(1)">Next <i class="bi bi-arrow-right ms-1"></i></button>
  <button type="button" class="btn btn-tp-green btn-lg px-5" id="btnSubmit" style="display:none;" onclick="handleSubmit()"><i class="bi bi-check-circle me-2"></i>SUBMIT</button>
</div>
```

### Desktop summary sidebar

```html
<div class="col-lg-4 d-none d-lg-block" id="wizardSidebarCol">
  <div class="wizard-summary sticky-top" style="top: 90px;">
    <div class="form-section">
      <div class="form-section-header"><i class="bi bi-list-check me-2"></i>SUMMARY</div>
      <div class="form-section-body p-0">
        <div class="summary-row" id="summaryCustomer">
          <div class="summary-icon"><i class="bi bi-person"></i></div>
          <div><div class="summary-label">Your Information</div>
               <div class="summary-value" id="sumName">—</div>
               <div class="summary-sub" id="sumMobile">—</div></div>
        </div>
      </div>
    </div>
  </div>
</div>
```

```css
.summary-row { display: flex; align-items: flex-start; gap: 12px; padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--tp-gray-100); transition: all 0.3s ease; }
.summary-row.summary-active { background: rgba(0,153,68,0.04); border-left: 3px solid var(--tp-green); }
.summary-icon { width: 32px; height: 32px; border-radius: 8px; background: var(--tp-gray-100);
    color: var(--tp-gray-500); display:flex; align-items:center; justify-content:center; font-size:.9rem; flex-shrink:0; transition: all .3s ease; }
.summary-active .summary-icon { background: var(--tp-green); color: white; }
.summary-label { font-size: .68rem; font-weight: 700; letter-spacing: .5px; text-transform: uppercase; color: var(--tp-text-secondary); }
.summary-value { font-weight: 600; font-size: .88rem; color: var(--tp-text); word-break: break-word; }
.summary-sub   { font-size: .78rem; color: var(--tp-text-secondary); }
```

Sidebar hides on the final CONFIRM step via inline style toggling (not `d-none` — it conflicts with `d-lg-block`).

### Mobile bottom bar

```css
.mobile-summary-bar { position: fixed; bottom: 0; left: 0; right: 0; z-index: 999;
    background: var(--tp-white); border-top: 2px solid var(--tp-green); box-shadow: 0 -4px 20px rgba(0,0,0,0.08); }
.mob-tab-btn { flex: 1; display:flex; align-items:center; justify-content:center; gap:6px;
    padding: .45rem .75rem; font-size:.78rem; font-weight:600; color: var(--tp-text-secondary);
    background: var(--tp-gray-100); border: 1.5px solid transparent; border-radius: 999px;
    transition: transform .12s cubic-bezier(.34,1.56,.64,1), background .15s, color .15s, box-shadow .15s; }
.mob-tab-btn:active { transform: scale(0.93); }
.mob-tab-btn.active-tab { color: var(--tp-white); background: var(--tp-green); border-color: var(--tp-green);
    box-shadow: 0 4px 12px rgba(0,153,68,.35); animation: mob-tab-pop .25s cubic-bezier(.34,1.56,.64,1); }
@keyframes mob-tab-pop { 0%{transform:scale(.88)} 60%{transform:scale(1.06)} 100%{transform:scale(1)} }
.mobile-summary-step-dots .dot { width:8px; height:8px; border-radius:50%; background: var(--tp-gray-300); transition: all .3s ease; }
.mobile-summary-step-dots .dot.active  { background: var(--tp-green); }
.mobile-summary-step-dots .dot.current { width:20px; border-radius:4px; background: var(--tp-green); box-shadow: 0 0 0 3px var(--tp-green-glow); }
@media (max-width: 991px) { body { padding-bottom: 64px; } }   /* clearance for the fixed bar */
```

## Form controls

```css
.form-control, .form-select { border-radius: var(--tp-radius-sm); border: 1.5px solid var(--tp-gray-300);
    padding: 0.55rem 0.85rem; font-size: 0.9rem; transition: var(--tp-transition-fast); background-color: var(--tp-white); }
.form-control:hover, .form-select:hover { border-color: var(--tp-gray-400); }
.form-control:focus, .form-select:focus { border-color: var(--tp-green); box-shadow: 0 0 0 3px var(--tp-green-glow); }
.form-label { font-weight: 600; font-size: 0.82rem; color: var(--tp-text-secondary);
    text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 0.35rem; }
.form-label.required::after, .form-check-label.required::after { content: " *"; color: #dc3545; font-weight: 700; }
.input-group-text { border-radius: 0 var(--tp-radius-sm) var(--tp-radius-sm) 0; background: var(--tp-gray-100);
    border: 1.5px solid var(--tp-gray-300); border-left: none; font-size: 0.85rem; color: var(--tp-text-secondary); }
.is-invalid { border-color: #dc3545 !important; box-shadow: 0 0 0 3px rgba(220,53,69,0.15) !important; }
.invalid-feedback { display: none; font-size: 0.8rem; color: #dc3545; margin-top: 4px; font-weight: 500; }
.is-invalid ~ .invalid-feedback, .is-invalid + .invalid-feedback { display: block; }
```

Readonly inputs (inline tint, not a class):
```html
<input asp-for="MobileNumber" class="form-control" readonly
       style="background: var(--tp-gray-50); color: var(--tp-text-secondary);" />
```

Derived/auto-filled values render as chips + hidden input:
```css
.info-chip { display:flex; flex-direction:column; gap:2px; padding:.5rem .75rem; border-radius:8px;
    background: var(--tp-gray-50); border: 1px solid var(--tp-gray-200); min-height:56px; justify-content:center; }
.info-chip .chip-label { font-size:.68rem; font-weight:600; color: var(--tp-gray-500); text-transform:uppercase; letter-spacing:.4px; }
.info-chip .chip-value { font-size:.95rem; font-weight:600; color: var(--tp-text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.info-chip .chip-value.is-empty { color: var(--tp-gray-400); font-weight:400; }
```
```html
<div class="info-chip"><span class="chip-label">Brand</span><span id="brandDisplay" class="chip-value is-empty">—</span></div>
<input asp-for="Brand" type="hidden" data-summary="brand" data-msg="Brand is required" />
```

AI/OCR-filled highlight:
```css
.ai-filled { border-color: var(--tp-green) !important; background-color: rgba(0,153,68,0.04) !important; }
.ai-highlight { animation: aiPulse 0.6s ease-in-out 2; }
@keyframes aiPulse { 0%,100% { box-shadow: 0 0 0 0 rgba(0,153,68,0); } 50% { box-shadow: 0 0 0 4px rgba(0,153,68,0.2); } }
```

Dropzone: `2px dashed var(--tp-gray-300)`; `.dragover` = green border + `scale(1.01)` + glow ring; `.has-file` = solid green border + `rgba(0,153,68,.04)` tint; 56px circular gradient icon.

## Modals

Confirmation modal (canonical):
```html
<div class="modal fade" id="confirmModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content border-0 shadow">
      <div class="modal-header border-0 pb-0">
        <h5 class="modal-title fw-bold"><i class="bi bi-shield-check text-success me-2"></i>Confirm &amp; Proceed</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        <p class="mb-2">Are you sure?</p>
        <p class="text-muted small mb-0"><i class="bi bi-info-circle me-1"></i>Secondary context line.</p>
      </div>
      <div class="modal-footer border-0 pt-0">
        <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Back</button>
        <button type="button" class="btn btn-tp-green px-4" onclick="confirmAction()"><i class="bi bi-box-arrow-up-right me-2"></i>Confirm</button>
      </div>
    </div>
  </div>
</div>
```

Compact yes/no: `modal-dialog-centered modal-sm`, `border-radius:14px`, big centered icon (`bi-question-circle-fill text-warning` at 2.5rem), `flex-fill` footer buttons at `.85rem`. Success variant: `bi-check-circle-fill text-success` at 3rem + `data-bs-backdrop="static" data-bs-keyboard="false"`.

Large form modal: `modal-lg modal-dialog-centered modal-dialog-scrollable`, 16px radius, gradient blue header (`linear-gradient(135deg, var(--tp-blue), #003a7a)`) with `btn-close-white`, body `max-height:75vh; overflow-y:auto`. Under 576px: full-screen, sticky footer, `font-size:16px` on inputs (prevents iOS zoom).

Full-page loading overlay:
```css
.extract-overlay { position: fixed; inset: 0; z-index: 1090; background: rgba(0,0,0,0.45);
    display: flex; align-items: center; justify-content: center;
    opacity: 0; visibility: hidden; transition: opacity .3s ease, visibility .3s ease; }
.extract-overlay.show { opacity: 1; visibility: visible; }
.extract-overlay-card { background:#fff; border-radius:16px; padding:40px 36px; text-align:center;
    box-shadow: 0 8px 40px rgba(0,0,0,.2); max-width:360px; width:90%; }
.extract-overlay-card .spinner-border { width:3rem; height:3rem; border-width:.3rem; }
```

## Badges

```css
.badge-status { padding: .4em 1em; border-radius: 50px; font-weight: 600; font-size: .8rem;
    letter-spacing: .3px; display: inline-flex; align-items: center; gap: 4px; }
.badge-status::before { content:''; width:6px; height:6px; border-radius:50%; display:inline-block; }
.badge-active  { background: rgba(0,153,68,.1);   color: var(--tp-green-dark); } .badge-active::before  { background: var(--tp-green); }
.badge-pending { background: rgba(255,152,0,.1);  color: #e65100; }             .badge-pending::before { background:#ff9800; animation: pulse-dot 2s infinite; }
.badge-expired { background: rgba(158,158,158,.1);color:#616161; }              .badge-expired::before { background:#9e9e9e; }
.badge-rejected{ background: rgba(244,67,54,.1);  color:#c62828; }              .badge-rejected::before{ background:#f44336; }
.badge-claimed { background: rgba(0,79,159,.1);   color: var(--tp-blue-dark); } .badge-claimed::before { background: var(--tp-blue); }
@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:.4} }

.tyre-badge { width:28px; height:28px; border-radius:8px; display:inline-flex; align-items:center;
    justify-content:center; font-weight:700; font-size:.75rem; background: var(--tp-green); color:#fff; }
```

Server-computed status style (tinted bg + saturated text on `badge rounded-pill fw-semibold`):
```csharp
string StatusBadgeStyle(string code) => code switch {
    "Active"   => "background: rgba(0,153,68,0.12); color: #009944;",
    "Pending"  => "background: rgba(255,163,0,0.15); color: #c47600;",
    "Rejected" => "background: rgba(220,53,69,0.12); color: #dc3545;",
    "Claimed"  => "background: rgba(0,79,159,0.12); color: #004F9F;",
    _          => "background: var(--tp-gray-100); color: var(--tp-gray-500);"
};
```

## Tabs (status-filter lists)

Plain Bootstrap `nav-tabs` + count badges (`bg-secondary` all / `bg-warning text-dark` in-progress / `bg-success` approved / `bg-danger` rejected); one `tab-pane` per pre-filtered partial. Mobile: `flex-wrap:nowrap; overflow-x:auto; -webkit-overflow-scrolling:touch;` on the strip.

## Tables & lists

```css
.table-tp { border-collapse: separate; border-spacing: 0; border-radius: var(--tp-radius-sm); overflow: hidden; font-size: .88rem; }
.table-tp thead th { background: var(--tp-gray-100); font-size:.72rem; text-transform:uppercase; letter-spacing:.5px;
    color: var(--tp-text-secondary); font-weight:700; padding:.75rem; border-bottom:2px solid var(--tp-gray-200); }
.table-tp tbody tr:hover { background-color: rgba(0,153,68,0.03); }
.table-tp tbody td { padding:.75rem; vertical-align:middle; border-bottom:1px solid var(--tp-gray-100); }
```

Below `md`: desktop table in `d-none d-md-block`, separate stacked card list for mobile. Action state travels via `data-*` attributes read by a delegated click handler — never inline JSON.

Empty state: `card card-tp` → 80px grey icon circle → bold H5 → muted copy (`max-width:360px`) → green CTA.

## Hero & action cards

```css
.hero-banner { border-radius: var(--tp-radius-lg); overflow: hidden; line-height: 0; }
.hero-banner-img { width: 100%; height: auto; display: block; border-radius: var(--tp-radius-lg); }
@media (max-width: 767.98px) { .hero-banner { border-radius: 12px; } }
```

Action card (home page 3-up row):
```html
<a asp-controller="X" asp-action="Y" class="action-card action-card-green text-decoration-none">
  <div class="action-card-bg-icon"><i class="bi bi-shield-check"></i></div>
  <div class="action-card-inner">
    <div class="action-card-icon"><i class="bi bi-clipboard-plus"></i></div>
    <h5 class="fw-bold mb-1">Register</h5>
    <p class="mb-0">One-line description</p>
  </div>
  <div class="action-card-arrow"><i class="bi bi-arrow-right"></i></div>
</a>
```
`.action-card` = min-height 200px gradient tile, 16px radius, oversized rotated watermark icon at 8% opacity, glassy 44px icon square, circular arrow sliding right on hover; flips to a compact horizontal row on mobile. Gradients: green `linear-gradient(160deg, #00b341 0%, var(--tp-green) 40%, #005c22 100%)`, blue `linear-gradient(160deg, #0069d9 0%, var(--tp-blue) 40%, #002d6b 100%)`, dark `linear-gradient(160deg, #3d3d3d 0%, #2d3436 40%, #1a1a2e 100%)` + `border: 1px solid rgba(255,229,0,.15)`.

## Scroll reveal + toasts

```js
const observer = new IntersectionObserver(entries => entries.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('visible'); observer.unobserve(e.target); }
}), { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
document.querySelectorAll('.fade-in-up, .fade-in-left, .fade-in-right, .scale-in').forEach(el => observer.observe(el));
```

Toast pattern (no library):
```html
<div id="successToast" class="alert alert-success alert-dismissible fade show position-fixed"
     style="top:1.5rem;right:1.5rem;z-index:9999;min-width:300px;" role="alert">
  <i class="bi bi-check-circle-fill me-2"></i>@TempData["Success"]
  <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
```
```js
setTimeout(() => bootstrap.Alert.getOrCreateInstance(document.getElementById('successToast'))?.close(), 6000);
```

Button-busy idiom:
```js
btn.disabled = true;
btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
// restore original innerHTML in finally
```

## Tom Select

Global wrapper (site.js):
```js
window.initTpSearchableSelect = function (selectEl, options) {
    if (!selectEl) return null;
    if (typeof TomSelect === 'undefined') { console.warn('TomSelect not loaded; native <select> fallback.'); return null; }
    if (selectEl.tomselect) { try { selectEl.tomselect.destroy(); } catch (e) {} }
    const defaults = {
        placeholder: 'Select...', allowEmptyOption: true, maxOptions: null, create: false,
        sortField: { field: 'text', direction: 'asc' },
        render: { no_results: (data, escape) => '<div class="no-results">No matches for "' + escape(data.input) + '"</div>' }
    };
    return new TomSelect(selectEl, Object.assign({}, defaults, options || {}));
};
```

Per-instance inside overflow containers (wizard panels, cards):
```js
initTpSearchableSelect(sel, {
    placeholder: 'Select item',
    openOnFocus: true,          // false causes stuck-closed state after programmatic pre-select
    dropdownParent: 'body',     // escape overflow:hidden clipping
    onChange: function () { onItemChange(sel); }
});
if (savedVal && sel.tomselect) {
    sel.tomselect.setValue(savedVal, true);   // silent
    sel.tomselect.close();                    // then force clean closed state
    sel.tomselect.blur();
}
```

Required CSS companions (per page using TS in overflow containers):
```css
.ts-dropdown { z-index: 9999 !important; }
.ts-wrapper  { overflow: visible !important; }
```
Theme: green focus ring `0 0 0 .15rem var(--tp-green-glow)`, green active/selected options, `select.is-invalid + .ts-wrapper .ts-control { border-color:#dc3545; }`.

Two-phase init: populate the native `<select>` while hidden; call the TS init only when the panel becomes visible. Add a document-level delegated `change` listener as backup for callbacks lost across destroy/recreate.

## Flatpickr

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css" />
<script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>

<input type="text" class="form-control date-picker" id="InvoiceDatePicker" placeholder="DD/MM/YYYY" autocomplete="off" required data-msg="Date is required" />
<input asp-for="InvoiceDate" type="hidden" id="InvoiceDate" />
```
```js
flatpickr('#InvoiceDatePicker', {
    dateFormat: 'd/m/Y',
    allowInput: true,
    onChange: function(selectedDates) {
        if (selectedDates.length) {
            const d = selectedDates[0];   // build ISO from LOCAL parts — never toISOString() (TZ drift)
            document.getElementById('InvoiceDate').value =
                d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
        } else { document.getElementById('InvoiceDate').value = ''; }
    }
});
```
Rehydrate: `el._flatpickr.setDate(d, false)`; clear: `el._flatpickr.clear()`.

## Leaflet outlet picker

```js
map = L.map('outletMap', { zoomControl: true, scrollWheelZoom: true }).setView([4.2, 108.5], 6); // Malaysia
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors', maxZoom: 19 }).addTo(map);

function buildLogoIcon(logoUrl, ringColor) {
    return L.divIcon({
        className: '',
        html: `<div style="width:44px;height:44px;background:#fff;border-radius:50% 50% 50% 0;border:3px solid ${ringColor};box-shadow:0 3px 8px rgba(0,0,0,0.35);transform:rotate(-45deg);display:flex;align-items:center;justify-content:center;"><img src="${logoUrl}" style="width:28px;height:28px;object-fit:contain;transform:rotate(45deg);" /></div>`,
        iconSize: [44, 52], iconAnchor: [22, 52], popupAnchor: [0, -48]
    });
}
const primaryIcon = buildLogoIcon('@Url.Content("~/images/brand-logo.png")', '#009944');   // green ring
const partnerIcon = buildLogoIcon('@Url.Content("~/images/partner-icon.png")', '#004F9F'); // blue ring
```

- No radius circles — proximity is "X.X km away" text + `map.fitBounds(bounds, { padding: [30,30], maxZoom: 13 })`; selected outlet `setView([lat,lng], 15)`.
- Defer init until the panel is visible, then `map.invalidateSize()`.
- Picker layout: flex row, 380px map left / 340px scrollable list right; stacked 240px map + 250px list under 768px.

```css
.outlet-picker-item.selected { background: rgba(0,153,68,.12); border-left: 4px solid var(--tp-green);
    box-shadow: inset 0 0 0 1px rgba(0,153,68,.35); padding-right: 96px; }
.outlet-picker-item.selected::after { content: "\2713 Selected"; position:absolute; top:10px; right:12px;
    background: var(--tp-green); color:#fff; font-size:.7rem; font-weight:700; padding:3px 8px; border-radius:999px; line-height:1; }
```

## Validation & fetch conventions

```js
function setFieldError(field, message) {
    field.classList.add('is-invalid');
    let feedback = field.parentElement?.querySelector('.invalid-feedback');
    // walk ancestors through input-groups if not found
    if (feedback) feedback.textContent = message;
    field.addEventListener('input', () => field.classList.remove('is-invalid'), { once: true });
}
// On step-validation failure: panel.classList.add('wizard-shake') for 500ms + focus first .is-invalid
```

Anti-forgery on AJAX:
```js
const formData = new FormData(form);
const token = form.querySelector('input[name="__RequestVerificationToken"]')?.value;
const response = await fetch('@Url.Action("Submit", "Claim")', {
    method: 'POST', headers: token ? { 'RequestVerificationToken': token } : {}, body: formData });
```

Rules:
- Endpoints always via `@Url.Action(...)` — never hard-coded paths (virtual-directory safety).
- Responses are `{ success, message, ... }` JSON; every handler try/catch/finally + button-state restore.
- Escape all JS-built HTML via `div.textContent`-based helper.
- Debounce search inputs 400ms, min 2 chars.
- In Razor inline JS regexes, escape `@` as `@@` (e.g. email regex).
