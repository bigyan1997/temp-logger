# Achieve Temperature Logger — Project Plan

Replaces the paper logs in HACCP Plan v1.6: **Table 9** (cold/frozen storage), **Table 10** (receiving), **Table 11** (dispatch).

## 1. Decisions

| Topic | Decision |
|---|---|
| Stack | Django + DRF, Postgres, React + Vite + Tailwind (plain JavaScript, same as npd-tracker-v2) |
| Users | Named accounts, two roles: **admin** (day) and **night** |
| Who logs what | Storage: night 9PM slots, day 9AM/3PM slots. **Receiving and dispatch: both roles** |
| Alerts | Dashboard only for now. Email/SMS later (Phase 4, not being worked on now; SMS provider idea: MightyText, unverified) |
| Workflow | Built on the owner's own computer first, then pushed to GitHub and pulled onto the orders PC. Everything must be documented in the repo (see CLAUDE.md, NOTES.md) |
| Hosting | The orders PC (office Windows PC), port **8003** (8000/8001/8002 are taken by other apps), Waitress, LAN + Tailscale, keep-alive task, same pattern as npd-tracker-v2 / fleet-maintenance |
| Retention | **Never delete.** Records are voided/superseded, never removed |
| Deferred | Meaning of highlighter colours on paper Tables 10/11 (more info coming) |

## 2. Rules taken from the HACCP plan

| Check | Limit | Source |
|---|---|---|
| Coolroom | ≤ 5 °C | SOP 4.1.2 |
| Freezer / Chest freezer | ≤ -15 °C (hard frozen) | Table 1 |
| Receiving chilled | ≤ 5 °C | SOP 4.1.1 |
| Receiving frozen | ≤ -15 °C | Table 1 |
| Receiving freshly baked pies over 5 °C | Allowed only if moved to coolroom immediately | Table 1 corrective action |
| Dispatch | ≤ 5 °C | SOP 4.1.3 |

Limits are stored per unit/check type and editable by admin (changes are audit-logged).

Corrective-action options offered when a reading fails:
- Storage: used immediately / moved to other unit / discarded (2hr/4hr rule: <2h use or move, 2–4h use immediately or discard, >4h discard) / equipment repair arranged
- Receiving: rejected / accepted with supplier justification / pie moved to coolroom / supplier notified
- Dispatch: contacted Operations Manager / product discarded / re-checked

## 3. Roles and permissions

| Action | Night | Admin |
|---|---|---|
| Enter readings (storage, receiving, dispatch) | yes | yes |
| Record corrective action | yes | yes |
| Sign off corrective action | no | yes |
| View own recent entries | yes | yes |
| View all records, trends, reports | no | yes |
| Void/correct an entry (with reason) | no | yes |
| Manage users, units, suppliers, runs, limits | no | yes |

Login is per person, so "entered by" is automatic. No self-registration; admin creates accounts.

## 4. Data model

Every table has `created_at`, and records carry `entered_by` (the login) and `recorded_by` (the StaffMember). No hard deletes anywhere.

