from flask import Blueprint, jsonify, request

from auth import require_api_key
from config import Config
from repositories.transportation_repo import (
    get_family_transportation,
    get_transportation_buses,
    get_transportation_employees,
    get_transportation_regions,
    get_transportation_student_count,
    get_transportation_students,
    get_transportation_summary,
)


transportation_bp = Blueprint("transportation", __name__)


def _study_year():
    return (request.args.get("study_year") or Config.CURRENT_YEAR).strip()


def _optional_int(name):
    value = request.args.get(name)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {name}")


def _pagination():
    try:
        limit = int(request.args.get("limit", 500))
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        raise ValueError("Invalid pagination")
    if limit < 1 or limit > 1000:
        raise ValueError("Invalid limit")
    if offset < 0:
        raise ValueError("Invalid offset")
    return limit, offset


def _error(exc):
    if isinstance(exc, ValueError):
        return jsonify({"status": "error", "message": str(exc)}), 400
    return jsonify({"status": "error", "message": "Transportation query failed"}), 500


@transportation_bp.route("/api/transportation/students", methods=["GET"])
@require_api_key
def transportation_students():
    try:
        year = _study_year()
        limit, offset = _pagination()
        family_id = _optional_int("family_id")
        region_id = _optional_int("region_id")
        students = get_transportation_students(
            year, limit, offset, family_id, region_id
        )
        total = get_transportation_student_count(year, family_id, region_id)
        return jsonify({
            "status": "ok",
            "study_year": year,
            "count": len(students),
            "total": total,
            "limit": limit,
            "offset": offset,
            "students": students,
        })
    except Exception as exc:
        return _error(exc)


@transportation_bp.route("/api/transportation/buses", methods=["GET"])
@require_api_key
def transportation_buses():
    try:
        include_inactive = request.args.get("include_inactive", "1") != "0"
        buses = get_transportation_buses(include_inactive)
        return jsonify({"status": "ok", "count": len(buses), "buses": buses})
    except Exception as exc:
        return _error(exc)


@transportation_bp.route("/api/transportation/regions", methods=["GET"])
@require_api_key
def transportation_regions():
    try:
        regions = get_transportation_regions(_study_year())
        return jsonify({
            "status": "ok", "count": len(regions), "regions": regions
        })
    except Exception as exc:
        return _error(exc)


@transportation_bp.route("/api/transportation/employees", methods=["GET"])
@require_api_key
def transportation_employees():
    try:
        employees = get_transportation_employees()
        return jsonify({
            "status": "ok", "count": len(employees), "employees": employees
        })
    except Exception as exc:
        return _error(exc)


@transportation_bp.route("/api/transportation/summary", methods=["GET"])
@require_api_key
def transportation_summary():
    try:
        year = _study_year()
        return jsonify({
            "status": "ok",
            "study_year": year,
            "summary": get_transportation_summary(year),
        })
    except Exception as exc:
        return _error(exc)


@transportation_bp.route(
    "/api/families/<int:family_id>/transportation", methods=["GET"]
)
@require_api_key
def family_transportation(family_id):
    try:
        year = _study_year()
        rows = get_family_transportation(family_id, year)
        if not rows:
            return jsonify({
                "status": "error", "message": "Transportation record not found"
            }), 404
        return jsonify({
            "status": "ok",
            "family_id": family_id,
            "study_year": year,
            "count": len(rows),
            "transportation": rows,
        })
    except Exception as exc:
        return _error(exc)
