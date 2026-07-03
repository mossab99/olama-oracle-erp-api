# Olama Oracle ERP API Bridge

A GitHub-ready setup and deployment guide for the Flask API bridge that connects the legacy Oracle ERP database to WordPress/Laravel systems through a controlled HTTP API.

The API reads from Oracle and exposes selected school ERP data such as families and students. Oracle remains the source of truth; WordPress/Laravel consume the API or sync data from it.

---

## 1. Project Goal

This project solves the problem of connecting modern web systems to a legacy Oracle ERP without giving WordPress direct Oracle access.

```text
Oracle ERP Database
        ↓
Flask API Bridge
        ↓
WordPress / Laravel / Future ERP
```

Current API capabilities:

- Oracle connection health check
- Active families
- Family details
- Students by family
- Active students for the current academic year
- Student search
- Safe API-key protection
- GitHub-based deployment to a Proxmox Ubuntu container

Planned extensions:

- Family financial card
- Family statement
- Payment/receipt details
- WordPress sync plugin
- Laravel ERP migration layer

---

## 2. Final Working Architecture

### School Network

```text
Oracle ERP Server
192.168.0.118:1521
Service Name: orcl
Schema: DEMO

        ↓ Oracle Client connection

Ubuntu Proxmox LXC API Server
192.168.0.16:5000
Flask + Gunicorn + python-oracledb
```

### Home / Development WordPress Network

```text
Home WordPress Development Server
        ↓ internet / port forwarding / SSH tunnel
School Public IP
        ↓
Flask API LXC
192.168.0.16:5000
```

### Public/Remote Access Options

#### Option A — Public Port Forwarding

Router/firewall rule:

```text
PUBLIC_IP:15000  →  192.168.0.16:5000
```

WordPress API base URL:

```text
http://PUBLIC_IP:15000
```

#### Option B — SSH Tunnel

```bash
ssh -N -L 15000:192.168.0.16:5000 user@PUBLIC_IP
```

WordPress API base URL:

```text
http://127.0.0.1:15000
```

Use `127.0.0.1:15000` only if the SSH tunnel is running on the same machine that hosts WordPress.

---

## 3. Technology Stack

| Layer | Technology |
|---|---|
| API Framework | Flask |
| Production Server | Gunicorn |
| Oracle Driver | python-oracledb |
| Oracle Mode | Thick Mode |
| Oracle Client | Oracle Instant Client 19 |
| Container OS | Ubuntu 22.04 LTS LXC |
| Host | Proxmox VE |
| Deployment | GitHub + deploy script |
| Runtime Service | systemd |
| Consumer | WordPress / Laravel |

---

## 4. Important Oracle Notes

The ERP database is Oracle 11g, so this API uses `python-oracledb` in Thick Mode with Oracle Instant Client.

Do not use:

```bash
cx_Oracle
```

Use:

```bash
oracledb
```

Python import:

```python
import oracledb
```

The successful connection uses:

```text
SERVICE_NAME=orcl
```

not SID.

---

## 5. Repository Structure

```text
oracle_erp_api_bridge/
│
├── app.py
├── config.py
├── db.py
├── auth.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── deploy.sh
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

---

## 6. Security Rules

Never commit these files to GitHub:

```text
.env
__pycache__/
*.pyc
*.pyo
*.log
venv/
.venv/
env/
test_client.py
test_db.py
test_db_service.py
*.zip
```

The real `.env` file must stay only on the server.

Commit `.env.example`, not `.env`.

---

## 7. Recommended `.gitignore`

```gitignore
.env
__pycache__/
*.pyc
*.pyo
*.log

venv/
.venv/
env/

*.zip

test_client.py
test_db.py
test_db_service.py
test_oracle_port.ps1
```

---

## 8. Example `.env.example`

```env
ORACLE_HOST=192.168.0.118
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=orcl
ORACLE_SID=
ORACLE_USER=DEMO
ORACLE_PASSWORD=CHANGE_ME

CURRENT_YEAR=2025/2026

API_HOST=0.0.0.0
API_PORT=5000
API_SECRET_KEY=CHANGE_ME

