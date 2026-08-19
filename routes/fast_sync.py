from flask import Blueprint, current_app, jsonify, request

from auth import require_api_key
from config import Config
from repositories.fast_sync_repo import get_fast_sync_page


fast_sync_bp = Blueprint("fast_sync", __name__)


@fast_sync_bp.route("/api/v1/sync/families-bulk", methods=["GET"])
@require_api_key
def families_bulk():
    try:
        study_year = (request.args.get("study_year") or Config.CURRENT_YEAR).strip()
        limit = int(request.args.get("limit", 50))
        cursor = int(request.args.get("cursor", 0))
        if not study_year:
            raise ValueError("A valid study_year is required")
        if limit < 1 or limit > 100:
            raise ValueError("Invalid limit")
        if cursor < 0:
            raise ValueError("Invalid cursor")

        page = get_fast_sync_page(study_year, limit, cursor)
        return jsonify({
            "status": "ok",
            "version": 1,
            "study_year": study_year,
            "count": len(page["families"]),
            **page,
        })
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Fast Sync bulk query failed")
        return jsonify({"status": "error", "message": "Fast Sync bulk query failed"}), 500
