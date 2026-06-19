@echo off
cd /d "%~dp0"

echo Starting Oracle ERP API Bridge...
echo Oracle Server: 192.168.0.118
echo API Machine:   192.168.0.13
echo API URL:       http://192.168.0.13:5000
echo.

python app.py

pause
