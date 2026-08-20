# SMS Notification Templates — Reference Implementation (C# / ASP.NET Core + SQL Server)

Production-proven. Rename tables/brand values to your project; keep the mechanics. All credentials shown as placeholders — never commit real ones.

## 1. Interface

```csharp
public interface INotificationService
{
    /// <summary>
    /// Looks up a Master_NotificationTemplate row by code (and optional company),
    /// substitutes placeholders in the SMS body, and sends via the SMS gateway.
    /// Failure is logged and swallowed — callers should not rely on this throwing.
    /// </summary>
    /// <param name="placeholders">Map of placeholder → value (e.g. { "[link]" => "https://..." }).
    /// The KEY is the full delimited token. Pass null/empty for none.</param>
    /// <param name="companyId">Optional company filter. Null = match any company.</param>
    /// <returns>True if dispatched; false if template missing or gateway rejected.</returns>
    Task<bool> SendTemplatedSmsAsync(string templateCode, string mobileNumber,
        IDictionary<string, string>? placeholders = null, int? companyId = null);

    /// <summary>Reads a single Value from Master_SystemInformation by Parameter name. Null if missing.</summary>
    Task<string?> GetSystemValueAsync(string parameter);
}
```

## 2. SendTemplatedSmsAsync (verbatim)

```csharp
public async Task<bool> SendTemplatedSmsAsync(string templateCode, string mobileNumber,
    IDictionary<string, string>? placeholders = null, int? companyId = null)
{
    try
    {
        // 1. Template lookup — connection in a using BLOCK so it closes BEFORE the
        //    outbound HTTP send (don't hold a DB connection across a gateway round-trip).
        string? smsBody = null;
        using (var connection = new SqlConnection(_connectionString))
        {
            await connection.OpenAsync();
            string sql = companyId.HasValue
                ? @"SELECT TOP 1 SMSMessage FROM Master_NotificationTemplate
                    WHERE TemplateCode = @Code AND CompanyID = @CompanyID AND Status = 'A'"
                : @"SELECT TOP 1 SMSMessage FROM Master_NotificationTemplate
                    WHERE TemplateCode = @Code AND Status = 'A'";
            using var cmd = new SqlCommand(sql, connection);
            cmd.Parameters.AddWithValue("@Code", templateCode);
            if (companyId.HasValue) cmd.Parameters.AddWithValue("@CompanyID", companyId.Value);
            var result = await cmd.ExecuteScalarAsync();
            if (result != null && result != DBNull.Value) smsBody = result.ToString();
        }

        if (string.IsNullOrWhiteSpace(smsBody))
        {
            _logger.LogWarning("SMS template {TemplateCode} not found (CompanyID={CompanyID}) — skipping send to {Mobile}",
                templateCode, companyId, mobileNumber);
            return false;
        }

        // 2. Placeholder substitution — key IS the full token ("[link]"), plain Replace,
        //    dictionary order, null value → empty string.
        if (placeholders != null)
            foreach (var kvp in placeholders)
                smsBody = smsBody.Replace(kvp.Key, kvp.Value ?? string.Empty);

        // (recommended addition) unresolved-token guard:
        // if (Regex.IsMatch(smsBody, @"\{[A-Z]+\}|\[[a-z]+\]"))
        //     _logger.LogWarning("Unresolved placeholder in {TemplateCode}: {Body}", templateCode, smsBody);

        // 3. Send. Full body logged at Information = deliberate audit trail.
        _logger.LogInformation("SMS outgoing [{TemplateCode} → {Mobile}]: {Body}", templateCode, mobileNumber, smsBody);
        var sent = await _smsService.SendSmsAsync(mobileNumber, smsBody);
        if (!sent)
            _logger.LogWarning("SMS gateway rejected templated message {TemplateCode} to {Mobile}", templateCode, mobileNumber);
        return sent;
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "Failed to send templated SMS {TemplateCode} to {Mobile}", templateCode, mobileNumber);
        return false;   // NEVER throw to the caller
    }
}
```

## 3. GetSystemValueAsync (verbatim)

```csharp
public async Task<string?> GetSystemValueAsync(string parameter)
{
    try
    {
        using var connection = new SqlConnection(_connectionString);
        await connection.OpenAsync();
        using var cmd = new SqlCommand(
            "SELECT TOP 1 Value FROM Master_SystemInformation WHERE Parameter = @Parameter", connection);
        cmd.Parameters.AddWithValue("@Parameter", parameter);
        var result = await cmd.ExecuteScalarAsync();
        return result == null || result == DBNull.Value ? null : result.ToString();
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "Failed to read system parameter {Parameter}", parameter);
        return null;   // missing and error look the same to callers — they coalesce with ??
    }
}
```

No caching — one round trip per call. Add an in-memory cache with short TTL only if you accept staleness on ops-edited values.