ORACLE_CLIENT_DIR=/opt/oracle/instantclient_19
```

Do not commit the real password or real API key.

---

## 9. Python Requirements

`requirements.txt`:

```txt
flask
flask-cors
oracledb
python-dotenv
```

Gunicorn is installed on the server:

```bash
pip install gunicorn
```

---

## 10. Main Configuration

`config.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    ORACLE_HOST = os.getenv("ORACLE_HOST", "192.168.0.118")
    ORACLE_PORT = int(os.getenv("ORACLE_PORT", "1521"))

    ORACLE_SERVICE_NAME = os.getenv("ORACLE_SERVICE_NAME", "orcl")
    ORACLE_SID = os.getenv("ORACLE_SID", "")

    ORACLE_USER = os.getenv("ORACLE_USER", "DEMO")
    ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "")

    CURRENT_YEAR = os.getenv("CURRENT_YEAR", "2025/2026")

    API_SECRET_KEY = os.getenv("API_SECRET_KEY", "change-this-secret-key")
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "5000"))

    ORACLE_CLIENT_DIR = os.getenv("ORACLE_CLIENT_DIR", "")
```

---

## 11. Oracle Database Connection

`db.py`:

```python
import oracledb
from config import Config


_oracle_client_initialized = False


def init_oracle_client():
    global _oracle_client_initialized

    if _oracle_client_initialized:
        return

    if Config.ORACLE_CLIENT_DIR:
        oracledb.init_oracle_client(lib_dir=Config.ORACLE_CLIENT_DIR)
    else:
        oracledb.init_oracle_client()

    _oracle_client_initialized = True


def get_dsn():
    if Config.ORACLE_SERVICE_NAME:
        return oracledb.makedsn(
            Config.ORACLE_HOST,
            Config.ORACLE_PORT,
            service_name=Config.ORACLE_SERVICE_NAME
        )

    return oracledb.makedsn(
        Config.ORACLE_HOST,
        Config.ORACLE_PORT,
        sid=Config.ORACLE_SID
    )


def get_connection():
    init_oracle_client()

    return oracledb.connect(
        user=Config.ORACLE_USER,
        password=Config.ORACLE_PASSWORD,
        dsn=get_dsn()
    )


