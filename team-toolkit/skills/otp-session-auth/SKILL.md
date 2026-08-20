---
name: otp-session-auth
description: OTP-over-SMS (TAC) login with session-flag auth for ASP.NET Core MVC — no Identity, no JWT. Covers OTP generation/expiry/single-use, auto-signup of new users, mobile number normalization (+60 canonical form), OtpBypass config for local dev and Playwright, Pending-to-real session key promotion with multi-outlet selection, SessionAuthFilter (AJAX 401 vs redirect with returnUrl), 30-min idle timeout UX, and role gating (Consumer/Dealer). Use when building phone-number login, TAC verification, or session-based auth in a microsite.
---

# OTP-over-SMS Login + Session Auth (ASP.NET Core MVC)

You are building phone-number login: user enters mobile → gets a 6-digit TAC by SMS → verifies → a session is established. Auth state is ONLY session keys guarded by one `IActionFilter` — no ASP.NET Identity, no cookie-auth scheme, no JWT. Architecture: Web MVC (holds session) → named HttpClient with Basic auth → API (`/api/sms/*`) → SMS service (DB-backed OTP storage) → SMS gateway.

Full reference code (controllers, service, filter, views, SQL) is in [references/implementation.md](references/implementation.md) — load it before implementing. This file gives the flow and the invariants.

## Flow

```
Login page: [+60][ mobile ] [ TAC ] [Get TAC]
  Get TAC → POST /Auth/SendOtp (AJAX) → API send-otp → generate 6-digit code,
            upsert user if new, store OTP+expiry on user row, send SMS
            (60s client countdown on the button; label Get TAC → Sending… → 59s… → Resend)
  LOG IN  → POST /Auth/Login → API verify-otp → 200 {roleName, customerID, companyID, outlets[]}
            → Consumer: FinalizeSession → redirect (returnUrl or Home)
            → Dealer:   stage Pending* keys → SelectOutlet page → POST commits chosen outlet
                        → FinalizeSession + clear Pending* → redirect
```

## Invariants (violating any of these has bitten before)

1. **One canonical mobile format everywhere.** Normalize at the web boundary (`NormalizeMobile`: accept `0121234567`, `121234567`, `60...`, `+60...` → always `+60121234567`) and use that exact string for OTP send, OTP verify, the session key, and every DB row. It is the join key across the whole app. (The SMS gateway needs its own reformat — digits only, `60` prefix — done inside the SMS service only.)
2. **OTP is stored BEFORE the SMS is attempted** (columns `OTP VARCHAR(10)`, `OTPExpired DATETIME` on the user row). This is what makes the bypass work without a gateway, and means a gateway failure doesn't strand the user.
3. **Single-use:** NULL the OTP columns on successful verify. Each resend overwrites — only the newest code is valid. Expiry 5 minutes.
4. **Opaque failure:** wrong code, expired code, unknown user, never-issued — all return the same 401 "Invalid or expired OTP" (no user enumeration).
5. **Auto-signup on send:** unknown mobile → insert user with role `Consumer` (looked up by RoleName), a fixed CompanyID, `CreatedBy='SYSTEM'`. Dealers are provisioned manually, never auto-created.
6. **Dealer-wins tiebreak:** if one mobile maps to multiple active users, prefer the Dealer row (`ORDER BY CASE WHEN RoleName='Dealer' THEN 0 ELSE 1 END, UserID`).
7. **`IsAuthenticated` is never set during the pending phase.** Dealer multi-outlet selection stages `PendingMobileNumber` / `PendingRoleName` / `PendingOutlets` / `PendingDefaultCustomerId` / `PendingReturnUrl`; a half-logged-in dealer is as unauthorized as an anonymous visitor. The POST that commits the outlet re-validates the chosen id against the server-side pending list (forged POST can't pick a foreign outlet), promotes via `FinalizeSession`, then removes all Pending keys.
8. **Every returnUrl consumption is guarded by `Url.IsLocalUrl()`** (open-redirect safe). The filter builds it as `PathBase + Path + QueryString` (IIS virtual-dir safe).
9. **OtpBypass** (dev/Playwright): config `OtpBypass: { Enabled, Code, Mobiles[] }` — bypass only when ALL of: enabled AND code non-empty AND code matches AND mobile is allow-listed (case-insensitive HashSet). Bypass skips the DB OTP check but still runs role/outlet resolution, so the session is identical to a real login. Enabled only in `appsettings.Development.json`; prod config has it off. Tests fill the TAC directly and never click "Get TAC" (real SMS is unreliable in CI); bypass users must pre-exist in the DB.

## Session keys

| Key | Value |
|---|---|
| `IsAuthenticated` | `"true"` — the ONLY flag the filter checks |
| `MobileNumber` | canonical `+60...` |
| `UserRole` | `"Consumer"` / `"Dealer"` / other |
| `CustomerID`, `CompanyID` | ints (dealer's chosen outlet + company) |

Session config: `AddSession(IdleTimeout = 30 min, Cookie.HttpOnly, Cookie.IsEssential)`; `app.UseSession()` after `UseRouting()`, before `UseAuthorization()`.

## SessionAuthFilter

Registered `AddScoped`, applied per-controller with `[ServiceFilter(typeof(SessionAuthFilter))]`. Auth/Home/public controllers carry no filter. Behavior on unauthenticated: AJAX (`X-Requested-With: XMLHttpRequest` or Accept contains `application/json`) → 401 JSON `{ sessionExpired: true, message: "Session expired" }`; otherwise → redirect to Login with returnUrl.

## Timeout UX

Authenticated pages get an idle-timer script: 30-min client timer (MUST match server IdleTimeout) reset only by intentful events (`click`/`keydown`/`touchstart` — NOT mousemove/scroll, which don't hit the server), plus 401 interception on both jQuery ajaxError and a patched `window.fetch`, all funneling to a SessionTimeout page that clears the session and offers re-login. Use a `redirecting` latch to prevent double-navigation.

## Role gating

Roles compared by NAME, case-insensitive, everywhere. UI hiding (nav items, buttons) is defence-in-depth only — every gate has a server twin: page GETs redirect non-allowed roles, AJAX POSTs return explicit `403` + JSON message. Unknown/other roles fail closed (view-only).

## Hardening checklist for a new implementation (gaps found in the reference)

- Add server-side OTP rate limiting (reject resend < 60s, cap per mobile+IP per hour) — the reference has only a cosmetic client countdown.
- Compare OTPs with `CryptographicOperations.FixedTimeEquals`; use UTC times.
- Implement failed-attempt lockout (the `LoginAttempt` column existed but was never incremented).
- Use a distributed session store (SQL/Redis) if you need farm support or app-pool-recycle survival — default in-memory sessions die on recycle.
- Add `Cookie.SecurePolicy = Always`, `SameSite = Lax`.
- Prefer a GLOBAL auth filter + explicit anonymous opt-out — per-controller opt-in means new controllers are public by default.
- Never echo raw API error bodies/exception text to the browser in the send-OTP proxy.
- Add `[ValidateAntiForgeryToken]` on the outlet-selection POST; make Logout a POST.
- Don't store a shared plaintext default password on auto-created users — drop the column or store a random hash.
