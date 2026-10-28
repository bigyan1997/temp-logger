# Notes and progress log

Keep this up to date. It is how a fresh Claude session (for example on the orders PC) learns what has happened.

## Source material
- Paper logs (photos, Oct 2026) and `Achieve HACCP Plan - V 1.6.pdf` (10 June 2026). Originals are not in the repo.
- Problems seen in the paper logs that the app is designed to fix: missing minus signs (e.g. freezer `15.6`), out-of-limit values with no corrective action (receiving 13.0, 14.2, 16.7, 18.0; chest freezer -12; dispatch 5.1), overwritten dates/times, blank slots, chest freezer always `-17`.

## Decisions
| Date | Decision |
|---|---|
| 2026-10-29 | Stack Django/DRF + Postgres + React/Vite/Tailwind (plain JS) |
| 2026-10-29 | Named accounts, roles admin (day) / night; both log all three check types |
| 2026-10-29 | Never delete records; void + audit log |
| 2026-10-29 | Dashboard alerts only; email/SMS on hold until the owner asks |
| 2026-10-29 | Host on orders PC, port 8003, deployed by push to GitHub then pull on orders PC |
| 2026-10-29 | Four storage units incl. Old Coolroom (confirmed by owner: extra column, same slots/limit as Coolroom) |
| 2026-10-29 | Runs F and I do not exist; Table 10 columns are just admin-managed suppliers |

## Design research (2026-10-29)
- Mobile form/touch: [AppMaster mobile data capture](https://appmaster.io/blog/mobile-data-capture-field-teams), [City University numeric keypad study](https://scholars.cityu.edu.hk/en/publications/effects-of-key-size-and-key-layout-on-numeric-data-entry-performa/) (bigger keys and phone-style layout performed best), [mobile form input types](https://dev.to/lovanaut55/mobile-form-input-types-page-splits-and-uploads-a-practical-checklist-3g61)
- Status colour accessibility: [Dynatrace status and health](https://developer.dynatrace.com/design/patterns/status-and-health/), [UTMB indicating meaning with colour](https://www.utmb.edu/accessibility/digital/100-days-of-a11y/100-days-article/days-of-a11y/2024/04/29/day-20--indicating-meaning-with-color), [NHS Scotland status palette](https://www.turasdesignsystem.nhs.scot/design/data-visualisation/status-palette/)
- Tailwind dashboards/tables: [BootstrapDash UI components guide](https://www.bootstrapdash.com/blog/ui-components-in-tailwind-css-dashboards)
- Existing HACCP/temperature apps (for inspiration, vendor info so treat as marketing): [Operandio roundup](https://operandio.com/haccp-management-software/), [SafetyCulture HACCP apps](https://safetyculture.com/apps/haccp-software), [Zip HACCP alternatives](https://www.sourceforge.net/software/product/Zip-HACCP/alternatives). Common features: mobile checklists, template library, automated alerts when a unit leaves tolerance, corrective-action tracking, audit-ready reports.
- Operations dashboards: [ConsultEvo ops dashboard design](https://consultevo.com/hidden-cost-bad-clickup-design-ops-dashboards/) (top row of key metrics, colour used sparingly, same colour per status everywhere, role-based dashboards), [Jestor overdue dashboard](https://blog.jestor.com/dashboard-overdue-tasks-priority-status/), [IBM operational dashboard](https://ibm.com/docs/en/SSLPL8_cd/com.ibm.mbs.doc/operational_dashboard/opdash_overview.html) (separate overdue KPI cards).
- Design plan lives in PLAN.md section 10.

## Open questions
- Highlighter colour meaning on Tables 10/11 (owner will confirm later; do not work on it now).

## Progress log
- 2026-10-29: Plan written (PLAN.md), project context written (CLAUDE.md). No code yet.
- 2026-10-29: SMS/email put on hold until later. Design and usability plan added (PLAN.md section 10).
- 2026-10-29: Old Coolroom confirmed (same as Coolroom). Highlighter question postponed by owner.
- 2026-10-29: System design written (docs/SYSTEM_DESIGN.md): architecture, repo layout, ER model, flows, API, security, deployment, testing, risks.
- 2026-10-29: Initial setup done. Git repo initialised. Backend: Django 6.1.1 + DRF, custom `accounts.User` (role admin/night), session login/logout/me/change-password/csrf endpoints, login throttle (10/min), admin-role permission class, 9 passing tests (run with USE_SQLITE=1). Frontend: Vite + React 19 + Tailwind 4 + React Router + TanStack Query + lucide icons; login page, auth context, placeholder Home; production build works. Postgres database `temp_logger` NOT yet created (needs the postgres superuser; see README step 1).
