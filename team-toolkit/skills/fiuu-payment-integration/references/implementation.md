# Fiuu Integration — Reference Implementation (C# / ASP.NET Core + SQL Server)

Proven-in-production code. Adapt names (`RHP_*` tables, `Warranty` wording) to your domain — the mechanics must stay exactly as shown. All credential values are placeholders.

## 1. Config seed (SQL, idempotent)

```sql
IF NOT EXISTS (SELECT 1 FROM Master_SystemInformation WHERE Parameter = 'FiuuMerchantID')
    INSERT INTO Master_SystemInformation (Parameter, Value, Description)
    VALUES ('FiuuMerchantID', 'SB_<MerchantName>', 'Fiuu Merchant ID (sandbox IDs prefixed SB_).');
GO
IF NOT EXISTS (SELECT 1 FROM Master_SystemInformation WHERE Parameter = 'FiuuVerifyKey')
    INSERT INTO Master_SystemInformation (Parameter, Value, Description)
    VALUES ('FiuuVerifyKey', '<REDACTED-VERIFY-KEY>', 'Fiuu Verify Key (private key) — used to build the request vcode.');
GO
IF NOT EXISTS (SELECT 1 FROM Master_SystemInformation WHERE Parameter = 'FiuuSecretKey')
    INSERT INTO Master_SystemInformation (Parameter, Value, Description)
    VALUES ('FiuuSecretKey', '<REDACTED-SECRET-KEY>', 'Fiuu Secret Key — used to verify the return/callback skey.');
GO
IF NOT EXISTS (SELECT 1 FROM Master_SystemInformation WHERE Parameter = 'FiuuPaymentUrl')
    INSERT INTO Master_SystemInformation (Parameter, Value, Description)
    VALUES ('FiuuPaymentUrl', 'https://sandbox-payment.fiuu.com/RMS/pay/', 'Fiuu hosted payment base URL (trailing slash). Sandbox vs live.');
GO
IF NOT EXISTS (SELECT 1 FROM Master_SystemInformation WHERE Parameter = 'FiuuExtendedVcode')
    INSERT INTO Master_SystemInformation (Parameter, Value, Description)
    VALUES ('FiuuExtendedVcode', 'false', 'true = vcode includes currency (extended vcode); false = standard. Must match the Fiuu account setting.');
GO
```

Set real keys post-deploy with a direct `UPDATE`. Reader: `SELECT TOP 1 Value FROM Master_SystemInformation WHERE Parameter = @Parameter` (swallow-and-log on error, return null).

## 2. Gateway log table

```sql
CREATE TABLE Fiuu_Payment_Log (
    ID                  INT IDENTITY(1,1) PRIMARY KEY,
    OrderID             NVARCHAR(100)   NOT NULL,            -- = your business reference no (Fiuu "orderid")
    TranID              NVARCHAR(50)    NULL,                -- Fiuu transaction id (null until callback)
    UserID              INT             NULL,
    TransactionAmount   DECIMAL(18,2)   NOT NULL DEFAULT 0,
    Currency            NVARCHAR(10)    NULL,
    Status              NVARCHAR(20)    NULL,                -- pending / 00 (success) / 11 (fail) / 22 (pending)
    AppCode             NVARCHAR(50)    NULL,                -- Fiuu approval code
    PayDate             NVARCHAR(50)    NULL,                -- KEEP AS STRING — participates in skey hash
    ErrorCode           NVARCHAR(50)    NULL,
    ErrorDesc           NVARCHAR(500)   NULL,
    Channel             NVARCHAR(50)    NULL,                -- FPX bank / card channel (audit only)
    RawResponse         NVARCHAR(MAX)   NULL,                -- full callback payload for audit
    TransactionDateTime DATETIME        NOT NULL DEFAULT GETDATE(),
    LastModifiedDate    DATETIME        NULL
);
CREATE INDEX IX_Fiuu_Payment_Log_OrderID ON Fiuu_Payment_Log(OrderID);
```

Lifecycle: `create` inserts `'pending'` → callback UPDATEs in place by OrderID (before the signature gate, so bad-signature attempts still leave a raw audit trail) → return never writes. A retry inserts another pending row for the same OrderID; polling reads `TOP 1 ... ORDER BY ID DESC`.

