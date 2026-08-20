# TPP Microsite — Framework & Project Structure Blueprint

Scaffold recipe for a new Webmax microsite with the identical solution layering, folder conventions, and language patterns as the TPP RHP warranty microsite. Replace `TPPMicrosite` with the new solution name throughout.

## 1. Solution layout (5 projects, Clean-Architecture-lite)

```
<App>.sln                      # VS format 12.00, one "src" solution folder, Debug/Release AnyCPU only
src/
  <App>.Domain/          (classlib)  — constants/enums. No dependencies.
  <App>.Application/     (classlib)  — DTOs + service interfaces. → Domain
  <App>.Infrastructure/  (classlib)  — service implementations, raw SQL. → Domain, Application
  <App>.API/             (web api)   — REST layer. → Application, Infrastructure
  <App>.Web/             (mvc)       — Razor frontend. → Application ONLY
```

**Dependency rule:** `Web → Application` only (DTO contracts — Web talks to the API over HTTP, never touches the DB or Infrastructure). `API → Application + Infrastructure`.

### csproj templates

All projects: `net8.0`, `<Nullable>enable</Nullable>`, `<ImplicitUsings>enable</ImplicitUsings>`.

- **Domain**: no packages.
- **Application**: `<ProjectReference>` Domain + `<FrameworkReference Include="Microsoft.AspNetCore.App" />` (needed only if DTOs use `IFormFile`).
- **Infrastructure**: refs Domain + Application; packages `Microsoft.Data.SqlClient 5.2.*`, `Microsoft.Extensions.DependencyInjection.Abstractions 8.0.*`, `Microsoft.Extensions.Configuration.Abstractions 8.0.*`.
- **API** (`Microsoft.NET.Sdk.Web`): refs Application + Infrastructure; packages `Microsoft.AspNetCore.OpenApi 8.0.*`, `Swashbuckle.AspNetCore 6.6.*`. (Do NOT add EF Core — there is no ORM; the original's EF Design package was vestigial.)
- **Web** (`Microsoft.NET.Sdk.Web`): refs Application only; add `ClosedXML` (Excel export) / `QuestPDF` (PDF receipts) only if those features are needed.

## 2. Repo-root folders

```
/CLAUDE.md               project context doc: business rules, DB tables, endpoint matrix, session keys
/docs/                   architecture + flow docs (markdown; mermaid .mmd where useful)
/prototype/              static HTML design prototypes
/sql/                    flat folder of hand-run scripts (no migration runner):
                         "all table script.sql" (full schema) · <Table>_Create.sql ·
                         <Table>_Add<Column>.sql (migrations) ·
                         Master_SystemInformation_Insert_<Key>.sql (idempotent IF NOT EXISTS config seeds) ·
                         stored procs · simulation/cleanup helpers
/src/                    the five projects
/tests/                  Playwright (see §8)
/.gitignore              bin/obj, node_modules, test-results/, playwright-report/,
                         runtime upload stores (invoice/, claims/), logs/  ← PII, never committed
```

## 3. Web project structure

```
src/<App>.Web/
  Program.cs                       # top-level statements
  appsettings.json / appsettings.Development.json
  Properties/launchSettings.json   # fixed dev ports (e.g. http:5042)
  Controllers/   <Feature>Controller.cs
  Models/        <Feature>ViewModel.cs        (suffix: ...ViewModel)
  Filters/       SessionAuthFilter.cs
  Services/      Web-only helpers (PDF/audit loggers)
  Views/
    _ViewImports.cshtml            # @using <App>.Web(.Models) + @addTagHelper *
    _ViewStart.cshtml              # Layout = "_Layout";
    Shared/_Layout.cshtml          # shell (see components.md)
    <Feature>/<Page>.cshtml        # one folder per controller; partials prefixed "_"
  wwwroot/
    css/site.css                   # single global stylesheet — ALL brand tokens
    js/site.js                     # global helpers only; page JS lives in @section Scripts
    images/  documents/  lib/      # lib = LibMan-vendored bootstrap/jquery
  invoice/                         # runtime upload store: invoice/{RefNo}/{originalFileName} (gitignored)
  logs/                            # input-failures-YYYY-MM-DD.jsonl (gitignored)
```

### Web Program.cs (template)

```csharp
using System.Net.Http.Headers;
using System.Text;
using <App>.Web.Filters;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllersWithViews();
builder.Services.AddScoped<SessionAuthFilter>();

builder.Services.AddHttpClient("<App>Api", client =>
{
    client.BaseAddress = new Uri(builder.Configuration["ApiBaseUrl"] ?? "https://localhost:7000");
    var user = builder.Configuration["ApiAuth:Username"] ?? "";
    var pass = builder.Configuration["ApiAuth:Password"] ?? "";
    if (!string.IsNullOrEmpty(user))
    {
        var credentials = Convert.ToBase64String(Encoding.UTF8.GetBytes($"{user}:{pass}"));
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Basic", credentials);
    }
});

builder.Services.AddSession(options =>
{
    options.IdleTimeout = TimeSpan.FromMinutes(30);   // mirror in _Layout idle-timer JS
    options.Cookie.HttpOnly = true;
    options.Cookie.IsEssential = true;
});

var app = builder.Build();

if (!app.Environment.IsDevelopment()) { app.UseExceptionHandler("/Home/Error"); app.UseHsts(); }

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseRouting();
app.UseSession();          // session BEFORE authorization
app.UseAuthorization();

app.MapControllerRoute(name: "default", pattern: "{controller=Home}/{action=Index}/{id?}");
app.Run();
```

No `AddAuthentication` — auth is 100% session-flag based. No `UsePathBase` — virtual-directory safety comes from tilde/tag-helper URL resolution everywhere (see components.md).

### Web appsettings shape

```jsonc
{
  "Logging": { "LogLevel": { "Default": "Information", "Microsoft.AspNetCore": "Warning" } },
  "AllowedHosts": "*",
  "ApiBaseUrl": "http://localhost:5194",
  "ApiAuth": { "Username": "<user-secret>", "Password": "<user-secret>" },
  "InvoiceStorage": { "Path": "invoice", "MirrorPath": "" },   // MirrorPath = optional UNC second copy
  "LogStorage": { "Path": "logs" },
  "ResourceDocuments": { "Dealer": { "...": "/documents/..." }, "EndUser": { "...": "..." } }
}
```

**Web has NO connection string — it never touches the DB.** Never commit real credentials; use user-secrets/env vars.

### Web → API call pattern

Inject `IHttpClientFactory` + `ILogger<T>`; shared `private readonly JsonSerializerOptions _jsonOptions = new() { PropertyNameCaseInsensitive = true };`. Named client, relative paths:

```csharp
var client = _httpClientFactory.CreateClient("<App>Api");
var response = await client.PostAsync("api/warranty/register",
    new StringContent(JsonSerializer.Serialize(dto), Encoding.UTF8, "application/json"));
var body = await response.Content.ReadAsStringAsync();

if (response.IsSuccessStatusCode)
{
    var result = JsonSerializer.Deserialize<JsonElement>(body, _jsonOptions);
    var id = result.GetProperty("warrantyID").GetInt32();
    ...
}
// non-success: log status+body, TryExtractApiMessage(body, fallback) pulls .message
// out of the API's 400 JSON so business-rule text reaches the user verbatim
```

Wrap the transport call in its own try/catch (network failure → friendly "couldn't reach service" message + re-render view). Only third-party proxy calls use a short-lived `new HttpClient { Timeout = ... }`.

## 4. API project structure

```
src/<App>.API/
  Program.cs
  appsettings.json / appsettings.Development.json
  Properties/launchSettings.json     # fixed dev ports (e.g. http:5194), launchUrl "swagger"
  Controllers/   <Feature>Controller.cs
  Middleware/    BasicAuthMiddleware.cs
  claims/        runtime file store (gitignored)
```

No Models folder — request bodies are Application DTOs; tiny request classes declared at the bottom of the controller file.

### API Program.cs (template)

```csharp
using <App>.API.Middleware;
using <App>.Application.Interfaces;
using <App>.Infrastructure;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder.Services.AddInfrastructure(builder.Configuration);   // single extension = all DI

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowMVC", policy =>
        policy.WithOrigins(builder.Configuration.GetSection("AllowedOrigins").Get<string[]>() ?? Array.Empty<string>())
              .AllowAnyHeader().AllowAnyMethod());
});

var app = builder.Build();

await app.Services.GetRequiredService<IGenCodeService>().InitializeAsync();   // warm code cache at boot

if (app.Environment.IsDevelopment()) { app.UseSwagger(); app.UseSwaggerUI(); }

app.UseHttpsRedirection();
app.UseCors("AllowMVC");

// Basic-auth gate between Web and API — skipped in Development so local test flows aren't blocked
if (!app.Environment.IsDevelopment())
    app.UseMiddleware<BasicAuthMiddleware>();

app.MapControllers();
app.Run();
```

`BasicAuthMiddleware`: compares decoded `Authorization: Basic` header against `ApiAuth:Username/Password`; 401 + `WWW-Authenticate: Basic realm="<App> API"` otherwise; keeps a `PublicPaths` allow-list for external webhooks that can't send the header (those are secured by signature verification instead). No JWT, no Identity, no `[Authorize]`.

### API appsettings shape

```jsonc
{
  "Logging": { "LogLevel": { "Default": "Information", "Microsoft.AspNetCore": "Warning" } },
  "AllowedHosts": "*",
  "ConnectionStrings": { "DefaultConnection": "Server=<SERVER>;Database=<DB>;Trusted_Connection=true;TrustServerCertificate=true;" },
  "AllowedOrigins": [ "https://localhost:7178" ],
  "OtpBypass": { "Enabled": false, "Code": "", "Mobiles": [] },   // Development.json turns this on for local/Playwright
  "ApiAuth": { "Username": "<user-secret>", "Password": "<user-secret>" },
  "ClaimStorage": { "Path": "claims", "MirrorPath": "" }
}
```

### API controller pattern

```csharp
[ApiController]
[Route("api/[controller]")]
public class WarrantyController : ControllerBase
{
    private readonly IWarrantyService _warrantyService;
    public WarrantyController(IWarrantyService warrantyService) { _warrantyService = warrantyService; }

    [HttpPost("register")]
    public async Task<IActionResult> Register([FromBody] WarrantyRegistrationCreateDto dto)
    {
        // cheap guards first, bare BadRequest(string)
        if (dto.Tyres.Count < 2 || dto.Tyres.Count > 4) return BadRequest("You must register between 2 and 4 tyres.");
        try
        {
            var (id, refNumber) = await _warrantyService.CreateRegistrationAsync(dto);
            return Ok(new { WarrantyID = id, WarrantyReferenceNumber = refNumber, Message = "..." });
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);   // business rule violated → 400 with user-facing text
        }
    }
}
```

Fuller variant (multipart endpoints): check `ModelState` first → `BadRequest(new { message = firstError })`; two-tier catch — `InvalidOperationException` → `LogWarning` + 400 `{ message }`; `Exception` → `LogError` + 500 generic. **Rule: `InvalidOperationException` from a service = user-fixable validation → 400; anything else → 500.** Successes return anonymous objects (camelCased by default).

## 5. Application project

```
src/<App>.Application/
  DTOs/         one file per FEATURE AREA (not per class) — WarrantyRegistrationDto.cs holds
                CreateDto + TyreDetailDto + ViewDto siblings
  Interfaces/   I<Feature>Service.cs
```

- Naming: `XxxCreateDto` (inbound), `XxxViewDto` (outbound), `PagedXxxResultDto`.
- Plain POCOs: non-nullable strings `= string.Empty;`, lists `= new();`, optionals `string?`. No records. Validation attributes only on multipart DTOs.
- Interfaces: all members `...Async` returning `Task<T>`; XML `///` doc-comments carrying business rationale; tuple returns for id+ref results: `Task<(int WarrantyId, string RefNumber)>`.

## 6. Infrastructure project

```
src/<App>.Infrastructure/
  DependencyInjection.cs    # static AddInfrastructure(this IServiceCollection, IConfiguration)
  Services/                 # <Feature>Service.cs implementing Application interfaces
```

### DI registration pattern

Services take the **connection string as a plain `string` ctor arg** (not IConfiguration) → explicit factory lambdas:

```csharp
public static class DependencyInjection
{
    public static IServiceCollection AddInfrastructure(this IServiceCollection services, IConfiguration configuration)
    {
        var connectionString = configuration.GetConnectionString("DefaultConnection")
            ?? throw new InvalidOperationException("Connection string 'DefaultConnection' not found.");

        services.AddSingleton<IGenCodeService>(sp => new GenCodeService(connectionString, sp.GetRequiredService<ILogger<GenCodeService>>()));
        services.AddScoped<IWarrantyService>(sp => new WarrantyService(connectionString,
            sp.GetRequiredService<ILogger<WarrantyService>>(), sp.GetRequiredService<IGenCodeService>()));
        // optional services registered conditionally, e.g. only when an API key is configured
        return services;
    }
}
```

Lifetimes: caching lookups = **Singleton**; everything else **Scoped**.

### Raw SQL data-access conventions (no ORM, no repository layer)

- `using var connection = new SqlConnection(_connectionString); await connection.OpenAsync();`
- `using var cmd = new SqlCommand(sql, connection[, transaction]);` + `cmd.Parameters.AddWithValue("@PascalName", value)` — **never interpolate user input into SQL**.
- Reads: `ExecuteReaderAsync()` + `while (await reader.ReadAsync())` mapped by a `private static XxxDto MapXxx(SqlDataReader reader)` helper (`reader.IsDBNull(i) ? null : reader.GetString(i)`).
- Inserts returning identity: `OUTPUT INSERTED.<Id>` + `ExecuteScalarAsync()`.
- Multi-statement writes: `connection.BeginTransaction()`, every command constructed `(sql, connection, transaction)`, `transaction.Commit()` in try / `catch { transaction.Rollback(); throw; }`. Private helpers take `(connection, transaction)` params.
- Shared `const string` SQL fragments (`SelectColumns`, `FromClause`) composed with `$@"..."`.
- **Business validation lives in the service**, thrown as `InvalidOperationException("user-facing message")`.

### GenCodeService (code→display lookup cache)

Singleton over a `Master_GenCode` (`Type`/`Code`/`Value`) table; warmed at API boot via `InitializeAsync()`; `SemaphoreSlim` + volatile double-check; `ConcurrentDictionary<string,string>` keyed `"{TYPE}|{CODE}"` upper-invariant; `GetValue(type, code)` falls back to the raw code. DB-facing status codes are `public const string` on static classes in `Domain/Enums` (e.g. `WarrantyStatus.PendingProcessing = "PEN"`).

## 7. C# language conventions

- `net8.0`, nullable + implicit usings on all projects; file-scoped namespaces everywhere; namespace = folder path; `Program.cs` = top-level statements.
- `var` when the type is obvious; explicit `string sql = @"..."` / `int x = 0` for primitives and SQL.
- Verbatim `@"..."` for multi-line SQL.
- Async all the way: `Async` suffix on every async member; never `.Result`/`.Wait()`.
- Constructor injection into `private readonly` fields (no primary constructors).
- Anonymous objects for API responses; `JsonElement` for consuming them.
- Prose-heavy comments explaining **why** (constraints, gotchas), XML `///` on interfaces.
- Constants over enums for DB codes.

## 8. Session/auth wiring

`SessionAuthFilter : IActionFilter`, registered scoped, applied per-controller with `[ServiceFilter(typeof(SessionAuthFilter))]` (Auth/Home left open):

```csharp
public void OnActionExecuting(ActionExecutingContext context)
{
    var session = context.HttpContext.Session;
    if (session.GetString("IsAuthenticated") != "true")
    {
        var isAjax = context.HttpContext.Request.Headers["X-Requested-With"] == "XMLHttpRequest"
                  || context.HttpContext.Request.Headers["Accept"].ToString().Contains("application/json");
        if (isAjax)
            context.Result = new JsonResult(new { sessionExpired = true, message = "Session expired" }) { StatusCode = 401 };
        else
        {
            var request = context.HttpContext.Request;
            var returnUrl = request.PathBase + request.Path + request.QueryString;  // PathBase → IIS virtual-dir safe
            context.Result = new RedirectToActionResult("Login", "Auth", new { returnUrl });
        }
    }
}
```

Session keys set at login: `IsAuthenticated` ("true"), `MobileNumber` (`+60...`), `UserRole`, `CustomerID`, `CompanyID`. Pre-login staging keys use a `Pending` prefix. Role checks are manual in-controller helpers (`IsConsumer()`, dealer-only endpoints return 403); views read `Context.Session` directly for nav gating but are always mirrored by a server-side gate.

## 9. Playwright test structure

```
tests/
  api/   package.json (name <app>-api-tests, @playwright/test)
         playwright.config.ts  # baseURL env API_BASE_URL || http://localhost:5194, Accept: application/json
         tests/<feature>.api.spec.ts
  ui/    package.json / playwright.config.ts  # baseURL env WEB_BASE_URL || http://localhost:5042,
         # screenshot only-on-failure, trace on-first-retry, chromium project
         tests/<flow>.spec.ts + helpers/ (auth.ts, wizard.ts) + fixtures/
  sql/   reset-test-data.sql, seed-test-data.sql
```

Workflow: reset DB → seed → run API tests → run UI tests. Reporter: `[['list'],['html',{open:'never'}]]`.

## 10. Config placement rule

- **appsettings.json** = deployment plumbing: connection string (API only), service base URLs, storage paths, CORS origins, dev bypass flags. Dev overrides in `appsettings.Development.json`. Secrets via user-secrets/env — never committed.
- **`Master_SystemInformation` DB table** (`Parameter`/`Value`/`Description`) = business/tenant config and any secret the Web tier must never see: payment-gateway credentials (API-side only), public URLs substituted into SMS templates, provider settings. Accessor: `GetSystemValueAsync(parameter)`. Seeded by idempotent `IF NOT EXISTS ... INSERT` scripts in `sql/` with placeholder values.
- Related DB-driven config: `Master_NotificationTemplate` (message bodies by `TemplateCode`+`CompanyID`), `Master_GenCode` (lookups), routing-matrix tables.
