from flask import Blueprint, current_app, jsonify, request

from auth import require_api_key
from repositories.academic_info_repo import (
    get_academic_snapshot,
    get_academic_students,
    get_grade_sections,
    get_grade_subjects,
    get_grades,
    get_sections,
)


academic_info_bp = Blueprint("academic_info", __name__)


def _study_year():
    value = request.args.get("study_year", "").strip()
    if not value or len(value) > 20:
        raise ValueError("A valid study_year is required")
    return value


def _optional_int(name):
    value = request.args.get(name)
    if value in (None, ""):
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {name}")
    if value < 0:
        raise ValueError(f"Invalid {name}")
    return value


def _response(key, loader, study_year=None):
    try:
        data = loader()
        payload = {"status": "ok", "count": len(data), key: data}
        if study_year is not None:
            payload["study_year"] = study_year
        return jsonify(payload)
    except Exception:
        current_app.logger.exception("Academic endpoint failed: %s", request.path)
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve academic information",
        }), 500


@academic_info_bp.route("/api/academic/grades", methods=["GET"])
@require_api_key
def grades():
    return _response("grades", get_grades)


@academic_info_bp.route("/api/academic/sections", methods=["GET"])
@require_api_key
def sections():
    return _response("sections", get_sections)


@academic_info_bp.route("/api/academic/grade-sections", methods=["GET"])
@require_api_key
def grade_sections():
    try:
        study_year = _study_year()
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    return _response(
        "grade_sections", lambda: get_grade_sections(study_year), study_year
    )


@academic_info_bp.route("/api/academic/students", methods=["GET"])
@require_api_key
def academic_students():
    try:
        study_year = _study_year()
        grade_id = _optional_int("grade_id")
        section_id = _optional_int("section_id")
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    return _response(
        "students",
        lambda: get_academic_students(study_year, grade_id, section_id),
        study_year,
    )


@academic_info_bp.route("/api/academic/grade-subjects", methods=["GET"])
@require_api_key
def grade_subjects():
    try:
        study_year = _study_year()
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    return _response(
        "grade_subjects", lambda: get_grade_subjects(study_year), study_year
    )


@academic_info_bp.route("/api/academic/snapshot", methods=["GET"])
@require_api_key
def academic_snapshot():
    try:
        study_year = _study_year()
        snapshot = get_academic_snapshot(study_year)
        snapshot["status"] = "ok"
        return jsonify(snapshot)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Academic snapshot failed")
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve academic information",
        }), 500