Your business payment table needs at minimum: `PaymentStatus VARCHAR(10)` (NOT smaller — `'Paid'` truncates on VARCHAR(3)), `PaymentDate`, `TransactionRefNo NVARCHAR(50)`, `PaymentID`.

## 3. Create payment (outbound)

```csharp
[HttpPost("create-fiuu")]
public async Task<IActionResult> CreateFiuu([FromBody] CreateFiuuRequest request)
{
    var merchantId = await _config.GetSystemValueAsync("FiuuMerchantID");
    var verifyKey  = await _config.GetSystemValueAsync("FiuuVerifyKey");
    var paymentUrl = await _config.GetSystemValueAsync("FiuuPaymentUrl");
    if (string.IsNullOrWhiteSpace(merchantId) || string.IsNullOrWhiteSpace(verifyKey) || string.IsNullOrWhiteSpace(paymentUrl))
        return StatusCode(500, new { success = false, message = "Payment gateway is not configured." });

    // Fiuu expects amount as a decimal with 2 places (e.g. "25.00"), NOT cents.
    var amountStr = request.Amount.ToString("0.00", CultureInfo.InvariantCulture);
    var orderId = request.OrderId ?? string.Empty;
    const string currency = "MYR";

    // vcode: extended = MD5(amount+merchantID+orderid+verifyKey+currency); standard omits currency.
    // Toggle must mirror the Fiuu dashboard "extended vcode" account setting.
    // Self-check a generated vcode at https://api.fiuu.com/RMS/query/vcode.php
    var extendedVcode = string.Equals(await _config.GetSystemValueAsync("FiuuExtendedVcode"),
        "true", StringComparison.OrdinalIgnoreCase);
    var vcode = extendedVcode
        ? Md5(amountStr + merchantId + orderId + verifyKey + currency)
        : Md5(amountStr + merchantId + orderId + verifyKey);

    // Insert 'pending' log row here (OrderID, UserID, Amount, 'MYR', 'pending', GETDATE()).

    var baseUrl = paymentUrl.EndsWith("/") ? paymentUrl : paymentUrl + "/";
    var query = new Dictionary<string, string?>
    {
        ["amount"]      = amountStr,
        ["orderid"]     = orderId,
        ["bill_name"]   = string.IsNullOrWhiteSpace(request.Name) ? "Customer" : request.Name,
        ["bill_email"]  = request.Email ?? string.Empty,
        // Fiuu rejects '+' (any non-digit) in bill_mobile with "payment info format is not correct"
        ["bill_mobile"] = new string((request.Mobile ?? string.Empty).Where(char.IsDigit).ToArray()),
        ["bill_desc"]   = string.IsNullOrWhiteSpace(request.Description) ? $"Payment - {orderId}" : request.Description,
        ["country"]     = "MY",
        ["currency"]    = currency,
        ["vcode"]       = vcode,
        ["returnurl"]   = request.ReturnUrl ?? string.Empty,
        ["callbackurl"] = request.CallbackUrl ?? string.Empty
    };
    var qs = string.Join("&", query.Select(kv =>
        $"{Uri.EscapeDataString(kv.Key)}={Uri.EscapeDataString(kv.Value ?? string.Empty)}"));
    var redirectUrl = $"{baseUrl}{Uri.EscapeDataString(merchantId)}/?{qs}";
    return Ok(new { success = true, paymentUrl = redirectUrl });
}

private static string Md5(string input)
{
    var bytes = MD5.HashData(Encoding.UTF8.GetBytes(input));
    var sb = new StringBuilder(bytes.Length * 2);
    foreach (var b in bytes) sb.Append(b.ToString("x2"));   // lowercase hex
    return sb.ToString();
}
```

Request DTO: `{ OrderId, Amount (decimal), Name, Email, Mobile, Description, ReturnUrl, CallbackUrl }`. OrderId convention: `{PREFIX}-{yyyyMMdd}-{9 uppercase GUID chars}` (`Guid.NewGuid().ToString("N").Substring(0, 9).ToUpper()`).

Caller (web tier) builds: `returnUrl = $"{Request.Scheme}://{Request.Host}{Request.PathBase}/Payment/Success?orderId=..."` (PathBase for IIS virtual dirs) and `callbackUrl = $"{publicApiBaseUrl}/api/payment/fiuu-callback"`. On create failure, fall back to a manual payment page instead of erroring the whole flow.

