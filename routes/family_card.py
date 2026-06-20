from flask import Blueprint, jsonify, request

from auth import require_api_key
from repositories.family_card_repo import get_family_card


family_card_bp = Blueprint("family_card", __name__)


@family_card_bp.route("/api/families/<int:family_id>/card", methods=["GET"])
@require_api_key
def family_card(family_id):
    try:
        study_year = request.args.get("study_year")

        if study_year is not None:
            study_year = study_year.strip() or None

        card = get_family_card(family_id, study_year)

        if not card["family"]:
            return jsonify({
                "status": "not_found",
                "message": "Family not found"
            }), 404

        return jsonify({
            "status": "ok",
            "family_id": family_id,
            "study_year": study_year,
            "family": card["family"],
            "students": card["students"]
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
