@echo off
cd /d "%~dp0"

echo Installing Oracle ERP API Bridge dependencies...
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

echo.
echo Setup complete.
echo Copy .env.example to .env and update ORACLE_PASSWORD and API_SECRET_KEY.
pause