## 4. Signature verification (inbound, shared by callback + return)

```csharp
// key0 = MD5(tranID + orderid + status + domain + amount + currency)
// skey = MD5(paydate + domain + key0 + appcode + secretKey)     (domain = merchantID)
private async Task<bool> VerifyFiuuSignatureAsync(IReadOnlyDictionary<string, string?> f)
{
    var secretKey = await _config.GetSystemValueAsync("FiuuSecretKey") ?? string.Empty;
    var key0 = Md5(Get(f, "tranID") + Get(f, "orderid") + Get(f, "status") + Get(f, "domain") + Get(f, "amount") + Get(f, "currency"));
    var key1 = Md5(Get(f, "paydate") + Get(f, "domain") + key0 + Get(f, "appcode") + secretKey);
    var skey = Get(f, "skey");
    return !string.IsNullOrEmpty(skey) && string.Equals(skey, key1, StringComparison.OrdinalIgnoreCase);
}

private IReadOnlyDictionary<string, string?> ReadForm()
{
    var dict = new Dictionary<string, string?>(StringComparer.OrdinalIgnoreCase);
    if (Request.HasFormContentType)
        foreach (var kv in Request.Form) dict[kv.Key] = kv.Value.ToString();
    return dict;
}
private static string Get(IReadOnlyDictionary<string, string?> f, string key)
    => f.TryGetValue(key, out var v) ? v ?? string.Empty : string.Empty;
```

Use `paydate` exactly as received — never parse/reformat it.

## 5. Callback (authoritative webhook)

```csharp
// Server-to-server IPN. Fiuu retries until it receives the exact ack token.
[HttpPost("fiuu-callback")]
public async Task<IActionResult> FiuuCallback()
{
    var fields = ReadForm();
    var result = await ProcessFiuuResponseAsync(fields, "callback");
    if (!result.SignatureValid) return BadRequest("Invalid signature");
    return Content("CBTOKEN:MPSTATOK", "text/plain");   // EXACT literal, text/plain
}
```

