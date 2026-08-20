---
name: sms-notification-templates
description: DB-templated SMS/WhatsApp notification system for ASP.NET Core — Master_NotificationTemplate lookups by TemplateCode+CompanyID, placeholder substitution ([link]/{TOKEN} string replace), dynamic values from a SystemInformation key/value table, swallow-and-log error contract (notifications never fail the business operation), firing notifications from idempotent write cores so retries never double-send, OneWaySMS gateway mechanics, idempotent template seed scripts. Use when adding SMS notifications, notification templates, message placeholders, or transactional messaging to a project.
---

# DB-Templated SMS Notification System

You are adding transactional SMS (optionally WhatsApp) notifications where message bodies live in a DATABASE template table (ops can edit copy without redeploy), dynamic values come from a key/value config table, and sends can never break the business operation that triggered them.

Full reference code (service methods verbatim, gateway mechanics, seed scripts) is in [references/implementation.md](references/implementation.md) — load it before implementing.

## Architecture

```
Business event (e.g. payment recorded)
  → INotificationService.SendTemplatedSmsAsync(templateCode, mobile, placeholders, companyId)
      1. SELECT TOP 1 SMSMessage FROM Master_NotificationTemplate
         WHERE TemplateCode=@Code [AND CompanyID=@CompanyID] AND Status='A'
      2. foreach placeholder: body = body.Replace(key, value)   ← key IS the full token, e.g. "[link]"
      3. ISmsService.SendSmsAsync(mobile, body)                 ← provider-specific transport
  → GetSystemValueAsync(parameter): SELECT Value FROM Master_SystemInformation WHERE Parameter=@p
```

Two-layer split: `INotificationService` (template + placeholders + config values, provider-agnostic) / `ISmsService` (gateway transport, swappable). Register both Scoped; API tier only — the web tier reaches notifications only through API calls.

## The five rules

1. **Never throw to the caller.** Every failure path in the notification service is log + `return false`: template missing, gateway rejection, DB error, anything. The business operation (payment, approval) must never fail or roll back because SMS hiccupped. Callers discard the bool; the log is the audit.
2. **Fire from the idempotent write core, AFTER the state transition.** Put the send at the bottom of the same method that has the "already done → no-op" guard (e.g. payment recording). The notification inherits the operation's idempotency for free — webhook retries and racing confirmation channels still yield exactly ONE SMS. Never notify at intent time (e.g. registration-before-payment) — abandoned flows must not message users.
3. **Placeholder keys are full literal tokens.** The dictionary key is `"[link]"` or `"{REASON}"`, not `link`. Substitution is plain `string.Replace` in dictionary order; null values become empty string. Pick ONE delimiter style project-wide (the reference accidentally had both `[link]` and `{LINK}` — works, but a caller passing the wrong style silently ships the raw token to the customer). Add a post-substitution unresolved-token check: `Regex.IsMatch(body, @"\{[A-Z]+\}|\[[a-z]+\]")` → log warning.
4. **The notification service never auto-resolves config.** Callers read dynamic values (`GetSystemValueAsync("SiteUrl")`) and pass them in the placeholder map — keeps the service dumb and testable.
5. **Templates are seeded idempotently**: one script per template, `IF NOT EXISTS (... TemplateCode + CompanyID ...) INSERT ... PRINT 'Inserted' ELSE PRINT 'Skipped'`, trailing `GO`. Config parameters same pattern keyed on `Parameter`, with `-- TODO: replace` markers on placeholder values. Never commit real secrets in seeds.

## Data model

- `Master_NotificationTemplate(TemplateCode, SMSMessage, EmailSubject, EmailContent, CompanyID, Status, LastModDate, LastModBy)` — SMS reads only `SMSMessage`; the email columns carry the same tokens so a future email sender reuses the identical placeholder dictionary.
- Lookup: `companyId` supplied → strict equality, NO fallback to a global row (missing scoped row = no SMS); `companyId` null → match any company. `Status='A'` always. `TOP 1` with no ORDER BY means duplicate rows are non-deterministic — the idempotent seeds are what prevent that.
- `Master_SystemInformation(Parameter, Value, Description)` — global key/value runtime config (public URLs for `[link]`, support contact numbers, provider settings). No caching in the reference — add caching only if you accept staleness on ops edits.
- Gateway credentials in a company table row (or config) — read at send time, so ops can rotate without redeploy.

## Gateway notes (OneWaySMS reference; swap `ISmsService` for other providers)

Two sequential HTTP GETs: submit (returns an MT id) then status poll (`"0"`/`"100"` = success). Credentials as query params, ISO-8859-1 encoding; Unicode messages (any char > 127) switch `languagetype` to 2 with UCS-2 hex encoding (`{0:x4}` per char). Mobile format for the gateway: digits only, `60` country prefix (distinct from the app's canonical `+60...` — convert inside the SMS service only). Log the URL with the query string STRIPPED (`url.Split('?')[0]`) so credentials never land in logs. Parameterize the sender ID (the reference hard-coded a brand).

WhatsApp (Infobip-style): same config-in-DB convention (`WhatsAppApiBaseUrl` / `WhatsAppApiKey` / `WhatsAppFromNumber` parameters), `POST {base}/whatsapp/1/message/template` with `Authorization: App <apiKey>` — implement as another `ISmsService`-style transport behind the same notification facade.

## Logging conventions

Structured templates, PascalCase holes, never interpolation. Full rendered body at Information before send (deliberate audit trail — accept that links/PII land in logs, or mask); template-missing and gateway-rejection at Warning; exceptions at Error with the exception first. IDs in payment-side logs, never PII.

## Upgrades worth making over the reference

- Background dispatch (queue/outbox + `IHostedService`) instead of sending inline in the HTTP request — the reference held a payment webhook connection open across two gateway round-trips. Safe to change: no caller uses the return value.
- `IHttpClientFactory` with timeout/retry instead of `new HttpClient()` per send.
- One placeholder delimiter + unresolved-token guard.
- Company-scoped gateway credentials if genuinely multi-tenant (the reference hard-coded one company row).
- Message-length awareness (SMS segments) if templates grow.