## 4. DI (API host only)

```csharp
services.AddScoped<ISmsService>(sp => new SmsService(
    connectionString, bypassEnabled, bypassCode, bypassMobiles,
    sp.GetRequiredService<ILogger<SmsService>>()));
services.AddScoped<INotificationService>(sp => new NotificationService(
    connectionString,
    sp.GetRequiredService<ISmsService>(),
    sp.GetRequiredService<ILogger<NotificationService>>()));
```

## 5. The canonical call site — inside the idempotent write core

```csharp
// Inside RecordPaymentCoreAsync — AFTER the idempotency guard ("already Paid → return")
// and AFTER the state transition committed. Ordering is the design:
//   guard → business writes → audit log (own try/catch) → SMS (last)
// The SMS inherits the operation's idempotency: gateway webhook retries and racing
// confirmation channels still produce exactly one message.

if (!string.IsNullOrEmpty(mobileNumber))
{
    var statusUrl = await _notifications.GetSystemValueAsync("TPPMicrositeUrl") ?? string.Empty;
    await _notifications.SendTemplatedSmsAsync(
        "RegistrationPending",
        mobileNumber,
        new Dictionary<string, string> { ["[link]"] = statusUrl },
        companyId: 1);
}
```

And the explicit non-call-site, at the end of the registration transaction:

```csharp
transaction.Commit();
// Consumer SMS notification is fired after successful payment by the payment core,
// not here — abandoned-payment registrations should not receive the "we're processing" message.
return (recordId, refNumber);
```

Why: business rows are created BEFORE payment, so unpaid/abandoned rows exist. Messaging those users would be false. Bind sends to the completed state transition, never to intent.

## 6. Seed scripts

### Template (one file per template)

```sql
-- =============================================================================
-- Insert "RegistrationPending" notification template.
-- Sent to the consumer right after payment is recorded.
-- Idempotent: skips if TemplateCode already exists for CompanyID=1.
-- =============================================================================
IF NOT EXISTS (
    SELECT 1 FROM Master_NotificationTemplate
    WHERE TemplateCode = 'RegistrationPending' AND CompanyID = 1
)
BEGIN
    INSERT INTO Master_NotificationTemplate
        (TemplateCode, SMSMessage, EmailSubject, EmailContent, CompanyID, Status, LastModDate, LastModBy)
    VALUES (
        'RegistrationPending',
        'Thank you for registering. We are processing your registration (within 3 business days). Check status at: [link]. This is an auto message, please do not reply.',
        'Registration Pending',
        '<p>Dear Sir / Madam</p>'
      + '<p>Thank you for registering. We are processing your registration. Check status at: [link].</p>'
      + '<p><em>This is an auto message, please do not reply.</em></p>',
        1, 'A', GETDATE(), 'system'
    );
    PRINT 'Inserted RegistrationPending template.';
END
ELSE
BEGIN
    PRINT 'Skipped: RegistrationPending template already exists for CompanyID=1.';
END
GO
```

Pattern rules: banner comment (what/when/idempotent) · `IF NOT EXISTS` on `TemplateCode + CompanyID` · explicit column list · email HTML as concatenated `<p>` fragments carrying the SAME tokens as the SMS · `PRINT` on both branches (operator feedback in SSMS) · trailing `GO`.

### Config parameter

```sql
IF NOT EXISTS (SELECT 1 FROM Master_SystemInformation WHERE Parameter = 'TPPMicrositeUrl')
BEGIN
    INSERT INTO Master_SystemInformation (Parameter, Value, Description)
    VALUES (
        'TPPMicrositeUrl',
        'https://your-domain.com/Warranty/Status',  -- TODO: replace with real URL
        'Public URL to the consumer status page. Substituted into the [link] placeholder in notification templates.'
    );
    PRINT 'Inserted TPPMicrositeUrl parameter.';
END
ELSE BEGIN PRINT 'Skipped: TPPMicrositeUrl parameter already exists.'; END
GO
```

Gotcha from production: if the stored URL is a prefix ending in `?ref=`, the caller must APPEND the reference number before substituting — the reference substituted it raw and shipped SMS with a dangling `?qstrRefNo=`. Decide: bare page URL (simplest) or prefix+append, and be consistent.

## 7. Placeholder catalog pattern

Maintain a table like this in your project docs — every template's tokens and what fills them:

| TemplateCode | Tokens | Filled by |
|---|---|---|
| `RegistrationPending` | `[link]` | `GetSystemValueAsync("SiteUrl")` |
| `RegistrationCompleted` | `{LINK}` | site URL |
| `RegistrationRejected` | `{REASON}`, `{CONTACT}` | rejection remark; `SupportContactNo` param |
| `ClaimCompleted` | `{LINK}` | `ClaimStatusUrl` param |
| `<Plan>Completed` | `{CUSTOMER}`, `{PLAN}`, `{LINK}` | customer name; plan name; site URL |

