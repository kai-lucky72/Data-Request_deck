# Engineering notes

## 1. Design and decisions

The model is relational: a user owns requests; each request has status-history rows and assignment rows; each assignment links one episode to a request and records who assigned it and when.

```text
User 1 ─── * Request 1 ─── * RequestStatusHistory
                         └── * Assignment * ─── 1 Episode
                                  └── assigned_by → User
```

PostgreSQL is the source of truth. A request stores its current status for queue reads; `RequestStatusHistory` records prior states, actor, timestamp, and note for auditing and delivery-time analytics. The React UI holds the bearer token for the browser session and loads data through FastAPI. Live events are refresh signals only; the API remains the source for the displayed records.

Hardest decisions:

1. **Use an `Assignment` join table.** It preserves assignment metadata and uses a unique episode constraint to prevent reuse. There is no release action, so an episode cannot be reassigned later. That is stricter than “one request at a time”; if reuse is needed, I would add an explicit release action and enforce uniqueness only for active assignments.
2. **Separate current status from status history.** Queue reads stay simple while the history supports audit and median delivery-time calculations. A status and its history row are committed together.
3. **Keep deployment small without sharing role pages.** React builds in the Node stage of the Docker image; FastAPI serves its static output and the API from the same origin. Each role has its own routes and navigation, with permissions enforced by the API.

For live updates I chose **Server-Sent Events (SSE), not WebSockets**. The required communication is one-way, from server to browser. An authenticated stream publishes generic change notices; the browser reloads authorized data through the API.

## 2. Simplifications and next work

The UI is compact: episode assignment uses a request ID and filtered list, capped at 200 results. The request UI loads a bounded list rather than providing full pagination. CSV imports run synchronously and return row-level skip reasons. There are no export jobs or email notifications.

With two more days, I would:

- Add an assignment picker with request progress, plus server-side episode pagination.
- Run large CSV imports as background jobs with progress and an error report.
- Audit admin account and role changes.

## 3. What went wrong

- **Docker could not connect to PostgreSQL.** The API used `localhost`, which inside its container meant the API container. Logs showed a refused connection. I changed the Compose URL to `db:5432`; host tools use `localhost:5433`. Migrations, seeding, and the health endpoint then worked.
- **The frontend had broken navigation and blank lists.** Older HTML pages linked into the wrong role workspace and some operator links returned 404s. I replaced them with role-specific React routes served by FastAPI. When lists still looked empty, browser inspection showed that a shared component always displayed its empty-state message, even when the API returned rows. It now checks whether the returned list is actually empty.
- **The browser needed authenticated live updates.** Native `EventSource` cannot set the app’s bearer-token header, so I used `fetch` with an authenticated SSE stream, keepalives, and reconnect handling. The in-memory event broker fits the single API process in Compose; multiple API replicas need a shared broker.
- **Login failed under the installed bcrypt version.** The container traceback identified a Passlib/bcrypt incompatibility. I switched to bcrypt’s `hashpw` and `checkpw` functions and added password verification coverage.

## 4. Security

- Passwords use bcrypt hashes. Login issues a signed JWT with a configurable 60-minute default expiry. Protected routes reload the active account and enforce roles server-side; UI route checks are for navigation, not access control.
- Pydantic validates request fields; CSV rows are validated and bad or duplicate rows are reported. React escapes displayed text by default.
- The two risks I watch most are **broken object-level authorization** and **stolen credentials/tokens**. The API checks ownership on client request reads and decisions and does not return password hashes. Tokens are stored in session storage, so an XSS bug could expose one. Public deployment needs HTTPS, a strong private signing key, and production credential handling. Demo accounts and the Compose fallback key are local-only.

## 5. Scale

- **At 10× users:** database connection-pool pressure and long-lived SSE connections are likely first. I would measure pool use and request latency, then tune capacity. Multiple API workers/replicas require a shared event broker such as Redis or PostgreSQL notifications.
- **At 100× episodes:** synchronous imports and broad date-range analytics are likely first. Task, robot, and episode IDs are indexed, but recording-date aggregation still reads matching rows. I would inspect query plans, add a useful date index, batch large imports in a background job, and consider rollups or date partitioning if measurements support them.

PostgreSQL is the Compose database. CI uses SQLite; its median calculation uses window functions because SQLite lacks PostgreSQL’s `percentile_cont` aggregate.

## 6. AI and development tools

- **Grok:** helped shape the initial architecture and data model and draft the README. I revised the documentation to match the delivered system.
- **GitHub Copilot:** assisted with debugging.
- **Codex:** assisted with React frontend work, API and Docker/CI changes, tests, and live debugging. I checked the behavior against the project requirements.