Auth exemption (Fiuu can't send your Authorization header) — explicit allow-list in your auth middleware:

```csharp
private static readonly string[] PublicPaths = { "/api/payment/fiuu-callback" };
// skip auth when path.StartsWith any PublicPath (OrdinalIgnoreCase); skey verification is the security
```

Shared processing core:

```csharp
private async Task<(bool SignatureValid, bool Paid, string Status)> ProcessFiuuResponseAsync(
    IReadOnlyDictionary<string, string?> f, string source)
{
    var orderId = Get(f, "orderid"); var status = Get(f, "status"); var tranId = Get(f, "tranID");
    var signatureValid = await VerifyFiuuSignatureAsync(f);

    // 1. UPDATE Fiuu_Payment_Log by OrderID (TranID, Status, AppCode, PayDate, Currency,
    //    ErrorCode, ErrorDesc, Channel, RawResponse = JsonSerializer.Serialize(f), LastModifiedDate)
    //    — BEFORE the signature gate, so forged attempts leave an audit trail.

    if (!signatureValid) return (false, false, status);

    // status "00" = success, "11" = failed, "22" = pending
    if (status == "00" && !string.IsNullOrWhiteSpace(orderId))
    {
        // 2. Resolve your business record by reference no (orderid), get customer mobile from DB
        //    (not from the request).
        // 3. Parse amount invariant: decimal.TryParse(Get(f,"amount"), NumberStyles.Any,
        //    CultureInfo.InvariantCulture, out var amt)
        // 4. await RecordPaymentCoreAsync(conn, recordId, orderId, mobile, "FIUU", tranId, amt, "Paid via Fiuu");
        return (true, true, status);
    }
    return (true, false, status);
}
```

## 6. Return (read-only) + status polling

```csharp
[HttpPost("fiuu-return")]
public async Task<IActionResult> FiuuReturn()
{
    var f = ReadForm();
    var orderId = Get(f, "orderid");
    var signatureValid = await VerifyFiuuSignatureAsync(f);
    var paid = signatureValid && !string.IsNullOrWhiteSpace(orderId) && await IsRecordPaidAsync(orderId);
    return Ok(new { signatureValid, gatewayStatus = Get(f, "status"), paid });
    // NEVER records. Doesn't even write the log.
}

[HttpGet("status/{id:int}")]
public async Task<IActionResult> PaymentStatus(int id)
{
    // paid   ← business header PaymentStatus = 'Paid' (only the webhook sets this)
    // failed ← NOT paid AND latest Fiuu_Payment_Log.Status = '11' for this record's ref
    //          (SELECT TOP 1 Status ... WHERE OrderID = header.RefNo ORDER BY ID DESC)
    return Ok(new { paid, failed, status = payStatus });
}
```

Web tier forwards the browser's return POST to `fiuu-return` as `FormUrlEncodedContent` (collect fields form-first then query-fallback, case-insensitive). Page logic:
- gatewayStatus `11` → failed view (with "Try Again" → back to payment page)
- signature ok but `paid == false` (status 00/22, webhook not yet landed) → "Processing" view + polling
- `paid == true` → success view
- No gateway fields at all → treat as processing; **never record here** (this exact mistake previously produced false paid rows).

Polling JS: pre-render `#processingBlock` (visible) + `#successBlock`/`#failedBlock` (`d-none`); `setInterval` 3000ms, max 20 tries; on `paid` reveal success, on `failed` reveal failed, on timeout soften the message ("may still be processing — check back in a few minutes") without declaring failure; swap blocks in place, never reload (reload re-POSTs the return).

## 7. Idempotent record core

```csharp
// Inserts the payment row, flips the business header to Paid, writes the audit log and
// fires the confirmation SMS — exactly once. Already 'Paid' → no-op (webhook retries +
// alternate confirmation paths can both fire).
private async Task<(bool Recorded, int? PaymentId)> RecordPaymentCoreAsync(
    SqlConnection connection, int recordId, string? refNo, string? mobileNumber,
    string paymentMethod, string? paymentRef, decimal paidAmount, string? remarks)
{
    // 1. IDEMPOTENCY GUARD
    //    SELECT PaymentStatus FROM <Header> WHERE ID = @id
    //    if 'Paid' (OrdinalIgnoreCase) → log + return (false, null)

    // 2. Insert payment row: INSERT INTO <Payment> (..., Currency='MYR', PaidDate=GETDATE(),
    //    PaidStatus='SUCCESS', CreatedBy='SYSTEM') OUTPUT INSERTED.PaymentID

    // 3. UPDATE <Header> SET PaymentID=@pid, PaymentStatus='Paid', PaymentDate=GETDATE(),
    //    TransactionRefNo=@paymentRef WHERE ID=@recordId

    // 4. Audit/workflow log insert — in its OWN try/catch (log failure must not fail the record)

    // 5. LAST: fire the confirmation SMS/notification (errors swallowed by the notification
    //    service) — placing it here means abandoned payments never notify, and the SMS
    //    inherits the payment's idempotency for free.

    return (true, paymentId);
}
```

Hardening upgrades over the reference (recommended): wrap steps 1–3 in a transaction, or make step 3 `UPDATE ... WHERE ID=@id AND (PaymentStatus IS NULL OR PaymentStatus <> 'Paid')` and check rows-affected — the plain guard-then-write is not atomic under truly simultaneous callbacks. Also consider returning non-200 from the callback when the DB write throws, so Fiuu keeps retrying (the reference swallows the exception and acks anyway).

Expose the same core via `POST api/payment/record` for gateway-less confirmation paths (e.g. DuitNow QR "I've completed payment") — the shared idempotency makes races between channels harmless.

## 8. Testing & ops

- Sandbox: `https://sandbox-payment.fiuu.com/RMS/pay/`, merchant `SB_...`. Live: `https://pay.fiuu.com/RMS/pay/`, no prefix.
- Simulate a success without the gateway: a SQL script mirroring the record core exactly (guard on already-Paid; deliberately skip the SMS).
- Abandoned-payment sweep (records created pre-payment that stay `PaymentStatus IS NULL`): daily job, `@MinAgeHours = 24`, delete children first (gateway log by OrderID, then routing/detail rows, header last) in a transaction, with a preview mode flag; skip anything referenced by downstream records.
- Vcode debugging: rejected before the bank list = signing problem (extended-vcode mismatch or non-digit bill_mobile); rejected after = usually amount/orderid mismatch.
