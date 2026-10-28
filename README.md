# Achieve Temperature Logger

Temperature logging for Achieve Cafe Provisions, replacing the paper HACCP logs (storage, receiving, dispatch).

- Plan and spec: [PLAN.md](PLAN.md)
- Architecture and data model: [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)
- Context for Claude sessions: [CLAUDE.md](CLAUDE.md)
- Decisions and progress: [NOTES.md](NOTES.md)

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
Named accounts only; create them in Django admin (`/admin/`). Roles: **Admin (day)** and **Night**. Accounts are switched off, never deleted.

Deployment instructions for the orders PC will be added when the first deploy happens.
