# OTP Session Auth — Reference Implementation (C# / ASP.NET Core + SQL Server)

Production-proven code. Rename `Master_*` tables / `TPPApi` client to your project's names; keep the mechanics. Secrets shown as placeholders.

## 1. Schema

```sql
CREATE TABLE Master_Role (
    RoleID   INT IDENTITY(1,1) PRIMARY KEY,
    RoleName VARCHAR(50) NOT NULL,
    Status   CHAR(1) NOT NULL DEFAULT 'A'
);
IF NOT EXISTS (SELECT * FROM Master_Role WHERE RoleName = 'Consumer')
    INSERT INTO Master_Role (RoleName, Status) VALUES ('Consumer', 'A');

CREATE TABLE Master_User (
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    UserLogin VARCHAR(80) NOT NULL,
    UserName VARCHAR(80) NOT NULL,
    RoleID INT NOT NULL DEFAULT 0,
    CompanyID INT NULL,
    CustomerID INT NULL,             -- dealer's default outlet (legacy single-outlet field)
    MobileNo VARCHAR(20) NULL,       -- canonical +60... form
    OTP VARCHAR(10) NULL,
    OTPExpired DATETIME NULL,
    LoginAttempt INT NOT NULL DEFAULT 0,
    AccountLocked CHAR(1) NOT NULL DEFAULT 'N',
    LockedTime DATETIME NULL,
    Status CHAR(1) NOT NULL DEFAULT 'A',
    CreatedBy NVARCHAR(80) NULL, CreatedDate DATETIME NOT NULL DEFAULT GETDATE(),
    LastModifiedBy NVARCHAR(80) NULL, LastModifiedDate DATETIME NULL
);
-- filtered index matches every OTP query's predicate
CREATE INDEX IX_Master_User_MobileNo ON Master_User (MobileNo) WHERE Status = 'A';

-- multi-outlet mapping (dealer → outlets); add FKs + UNIQUE(UserID, CustomerID) — the
-- reference lacked both
CREATE TABLE Master_UserCustomer (
    UserCustomerID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT NOT NULL,
    CustomerID INT NOT NULL
);
```

## 2. SMS/OTP service (Infrastructure)

```csharp
public interface ISmsService
{
    Task<bool> SendOtpAsync(string mobileNumber);
    Task<VerifyOtpResult> VerifyOtpAsync(string mobileNumber, string otp);
    Task<bool> SendSmsAsync(string mobileNumber, string message);
}

public class VerifyOtpResult
{
    public bool Success { get; set; }
    public string? RoleName { get; set; }
    public int? CustomerID { get; set; }   // legacy single-outlet fallback
    public int? CompanyID { get; set; }
    public List<UserOutletDto>? Outlets { get; set; }   // from Master_UserCustomer
}
public class UserOutletDto { public int CustomerID { get; set; } public int CompanyID { get; set; } }
```

### Generation, send, store

```csharp
private const int OtpExpiryMinutes = 5;
private static string GenerateOtp() =>
    RandomNumberGenerator.GetInt32(0, 1000000).ToString("D6");   // crypto RNG, zero-padded

public async Task<bool> SendOtpAsync(string mobileNumber)
{
    string otp = GenerateOtp();
    DateTime otpExpiry = DateTime.Now.AddMinutes(OtpExpiryMinutes);   // use UtcNow in new builds

    await EnsureUserExistsAsync(mobileNumber);           // auto-signup (below)
    await StoreOtpAsync(mobileNumber, otp, otpExpiry);   // PERSIST BEFORE SEND

    string message = $"Your TAC is {otp}. Valid for {OtpExpiryMinutes} minutes. Do not share this code with anyone.";
    return await SendSmsAsync(mobileNumber, message);
}

// StoreOtpAsync: UPDATE Master_User SET OTP=@OTP, OTPExpired=@OTPExpired
//                WHERE MobileNo=@MobileNo AND Status='A'
```

### Auto-signup

