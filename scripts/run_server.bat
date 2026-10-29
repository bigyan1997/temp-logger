@echo off
rem Temperature Logger server (port 8003). Started at boot by the "Temperature Logger Server"
rem scheduled task (made by install_autostart.ps1) and, if it stops responding, by keep_alive.ps1.
rem If the server stops for any reason it is started again after 5 seconds.
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
:loop
rem Another copy already serving? Then this one is not needed.
netstat -ano -p tcp | findstr "LISTENING" | findstr /c:"0.0.0.0:8003 " >nul && (
    echo Temperature Logger is already running on port 8003 - nothing to do.
    exit /b 0
)
echo %date% %time% Starting Temperature Logger on port 8003...
waitress-serve --listen=0.0.0.0:8003 config.wsgi:application
echo %date% %time% Server stopped - restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto loop
