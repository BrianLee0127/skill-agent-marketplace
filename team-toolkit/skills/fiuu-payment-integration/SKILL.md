---
name: fiuu-payment-integration
description: Integrate the Fiuu (formerly Razer/MOLPay) hosted-page payment gateway (FPX/card, Malaysia) into an ASP.NET Core project. Non-seamless redirect flow with MD5 vcode request signing, two-stage skey webhook verification, webhook-authoritative payment recording with idempotency, CBTOKEN:MPSTATOK ack, payment log table, status polling page, sandbox vs live config. Use when adding Fiuu/MOLPay/FPX online-banking payment, payment callbacks, or debugging "payment info format is not correct" errors.
---

# Fiuu Payment Gateway Integration (Hosted Page, Malaysia)

You are integrating Fiuu's non-seamless hosted-page flow: your server builds a signed redirect URL, the customer pays on Fiuu's page, and Fiuu reports the result over TWO independent channels — a server-to-server webhook (authoritative) and a browser return (informational only). Currency: MYR.

Full copy-paste implementation (C# + SQL, proven in production) lives in [references/implementation.md](references/implementation.md) — load it before writing any code. This file gives the architecture and the rules that must not be violated.

## Architecture

```
Customer → Web app → POST create-payment (server) ──builds──> signed hosted-page URL
                                                              (vcode = MD5 request signature)
Customer pays on Fiuu's page
Fiuu ──server-to-server──> POST /fiuu-callback   ← AUTHORITATIVE: verifies skey, records payment,
                                                    must reply literal "CBTOKEN:MPSTATOK" (text/plain)
Fiuu ──browser redirect──> returnurl → your "PaymentSuccess" page → POST /fiuu-return
                                                  ← verifies skey, READ-ONLY paid check, never records
PaymentSuccess page polls GET /payment-status every 3s (~60s) until paid/failed flips
```

Keys live server-side only (DB key/value table or secret store) — never in the web tier, never in client code, never committed to git.

## Non-negotiable rules

1. **Only the webhook records payment.** The browser return is unreliable (closed tab, network drop) and races the webhook. Recording on return WILL create false-paid rows. The return endpoint verifies the signature and reports whether the webhook already recorded — nothing else.
2. **Recording must be idempotent.** Fiuu retries the webhook until it receives the exact ack; guard with "already Paid → no-op" before any write.
3. **Webhook ack is the literal string `CBTOKEN:MPSTATOK`** as `text/plain`. Anything else = Fiuu marks delivery failed and retries.
4. **Outbound signature (vcode):** `MD5(amount + merchantID + orderid + verifyKey [+ currency])` — lowercase hex, no separators. The `+ currency` suffix applies ONLY when the merchant account's "extended vcode" dashboard toggle is on. This toggle is account-level and NOT derivable from code — store it as config (`FiuuExtendedVcode`) and keep it mirrored with the dashboard. Mismatch = every payment rejected with **"Your payment info format is not correct"** before the customer picks a bank (the #1 integration failure). Self-check at `https://api.fiuu.com/RMS/query/vcode.php`.
5. **Inbound signature (skey), two stages:** `key0 = MD5(tranID + orderid + status + domain + amount + currency)`; `skey = MD5(paydate + domain + key0 + appcode + secretKey)` (`domain` = merchant ID). Compare case-insensitively. Use `paydate` as the RAW string received — reformatting breaks the hash (store it as NVARCHAR, not DATETIME). A missing/bad skey is never treated as paid.
6. **Amount is a 2-dp decimal string** (`25.00`, invariant culture), NOT cents — and the exact same string goes into the vcode hash and the `amount` query param.
7. **`bill_mobile` digits only.** A `+`, space, or dash triggers the same "payment info format is not correct" error.
8. **URL shape:** `{paymentBaseUrl}{merchantID}/?{urlencoded query}` — trailing slash after merchant ID required. Sandbox base `https://sandbox-payment.fiuu.com/RMS/pay/` (merchant IDs prefixed `SB_`), live `https://pay.fiuu.com/RMS/pay/`.
9. **The callback URL must be public HTTPS and exempt from your API auth** (Fiuu can't send your Authorization header) — the skey IS its security. Keep an explicit allow-list, not a blanket auth bypass.
10. **`returnurl` must include the request PathBase** (IIS virtual-directory safety); `callbackurl` must point at the public API host, not the web host.

## Config (DB key/value, API-side only)

| Key | Purpose |
|---|---|
| `FiuuMerchantID` | Merchant ID (= `domain` in skey); `SB_` prefix in sandbox |
| `FiuuVerifyKey` | Private key → builds outbound vcode |
| `FiuuSecretKey` | Secret key → verifies inbound skey |
| `FiuuPaymentUrl` | Hosted-page base URL (trailing slash), sandbox vs live |
| `FiuuExtendedVcode` | `'true'`/`'false'` — must mirror the dashboard toggle |

Seed with idempotent `IF NOT EXISTS` INSERT scripts holding placeholders; set real keys directly in the DB per environment. Why DB not appsettings: no secrets in git, ops can rotate without redeploy, web tier never sees them.

## Status codes & polling

Gateway `status`: `00` success · `11` failed · `22` pending. The payment-status endpoint returns `{ paid, failed, status }`: `paid` from the business header (set only by the webhook), `failed` when not paid AND the latest gateway-log row is `11`. The processing page polls every 3s up to ~20 tries, swapping pre-rendered processing/success/failed blocks in place — never reloading (a reload re-POSTs the gateway return). On timeout, soften the message; don't declare failure.

## Known hardening gaps to fix in a new implementation (see references §8)

- Put the record core in a DB transaction or use a conditional `UPDATE ... WHERE PaymentStatus IS NULL` — the guard-then-write isn't atomic.
- Consider replying non-200 to the webhook if the DB write throws (otherwise Fiuu stops retrying while nothing was recorded).
- Payment-status column must be at least `VARCHAR(10)` — a legacy `VARCHAR(3)` truncates `'Paid'` to `'Pai'` and paid-detection silently never fires.
- Validate order exists/unpaid in the create endpoint if double-billing matters to you.
- Plan an abandoned-registration sweep: records created before payment stay `PaymentStatus IS NULL` forever when the customer abandons; clean children-first in a transaction after a minimum age.
