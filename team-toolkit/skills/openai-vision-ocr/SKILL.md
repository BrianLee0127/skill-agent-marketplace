---
name: openai-vision-ocr
description: OpenAI Vision OCR auto-fill for ASP.NET Core web forms — photograph/upload a document (invoice, label, tyre sidewall) and auto-populate form fields. Covers the Vision API call (base64 data URLs, PDF file parts, detail levels, max_tokens per use case), battle-tested prompt patterns (JSON contract prompts, look-alike character correction, null-over-guess rules), multipart proxy chain Web→API→OpenAI, conditional DI when no API key, .ai-filled highlight UX, camera capture inputs, scan-locks on wizard navigation, and validation of extracted values. Use when adding OCR, document extraction, photo-scan autofill, or GPT Vision to a form.
---

# OpenAI Vision OCR Form Auto-Fill

You are adding "photograph it and the form fills itself" to an ASP.NET Core app. Two proven variants: **document extraction** (invoice/receipt → many fields + line items, JSON contract) and **single-value extraction** (e.g. a code off a tyre sidewall → one string). Chain: browser JS → Web MVC multipart proxy → API endpoint → OpenAI `chat/completions` with an image part.

Full reference code (service, prompts verbatim, controllers, frontend JS) is in [references/implementation.md](references/implementation.md) — load it before implementing.

## Architecture rules

1. **The OpenAI key lives API-side only**, config `OpenAI: { ApiKey, Model, MaxTokens: { <UseCase>: n } }` — never in the web tier, never in the browser. Register the service **conditionally**: skip DI when the key is missing/placeholder, resolve with `IServiceProvider.GetService<T>()` in the controller, return **503** "not configured" instead of crashing.
2. **Model output is untrusted input.** Everything extracted flows through the SAME validation as typed input (fire synthetic `input`/`change` events after programmatic fill so existing validators run). Never let OCR values bypass business rules, and never take authoritative values (like prices) from OCR — take them from your catalog after matching.
3. **The user is never blocked.** Extraction failure = "please fill in manually", with every field still manually editable. A permanent caption tells users to verify AI-filled values.
4. **Prompt = the whole spec.** No system message needed — one user message with a text part (the full prompt) + one image/file part. `temperature: 0.0`. Demand "ONLY valid JSON (no markdown)" but STILL strip markdown fences defensively before parsing (no `response_format` guarantee on vision).
5. **Budget per use case**: separate `max_tokens` (e.g. 2000 for a full document, 50 for a single code) — the single-value cap is the main cost lever. Use `detail: "high"` only when reading small text; consider downscaling client-side (~1024px) before upload — the reference sent full phone photos and that's the biggest cost waste.

## Prompt engineering patterns that made this work (details + verbatim prompts in references)

- **JSON contract prompts**: end with "Return this exact JSON structure:" + a literal JSON skeleton including types and `"string or null"` markers. Deserialize case-insensitively into a DTO.
- **Null over guess**: for every inferred field, explicit "If unclear or not stated, return null — do not guess", plus domain-specific disambiguation lists (e.g. "a value is a COMPANY name (return null) if it contains: SDN BHD, PLT, ENTERPRISE, ...").
- **Quantity expansion**: "if Qty > 1, create that many separate entries" — otherwise line items with quantity collapse to one.
- **Format normalization in-prompt**: date "return ONLY yyyy-MM-dd" with a worked example, phone "local format without country code", domain formats (e.g. tyre size "normalise 245/45/17 → 245/45R17").
- **Negative instructions with examples**: "NEVER extract dates from DOT codes (e.g. 1W8JN039X0326), serial numbers, ..." — vision models grab plausible-looking values from the wrong place without these.
- **Look-alike character correction** for code reading: tell the model 0 vs O, I/L vs 1, S vs 5, Z vs 2, B vs 8 rules AND re-apply them deterministically in C# afterwards (belt and braces — map letters→digits in known-digit positions, length sanity check, reject out-of-range).
- **Sentinel for not-found**: "If no code is clearly visible, return exactly: NONE" — then check for it server-side.

## UX conventions

- Dropzone (click / drag / camera): hidden `<input type="file">` for browse + second hidden input with `capture="environment"` for the camera; `DataTransfer` shim to copy dropped/camera files into the real posted input.
- Full-page overlay with spinner + **"Skip, I'll fill in manually"** button (skip hides the overlay; the fetch continues and still fills when it lands). On completion: tick/warning icon, auto-dismiss ~2s.
- `.ai-filled` class (green border + tint) on every populated field + one `.ai-highlight` pulse animation; a "Clear" action must wipe ALL AI-filled state across steps.
- Per-item scan buttons (e.g. one camera per row): **counter-based busy lock** on the wizard's Next button (`_scansActive++/--`, disable + spinner label while > 0) — handles parallel scans; always decrement in `finally` and reset `fileInput.value = ''` so re-scanning the same file re-fires `change`.
- Fuzzy matching extracted names to your catalog (outlet names, product SKUs): normalize (drop legal-entity noise tokens), token-overlap score with a threshold; on no match, WIPE the OCR values for those fields and force manual selection.

## Hardening gaps to fix over the reference

- Use `IHttpClientFactory` (not `new HttpClient()` per call), set an explicit timeout, pass a `CancellationToken`, retry with backoff on 429/5xx.
- Guard the JSON deserialize (malformed model reply currently throws → 500) and the `choices[0]` access.
- Log the response `usage` object for cost tracking; consider per-session rate limiting.
- Enforce file size client-side too (the reference only enforced 10MB + MIME allow-list server-side via `[RequestSizeLimit]`).
- Rotate any committed API key immediately; use user-secrets/env.
