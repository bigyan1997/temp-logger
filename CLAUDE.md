# Achieve Temperature Logger — context for Claude

Read this first, then [PLAN.md](PLAN.md) (full spec), [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) (architecture, data model, flows) and [NOTES.md](NOTES.md) (decisions and progress log).

## What this is
A temperature logger for **Achieve Cafe Provisions** (food distributor, Marrickville NSW) replacing paper logs from HACCP Plan v1.6: Table 9 (cold/frozen storage), Table 10 (receiving), Table 11 (dispatch). Purpose is HACCP compliance and auditor-ready records.

## Stack
Django + DRF, Postgres, React + Vite + Tailwind (plain JavaScript, no TypeScript). Same pattern as the owner's other apps `npd-tracker-v2` and `fleet-maintenance` (look at `C:\Users\fleet\npd-tracker-v2` for deploy scripts: `run_server.bat`, `auto_deploy.ps1`, `keep_alive.ps1`).

## Workflow
- Built on the owner's own computer first. Later pushed to GitHub, then pulled onto the **orders PC** (Windows, office), where it runs on **port 8003** under Waitress, reachable on the LAN and over Tailscale. Ports 8000/8001/8002 belong to other apps.
- Because the orders PC is a different machine, Claude's memory does not carry over. **Everything needed must live in this repo.** Update NOTES.md after every meaningful change.
- Keep secrets, hostnames, IPs and credentials out of the repo (use `.env`, gitignored, and a local `DEPLOYMENT_NOTES.md` on the orders PC that is also gitignored).
- On the orders PC the live folder may be the one serving the app: do not overwrite a live `frontend/dist` with a plain build; follow the npd-tracker-v2 NOTES.md infra section.

## Business rules (non-negotiable)
- **Never delete records.** No delete endpoints, no admin delete, block DELETE in Postgres. Corrections = void with reason + replacement row linked via `supersedes`; every change goes to AuditLog.
- Named accounts, roles `admin` (day) and `night`. Both roles enter storage, receiving and dispatch readings; only admin signs off corrective actions, voids, views all records and manages settings.
- **Who took the reading:** logins are shared (admin@ and night@), so every reading/check must also record `recorded_by` = a `StaffMember` picked from an admin-managed list ("Your name", required, remembered per phone). Use the `setup.models.Attributed` abstract model on StorageReading/ReceivingCheck/DispatchReading and `RecordedBySerializerMixin` on their serializers. Staff are deactivated, never deleted.
- **Code style:** the owner wants all code clean, tidy and easy to understand: small focused files, plain names, short comments that explain why, no clever tricks. Reuse the existing patterns (`ConfigViewSet` on the backend; `sections.js` + `ResourcePage` on the frontend) instead of writing one-off screens.
- **Admin never needs Django admin:** everything day staff manage (logins, staff names, units and limits, suppliers, runs) is in the React Settings area (`/settings`).
- Limits: chilled/coolrooms/dispatch ≤5 °C, frozen ≤-15 °C. Baked pies over 5 °C on receiving are acceptable only if moved to the coolroom immediately. An out-of-limit reading cannot be saved without a corrective action.
- Storage units: Coolroom, Old Coolroom, Freezer, Chest Freezer. Storage slots: Sun 21:00; Mon–Thu 09:00 and 21:00; Fri 09:00 and 15:00.
- Dispatch runs: A, B, C, D, E, G, H, J, K, L, M (no F or I).
- Receiving suppliers are admin-managed (Atown–Knefeh, Posh Foods, Shepherd's, Yianni, Madhouse, Helens, Garlos, Quality Patisserie to start).
- Alerts: dashboard only. Email/SMS is on hold, do not build it until the owner asks.
- Design: easy, clear, visually appealing. Follow PLAN.md section 10 (big touch targets, custom number pad with ± key, status never by colour alone, calm teal/white look).
- The meaning of highlighter colours on the paper Tables 10/11 is unknown; the owner will provide it later. Do not invent it.
- Time zone Australia/Sydney, timestamps stored UTC.

## Status
See the progress log in NOTES.md. Initial setup (auth, Django, frontend scaffold) is done; next is Phase 1 models (units, suppliers, runs, readings) and entry screens. Setup commands are in README.md. Use `USE_SQLITE=1` only for quick local tests.
