from flask import Blueprint, jsonify, request

from auth import require_api_key
from config import Config
from repositories.families_repo import get_family_by_id
from repositories.financial_repo import get_family_financial_card


financial_bp = Blueprint("financial", __name__)


@financial_bp.route("/api/families/<int:family_id>/financial-card", methods=["GET"])
@require_api_key
def family_financial_card(family_id):
    try:
        study_year = request.args.get("study_year", Config.CURRENT_YEAR).strip()

        if not study_year:
            study_year = Config.CURRENT_YEAR

        family = get_family_by_id(family_id)

        if not family:
            return jsonify({
                "status": "error",
                "message": "Family not found"
            }), 404

        card = get_family_financial_card(family_id, study_year)

        return jsonify({
            "status": "ok",
            "family_id": family_id,
            "study_year": study_year,
            "family_summary": card["family_summary"],
            "students": card["students"],
            "due_allocations": card["due_allocations"],
            "student_transactions": card["student_transactions"]
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
