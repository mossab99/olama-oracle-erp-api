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