```csharp
private async Task EnsureUserExistsAsync(string mobileNumber)
{
    // SELECT UserID WHERE MobileNo=@m AND Status='A' — if found, return
    // roleId: SELECT RoleID FROM Master_Role WHERE RoleName='Consumer' AND Status='A'
    //         (FAIL LOUDLY if missing — the reference silently fell back to 0)
    // INSERT Master_User (UserLogin, UserName, RoleID, CompanyID, MobileNo, Status,
    //                     AccountLocked, LoginAttempt, CreatedBy, CreatedDate)
    // VALUES (@MobileNo, @MobileNo, @RoleID, 1, @MobileNo, 'A', 'N', 0, 'SYSTEM', GETDATE())
    // CompanyID hard-set at signup so a consumer never has NULL CompanyID.
    // Do NOT store a shared default password (the reference did — drop it).
}
```

### Verify (single-use, opaque failure, bypass, dealer-wins)

```csharp
public async Task<VerifyOtpResult> VerifyOtpAsync(string mobileNumber, string otp)
{
    var fail = new VerifyOtpResult { Success = false };

    bool isBypass = _bypassEnabled
                 && !string.IsNullOrEmpty(_bypassCode)
                 && otp == _bypassCode
                 && _bypassMobiles.Contains(mobileNumber);   // HashSet, OrdinalIgnoreCase

    if (!isBypass)
    {
        // SELECT OTP, OTPExpired FROM Master_User WHERE MobileNo=@m AND Status='A'
        // no row → fail;  OTP or expiry NULL (consumed/never issued) → fail
        // stored != otp OR now > expiry → fail            (same opaque result for all)
        //   (new builds: CryptographicOperations.FixedTimeEquals)
        // then single-use clear:
        // UPDATE Master_User SET OTP=NULL, OTPExpired=NULL WHERE MobileNo=@m AND Status='A'
    }

    // Role resolution — Dealer wins when one mobile has multiple active users:
    // SELECT TOP 1 u.UserID, r.RoleName, u.CustomerID, u.CompanyID
    // FROM Master_User u LEFT JOIN Master_Role r ON r.RoleID = u.RoleID
    // WHERE u.MobileNo=@m AND u.Status='A'
    // ORDER BY CASE WHEN r.RoleName='Dealer' THEN 0 ELSE 1 END, u.UserID

    // Multi-outlet (dealers only):
    // SELECT uc.CustomerID, mc.CompanyID FROM Master_UserCustomer uc
    // JOIN Master_Customer mc ON mc.CustomerID = uc.CustomerID WHERE uc.UserID=@id

    return new VerifyOtpResult { Success = true, RoleName = roleName,
        CustomerID = customerId, CompanyID = companyId, Outlets = outlets };
}
```

### DI + bypass config

```csharp
// appsettings.Development.json ONLY:
// "OtpBypass": { "Enabled": true, "Code": "123456",
//                "Mobiles": [ "+60123456789", "+60167682236" ] }
// appsettings.json (prod): { "Enabled": false, "Code": "", "Mobiles": [] }

var bypassEnabled = configuration.GetValue<bool>("OtpBypass:Enabled");
var bypassCode = configuration["OtpBypass:Code"] ?? string.Empty;
var bypassMobiles = configuration.GetSection("OtpBypass:Mobiles").Get<string[]>() ?? Array.Empty<string>();
services.AddScoped<ISmsService>(sp => new SmsService(
    connectionString, bypassEnabled, bypassCode, bypassMobiles,
    sp.GetRequiredService<ILogger<SmsService>>()));
```

## 3. API endpoints

