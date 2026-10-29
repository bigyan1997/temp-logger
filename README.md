# Achieve Temperature Logger

Temperature logging for Achieve Cafe Provisions, replacing the paper HACCP logs (storage, receiving, dispatch).

- Plan and spec: [PLAN.md](PLAN.md)
- Architecture and data model: [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)
- Deploying to the orders PC: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- Context for Claude sessions: [CLAUDE.md](CLAUDE.md)
- Decisions and progress: [NOTES.md](NOTES.md)

**What it does:** night and day staff log storage, receiving and dispatch temperatures on a computer; out-of-limit readings need a corrective action; the admin gets a dashboard, records, trends, PDF reports for auditors, and an audit log. Records are never deleted.

Stack: Django 6 + DRF, Postgres, React + Vite + Tailwind (plain JS). Runs on the office orders PC, port 8003.

## Local setup (development)

### 1. Postgres (once)
In psql as the `postgres` superuser (pick your own password):
```sql
CREATE ROLE temp_logger LOGIN PASSWORD 'choose-a-password' CREATEDB;
CREATE DATABASE temp_logger OWNER temp_logger;
```
`CREATEDB` lets Django's test runner create a throwaway test database.

### 2. Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
copy .env.example .env            # then edit: DJANGO_SECRET_KEY, DB_PASSWORD
python manage.py migrate
python manage.py createsuperuser  # first admin; set role to "Admin (day)" in /admin/
python manage.py runserver 8003
```
Quick tests without Postgres: `set USE_SQLITE=1` then `python manage.py test` (never use on the orders PC).

### 3. Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to Django on :8003
npm run build      # production bundle into frontend/dist (served by Django)
```

## Accounts
Login is by **email + password**. Two shared accounts: `admin@achievecafeprovisions.com.au` (role Admin) and `night@achievecafeprovisions.com.au` (role Night). Admin staff manage logins, staff names, storage units (with limits), suppliers and delivery runs in the app itself under **Settings**, so Django admin (`/admin/`) is only a back-up tool. Logins live in the database, so they must be created again on each new database (including the orders PC). Accounts are deactivated, never deleted.

## Running the tests
```bash
cd backend
.venv\Scripts\activate
python manage.py test --noinput
```
The tests use Postgres (the role needs `CREATEDB`), including the checks that the database refuses to delete records.

## Deploying
See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the orders PC (port 8003, keep-alive, nightly backup, updating with `scripts\deploy.ps1`).
