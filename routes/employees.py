from flask import Blueprint, jsonify, request

from auth import require_api_key
from repositories.employees_repo import get_active_employees


employees_bp = Blueprint("employees", __name__)


def _pagination_args():
    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        raise ValueError("Invalid pagination")

    if limit < 1 or limit > 1000:
        raise ValueError("Invalid limit")
    if offset < 0:
        raise ValueError("Invalid offset")

    return limit, offset


@employees_bp.route("/api/employees", methods=["GET"])
@require_api_key
def employees():
    try:
        limit, offset = _pagination_args()
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    try:
        data = get_active_employees(limit=limit, offset=offset)
        return jsonify({
            "status": "ok",
            "employee_status": "مستمر",
            "count": len(data),
            "limit": limit,
            "offset": offset,
            "employees": data,
        })
    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve employees",
        }), 500
