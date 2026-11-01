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
- Named accounts, roles `admin` (day) and `night`. Both roles enter storage, receiving and dispatch readings; only admin voids, views all records and manages settings. **Corrective actions are signed off by a manager** (a staff name ticked "can sign off", day or night): the night login sees only what is waiting and can sign off. The manager picks their name; if they also took the reading they must add a note saying why (their own sign-off is allowed, but the note is required). Person, login, note and time are recorded and audit-logged.
- **Who took the reading:** logins are shared (admin@ and night@), so every reading/check must also record `recorded_by` = a `StaffMember` picked from an admin-managed list ("Your name", required, remembered per phone). Use the `setup.models.Attributed` abstract model on StorageReading/ReceivingCheck/DispatchReading and `RecordedBySerializerMixin` on their serializers. Staff are deactivated, never deleted.
- **Devices:** all staff use desktop/laptop computers. Design desktop-first and keyboard-first (type the number, Tab between fields, Enter to save, several readings per screen). No phone-specific number pad. Stay responsive but do not optimise for phones.
- **Code style:** the owner wants all code clean, tidy and easy to understand: small focused files, plain names, short comments that explain why, no clever tricks. Reuse the existing patterns (`ConfigViewSet` on the backend; `sections.js` + `ResourcePage` on the frontend) instead of writing one-off screens.
- **Admin never needs Django admin:** everything day staff manage (logins, staff names, units and limits, suppliers, runs) is in the React Settings area (`/settings`).
- Limits: chilled/coolrooms/dispatch ≤5 °C, frozen ≤-15 °C. Baked pies over 5 °C on receiving are acceptable only if moved to the coolroom immediately. An out-of-limit reading cannot be saved without a corrective action.
- Storage units: Coolroom, Old Coolroom, Freezer, Chest Freezer. Storage slots: Sun 21:00; Mon–Thu 09:00 and 21:00; Fri 09:00 and 15:00.
- Dispatch runs: A, B, C, D, E, G, H, J, K, L, M (no F or I).
- Receiving suppliers are admin-managed (Atown–Knefeh, Posh Foods, Shepherd's, Yianni, Madhouse, Helens, Garlos, Quality Patisserie to start).
- **Git commits:** never mention Claude or add a co-author line in commit messages (owner's instruction).
- Alerts: dashboard only. Email/SMS is on hold, do not build it until the owner asks.
- Design: easy, clear, visually appealing. Follow PLAN.md section 10 (big touch targets, custom number pad with ± key, status never by colour alone, calm teal/white look).
- The meaning of highlighter colours on the paper Tables 10/11 is unknown; the owner will provide it later. Do not invent it.
- Time zone Australia/Sydney, timestamps stored UTC.

## Status
All planned features are built (see NOTES.md for the detail): logging screens, corrective actions, Today page, admin dashboard, records with void/correct, trends, PDF reports, audit log, settings, database protections, deployment scripts. Recent changes: Sunday rows on Tables 10/11, PDFs up to 186 days, one Save at the bottom of Receiving and Dispatch (Dispatch starts with no runs: add the ones that went out), corrective-action sign-off records the person (`signed_off_person`), is done by managers on either login (`StaffMember.can_sign_off`) and needs a note for their own entries and the PDFs show "Logged by", `scripts/install_autostart.ps1` for boot-time start. After pulling new code always run `python manage.py migrate` (`scripts\deploy.ps1` does). Not yet done: first deploy on the orders PC (follow docs/DEPLOYMENT.md), clicking through the screens in a browser, and the optional extras listed under "Known gaps" in NOTES.md.

Where things are: `backend/readings` (readings, rules, day, dashboard, void), `backend/audit`, `backend/reports`, `backend/setup` (lists), `backend/accounts` (logins); `frontend/src/pages` (screens), `frontend/src/components`, `frontend/src/lib`; `scripts/` (Windows server scripts). Run the backend tests with `python manage.py test --noinput` (needs Postgres). Use `USE_SQLITE=1` only for quick local runs.
