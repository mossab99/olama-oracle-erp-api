from flask import Blueprint, jsonify, request
from auth import require_api_key

from repositories.students_repo import (
    get_all_students,
    get_student_by_family_and_student_id,
    search_students
)

students_bp = Blueprint("students", __name__)


@students_bp.route("/api/students", methods=["GET"])
@require_api_key
def students():
    try:
        data = get_all_students()

        return jsonify({
            "status": "ok",
            "count": len(data),
            "students": data
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@students_bp.route("/api/students/<family_id>/<student_id>", methods=["GET"])
@require_api_key
def student_details(family_id, student_id):
    try:
        student = get_student_by_family_and_student_id(family_id, student_id)

        if not student:
            return jsonify({
                "status": "error",
                "message": "Student not found"
            }), 404

        return jsonify({
            "status": "ok",
            "student": student
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@students_bp.route("/api/students/search", methods=["GET"])
@require_api_key
def student_search():
    try:
        q = request.args.get("q", "").strip()

        if not q:
            return jsonify({
                "status": "error",
                "message": "Missing search query. Use /api/students/search?q=name"
            }), 400

        data = search_students(q)

        return jsonify({
            "status": "ok",
            "query": q,
            "count": len(data),
            "students": data
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500