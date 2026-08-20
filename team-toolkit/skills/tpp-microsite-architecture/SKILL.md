---
name: tpp-microsite-architecture
description: TPP microsite framework and project-structure scaffold for ASP.NET Core 8. 5-project Clean-Architecture-lite solution (Domain/Application/Infrastructure/API/Web), Web→API HttpClient pattern with Basic auth, raw ADO.NET SQL services (no ORM), session-flag auth via SessionAuthFilter, DTO/interface naming, repo foldering (sql/, docs/, tests/ Playwright), appsettings-vs-DB config rules, C# language conventions. Use when scaffolding a new Webmax microsite solution or adding a feature layer so it matches the TPP RHP structure. For look-and-feel use the companion skill tpp-microsite-ui.
---

# TPP Microsite Architecture — Framework & Structure Scaffold

You are scaffolding (or extending) a Webmax microsite that must use the same framework, layering, and folder conventions as the TPP RHP warranty microsite. Stack: ASP.NET Core 8, C#, SQL Server via raw ADO.NET (no ORM, no repositories), Razor MVC frontend, REST API layer, Playwright tests.

The complete blueprint — csproj templates, both Program.cs files, appsettings shapes, controller/service/DI patterns, SessionAuthFilter, test structure — lives in [references/architecture.md](references/architecture.md). **Load it before creating any project or file.** Replace `TPPMicrosite`/`<App>` with the new solution name.

## Non-negotiable structure rules

1. **Five projects**: `Domain` (constants/enums) ← `Application` (DTOs + interfaces) ← `Infrastructure` (services, SQL) ← `API`; and `Web` references **Application only**.
2. **Web never touches the database.** It calls the API over a named `HttpClient` (`ApiBaseUrl` + Basic auth from config) with relative paths and reads responses as `JsonElement` (case-insensitive).
3. **Raw SQL only**: `SqlConnection`/`SqlCommand`, named `@Pascal` parameters (never interpolate user input), `OUTPUT INSERTED.<Id>` + `ExecuteScalarAsync()` for identities, explicit transactions with rollback, `private static MapXxx(SqlDataReader)` helpers.
4. **Error contract**: business validation lives in Infrastructure services and throws `InvalidOperationException("user-facing message")` → API catches it → `400 { message }` → Web extracts `.message` and shows it verbatim. Everything else → logged 500 with a generic message.
5. **Auth is session-flag based** — no Identity, no JWT. `SessionAuthFilter` checks `Session["IsAuthenticated"] == "true"` (401 JSON for AJAX, redirect-with-returnUrl otherwise). API is gated by `BasicAuthMiddleware` outside Development, with a `PublicPaths` allow-list for signature-verified webhooks.
6. **DI in one place**: `Infrastructure/DependencyInjection.cs` → `AddInfrastructure(configuration)`; services take the connection string as a plain `string` ctor arg via factory lambdas; caches Singleton, the rest Scoped.
7. **Config placement**: deployment plumbing in `appsettings.json` (connection string API-side only; secrets via user-secrets/env, never committed); business/tenant config and Web-forbidden secrets in the `Master_SystemInformation` DB table, seeded by idempotent `IF NOT EXISTS` scripts in `sql/`.
8. **Language conventions**: net8.0, nullable + implicit usings, file-scoped namespaces (namespace = folder path), top-level `Program.cs`, `Async` suffix everywhere, tuple returns for id+ref results (`Task<(int Id, string RefNo)>`), constants over enums for DB codes.
9. **Repo foldering**: `src/` (five projects), `sql/` (flat hand-run scripts), `docs/`, `prototype/`, `tests/api` + `tests/ui` + `tests/sql` (Playwright, separate npm packages); runtime upload stores and logs are gitignored (PII).

For UI styling, layout shell, and component recipes use the companion skill **tpp-microsite-ui** — this skill covers only structure and backend conventions.