```csharp
[ApiController]
[Route("api/[controller]")]
public class SmsController : ControllerBase
{
    [HttpPost("send-otp")]
    public async Task<IActionResult> SendOtp([FromBody] SendOtpRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.MobileNumber))
            return BadRequest(new { Message = "Mobile number is required." });
        var ok = await _smsService.SendOtpAsync(request.MobileNumber);
        return ok ? Ok(new { Message = "OTP sent successfully." })
                  : StatusCode(500, new { Message = "Failed to send OTP. Please try again." });
    }

    [HttpPost("verify-otp")]
    public async Task<IActionResult> VerifyOtp([FromBody] VerifyOtpRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.MobileNumber) || string.IsNullOrWhiteSpace(request.OTP))
            return BadRequest(new { Message = "Mobile number and OTP are required." });
        var result = await _smsService.VerifyOtpAsync(request.MobileNumber, request.OTP);
        if (!result.Success) return Unauthorized(new { Message = "Invalid or expired OTP." });
        return Ok(new { Message = "OTP verified successfully.",
            RoleName = result.RoleName, CustomerID = result.CustomerID,
            CompanyID = result.CompanyID, Outlets = result.Outlets });
    }
}
```

## 4. Web AuthController

### Mobile normalization (canonical form — the single join key)

```csharp
/// Canonical Malaysian mobile in "+60XXXXXXXXX" form. Accepts "0121234567",
/// "121234567", "+60121234567", "60121234567" — all → "+60121234567".
private static string NormalizeMobile(string? raw)
{
    var m = (raw ?? string.Empty).Trim().Replace(" ", "").Replace("-", "");
    if (m.StartsWith("+60")) m = m.Substring(3);
    else if (m.StartsWith("60")) m = m.Substring(2);
    m = m.TrimStart('0');
    return "+60" + m;
}
```

Apply on send, on verify, and for the session value. NOTE: `+` in a URL **path** segment is rejected by IIS — always pass mobiles as query params with `Uri.EscapeDataString`.

### POST Login (verify + branch)

```csharp
[HttpPost]
public async Task<IActionResult> Login(LoginViewModel model, string? returnUrl = null)
{
    // ModelState + TAC-present checks → re-render with ViewBag.ReturnUrl on failure
    var verifyMobile = NormalizeMobile(model.MobileNumber);
    var client = _httpClientFactory.CreateClient("TPPApi");
    var response = await client.PostAsync("api/sms/verify-otp", JsonContent(new { mobileNumber = verifyMobile, otp = model.TAC }));
    if (!response.IsSuccessStatusCode)
    {
        ModelState.AddModelError("TAC", "Invalid or expired TAC. Please try again.");
        ViewBag.ReturnUrl = returnUrl;
        return View(model);
    }

    // Defensive parse — any failure leaves fields null, which FAILS CLOSED because
    // every role gate is an allow-list.
    string? roleName = null; int? customerId = null; int? companyId = null;
    List<UserOutletDto>? outlets = null;
    try { /* read roleName / customerID / companyID / outlets from JsonElement */ } catch { }

    if (string.Equals(roleName, "Dealer", StringComparison.OrdinalIgnoreCase))
    {
        // Candidates = legacy CustomerID first (becomes default), then Master_UserCustomer
        // rows deduped by CustomerID.
        var candidates = new List<UserOutletDto>();
        if (customerId.HasValue)
            candidates.Add(new UserOutletDto { CustomerID = customerId.Value, CompanyID = companyId ?? 0 });
        if (outlets != null)
            foreach (var o in outlets)
                if (!candidates.Any(c => c.CustomerID == o.CustomerID)) candidates.Add(o);

        if (candidates.Count > 0)
        {
            // IsAuthenticated stays UNSET — filter still blocks everything but Auth pages.
            HttpContext.Session.SetString("PendingMobileNumber", verifyMobile);
            HttpContext.Session.SetString("PendingRoleName", roleName ?? string.Empty);
            HttpContext.Session.SetString("PendingOutlets", EncodeOutlets(candidates));
            if (customerId.HasValue) HttpContext.Session.SetInt32("PendingDefaultCustomerId", customerId.Value);
            if (!string.IsNullOrEmpty(returnUrl) && Url.IsLocalUrl(returnUrl))
                HttpContext.Session.SetString("PendingReturnUrl", returnUrl);
            return RedirectToAction("SelectOutlet");
        }
    }

    FinalizeSession(verifyMobile, roleName, customerId, companyId);
    if (!string.IsNullOrEmpty(returnUrl) && Url.IsLocalUrl(returnUrl)) return Redirect(returnUrl);
    return RedirectToAction("Index", "Home");
}

private void FinalizeSession(string mobile, string? roleName, int? customerId, int? companyId)
{
    HttpContext.Session.SetString("MobileNumber", mobile);
    HttpContext.Session.SetString("IsAuthenticated", "true");
    HttpContext.Session.SetString("UserRole", roleName ?? string.Empty);
    if (customerId.HasValue) HttpContext.Session.SetInt32("CustomerID", customerId.Value);
    if (companyId.HasValue) HttpContext.Session.SetInt32("CompanyID", companyId.Value);
}

// Session staging encodes outlets as "cust:comp,cust:comp" (compact, not JSON);
// malformed pairs silently dropped on decode.
private static string EncodeOutlets(List<UserOutletDto> o) =>
    string.Join(",", o.Select(x => $"{x.CustomerID}:{x.CompanyID}"));
```