(Standardize on ONE delimiter — the mixed `[link]`/`{LINK}` above is the reference's historical accident.)

## 8. OneWaySMS gateway transport (swap for your provider)

```csharp
public async Task<bool> SendSmsAsync(string mobileNumber, string message)
{
    var cfg = await GetSmsConfigAsync();   // credentials from DB row — rotate without redeploy
    if (cfg == null) return false;

    string formattedNumber = FormatMobileNumber(mobileNumber);   // digits only, "60" prefix
    bool isUnicode = message.Any(c => c > 127);
    string data = isUnicode
        ? BuildUnicodeMessage(cfg, formattedNumber, message)     // languagetype=2, UCS-2 hex
        : BuildNormalMessage(cfg, formattedNumber, message);     // languagetype=1, ISO-8859-1

    string? mtId = await HttpGetAsync(cfg.ApiUrl + data);        // submit → MT id (or negative error)
    if (string.IsNullOrEmpty(mtId)) return false;

    string? responseCode = await HttpGetAsync(cfg.StatusUrl + $"?mtid={mtId}");   // status poll
    return responseCode == "0" || responseCode == "100";
}

private static string BuildNormalMessage(SmsConfig cfg, string phoneNo, string message)
{
    var enc = Encoding.GetEncoding("ISO-8859-1");
    return "?apiusername=" + HttpUtility.UrlEncode(cfg.Username, enc)
         + "&apipassword=" + HttpUtility.UrlEncode(cfg.Password, enc)
         + "&mobileno=" + phoneNo
         + "&senderid=" + cfg.SenderId          // PARAMETERIZE (reference hard-coded a brand)
         + "&languagetype=1"
         + "&message=" + HttpUtility.UrlEncode(message, enc);
}

private static string StringToHex(string s)    // unicode path: 4 hex digits per char, NOT url-encoded
{
    var sb = new StringBuilder();
    foreach (char c in s) sb.AppendFormat("{0:x4}", (uint)c);
    return sb.ToString();
}

private async Task<string?> HttpGetAsync(string url)
{
    try
    {
        using var client = new HttpClient();   // NEW BUILDS: IHttpClientFactory + timeout
        var response = await client.GetStringAsync(url);
        return response?.Trim();
    }
    catch (Exception ex)
    {
        // strip the query string — credentials must never land in logs
        _logger.LogError(ex, "SMS HTTP request failed: {Url}", url.Split('?')[0]);
        return null;
    }
}

private static string FormatMobileNumber(string phoneNo)
{
    phoneNo = new string(phoneNo.Where(char.IsDigit).ToArray());   // strips '+' too
    if (phoneNo.StartsWith("60")) return phoneNo;
    if (phoneNo.StartsWith("0")) return "60" + phoneNo.Substring(1);
    return "6" + phoneNo;
}
```

Credential storage (per company row; guard NULL columns — unguarded `GetString` throws):

```sql
-- Master_Company: SMSOneWayAPI, SMSOneWayStatus, SMSOneWayUsername, SMSOneWayPassword
SELECT SMSOneWayAPI, SMSOneWayStatus, SMSOneWayUsername, SMSOneWayPassword
FROM Master_Company WHERE CompanyCode = @CompanyCode AND Status = 'A'
```

## 9. WhatsApp transport (config convention; implement if needed)

Same DB-config convention — parameters `WhatsAppApiBaseUrl` (`https://<subdomain>.api.infobip.com`), `WhatsAppApiKey`, `WhatsAppFromNumber`, read via `GetSystemValueAsync`. Infobip template send:

```
POST {WhatsAppApiBaseUrl}/whatsapp/1/message/template
Authorization: App {WhatsAppApiKey}
Content-Type: application/json

{ "messages": [ { "from": "{WhatsAppFromNumber}", "to": "60XXXXXXXXX",
    "content": { "templateName": "...", "templateData": { "body": { "placeholders": ["..."] } },
                 "language": "en" } } ] }
```

Implement as a second transport behind the same `INotificationService` facade (template body still from your DB; WhatsApp template registration happens provider-side).

## 10. Background dispatch upgrade (recommended)

The reference sends inline in the HTTP request — a payment webhook held its connection open across two gateway GETs. Since no caller uses the bool result, replace the direct send with an outbox insert + `IHostedService` dispatcher:

```
SendTemplatedSmsAsync → INSERT Notification_Outbox (TemplateCode, Mobile, RenderedBody, Status='PEN', CreatedDate)
Dispatcher (BackgroundService, poll or SQL trigger): pick PEN rows, send, mark SENT/FAILED + attempt count with backoff
```

Keep the same swallow-and-log contract at the enqueue site.
