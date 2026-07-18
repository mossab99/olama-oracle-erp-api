from flask import Blueprint, jsonify, request

from auth import require_api_key
from config import Config
from repositories.families_repo import get_family_by_id
from repositories.transportation_repo import (
    get_family_transportation,
    get_transportation_buses,
    get_transportation_regions,
)


transportation_bp = Blueprint("transportation", __name__)


def _safe_error():
    return jsonify({
        "status": "error",
        "message": "Transportation query failed"
    }), 500


@transportation_bp.route("/api/transportation/buses", methods=["GET"])
@require_api_key
def transportation_buses():
    try:
        buses = get_transportation_buses()
        return jsonify({
            "status": "ok",
            "count": len(buses),
            "buses": buses
        })
    except Exception:
        return _safe_error()


@transportation_bp.route("/api/transportation/regions", methods=["GET"])
@require_api_key
def transportation_regions():
    try:
        study_year = (request.args.get("study_year") or Config.CURRENT_YEAR).strip()
        regions = get_transportation_regions(study_year)
        return jsonify({
            "status": "ok",
            "study_year": study_year,
            "count": len(regions),
            "regions": regions
        })
    except Exception:
        return _safe_error()


@transportation_bp.route("/api/families/<int:family_id>/transportation", methods=["GET"])
@require_api_key
def family_transportation(family_id):
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

        transportation = get_family_transportation(family_id, study_year)

        return jsonify({
            "status": "ok",
            "family_id": family_id,
            "study_year": study_year,
            "count": len(transportation),
            "transportation": transportation
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
