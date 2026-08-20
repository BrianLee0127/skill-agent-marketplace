# OpenAI Vision OCR — Reference Implementation

Production-proven. The domain here is a tyre-warranty invoice + DOT sidewall code; adapt field lists to your document type, keep the mechanics and prompt patterns.

## 1. Service — the OpenAI call

```csharp
public class InvoiceService : IInvoiceService
{
    private readonly string _apiKey;
    private readonly string _model;              // default "gpt-4o"
    private readonly int _invoiceMaxTokens;      // default 2000
    private readonly int _dotMaxTokens;          // default 50
    private static readonly JsonSerializerOptions JsonOptions = new() { PropertyNameCaseInsensitive = true };

    public async Task<InvoiceExtractDto?> ExtractInvoiceDataAsync(byte[] imageBytes, string contentType)
    {
        var base64Data = Convert.ToBase64String(imageBytes);
        var dataUri = $"data:{contentType};base64,{base64Data}";

        // PDFs go as a file part; images as image_url
        object fileContent = contentType.ToLower() == "application/pdf"
            ? new { type = "file", file = new { filename = "invoice.pdf", file_data = dataUri } }
            : (object)new { type = "image_url", image_url = new { url = dataUri, detail = "high" } };

        var requestBody = new
        {
            model = _model,
            messages = new object[]
            {
                new { role = "user", content = new object[]
                    { new { type = "text", text = GetInvoicePrompt() }, fileContent } }
            },
            max_tokens = _invoiceMaxTokens,
            temperature = 0.0
        };

        // NEW BUILDS: use IHttpClientFactory + timeout + CancellationToken + 429/5xx retry
        using var httpClient = new HttpClient();
        httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", _apiKey);
        var response = await httpClient.PostAsync("https://api.openai.com/v1/chat/completions",
            new StringContent(JsonSerializer.Serialize(requestBody), Encoding.UTF8, "application/json"));

        if (!response.IsSuccessStatusCode)
        {
            _logger.LogError("OpenAI API call failed with status {StatusCode}: {Error}",
                (int)response.StatusCode, await response.Content.ReadAsStringAsync());
            return null;
        }

        var result = JsonSerializer.Deserialize<JsonElement>(await response.Content.ReadAsStringAsync());
        var content = result.GetProperty("choices")[0].GetProperty("message").GetProperty("content").GetString();
        if (string.IsNullOrEmpty(content)) return null;
        // guard this in new builds: try/catch JsonException → null
        return JsonSerializer.Deserialize<InvoiceExtractDto>(ExtractJsonFromResponse(content), JsonOptions);
    }

    // No response_format on vision → strip fences defensively
    private static string ExtractJsonFromResponse(string content)
    {
        content = content.Trim();
        if (content.StartsWith("```"))
        {
            var firstNewline = content.IndexOf('\n');
            if (firstNewline > 0) content = content[(firstNewline + 1)..];
            if (content.EndsWith("```")) content = content[..^3];
            content = content.Trim();
        }
        return content;
    }
}
```

## 2. The prompts (verbatim — these took many iterations)

### Document (invoice) extraction — JSON contract prompt

```
You are an OCR assistant for a tyre warranty registration system. Extract data from this invoice image and return ONLY valid JSON (no markdown, no explanation).

Rules:
- Extract customer name, phone number, vehicle plate number, vehicle brand, vehicle model, car type, mileage, invoice number, and invoice date.
- Customer name: look for a real personal (human) name in this priority order:
  1. The "Bill To" / "Customer" / "Nama" / "Sold To" field.
  2. If that field is blank, generic ("CASH SALES", "CASH", "TUNAI", "WALK IN"), or a company name, fall back to the "Attn." / "Attention" / "Kepada" field.
  A value is a PERSONAL name if it looks like a Malaysian individual's name — e.g. "AHMAD BIN HASSAN", "LEE CHEE KEONG", "PRIYA A/P RAJU", "TAN AH KOW". A value is a COMPANY name (return null) if it contains any of: "SDN BHD", "SDN.", "BHD", "PLT", "LLP", "& CO", "PTE LTD", "ENTERPRISE", "TRADING", "AUTOCARE", "AUTO CENTRE", "AUTO CENTER", "CENTRE", "CENTER", "SERVICES", "ACCESSORIES", "INDUSTRIES", "HOLDINGS", "GROUP", "SDN", or any other obvious business-entity keyword. Also return null if the value is purely generic cash-sale text. When in doubt whether a value is a person or company, return null.
