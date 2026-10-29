# Deploying to the orders PC

The app runs on the office orders PC (Windows) on **port 8003**, using Waitress, next to the other apps that use ports 8000 to 8002. Staff reach it on the office network at `http://<orders-pc-address>:8003`, or from home over Tailscale.

Keep real addresses, passwords and keys out of the repo. Put them in `backend\.env` and in a local `DEPLOYMENT_NOTES.md` (both are gitignored).

## First-time setup

1. **Install** (if not already there): Git, Python 3.14, Node.js, PostgreSQL.
2. **Get the code**
   ```
   cd C:\Users\<you>
   git clone https://github.com/bigyan1997/temp-logger.git
   cd temp-logger
   ```
3. **Create the database** (pgAdmin Query Tool, one statement at a time, with your own password):
   ```sql
   CREATE ROLE temp_logger LOGIN PASSWORD 'choose-a-password' CREATEDB;
   ```
   ```sql
   CREATE DATABASE temp_logger OWNER temp_logger;
   ```
4. **Backend**
   ```
   cd backend
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```
   Edit `.env`: set `DB_PASSWORD`, a long random `DJANGO_SECRET_KEY`, and:
   ```
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,<orders-pc-name-or-address>,<tailscale-address>
   CSRF_TRUSTED_ORIGINS=http://<orders-pc-name-or-address>:8003,http://<tailscale-address>:8003
   ```
   Then:
   ```
   python manage.py migrate
   python manage.py create_default_logins --password "<a-strong-password>"
   ```
   `migrate` also adds the default storage units, suppliers and runs, and the database protections that stop records being deleted. `create_default_logins` makes `admin@achievecafeprovisions.com.au` and `night@achievecafeprovisions.com.au`. Logins are data, so they must be created on this database; they do not come from GitHub.
5. **Frontend**
   ```
   cd ..\frontend
   npm install
   npm run build
   cd ..\backend
   python manage.py collectstatic --noinput
   ```
6. **Try it**: `scripts\run_server.bat`, then open `http://localhost:8003` on that PC.
7. **Let the office reach it**: allow port 8003 through Windows Firewall (PowerShell as Administrator):
   ```
   New-NetFirewallRule -DisplayName "Temperature Logger 8003" -Direction Inbound -Protocol TCP -LocalPort 8003 -Action Allow -Profile Private
   ```
8. **Start at boot and stay up** (PowerShell opened with *Run as administrator*, from the repo folder):
   ```
   .\scripts\install_autostart.ps1
   ```
   This starts the server whenever the PC turns on (nobody has to log in), restarts it if it stops, checks every 5 minutes that it still answers, and stops the PC sleeping while plugged in. It is safe to run again. Log: `backend\logs\server.log`.
9. **After a reboot**: restart the PC once and open `http://localhost:8003` after about a minute to confirm it came back by itself. (Also set Windows Update "active hours" so it does not restart in the middle of the day. When it does restart, the server comes back by itself.)
10. **Nightly backup** (2 am). Use a different drive or a synced folder for `-BackupDir` if you can:
    ```
    schtasks /Create /TN "Temperature Logger Backup" /SC DAILY /ST 02:00 /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"$PWD\scripts\backup.ps1\" -BackupDir D:\Backups\temp-logger"
    ```
    Run `scripts\backup.ps1` once by hand and check that a `.dump` file appears. **Test a restore before relying on it** (see below).

## Updating

After new code is pushed to GitHub, on the orders PC:

```
cd C:\Users\<you>\temp-logger
.\scripts\deploy.ps1
```

It pulls, installs packages, runs the tests, builds the frontend into a side folder, migrates the database, swaps the new frontend in, restarts the server, and checks it answers. If anything fails it stops before replacing the running app.

If Claude Code is used on the orders PC, it should read `CLAUDE.md` first. Never run a plain `npx vite build` while the app is live (it replaces the live `dist` folder); `deploy.ps1` builds to `dist-next` for that reason.

## Restoring from a backup

Practise this on a spare database first:

```
createdb -h 127.0.0.1 -U postgres temp_logger_restore_test
pg_restore -h 127.0.0.1 -U postgres -d temp_logger_restore_test D:\Backups\temp-logger\temp_logger_2026-11-02.dump
```
Open the result in pgAdmin and check the readings are there. To restore for real, stop the server, restore into an empty `temp_logger` database, and start it again.

## Where things are

| What | Where |
|---|---|
| Server log, keep-alive log, backup log | `backend\logs\` |
| Database settings and secrets | `backend\.env` (never committed) |
| Backups | the `-BackupDir` you chose |
| Port | 8003 (`scripts\run_server.bat`) |
