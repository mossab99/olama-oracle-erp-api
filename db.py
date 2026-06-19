import oracledb
from config import Config


_oracle_client_initialized = False


def init_oracle_client():
    """
    Initialize Oracle Thick Mode.

    Required for Oracle 11g.
    ORACLE_CLIENT_DIR should point to the folder that contains oci.dll.
    Example:
        C:\\oracle\\instantclient_19
    """
    global _oracle_client_initialized

    if _oracle_client_initialized:
        return

    if Config.ORACLE_CLIENT_DIR:
        oracledb.init_oracle_client(lib_dir=Config.ORACLE_CLIENT_DIR)
    else:
        # Use this only if Oracle Instant Client is already available in Windows PATH.
        oracledb.init_oracle_client()

    _oracle_client_initialized = True


def get_dsn():
    """
    Build Oracle DSN.

    Your successful test used:
        SERVICE_NAME=orcl

    So this function prefers ORACLE_SERVICE_NAME.
    If ORACLE_SERVICE_NAME is empty, it falls back to ORACLE_SID.
    """
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
    """
    Open a new Oracle database connection.
    """
    init_oracle_client()

    return oracledb.connect(
        user=Config.ORACLE_USER,
        password=Config.ORACLE_PASSWORD,
        dsn=get_dsn()
    )


def rows_to_dicts(cursor, rows):
    """
    Convert Oracle query result rows to list of dictionaries.
    """
    columns = [col[0].lower() for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def query_all(sql, params=None):
    """
    Execute SELECT query and return all rows as dictionaries.
    """
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
    """
    Execute SELECT query and return one row as dictionary.
    """
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


def execute(sql, params=None):
    """
    Execute INSERT, UPDATE, DELETE, or PL/SQL command.
    Commits automatically.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(sql, params or {})
        conn.commit()
        return cursor.rowcount

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()