def rows_to_dicts(cursor, rows):
    columns = [col[0].lower() for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def query_all(sql, params=None):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(sql, params or {})
        rows = cursor.fetchall()
        return rows_to_dicts(cursor, rows)
    finally:
        cursor.close()
        conn.close()


def query_one(sql, params=None):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(sql, params or {})
        row = cursor.fetchone()

        if not row:
            return None

        columns = [col[0].lower() for col in cursor.description]
        return dict(zip(columns, row))
    finally:
        cursor.close()
        conn.close()
```

---

## 12. API Authentication

Protected endpoints require this HTTP header:

```text
X-API-Key: YOUR_SECRET_KEY
```

`auth.py`:

```python
from functools import wraps
from flask import request, jsonify
from config import Config


def require_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return jsonify({
                "status": "error",
                "message": "Missing X-API-Key header"
            }), 401

        if api_key != Config.API_SECRET_KEY:
            return jsonify({
                "status": "error",
                "message": "Invalid API key"
            }), 403

        return func(*args, **kwargs)

    return wrapper
```

---

## 13. API Endpoints

| Method | Endpoint | Protected | Description |
|---|---|---:|---|
| GET | `/` | No | API index |
| GET | `/api/health` | No | Test Oracle connection |
| GET | `/api/families` | Yes | Get active families |
| GET | `/api/families/{family_id}` | Yes | Get one family with students |
| GET | `/api/families/{family_id}/students` | Yes | Get students for one family |
| GET | `/api/students` | Yes | Get all active students for current year |
| GET | `/api/students/search?q=name` | Yes | Search students |
| GET | `/api/students/{family_id}/{student_id}` | Yes | Get one student |

---

## 14. Oracle ERP Tables Used

| Purpose | Oracle Table |
|---|---|
| Families | `SCH_FAMILY_CARD` |
| Students | `SCH_STUDENT_CARD` |
| Student yearly records | `SCH_STUDENT_CARD_YEAR` |
| Family classification | `SCH_FAMILY_CLASS` |
| Schools | `SCH_SCHOOL` |
| Classes | `SCH_CLASSES` |
| Sections | `SCH_SECTIONS` |
| Branches | `SCH_STUDY_BRANCHES` |

Important: `STUDENT_ID` is not globally unique. The correct student key is:

```text
FAMILY_ID + STUDENT_ID
```

---

## 15. Proxmox LXC Setup

Recommended container:

```text
OS: Ubuntu 22.04 LTS or Ubuntu 24.04 LTS
CPU: 2 cores
RAM: 2 GB
Disk: 16 GB
Network: static IP
Example IP: 192.168.0.16
```

Install packages:

```bash
apt update
apt upgrade -y

apt install -y \
  git \
  curl \
  wget \
  unzip \
  nano \
  openssh-client \
  python3 \
  python3-pip \
  python3-venv \
  build-essential \
  libaio1 \
  libnsl2
```

Verify:

```bash
python3 --version
git --version
dpkg -l | grep -E "libaio|libnsl"
```

---

## 16. GitHub Deployment Setup

Generate SSH deploy key inside the container:

```bash
ssh-keygen -t ed25519 -C "olama-oracle-api-container"
```

Show the public key:

```bash
cat ~/.ssh/id_ed25519.pub
```

Add it to GitHub:

```text
Repository → Settings → Deploy keys → Add deploy key
```

Keep write access disabled.

Test GitHub access:

```bash
ssh -o StrictHostKeyChecking=accept-new -T git@github.com
```

Clone repo:

```bash
mkdir -p /opt/olama
cd /opt/olama

git clone git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git oracle_erp_api
cd /opt/olama/oracle_erp_api
```

---

## 17. Oracle Instant Client Installation on Ubuntu

Upload Linux x64 Instant Client Basic 19c to the server:

```text
instantclient-basic-linux.x64-19.31.0.0.0dbru.zip
```

Extract:

```bash
mkdir -p /opt/oracle
cd /opt/oracle

unzip /root/instantclient-basic-linux.x64-19.31.0.0.0dbru.zip
```

Expected path:

```text
/opt/oracle/instantclient_19
```

If needed, rename:

```bash
mv /opt/oracle/instantclient_19_31 /opt/oracle/instantclient_19
```

Register Oracle library path:

```bash
echo /opt/oracle/instantclient_19 > /etc/ld.so.conf.d/oracle-instantclient.conf
ldconfig
```

Verify:

```bash
ldconfig -p | grep libclntsh
```

Expected:

```text
libclntsh.so => /opt/oracle/instantclient_19/libclntsh.so
```

---

## 18. Server `.env`

Create:

```bash
nano /opt/olama/oracle_erp_api/.env
```

Example:

```env
ORACLE_HOST=192.168.0.118
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=orcl
ORACLE_SID=
ORACLE_USER=DEMO
ORACLE_PASSWORD=CHANGE_ME

CURRENT_YEAR=2025/2026

API_HOST=0.0.0.0
API_PORT=5000
API_SECRET_KEY=CHANGE_ME

ORACLE_CLIENT_DIR=/opt/oracle/instantclient_19
```

Restart the API after changing `.env`:

```bash
systemctl restart olama-oracle-api
```

---

## 19. Python Virtual Environment

```bash
cd /opt/olama/oracle_erp_api

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install gunicorn
```

---

## 20. Oracle Connection Test

```bash
cd /opt/olama/oracle_erp_api
source venv/bin/activate

python -c "from db import get_connection; conn=get_connection(); cur=conn.cursor(); cur.execute('SELECT 1 FROM dual'); print(cur.fetchone()); cur.close(); conn.close()"
```

Expected:

```text
(1,)
```

---

## 21. Manual Flask Test

```bash
cd /opt/olama/oracle_erp_api
source venv/bin/activate

python app.py
```

Open:

```text
http://192.168.0.16:5000/api/health
```

Expected:

```json
{
  "host": "192.168.0.118",
  "oracle": "connected",
  "port": 1521,
  "service_name": "orcl",
  "sid": "",
  "status": "ok",
  "test": 1
}
```

Stop manual Flask server:

```text
CTRL + C
```

---

## 22. Gunicorn systemd Service

Create:

```bash
nano /etc/systemd/system/olama-oracle-api.service
```

Paste:

```ini
[Unit]
Description=Olama Oracle ERP Flask API
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/opt/olama/oracle_erp_api
Environment="PATH=/opt/olama/oracle_erp_api/venv/bin"
ExecStart=/opt/olama/oracle_erp_api/venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 app:create_app()

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable olama-oracle-api
systemctl start olama-oracle-api
systemctl status olama-oracle-api
```

Expected:

```text
active (running)
```

Check logs:

```bash
journalctl -u olama-oracle-api -f
```

Restart service:

```bash
systemctl restart olama-oracle-api
```

---

## 23. API Tests

Health:

```bash
curl http://localhost:5000/api/health
```

Students:

```bash
curl -H "X-API-Key: YOUR_SECRET_KEY" http://localhost:5000/api/students
```

Readable count:

```bash
apt install -y jq

curl -s -H "X-API-Key: YOUR_SECRET_KEY" http://localhost:5000/api/students | jq '.status, .count'
```

Expected:

```text
"ok"
710
```

Families:

```bash
curl -H "X-API-Key: YOUR_SECRET_KEY" http://localhost:5000/api/families
```

Search:

```bash
curl -H "X-API-Key: YOUR_SECRET_KEY" "http://localhost:5000/api/students/search?q=محمد"
```

---

## 24. Deployment Script

Create:

```bash
nano /opt/olama/oracle_erp_api/deploy.sh
```

Paste:

```bash
#!/bin/bash
set -e

APP_DIR="/opt/olama/oracle_erp_api"
SERVICE_NAME="olama-oracle-api"

cd "$APP_DIR"

echo "Pulling latest code from GitHub..."
git pull --ff-only origin main

echo "Updating Python dependencies..."
source "$APP_DIR/venv/bin/activate"
pip install -r requirements.txt
pip install gunicorn

echo "Restarting API service..."
systemctl restart "$SERVICE_NAME"

echo "Deployment complete."
systemctl status "$SERVICE_NAME" --no-pager
```

Make executable:

```bash
chmod +x /opt/olama/oracle_erp_api/deploy.sh
```

Deploy after pushing to GitHub:

```bash
/opt/olama/oracle_erp_api/deploy.sh
```

---

## 25. Optional Auto Pull From GitHub

Create:

```bash
nano /opt/olama/oracle_erp_api/check_update.sh
```

Paste:

```bash
#!/bin/bash

APP_DIR="/opt/olama/oracle_erp_api"
LOG_FILE="/var/log/olama-oracle-api-deploy.log"

cd "$APP_DIR" || exit 1

git fetch origin main

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$(date) - New version found. Deploying..." >> "$LOG_FILE"
    "$APP_DIR/deploy.sh" >> "$LOG_FILE" 2>&1
fi
```

Make executable:

```bash
chmod +x /opt/olama/oracle_erp_api/check_update.sh
```

Add cron:

```bash
crontab -e
```

Add:

```cron
*/5 * * * * /opt/olama/oracle_erp_api/check_update.sh
```

---

## 26. WordPress Integration

### If WordPress is inside the school network

Use:

```text
http://192.168.0.16:5000
```

### If WordPress is outside the school network

Use either:

#### Public port forwarding

```text
http://PUBLIC_IP:15000
```

Router rule:

```text
External TCP 15000 → 192.168.0.16:5000
```

#### SSH tunnel

```bash
ssh -N -L 15000:192.168.0.16:5000 user@PUBLIC_IP
```

Then WordPress uses:

```text
http://127.0.0.1:15000
```

Only use this if the tunnel is running on the WordPress server.

---

## 27. WordPress PHP Example

```php
$response = wp_remote_get('http://PUBLIC_IP:15000/api/families', [
    'timeout' => 60,
    'headers' => [
        'X-API-Key' => 'YOUR_SECRET_KEY',
        'Accept' => 'application/json',
    ],
]);

if (is_wp_error($response)) {
    error_log($response->get_error_message());
    return;
}

$body = wp_remote_retrieve_body($response);
$data = json_decode($body, true);

$families = $data['families'] ?? [];
```

---

## 28. Troubleshooting

### `DPI-1047`

Oracle Client is not found or cannot load.

Check:

```bash
ls /opt/oracle/instantclient_19
ldconfig -p | grep libclntsh
cat /opt/olama/oracle_erp_api/.env
```

Make sure:

```env
ORACLE_CLIENT_DIR=/opt/oracle/instantclient_19
```

### `ORA-01017`

Invalid Oracle username/password.

Check:

```env
ORACLE_USER=
ORACLE_PASSWORD=
```

### `ORA-12505`

Wrong SID. This project should use service name:

```env
ORACLE_SERVICE_NAME=orcl
ORACLE_SID=
```

### `curl: URL using bad/illegal format`

Use correct header format:

```bash
curl -H "X-API-Key: YOUR_SECRET_KEY" http://localhost:5000/api/students
```

### WordPress error: `Failed to connect to 127.0.0.1 port 15000`

WordPress is configured to use a local SSH tunnel, but the tunnel is not running.

Either start the tunnel or change the WordPress API URL to the public forwarded URL.

### Service not running

```bash
systemctl status olama-oracle-api
journalctl -u olama-oracle-api -f
```

### Port 5000 not listening

```bash
ss -tlnp | grep 5000
```

Expected:

```text
0.0.0.0:5000
```

---

## 29. Production Security Checklist

Before production:

- [ ] Change `API_SECRET_KEY` to a long random value
- [ ] Do not commit `.env`
- [ ] Run through Gunicorn/systemd, not `python app.py`
- [ ] Do not expose Flask debug mode publicly
- [ ] Use HTTPS if exposed publicly
- [ ] Restrict firewall access to known IPs if possible
- [ ] Log sync runs and API errors
- [ ] Avoid exposing national IDs unless required
- [ ] Add pagination for large endpoints
- [ ] Add rate limiting if public

---

## 30. Recommended Next Enhancements

### API Enhancements

Add pagination:

```text
/api/students?page=1&limit=50
```

Add filters:

```text
/api/students?class_id=-1&section_id=5
```

Add financial card endpoint:

```text
/api/families/{family_id}/financial-card
```

Add sync endpoint:

```text
/api/sync/families-students
```

### WordPress Enhancements

- Store ERP data in custom WordPress tables
- Add manual sync screen
- Add sync logs
- Add parent portal financial card
- Add controlled user account creation for families

---

## 31. Current Verified Status

The following has been verified:

```text
Oracle Instant Client 19 installed
python-oracledb Thick Mode working
Oracle service name orcl working
DEMO schema connection working
/api/health working
/api/students returning 710 students
GitHub clone working
Ubuntu CT API deployment working
WordPress can connect after tunnel/port forwarding is configured
```

---

## 32. Final Deployment Flow

Developer machine:

```bash
git add .
git commit -m "Update API"
git push
```

API server:

```bash
/opt/olama/oracle_erp_api/deploy.sh
```

Check:

```bash
systemctl status olama-oracle-api
curl http://localhost:5000/api/health
```

---

## 33. Design Principle

The legacy Oracle ERP remains the master data source.

```text
Oracle ERP = source of truth
Flask API = controlled read bridge
WordPress = consumer / synced presentation layer
Laravel ERP = future replacement
```

Do not write financial or registration changes back to Oracle until the business rules are fully analyzed and validated.

# Student Crosswalk Endpoint

`GET /api/students/crosswalk` provides a protected, read-only, non-PII student identity feed for WordPress/Core/Billing migration checks. It does not replace or alter `/api/students` or `/api/students/search`.

Oracle `STUDENT_ID` is not globally unique. The authoritative source key is the composite `FAMILY_ID + STUDENT_ID`, exposed as `oracle_student_key` in `family_id:student_id` form.

Supported query parameters:

- `study_year`: optional exact study-year filter; omitted returns all available years.
- `include_inactive`: defaults to `0`; accepts `1`, `true`, `yes`, or `y`.
- `limit`: defaults to `500`, maximum `2000`.
- `offset`: defaults to `0`.
- `family_id`: optional integer filter.
- `student_id`: optional integer filter.

Returned fields are limited to Oracle family/student keys, study year, controlled status, class, section, school, branch, registration/withdrawal dates, and nullable legacy-reference placeholders. Student names, national numbers, mobile numbers, email, family address, parent contacts, and notes are excluded.

Current limitation: `immutable_legacy_billing_student_ref`, `legacy_billing_student_id`, and `legacy_school_student_id` remain `null` until Oracle exposes an authoritative legacy reference.

Diagnostics and metadata discovery:

```text
GET /api/students/crosswalk/diagnostics?study_year=2025%2F2026
GET /api/students/crosswalk/schema-candidates
```

Example commands using fictional/local credentials:

```bash
curl -H "X-API-Key: olama" "http://localhost:5000/api/students/crosswalk?study_year=2025%2F2026&include_inactive=1&limit=10"
curl -H "X-API-Key: olama" "http://localhost:5000/api/students/crosswalk/diagnostics?study_year=2025%2F2026"
curl -H "X-API-Key: olama" "http://localhost:5000/api/students/crosswalk/schema-candidates"
```

WordPress/Billing financial migration must remain blocked until Billing records map to `oracle_student_key` or an approved reviewed crosswalk exists.
