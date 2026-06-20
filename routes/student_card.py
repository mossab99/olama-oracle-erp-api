from flask import Blueprint, jsonify, request

from auth import require_api_key
from config import Config
from repositories.student_card_repo import get_student_card


student_card_bp = Blueprint("student_card", __name__)


@student_card_bp.route(
    "/api/families/<int:family_id>/students/<int:student_id>/card",
    methods=["GET"]
)
@require_api_key
def student_card(family_id, student_id):
    try:
        study_year = request.args.get("study_year", Config.CURRENT_YEAR).strip()

        if not study_year:
            study_year = Config.CURRENT_YEAR

        card = get_student_card(family_id, student_id, study_year)

        if not card["student"]:
            return jsonify({
                "status": "not_found",
                "message": "Student not found"
            }), 404

        return jsonify({
            "status": "ok",
            "family_id": family_id,
            "student_id": student_id,
            "study_year": study_year,
            "student": card["student"],
            "family": card["family"],
            "academic_current": card["academic_current"],
            "academic_history": card["academic_history"],
            "transportation_current": card["transportation_current"]
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