- Car type: classify as one of exactly "Fuel", "Hybrid", "BEV", or "Diesel". Look for explicit labels like "Fuel Type", "Engine Type", "Powertrain", or infer from the model name when unambiguous (e.g. "Tesla Model 3" → "BEV", "Toyota Camry Hybrid" → "Hybrid", "Hilux 2.4D / 2.8D" or "TDi" / "CRDi" / "dCi" → "Diesel"). If unclear or not stated, return null — do not guess.
- Extract all TYRE items only (ignore labour charges, alignment, balancing, etc.).
- IMPORTANT: Check the quantity (Qty) column for each tyre line item. If Qty is greater than 1, create that many separate tyre entries in the output array. For example, if a line shows "225/55R19 PRIMACY 5" with Qty 4, output 4 separate tyre objects (each with the same pattern, size, description, and unit price).
- For each tyre, extract: pattern name, size, full description, DOT/serial code, and unit price (use the UNIT price, not the line total).
- Tyre size format: Malaysian invoices sometimes omit the "R" before the rim diameter (e.g. "245/45/17" instead of the standard "245/45R17"). Always normalise to the standard format with R (e.g. "245/45R17", "225/55R19"). The third number in the slash-separated string is the rim size in inches.
- If serial/DOT codes are listed as a comma-separated string (e.g. "CODE1,CODE2,CODE3,CODE4"), split them and assign one per tyre in order.
- For inchCategory: if the rim size (e.g. R17, R19) is 17 or above, use "ABOVE_17", otherwise use "BELOW_17".
- Phone numbers: return in local Malaysian format without country code (e.g. "0194421988" not "+60194421988").
- Mileage: return as integer, strip leading zeros.
- Invoice date: Look ONLY for the header-level date field labeled "Bill Date", "Invoice Date", "Date", "Sales Date", "Tarikh" or similar — this is the date the invoice was issued. Malaysian invoices use DD/MM/YYYY format. Example: "Bill Date: 07/03/2026" means 7th March 2026 → return "2026-03-07". Return ONLY in "yyyy-MM-dd" format. NEVER extract dates from DOT codes (e.g. 1W8JN039X0326), serial numbers, tyre descriptions, mileage figures, or any product line items.
- Vehicle plate number: look for fields labeled "Plate No", "No. Plate", "Vehicle No", "Reg No", "Registration", or simply "Vehicle" — a short alphanumeric value like "BMB20", "WXY1234", "ABC 1234" in those fields is the registration plate, NOT the model name. Extract it as plateNumber.
- Vehicle brand and model: look for fields labeled "Model", "Make", "Brand", "Vehicle Model", or a combined "BRAND MODEL" string (e.g. "MAZDA CX-8", "MERCEDES-BENZ E200"). When "Model" appears as a separate labeled field distinct from "Vehicle" (which holds the plate), use that field for brand/model extraction. Split into brand and model separately.
- Outlet name: the tyre shop / dealer business name printed in the invoice header (usually at the top — e.g. "LNP AUTOCARE SDN BHD - SEPANG"). Return the full registered business name exactly as printed. Do NOT return "TyrePlus" or "Michelin" brand text (those are the franchise / product brand, not the outlet). Do NOT include the street address.
- If a field cannot be found, set it to null.

