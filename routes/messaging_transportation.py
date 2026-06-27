"""Bulk, read-only transportation audience endpoints for messaging."""

from flask import Blueprint, current_app, jsonify, request

from auth import require_api_key
from repositories.messaging_transportation_repo import (
    get_transportation_options,
    get_transportation_recipients,
)


messaging_transportation_bp = Blueprint("messaging_transportation", __name__)
ROUTE_MODES = {"either", "both", "departure", "arrival"}


def _optional_int(name):
    raw = request.args.get(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _boolean(name, default=True):
    raw = request.args.get(name)
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true"}:
        return True
    if normalized in {"0", "false"}:
        return False
    raise ValueError(f"{name} must be one of: 1, 0, true, false")


def _pagination():
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("limit and offset must be integers") from exc
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("offset must be 0 or greater")
    return limit, offset


def _required_study_year():
    study_year = (request.args.get("study_year") or "").strip()
    if not study_year:
        raise ValueError("study_year is required")
    return study_year


@messaging_transportation_bp.route(
    "/api/messaging/transportation/recipients", methods=["GET"]
)
@require_api_key
def transportation_recipients():
    try:
        study_year = _required_study_year()
        route_mode = (request.args.get("route_mode") or "either").strip().lower()
        if route_mode not in ROUTE_MODES:
            raise ValueError("route_mode must be one of: either, both, departure, arrival")

        limit, offset = _pagination()
        filters = {
            "study_year": study_year,
            "class_id": _optional_int("class_id"),
            "section_id": _optional_int("section_id"),
            "departure_bus": _optional_int("departure_bus"),
            "arrival_bus": _optional_int("arrival_bus"),
            "trans_route": _optional_int("trans_route"),
            "route_mode": route_mode,
            "active_only": _boolean("active_only", True),
            "family_id": _optional_int("family_id"),
        }
        count, recipients = get_transportation_recipients(
            **filters, limit=limit, offset=offset
        )
        public_filters = dict(filters)
        public_filters["active_only"] = 1 if filters["active_only"] else 0
        return jsonify({
            "status": "ok",
            "count": count,
            "limit": limit,
            "offset": offset,
            "filters": public_filters,
            "recipients": recipients,
        })
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Transportation recipients API error")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@messaging_transportation_bp.route(
    "/api/messaging/transportation/options", methods=["GET"]
)
@require_api_key
def transportation_options():
    try:
        study_year = _required_study_year()
        active_only = _boolean("active_only", True)
        options = get_transportation_options(study_year, active_only)
        return jsonify({
            "status": "ok",
            "study_year": study_year,
            "active_only": 1 if active_only else 0,
            **options,
        })
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Transportation options API error")
        return jsonify({"status": "error", "message": "Internal server error"}), 500