### SelectOutlet

- **GET**: bail to Login if Pending keys missing; decode candidates; resolve outlet display names via `POST api/outlet/by-ids` with a **JSON body of ids** — NOT a GET query string (a dealer mapped to hundreds of outlets trips IIS's default maxQueryString/maxUrl → 404.15 in prod while working locally on Kestrel).
- **POST** (add `[ValidateAntiForgeryToken]`): re-validate chosen `customerId` against the decoded pending list (defence in depth — forged POST can't select a foreign outlet) → `FinalizeSession(pendingMobile, pendingRole, match.CustomerID, match.CompanyID)` → remove ALL Pending keys → redirect to `PendingReturnUrl` (if `Url.IsLocalUrl`) or Home.
- UX: search box + client-side pager (page size 5), default outlet pre-checked, copy switches for 1 vs many outlets, footer note "To switch outlets later, log out and log back in."

### Logout / SessionTimeout

```csharp
public IActionResult Logout() { HttpContext.Session.Clear(); return RedirectToAction("Login"); }

[HttpGet]
public IActionResult SessionTimeout() { HttpContext.Session.Clear(); return View(); }
// the timeout page IS the logout — clearing before render
```

### SendOtp AJAX proxy

Normalize, forward to API, return `{ success, message }`. Do NOT echo raw API bodies or exception text to the browser (the reference did — info leak); log detail server-side, return generic messages.

## 5. SessionAuthFilter (complete)

```csharp
public class SessionAuthFilter : IActionFilter
{
    public void OnActionExecuting(ActionExecutingContext context)
    {
        var session = context.HttpContext.Session;
        if (session.GetString("IsAuthenticated") != "true")
        {
            var isAjax = context.HttpContext.Request.Headers["X-Requested-With"] == "XMLHttpRequest"
                      || context.HttpContext.Request.Headers["Accept"].ToString().Contains("application/json");
            if (isAjax)
                context.Result = new JsonResult(new { sessionExpired = true, message = "Session expired" })
                    { StatusCode = 401 };
            else
            {
                var request = context.HttpContext.Request;
                // PathBase → correct returnUrl under an IIS virtual directory
                var returnUrl = request.PathBase + request.Path + request.QueryString;
                context.Result = new RedirectToActionResult("Login", "Auth", new { returnUrl });
            }
        }
    }
    public void OnActionExecuted(ActionExecutedContext context) { }
}
```

Registration: `builder.Services.AddScoped<SessionAuthFilter>();` + `[ServiceFilter(typeof(SessionAuthFilter))]` on protected controllers. Caveat: bare `fetch()` sets neither AJAX header → gets the 302 HTML; either set `X-Requested-With` on your fetches or detect API-shaped routes by prefix.

## 6. Login view essentials

```html
<div class="input-group input-group-lg">
    <span class="input-group-text fw-bold">+60</span>
    <input asp-for="MobileNumber" class="form-control" placeholder="e.g. 121234567" id="mobileNumber" />
</div>
<div class="d-flex gap-2">
    <input asp-for="TAC" class="form-control form-control-lg" placeholder="123456"
           style="letter-spacing: 4px; text-align: center;" id="tacInput" />
    <button type="button" class="btn btn-tp-outline px-3" id="btnRequestTAC">
        <i class="bi bi-send me-1"></i>Get TAC</button>
</div>
```

```js
// strip spaces/dashes/leading zeros; validate ^1\d{8,9}$ ; POST '+60' + digits
// via @Url.Action("SendOtp","Auth") — never a hard-coded path (virtual-dir safety)
// On success: focus TAC input; startCountdown(60): button disabled,
// label 59s…1s → "Resend". On failure: restore button, show message.
```

Model validation: `[RegularExpression(@"^0?1\d{8,9}$")]` on MobileNumber (leading 0 optional — normalization runs after validation).

## 7. Idle-timeout script (render only when authenticated)

```js
(function () {
    var TIMEOUT_URL = '@Url.Action("SessionTimeout", "Auth")';
    var IDLE_LIMIT = 30 * 60 * 1000; // MUST match Program.cs IdleTimeout
    var idleTimer = null, redirecting = false;
    function goToTimeout() { if (redirecting) return; redirecting = true; window.location.href = TIMEOUT_URL; }
    function resetIdle() { if (redirecting) return; if (idleTimer) clearTimeout(idleTimer);
        idleTimer = setTimeout(goToTimeout, IDLE_LIMIT); }
    // intentful events only — mousemove/scroll don't hit the server and would desync
    ['click', 'keydown', 'touchstart'].forEach(e => document.addEventListener(e, resetIdle, { passive: true }));
    resetIdle();
    if (window.jQuery) jQuery(document).ajaxError((e, xhr) => { if (xhr && xhr.status === 401) goToTimeout(); });
    if (window.fetch) { var _f = window.fetch;
        window.fetch = function () { return _f.apply(this, arguments).then(r => {
            if (r && r.status === 401) goToTimeout(); return r; }); }; }
})();
```

The timeout duration appears in three places (session config, this script, the timeout page copy) — drive all three from one config value.

## 8. Role gates (server twins for every UI hide)

```csharp
private bool IsConsumer() =>
    string.Equals(HttpContext.Session.GetString("UserRole"), "Consumer", StringComparison.OrdinalIgnoreCase);

// Page GET:   if (!IsConsumer()) return RedirectToAction("Index", "Home");
// AJAX POST:  explicit 403 + JSON (Forbid() throws without an auth scheme registered!):
if (!string.Equals(userRole, "Dealer", StringComparison.OrdinalIgnoreCase))
{
    Response.StatusCode = 403;
    return Json(new { success = false, message = "Only authorized dealers can submit claims." });
}
```

Views read `Context.Session.GetString(...)` directly for nav gating — always mirrored by a server-side gate. Unknown roles fail closed: not Consumer → can't register; not Dealer → can't claim; they get view-only.

## 9. Playwright test wiring

```ts
// helpers/auth.ts — the "Get TAC" button is intentionally NOT clicked (real SMS
// is unreliable in CI); the bypass kicks in at verify-time.
export async function loginAs(page: Page, who: keyof typeof TEST_USERS) {
  const user = TEST_USERS[who];
  await page.goto('/Auth/Login');
  await page.fill('#mobileNumber', user.mobileLocal);
  await page.fill('#tacInput', user.tac);       // = OtpBypass.Code
  await page.click('#btnLogin');
  await expect(page).not.toHaveURL(/\/Auth\/Login/);
}
```

Bypass users must pre-exist; the DB reset script clears their OTP state but never deletes them. Pre-prod checklist item: `OtpBypass.Enabled = false` in production config.