Return this exact JSON structure:
{
  "customerName": "string or null",
  "mobileNumber": "string or null",
  "plateNumber": "string or null",
  "brand": "string or null",
  "model": "string or null",
  "carType": "Fuel | Hybrid | BEV | Diesel | null",
  "mileage": 0,
  "invoiceNumber": "string or null",
  "invoiceDate": "yyyy-MM-dd or null",
  "outletName": "string or null",
  "tyres": [
    {
      "tyrePattern": "e.g. PRIMACY 5",
      "tyreSize": "e.g. 225/55R19",
      "tyreDescription": "full description from invoice",
      "dotCode": "DOT code for this tyre (e.g. 1W8JN039X0326)",
      "serialNumber": "only if a SEPARATE serial number exists on the invoice distinct from the DOT code, otherwise null",
      "price": 0.00,
      "inchCategory": "ABOVE_17 or BELOW_17"
    }
  ]
}
```

Reusable pattern per rule: field name → where to look (label synonyms incl. local language) → what it looks like → what it is NOT → output format with worked example → null-over-guess.

### Single-value (DOT code) extraction — plain-text contract prompt

```
You are an OCR assistant for tyre warranty registration. The image shows a tyre sidewall.

Extract the DOT code (Tyre Identification Number, TIN). The DOT code:
- Is preceded by the word 'DOT' on the sidewall (you may ignore the 'DOT' prefix)
- Is alphanumeric, 11 to 13 characters total, often arranged in groups (e.g. 'H2LF YA9J 3507')
- Ends with 4 digits = manufacture week + year (e.g. '3507' = week 35 of 2007)

CHARACTER ACCURACY — be very careful with look-alike characters:
- 0 vs O: tyre DOT codes do NOT use the letter 'O'. ALWAYS read it as the digit 0 — anywhere in the code, not just the date suffix.
- The LAST 4 characters are ALWAYS digits (week + year). Never read them as letters: read 'O' as 0, 'I'/'L' as 1, 'S' as 5, 'Z' as 2, 'B' as 8 when they appear in these final 4 positions.
- Distinguish the digit 1 from the letters I/L by their shape and surrounding context.

Return ONLY the full code as a single uppercase string with NO spaces, NO 'DOT' prefix, NO explanation, NO punctuation.

Example output: H2LFYA9J3507

If no DOT code is clearly visible in the image, return exactly: NONE
```

### Deterministic post-processing (belt and braces — never trust the prompt alone)

```csharp
var raw = content.Trim().ToUpperInvariant();
if (raw == "NONE" || raw.Contains("NOT FOUND") || raw.Contains("UNREADABLE")) return null;
if (raw.StartsWith("DOT")) raw = raw.Substring(3);
var cleaned = new string(raw.Where(char.IsLetterOrDigit).ToArray());
if (cleaned.Length < 11 || cleaned.Length > 13) return null;   // length sanity
cleaned = cleaned.Replace('O', '0');                            // domain rule: no letter O
cleaned = NormalizeDotDateSuffix(cleaned);                      // known-digit positions
return cleaned;

private static char LetterToDigit(char c) => c switch
{
    'O' or 'Q' or 'D' => '0', 'I' or 'L' => '1', 'Z' => '2',
    'S' => '5', 'G' => '6', 'B' => '8', _ => c
};
private static string NormalizeDotDateSuffix(string code)
{
    if (code.Length < 4) return code;
    var chars = code.ToCharArray();
    for (int i = chars.Length - 4; i < chars.Length; i++) chars[i] = LetterToDigit(chars[i]);
    return new string(chars);
}
```

## 3. DTO

```csharp
public class InvoiceExtractDto
{
    public string? CustomerName { get; set; }
    public string? MobileNumber { get; set; }
    public string? PlateNumber { get; set; }
    public string? Brand { get; set; }
    public string? Model { get; set; }
    public string? CarType { get; set; }
    public int? Mileage { get; set; }
    public string? InvoiceNumber { get; set; }
    public string? InvoiceDate { get; set; }   // yyyy-MM-dd string, parsed client/server side
    public string? OutletName { get; set; }    // fuzzy-matched to the outlet picker
    public List<InvoiceTyreDto> Tyres { get; set; } = new();
}
```

camelCase model output ↔ PascalCase DTO works via `PropertyNameCaseInsensitive = true`.

## 4. API endpoints (conditional service)

```csharp
[ApiController]
[Route("api/[controller]")]
public class InvoiceController : ControllerBase
{
    private readonly IInvoiceService? _invoiceService;
    // GetService (not ctor injection) → missing key degrades to 503, not DI crash
    public InvoiceController(IServiceProvider sp) => _invoiceService = sp.GetService<IInvoiceService>();