- **StaffMember** — name, `active`; the people who take readings, picked in a required "Your name" dropdown on every entry (logins are the shared admin@/night@ accounts). Admin manages the list; never deleted
- **User** — Django user + `role` (admin/night), `active`
- **Unit** — name (Coolroom, Old Coolroom, Freezer, Chest Freezer), kind (chilled/frozen), `max_temp`, `active`
- **StorageSlot** (config) — weekday + time (Sun 21:00; Mon–Thu 09:00, 21:00; Fri 09:00, 15:00) and which unit(s) apply; generates the "due" list
- **StorageReading** — unit, slot date/time, `recorded_at`, value, entered_by, note, `status` (ok/out_of_limit), `voided`
- **Supplier** — name, `active` (Atown–Knefeh, Posh Foods, Shepherd's, Yianni, Madhouse, Helens, Garlos, Quality Patisserie; the column headings on Table 10 are just suppliers, so admin can add or deactivate any supplier)
- **ReceivingCheck** — supplier, date, `no_delivery` flag, temp (nullable), product_type (chilled/frozen/baked pie), packaging_ok, note, entered_by
- **Run** — code (A–E, G, H, J–M; F and I do not exist), `active`
- **DispatchReading** — run, date, temp, entered_by, note
- **CorrectiveAction** — link to the failing reading (one nullable FK per reading type, exactly one set; see docs/SYSTEM_DESIGN.md), action_taken, time_above_limit, notes, entered_by, signed_off_by/at
- **AuditLog** — model, object id, field, old → new, reason, user, timestamp (written by the void/correct flow)
- **Later:** ThermometerCalibration (Table 14), NonConformanceReport (Table 5), VerificationRecord (Tables 13/15)

Void/correct: original row is kept and marked `voided` with reason; a replacement row links to it via `supersedes`. DB-level protection: no DELETE endpoints, Django admin delete permissions removed, and a Postgres trigger/rule blocking DELETE on record tables.

## 5. API (DRF, session auth)

- `POST /api/auth/login|logout`, `GET /api/auth/me`
- `GET /api/due` — storage slots currently due/overdue
- `POST /api/storage-readings`, `POST /api/receiving-checks`, `POST /api/dispatch-readings`
- `POST /api/corrective-actions`, `POST /api/corrective-actions/:id/signoff` (admin)
- `GET` list endpoints with filters (date range, unit, supplier, run, out_of_limit) — admin
- `POST /api/<record>/:id/void` (admin, reason required)
- `GET /api/reports/{storage,receiving,dispatch}.pdf?from=&to=`
- Admin CRUD for units, suppliers, runs, users (deactivate, not delete)

Server validates everything: limit check sets `status`, an out-of-limit save is rejected unless a corrective action is included in the same request. Sanity checks reject implausible values (e.g. positive freezer reading asks to confirm).

## 6. Screens

**Everyone (phone-first, large touch targets):**
1. Login
2. **Today** — due storage readings (overdue in red), shortcuts to Receiving and Dispatch
3. **Storage entry** — three unit fields, ± button on the keypad, live green/red feedback
4. **Receiving** — supplier tiles, "no delivery" button, packaging toggle, product type
5. **Dispatch** — run tiles in a grid, quick temperature entry
6. **Corrective action sheet** — appears automatically on a failing reading
7. **My recent entries**

**Admin (laptop-friendly):**
1. **Dashboard** — missed readings, open corrective actions, latest out-of-limit values
2. **Records** — filterable tables for all three checks, voided rows shown struck through
3. **Trends** — per-unit chart with the limit line
4. **Corrective actions** — sign-off queue
5. **Reports** — PDFs laid out like Tables 9/10/11 for auditors
6. **Settings** — users, units and limits, suppliers, runs

## 7. Hosting and operations

- Same pattern as npd-tracker-v2: Waitress on port 8003, Whitenoise serving the built React bundle, keep-alive scheduled task, auto-deploy script.
- Reachable on office LAN and via Tailscale. HTTPS is not needed on LAN, but session cookies set accordingly.
- **Backups matter more here because nothing is deleted:** nightly `pg_dump` to a second location (another drive or Google Drive), kept for the retention period, with a restore test before go-live.
- Server time zone `Australia/Sydney`; all timestamps stored UTC.
- Secrets and host details kept out of the repo (like `DEPLOYMENT_NOTES.md`).

## 8. Phases

**Phase 1 — Core logging (MVP)**
- Django project, Postgres, auth, roles, named accounts
- Units, suppliers, runs, seed data
- Three entry forms, limit checks, forced corrective actions
- Today view with due/overdue slots
- Deployment on the office PC, backups

**Phase 2 — Admin oversight**
- Dashboard, records tables, trends
- Corrective-action sign-off
- Void/correct with audit log
- PDF exports matching Tables 9/10/11

**Phase 3 — HACCP verification**
- Monthly CCP record review checklist (Table 15, Office Manager)
- Thermometer calibration (Table 14), non-conformance report (Table 5)
- Table 13 audit checklist

**Phase 4 — Alerts**
- Email and SMS on out-of-limit and missed readings
- Escalation if a corrective action is unsigned

**Parallel (when info arrives):** highlighter colour meaning from Tables 10/11.

## 9. Open items

- Highlighter colour meaning on Tables 10/11: owner will confirm later. Not needed now.
- Old Coolroom: confirmed. It is an extra storage column with the same slots and ≤5 °C limit as Coolroom.
- (SMS/email: on hold.)

## 10. Design and usability

Goal: a night-shift worker in a cold room, wearing gloves, can log a reading in under 10 seconds without training. Admin can see "is everything OK?" in one glance.

### Principles (informed by web research, sources in NOTES.md)
1. **One task per screen, big targets.** Tap targets at least 48 px (research suggests 44 px minimum; field use with gloves benefits from larger). Custom on-screen number pad with keys around 20 mm, laid out like a phone keypad, including a large **±** key and a decimal key.
2. **Right keyboard.** Where the system keyboard is used, `inputmode="decimal"`. Labels sit above fields, never as placeholders.
3. **Status is never colour alone.** Every state has colour + icon + text: ✔ **In range**, ▲ **Near limit** (within 1 °C), ✖ **Out of limit**, ○ **Not yet logged**. Avoid red/green as the only distinction; use a colour-blind-safe palette (teal / amber / red-magenta) and different shapes.
4. **Prevent errors rather than report them.** Live check against the limit as the number is typed; confirm dialog for implausible values (positive freezer reading, change of more than ~10 °C from last reading); corrective-action sheet opens automatically on a fail.
5. **Auto-save drafts.** If a worker is interrupted mid-entry, the partly entered values are kept on the device.
6. **Show what is still to do.** Home screen is a checklist of due readings with a progress indicator; done items turn into a quiet tick.
7. **Plain language.** Words from the paper sheets (Coolroom, Old Coolroom, Freezer, Chest Freezer, Run A) and the corrective actions from the HACCP SOP. No jargon.
8. **Calm, uncluttered look.** Generous white space, one accent colour, clear type hierarchy, light theme by default with dark mode through Tailwind design tokens (useful for night shift).

### Visual direction
- Clean "clinical but friendly" style: white/cool-grey surfaces, deep teal as the brand accent, rounded cards, soft shadows, a single sans-serif font (Inter or similar), tabular numerals so temperatures line up.
- Temperature displayed large, with the limit shown small beside it ("-18.2 °C  limit ≤ -15").
- Icons from one consistent set (Lucide).

### Layout by role
- **Night/phone:** bottom tab bar (Today · Storage · Receiving · Dispatch · Mine). One screen = one job. Sticky "Save" button above the keypad. Installable as a PWA.
- **Admin/desktop:** left sidebar (Dashboard · Records · Trends · Corrective actions · Reports · Settings). Top strip of summary tiles (Missed, Out of limit, Awaiting sign-off, Logged today).
- **Tables:** sortable/filterable, sticky header, low-priority columns collapse on narrow screens, voided rows struck through, a colour + icon status column, pagination.
- **Charts:** one line per unit with a dashed limit line and out-of-limit points marked with a symbol, not just colour.

### Accessibility checks (build into Phase 1)
Colour contrast meeting WCAG AA, visible keyboard focus, form errors announced to screen readers, tested at 360 px wide, tested with a colour-blindness simulator.

### Build approach for the UI
Design tokens (colours, spacing, radii) defined once in the Tailwind config; small shared components (Button, NumberPad, StatusBadge, ReadingCard, DataTable, Modal) so every screen looks the same. Before coding, a quick clickable mock of the Today, Storage-entry and Dashboard screens for the owner to approve.

### Lessons from existing HACCP apps and operations dashboards
- Commercial apps (SafetyCulture, Zip HACCP, Operandio and others) all centre on: mobile checklists, alerts when a unit goes out of tolerance, corrective-action tracking and audit-ready reports. We cover the same ground, tailored to Achieve's exact sheets, with no per-user subscription.
- **Define "overdue" strictly:** a slot whose time has passed with no reading logged. Do not flag items that are merely upcoming, so the number can be trusted.
- Dashboard top row = key numbers only (Missed, Out of limit, Awaiting sign-off, Logged today). Use colour sparingly, and use the same colour/icon for each status on every screen.
- Separate lists for "needs action now" (overdue, out of limit) and "all good", so critical items never get lost in a long list.
- Role-based home screens: night sees their checklist, admin sees oversight. Not one screen for everyone.
