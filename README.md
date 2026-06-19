# Oracle ERP API Bridge

A small Flask API bridge that connects a Windows API machine to an Oracle 11g ERP database.

## Architecture

```text
Oracle ERP Database Server
192.168.0.118:1521 / SID ORCL
        ↑
        │ Oracle client connection
        │
Windows API Machine
192.168.0.13:5000
        ↑
        │ HTTP API
        │
WordPress / Laravel / Website
```

## Important

This project uses `python-oracledb`, imported as `oracledb`.

Do **not** install `cx_Oracle` for this project.

Oracle 11g usually requires Oracle Thick Mode, so you must install Oracle Instant Client and set `ORACLE_CLIENT_DIR`.

## Project Structure

```text
oracle_erp_api_bridge/
│
├── app.py
├── config.py
├── db.py
├── auth.py
├── requirements.txt
├── .env.example
├── run.bat
├── setup.bat
├── test_health.ps1
├── test_oracle_port.ps1
│
├── routes/
│   ├── __init__.py
│   ├── health.py
│   ├── families.py
│   └── students.py
│
└── repositories/
    ├── __init__.py
    ├── families_repo.py
    └── students_repo.py
```

## Setup on Windows machine 192.168.0.13

### 1. Install Python

Install Python 3.x.

During installation, enable:

```text
Add Python to PATH
```

### 2. Install Oracle Instant Client

Download Oracle Instant Client Basic 64-bit for Windows.

Extract it to something like:

```text
C:\oracle\instantclient_21_x
```

Make sure this value matches `ORACLE_CLIENT_DIR` in your `.env` file.

### 3. Create `.env`

Copy `.env.example` to `.env`:

```cmd
copy .env.example .env
```

Then edit `.env` and set:

```env
ORACLE_PASSWORD=your_real_password
API_SECRET_KEY=your_real_secret_key
ORACLE_CLIENT_DIR=C:\oracle\instantclient_21_x
```

### 4. Install dependencies

```cmd
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

Or run:

```cmd
setup.bat
```

### 5. Run the API

```cmd
python app.py
```

Or run:

```cmd
run.bat
```

### 6. Test locally on the Windows API machine

```text
http://localhost:5000/api/health
```

### 7. Test from another machine on the same LAN

```text
http://192.168.0.13:5000/api/health
```

Expected result:

```json
{
  "status": "ok",
  "oracle": "connected",
  "host": "192.168.0.118",
  "sid": "ORCL",
  "test": 1
}
```

## API Endpoints

| Method | Endpoint | Protected | Description |
|--------|----------|-----------|-------------|
| GET | `/` | No | API index |
| GET | `/api/health` | No | Check Oracle connection |
| GET | `/api/families` | Yes | All active families |
| GET | `/api/families/{id}` | Yes | Family with students |
| GET | `/api/families/{id}/students` | Yes | Students for one family |
| GET | `/api/students` | Yes | All students for current year |
| GET | `/api/students/{id}` | Yes | Single student |
| GET | `/api/students/search?q=name` | Yes | Search students by name |

## Authentication

Protected endpoints require:

```text
X-API-Key: your-secret-key
```

PowerShell example:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:5000/api/families" `
  -Headers @{ "X-API-Key" = "change-this-secret-key" }
```

JavaScript example:

```javascript
fetch("http://192.168.0.13:5000/api/families", {
    headers: {
        "X-API-Key": "change-this-secret-key"
    }
})
.then(response => response.json())
.then(data => console.log(data));
```

## Oracle Table Mapping

The repository SQL files currently use placeholder table names:

```text
FAMILIES
STUDENTS
```

You must replace them with the real Oracle ERP table names and column names.

Start by testing:

```text
/api/health
```

If health works, the Oracle connection is correct. Then map the real tables in:

```text
repositories/families_repo.py
repositories/students_repo.py
```

## Common Errors

### DPI-1047

Oracle Instant Client cannot be found.

Fix `ORACLE_CLIENT_DIR` in `.env`.

### ORA-12505

Oracle listener does not know the SID.

Check:

```env
ORACLE_SID=ORCL
```

### ORA-01017

Invalid username or password.

Check:

```env
ORACLE_USER=DEMO
ORACLE_PASSWORD=...
```

### Timeout or connection refused

Check:

- Oracle server IP: `192.168.0.118`
- Oracle port: `1521`
- Windows firewall on Oracle server
- Oracle listener is running
- Network route between `192.168.0.13` and `192.168.0.118`