    [HttpPost("extract")]
    [RequestSizeLimit(10 * 1024 * 1024)]
    public async Task<IActionResult> Extract(IFormFile file)
    {
        if (_invoiceService == null)
            return StatusCode(503, new { Message = "Invoice extraction service is not configured." });
        if (file == null || file.Length == 0) return BadRequest(new { Message = "No file uploaded." });
        var allowedTypes = new[] { "image/jpeg", "image/png", "image/webp", "image/gif", "application/pdf" };
        if (!allowedTypes.Contains(file.ContentType.ToLower()))
            return BadRequest(new { Message = "Only image files (JPEG, PNG, WebP, GIF) and PDF are supported." });
        // copy to MemoryStream → ExtractInvoiceDataAsync(bytes, file.ContentType)
        // null → 500 { Message }; success → Ok(result)
    }

    [HttpPost("extract-dot")]
    [RequestSizeLimit(10 * 1024 * 1024)]
    public async Task<IActionResult> ExtractDot(IFormFile file)
    {
        // same guards, images only. NEVER 500 on a failed read — return
        // 200 { success = false, message = "Could not read a code from this photo. Please try again with better lighting." }
        // success → Ok(new { success = true, dotCode })
    }
}
```

DI (conditional on real key):

```csharp
var openAiKey = configuration["OpenAI:ApiKey"] ?? "";
var openAiModel = configuration["OpenAI:Model"] ?? "gpt-4o";
var invoiceMaxTokens = configuration.GetValue<int?>("OpenAI:MaxTokens:Invoice") ?? 2000;
var dotMaxTokens = configuration.GetValue<int?>("OpenAI:MaxTokens:Dot") ?? 50;
if (!string.IsNullOrEmpty(openAiKey) && openAiKey != "-- YOUR OPENAI API KEY --")
    services.AddScoped<IInvoiceService>(sp => new InvoiceService(
        openAiKey, openAiModel, invoiceMaxTokens, dotMaxTokens,
        sp.GetRequiredService<ILogger<InvoiceService>>()));
```

## 5. Web multipart proxy

```csharp
[HttpPost]
public async Task<IActionResult> ExtractInvoice(IFormFile invoiceFile)
{
    try
    {
        using var ms = new MemoryStream();
        await invoiceFile.CopyToAsync(ms);
        ms.Position = 0;

        var content = new MultipartFormDataContent();
        var fileContent = new StreamContent(ms);
        fileContent.Headers.ContentType = new MediaTypeHeaderValue(invoiceFile.ContentType);
        content.Add(fileContent, "file", invoiceFile.FileName);   // API's param name is "file"

        var client = _httpClientFactory.CreateClient("TPPApi");
        var response = await client.PostAsync("api/invoice/extract", content);
        // ALWAYS return 200-with-JSON so browser response.json() never throws:
        // success → Json(new { success = true, data = <raw JsonElement> })
        // failure → Json(new { success = false, message = <unwrapped API message or generic> })
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "ExtractInvoice threw");
        return Json(new { success = false, message = "Extraction service is unavailable. Please fill in the form manually." });
    }
}
// ExtractDot: same multipart pattern, but pass the API body straight through:
// return Content(body, "application/json");   — and DO wrap it in try/catch (the reference forgot)
```

## 6. Frontend

### Dropzone + camera

```html
<div class="invoice-dropzone" id="invoiceDropzone" onclick="document.getElementById('InvoiceFile').click();">
    <input class="d-none" id="InvoiceFile" type="file" accept=".jpg,.jpeg,.png,.webp,.pdf"
           onchange="handleInvoiceSelect(this)" />
    <input type="file" class="d-none" id="InvoiceCameraInput" accept="image/*" capture="environment"
           onchange="handleCameraCapture(this)" />
    <!-- camera icon button calls event.stopPropagation() so it doesn't also trigger browse -->
