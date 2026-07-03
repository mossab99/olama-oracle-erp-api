from flask import Blueprint, jsonify, request

from auth import require_api_key
from repositories.students_crosswalk_repo import (
    get_student_crosswalk,
    get_student_crosswalk_diagnostics,
    get_student_crosswalk_schema_candidates,
)


students_crosswalk_bp = Blueprint("students_crosswalk", __name__)


def _optional_int(name, minimum=None):
    value = request.args.get(name)
    if value is None or value.strip() == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {name}")
    if minimum is not None and parsed < minimum:
        raise ValueError(f"Invalid {name}")
    return parsed


def _include_inactive():
    value = request.args.get("include_inactive", "0").strip().lower()
    if value in {"1", "true", "yes", "y"}:
        return True
    if value in {"0", "false", "no", "n", ""}:
        return False
    raise ValueError("Invalid include_inactive")


@students_crosswalk_bp.route("/api/students/crosswalk", methods=["GET"])
@require_api_key
def student_crosswalk():
    try:
        include_inactive = _include_inactive()
        limit = _optional_int("limit", 1)
        offset = _optional_int("offset", 0)
        family_id = _optional_int("family_id", 0)
        student_id = _optional_int("student_id", 0)
        limit = 500 if limit is None else limit
        offset = 0 if offset is None else offset
        if limit > 2000:
            raise ValueError("Invalid limit")

        study_year = request.args.get("study_year")
        study_year = study_year.strip() if study_year is not None else None
        study_year = study_year or None
        data = get_student_crosswalk(
            study_year=study_year,
            include_inactive=include_inactive,
            family_id=family_id,
            student_id=student_id,
            limit=limit,
            offset=offset,
        )
        return jsonify({
            "status": "ok",
            "count": len(data),
            "limit": limit,
            "offset": offset,
            "filters": {
                "study_year": study_year,
                "include_inactive": 1 if include_inactive else 0,
                "family_id": family_id,
                "student_id": student_id,
            },
            "students": data,
        })
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@students_crosswalk_bp.route(
    "/api/students/crosswalk/diagnostics", methods=["GET"]
)
@require_api_key
def student_crosswalk_diagnostics():
    try:
        study_year = request.args.get("study_year")
        study_year = study_year.strip() if study_year is not None else None
        study_year = study_year or None
        return jsonify({
            "status": "ok",
            "study_year": study_year,
            "diagnostics": get_student_crosswalk_diagnostics(study_year),
        })
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@students_crosswalk_bp.route(
    "/api/students/crosswalk/schema-candidates", methods=["GET"]
)
@require_api_key
def student_crosswalk_schema_candidates():
    try:
        candidates = get_student_crosswalk_schema_candidates()
        return jsonify({
            "status": "ok",
            "count": len(candidates),
            "candidates": candidates,
        })
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
