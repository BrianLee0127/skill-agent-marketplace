---
name: field-validation-standards
description: Audit every user-input field in an ASP.NET Core MVC (Webmax/TPP) project and enforce standard, consistent validation — email, Malaysian phone, IC/NRIC, postcode, car plate, currency, dates, OTP, passwords, file uploads and more. Applies client-side AND server-side rules, normalizes formats, and reports fields missing validation. Use before shipping any form, or when reviewing an existing project for validation gaps.
category: Backend
---

# Field Validation Standards (ASP.NET Core MVC — Webmax/TPP)

Enforce **one consistent validation standard** across every input field in the project. You go
through all forms, view models / DTOs, and API request models, identify each field's *type*, and
make sure it has correct **client-side AND server-side** validation plus **normalization**
(trim, casing, format). Fields that touch money, identity, or auth must never rely on client-side
checks alone.

## How to run this audit

1. **Find every input surface:** Razor forms (`.cshtml` with `<input>`/`asp-for`), view models,
   DTOs, `[FromBody]`/`[FromForm]` request models, and any JS that posts data.
2. **Classify each field** by the catalogue below (email? phone? IC? amount?).
3. **For each field, ensure all three layers exist:**
   - **Server (authoritative):** DataAnnotations on the model (`[Required]`, `[EmailAddress]`,
     `[RegularExpression]`, `[StringLength]`, `[Range]`) or a FluentValidation validator, checked
     with `ModelState.IsValid`.
   - **Client (UX):** matching jQuery Unobtrusive Validation / HTML5 attributes so users get
     instant feedback. Client rules must mirror server rules, never replace them.
   - **Normalization:** trim whitespace, lower-case emails, strip separators from phone/IC, before
     storing.
4. **Report gaps:** list every field that is missing a layer, then fix them.
5. Never trust client validation for security-relevant fields (amount, IDs, roles) — always
   re-validate on the server.

## Fields that need validation (the catalogue)

### Contact
| Field | Rule | Regex / attribute | Normalize |
|---|---|---|---|
| **Email** | RFC email, required if primary contact | `[EmailAddress]` + `^[^@\s]+@[^@\s]+\.[^@\s]+$` | trim, lower-case |
| **Mobile phone (MY)** | Malaysian mobile, 01X | `^(\+?60|0)1\d{7,9}$` | strip spaces/`-`, store as `01XXXXXXXX` or `+60…` |
| **Landline (MY)** | area code + number | `^(\+?60|0)[3-9]\d{6,8}$` | strip separators |
| **Website / URL** | valid http(s) URL | `[Url]` | trim, add scheme if missing |

### Identity (Malaysia)
| Field | Rule | Regex | Notes |
|---|---|---|---|
| **IC / NRIC (MyKad)** | 12 digits `YYMMDD-PB-###G` | `^\d{6}-\d{2}-\d{4}$` (or 12 digits) | validate the date part + state code `PB`; store digits only |
| **Old IC / passport** | alphanumeric | `^[A-Z0-9]{5,12}$` | upper-case |
| **Company reg. no. (SSM)** | new `YYYYMMDDNNNNN` (12 digit) or old `NNNNNN-X` | `^(\d{12}|\d{6,7}-[A-Z])$` | |
| **Car plate (MY)** | letters + digits, optional space | `^[A-Z]{1,3}\s?\d{1,4}\s?[A-Z]?$` | upper-case, single space |

### Address
| Field | Rule | Regex | Notes |
|---|---|---|---|
| **Postcode (MY)** | 5 digits | `^\d{5}$` | required with address |
| **State** | from a fixed list | dropdown, not free text | validate against enum |
| **Address line** | length-bounded | `[StringLength(200)]` | trim |

### Money & numbers
| Field | Rule | Attribute | Notes |
|---|---|---|---|
| **Amount / price** | ≥ 0, 2 decimals, max cap | `[Range(0, 1000000)]` + regex `^\d+(\.\d{1,2})?$` | **server-authoritative** — never trust the client amount for payment |
| **Quantity / mileage** | positive integer, range | `[Range(1, 9999999)]` | |
| **Percentage** | 0–100 | `[Range(0,100)]` | |

### Dates & time
| Field | Rule | Notes |
|---|---|---|
| **Date of birth** | valid date, not future, sane age (e.g. 12–120 yrs) | derive from IC if present and cross-check |
| **Appointment date/time** | valid, not in the past, within business hours / lead time | validate against outlet hours |
| **Expiry / warranty date** | valid date, ≥ today for future-dated | |

### Auth & security
| Field | Rule | Notes |
|---|---|---|
| **Password** | min 8, mix of letters+digits (project policy) | never log; hash server-side |
| **OTP / TAC** | exactly 6 digits, numeric, single-use, expiry | `^\d{6}$`; verify server-side, rate-limit |
| **Confirm password / confirm email** | must match the original | server-side compare |

### Files (for the OCR / upload features)
| Field | Rule | Notes |
|---|---|---|
| **Image / document upload** | allowed types (jpg/png/pdf), max size (e.g. 10 MB) | check MIME + extension server-side; reject others |

### Free text
| Field | Rule | Notes |
|---|---|---|
| **Name** | letters/spaces/`.'-`, length 2–100 | `^[A-Za-z .'\-@/]{2,100}$`; trim; title-case optional |
| **Notes / remarks** | length cap, strip/encode HTML | `[StringLength(1000)]`; prevent XSS on display |

## ASP.NET Core implementation patterns

- **DataAnnotations** for the common cases:
  ```csharp
  [Required, EmailAddress, StringLength(150)]
  public string Email { get; set; }

  [Required, RegularExpression(@"^(\+?60|0)1\d{7,9}$", ErrorMessage = "Enter a valid Malaysian mobile number")]
  public string Mobile { get; set; }

  [Range(0, 1000000)]
  public decimal Amount { get; set; }
  ```
- **Reusable custom attributes** for MY-specific formats (`[MalaysianMobile]`, `[Nric]`, `[CarPlate]`)
  so the rule lives in one place and is applied everywhere.
- **FluentValidation** when rules get conditional (e.g. IC required only for members).
- **Client mirror:** enable jQuery Unobtrusive Validation so the DataAnnotations render as client
  rules automatically; add custom `data-val-*` adapters for the custom attributes.
- **Normalize in the setter or a mapping step** before persistence (trim, lower-case email, strip
  phone/IC separators).
- **Always** guard the action with `if (!ModelState.IsValid) return View(model);` — client checks
  are UX only.

## When updating

- New field type in the project → add a row to the catalogue with its rule + regex + how to apply.
- Changed a shared format (e.g. how phone numbers are stored) → update the normalize column and the
  custom attribute so every form stays consistent.
