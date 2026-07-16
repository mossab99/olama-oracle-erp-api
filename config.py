import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    ORACLE_HOST = os.getenv("ORACLE_HOST", "192.168.0.118")
    ORACLE_PORT = int(os.getenv("ORACLE_PORT", "1521"))

    # Prefer SERVICE_NAME because your test succeeded with service_name="orcl"
    ORACLE_SERVICE_NAME = os.getenv("ORACLE_SERVICE_NAME", "orcl")
    ORACLE_SID = os.getenv("ORACLE_SID", "")

    ORACLE_USER = os.getenv("ORACLE_USER", "DEMO")
    ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "")

    CURRENT_YEAR = os.getenv("CURRENT_YEAR", "2025/2026")

    # HR_EMP_CARD may store the employee case as an Arabic description or as
    # a numeric lookup ID. The repository resolves the lookup description
    # automatically. Set this only when the Oracle schema has no discoverable
    # status-description lookup table.
    EMPLOYEE_ACTIVE_STATUS = os.getenv("EMPLOYEE_ACTIVE_STATUS", "مستمر")
    EMPLOYEE_ACTIVE_STATUS_ID = os.getenv("EMPLOYEE_ACTIVE_STATUS_ID", "")

    API_SECRET_KEY = os.getenv("API_SECRET_KEY", "olama")
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "5000"))

    ORACLE_CLIENT_DIR = os.getenv("ORACLE_CLIENT_DIR", "")