</div>
```

```js
// Drag&drop / camera → copy the file into the REAL posted input via DataTransfer
dropzone.addEventListener('drop', e => {
    const file = e.dataTransfer.files[0];
    if (file) {
        const input = document.getElementById('InvoiceFile');
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        showInvoicePreview(file);   // sets _invoicePresent = true, then extractInvoiceData(file)
    }
});
```

### Overlay with skip

```js
// showExtractOverlay(): spinner + "Auto-filling your details..." +
//   <button class="btn-skip" onclick="hideExtractOverlay()">Skip, I'll fill in manually</button>
// (skip only hides — the fetch continues and still autofills when it lands)
// updateExtractOverlay(success, message): tick/warning icon, button label → "Continue",
//   setTimeout(() => hideExtractOverlay(), 2000);
```

### Fetch + autofill

```js
const formData = new FormData();
formData.append('invoiceFile', file);
const response = await fetch('@Url.Action("ExtractInvoice", "Warranty")', { method: 'POST', body: formData });
const result = await response.json();
if (result.success && result.data) autoFillForm(result.data);
else showStatus('Could not extract data. Please fill in manually.');

// setField(name, value): set value + classList.add('ai-filled'); for date fields also
// drive the Flatpickr instance (picker._flatpickr.setDate(d, true)); NEVER fill readonly
// session-derived fields (e.g. mobile). After all fills:
document.querySelectorAll('.ai-filled').forEach(el => {
    el.classList.add('ai-highlight');
    setTimeout(() => el.classList.remove('ai-highlight'), 2000);
});
```

```css
.ai-filled { border-color: var(--brand) !important; background-color: rgba(0,153,68,0.04) !important; }
.ai-highlight { animation: aiPulse 0.6s ease-in-out 2; }
@keyframes aiPulse { 0%,100% { box-shadow: 0 0 0 0 rgba(0,153,68,0); }
                     50% { box-shadow: 0 0 0 4px rgba(0,153,68,0.2); } }
```

### Per-row scan button + counter lock

```js
// One camera input per row: <input type="file" accept="image/*" capture="environment"
//                                  class="d-none dot-photo-input" data-row="@i" />
let _scansActive = 0;
function setScanBusy(busy) {
    _scansActive += busy ? 1 : -1;
    if (_scansActive < 0) _scansActive = 0;
    const nextBtn = document.getElementById('btnNext');
    if (_scansActive > 0) {
        nextBtn.disabled = true;
        nextBtn.dataset.originalHtml = nextBtn.dataset.originalHtml || nextBtn.innerHTML;
        nextBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Reading...';
    } else {
        nextBtn.disabled = false;
        if (nextBtn.dataset.originalHtml) { nextBtn.innerHTML = nextBtn.dataset.originalHtml;
            delete nextBtn.dataset.originalHtml; }
    }
}
// handler: setScanBusy(true) → fetch → on success set value + .ai-filled + dispatch
// synthetic input/change events (so existing validators run on the OCR value) →
// finally { setScanBusy(false); fileInput.value = ''; /* re-scan same file re-fires change */ }
```

### Catalog/entity fuzzy matching (post-OCR)

```js
// Product match: exact normalized size match mandatory; then token-overlap on
// description+pattern requiring >= 1 non-size common token; no match → WIPE the OCR
// values and force manual pick (never keep unmatched authoritative fields).
// Entity (outlet) match: normalize by dropping legal-entity noise tokens
// ['SDN','BHD','ENTERPRISE','TRADING','SERVICES', <your brand words>], token-set
// similarity, threshold >= 0.5.
```

### Validation of extracted values

The scan handler dispatches `input`/`change`; existing validators run identically on typed and OCR'd values. Mirror every client rule server-side (throw `InvalidOperationException` → 400). Prices and other authoritative values never come from OCR — only from the catalog after a successful match.

## 7. Config

```jsonc
"OpenAI": {
  "ApiKey": "<user-secret — NEVER commit>",
  "Model": "gpt-4o",
  "MaxTokens": { "Invoice": 2000, "Dot": 50 }
}
```
