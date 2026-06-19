from flask import Blueprint, jsonify
from auth import require_api_key

from repositories.families_repo import (
    get_all_families,
    get_family_by_id,
    get_students_by_family_id
)

families_bp = Blueprint("families", __name__)


@families_bp.route("/api/families", methods=["GET"])
@require_api_key
def families():
    try:
        data = get_all_families()

        return jsonify({
            "status": "ok",
            "count": len(data),
            "families": data
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@families_bp.route("/api/families/<family_id>", methods=["GET"])
@require_api_key
def family_details(family_id):
    try:
        family = get_family_by_id(family_id)

        if not family:
            return jsonify({
                "status": "error",
                "message": "Family not found"
            }), 404

        students = get_students_by_family_id(family_id)

        return jsonify({
            "status": "ok",
            "family": family,
            "students": students
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@families_bp.route("/api/families/<family_id>/students", methods=["GET"])
@require_api_key
def family_students(family_id):
    try:
        students = get_students_by_family_id(family_id)

        return jsonify({
            "status": "ok",
            "family_id": family_id,
            "count": len(students),
            "students": students
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
