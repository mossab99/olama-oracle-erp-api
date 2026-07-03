import re

from flask import Blueprint, current_app, jsonify, request

from auth import require_api_key
from config import Config
from repositories.financial_contract_repo import (
    get_family_dues,
    get_family_receipts,
    get_family_summary_contract,
    get_family_transactions,
    get_financial_diagnostics,
    get_student_financial_summary,
)


financial_contract_bp = Blueprint("financial_contract", __name__)
STUDENT_KEY_PATTERN = re.compile(r"^([1-9][0-9]*):([1-9][0-9]*)$")


def _study_year():
    return (request.args.get("study_year") or Config.CURRENT_YEAR).strip()


def _pagination():
    try:
        limit = int(request.args.get("limit", 500))
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        return None, None, "Invalid pagination"
    if limit < 1 or limit > 2000:
        return None, None, "Invalid limit"
    if offset < 0:
        return None, None, "Invalid offset"
    return limit, offset, None


def _server_error(label):
    current_app.logger.exception("Oracle financial contract API error: %s", label)
    return jsonify({"status": "error", "message": "Internal server error"}), 500


@financial_contract_bp.route(
    "/api/families/<int:family_id>/financial", methods=["GET"]
)
@financial_contract_bp.route(
    "/api/families/<int:family_id>/balance", methods=["GET"]
)
@financial_contract_bp.route(
    "/api/financial/families/<int:family_id>", methods=["GET"]
)
@require_api_key
def family_financial_summary_alias(family_id):
    try:
        return jsonify(get_family_summary_contract(family_id, _study_year()))
    except Exception:
        return _server_error("family_summary")


@financial_contract_bp.route(
    "/api/families/<int:family_id>/financial-transactions", methods=["GET"]
)
@financial_contract_bp.route(
    "/api/families/<int:family_id>/transactions", methods=["GET"]
)
@require_api_key
def family_financial_transactions(family_id):
    limit, offset, error = _pagination()
    if error:
        return jsonify({"status": "error", "message": error}), 400
    study_year = _study_year()
    try:
        rows = get_family_transactions(family_id, study_year, limit, offset)
        return jsonify({
            "status": "ok",
            "family_id": family_id,
            "study_year": study_year,
            "count": len(rows),
            "limit": limit,
            "offset": offset,
            "transactions": rows,
        })
    except Exception:
        return _server_error("family_transactions")


@financial_contract_bp.route(
    "/api/families/<int:family_id>/dues", methods=["GET"]
)
@require_api_key
def family_dues(family_id):
    limit, offset, error = _pagination()
    if error:
        return jsonify({"status": "error", "message": error}), 400
    study_year = _study_year()
    try:
        rows = get_family_dues(family_id, study_year, limit, offset)
        return jsonify({
            "status": "ok",
            "family_id": family_id,
            "study_year": study_year,
            "count": len(rows),
            "limit": limit,
            "offset": offset,
            "dues": rows,
            "source": {
                "oracle_tables": ["SCH_FAMILY_DUE_ALLOC"],
                "notes": [
                    "Proven source columns have no stable due ID or student link."
                ],
            },
        })
    except Exception:
        return _server_error("family_dues")


@financial_contract_bp.route(
    "/api/families/<int:family_id>/receipts", methods=["GET"]
)
@require_api_key
def family_receipts(family_id):
    limit, offset, error = _pagination()
    if error:
        return jsonify({"status": "error", "message": error}), 400
    study_year = _study_year()
    try:
        rows = get_family_receipts(family_id, study_year, limit, offset)
        return jsonify({
            "status": "ok",
            "family_id": family_id,
            "study_year": study_year,
            "count": len(rows),
            "limit": limit,
            "offset": offset,
            "receipts": rows,
        })
    except Exception:
        return _server_error("family_receipts")


@financial_contract_bp.route(
    "/api/families/<int:family_id>/payments", methods=["GET"]
)
@require_api_key
def family_payments(family_id):
    limit, offset, error = _pagination()
    if error:
        return jsonify({"status": "error", "message": error}), 400
    return jsonify({
        "status": "ok",
        "family_id": family_id,
        "study_year": _study_year(),
        "financial_available": False,
        "count": 0,
        "limit": limit,
        "offset": offset,
        "payments": [],
        "source": {
            "oracle_tables": ["SCH_FIN_STUDENT_CARD"],
            "stable_keys": [],
            "notes": [
                "Oracle receipt rows are exposed by the receipts endpoint.",
                "No distinct payment entity or payment method field is proven.",
            ],
        },
    })


@financial_contract_bp.route(
    "/api/students/<student_key>/financial-summary", methods=["GET"]
)
@financial_contract_bp.route(
    "/api/students/<student_key>/financial", methods=["GET"]
)
@require_api_key
def student_financial_summary(student_key):
    match = STUDENT_KEY_PATTERN.fullmatch(student_key)
    if not match:
        return jsonify({
            "status": "error",
            "message": "student_key must use FAMILY_ID:STUDENT_ID",
        }), 400
    family_id, student_id = (int(match.group(1)), int(match.group(2)))
    try:
        return jsonify(get_student_financial_summary(
            family_id, student_id, _study_year()
        ))
    except Exception:
        return _server_error("student_summary")


@financial_contract_bp.route("/api/financial/diagnostics", methods=["GET"])
@require_api_key
def financial_diagnostics():
    study_year = _study_year()
    try:
        diagnostics = get_financial_diagnostics(study_year)
        return jsonify({
            "status": "ok",
            "study_year": study_year,
            "diagnostics": diagnostics,
            "readiness": {
                "transactions_import_ready": (
                    diagnostics["duplicate_serial_ids"] == 0
                    and diagnostics["rows_missing_stable_key"] == 0
                ),
                "dues_import_ready": False,
                "receipts_import_ready": diagnostics["receipt_rows"] > 0,
                "payments_import_ready": False,
                "balances_import_ready": False,
            },
            "source": {
                "oracle_tables": [
                    "SCH_FIN_FAMILY_CARD",
                    "SCH_FIN_STUDENT_CARD",
                    "SCH_FAMILY_DUE_ALLOC",
                ],
                "notes": [
                    "Diagnostics contain counts only.",
                    "Raw receipt IDs may repeat across ledger lines and are aggregated by the receipts endpoint.",
                ],
            },
        })
    except Exception:
        return _server_error("diagnostics")
