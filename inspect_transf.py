"""
Query the Oracle Bridge API via SSH tunnel (127.0.0.1:15100) 
to inspect SCH_STUDENT_TRANSF_CERT columns and test the snapshot.
"""
import urllib.request
import json

BASE = "http://127.0.0.1:15100"
KEY = "olama"

def api_get(path):
    req = urllib.request.Request(BASE + path, headers={"X-API-Key": KEY})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

# 1. Health check
print("=== Health ===")
print(json.dumps(api_get("/api/health"), indent=2, ensure_ascii=False))

# 2. Try the snapshot with 2025/2026 (will show full error if any)
print("\n=== Snapshot test (2025/2026) ===")
try:
    req = urllib.request.Request(
        BASE + "/api/academic/snapshot?study_year=2025%2F2026",
        headers={"X-API-Key": KEY}
    )
    import urllib.error
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            # Show only summary, not all rows
            summary = {k: (len(v) if isinstance(v, list) else v) for k, v in data.items()}
            print("Snapshot summary:", summary)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code}: {body}")
except Exception as e:
    print("Error:", e)

# 3. Try transferred students directly 
print("\n=== Transferred students endpoint (2025/2026) ===")
try:
    req = urllib.request.Request(
        BASE + "/api/academic/transferred-students?study_year=2025%2F2026",
        headers={"X-API-Key": KEY}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            print(f"Count: {data.get('count', '?')}")
            if data.get('transferred_students'):
                print("First record keys:", list(data['transferred_students'][0].keys()))
                print("First record:", data['transferred_students'][0])
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code}: {body}")
except Exception as e:
    print("Error:", e)
