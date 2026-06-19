from flask import Blueprint, jsonify
from db import get_connection
from config import Config

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health", methods=["GET"])
def health():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM dual")
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
            "status": "ok",
            "oracle": "connected",
            "host": Config.ORACLE_HOST,
            "port": Config.ORACLE_PORT,
            "service_name": Config.ORACLE_SERVICE_NAME,
            "sid": Config.ORACLE_SID,
            "test": result[0]
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "oracle": "not connected",
            "host": Config.ORACLE_HOST,
            "port": Config.ORACLE_PORT,
            "service_name": Config.ORACLE_SERVICE_NAME,
            "sid": Config.ORACLE_SID,
            "error": str(e)
        }), 500