from flask import Blueprint, jsonify, request, current_app
from auth import require_api_key
from config import Config
from repositories.messaging_financial_repo import (
    get_bulk_messaging_recipients,
    get_single_family_financial_summary,
    get_family_payment_report_payload
)

messaging_financial_bp = Blueprint("messaging_financial", __name__)


@messaging_financial_bp.route("/api/messaging/recipients", methods=["GET"])
@require_api_key
def messaging_recipients():
    try:
        study_year = request.args.get("study_year", Config.CURRENT_YEAR).strip() or Config.CURRENT_YEAR
        min_balance = request.args.get("min_balance")
        if min_balance is not None and min_balance.strip() == "":
            min_balance = None
        elif min_balance is not None:
            try:
                min_balance = float(min_balance)
            except ValueError:
                min_balance = None

        family_id = request.args.get("family_id")
        class_id = request.args.get("class_id")
        section_id = request.args.get("section_id")

        try:
            limit = max(1, int(request.args.get("limit", 50)))
        except ValueError:
            limit = 50

        try:
            offset = max(0, int(request.args.get("offset", 0)))
        except ValueError:
            offset = 0

        total_count, recipients = get_bulk_messaging_recipients(
            study_year=study_year,
            min_balance=min_balance,
            class_id=class_id,
            section_id=section_id,
            family_id=family_id,
            limit=limit,
            offset=offset
        )

        return jsonify({
            "status": "ok",
            "study_year": study_year,
            "count": total_count,
            "limit": limit,
            "offset": offset,
            "financial_available": True,
            "recipients": recipients
        })

    except Exception as e:
        current_app.logger.exception("Messaging financial API error")
        return jsonify({
            "status": "error",
            "message": "Internal server error: " + str(e)
        }), 500


@messaging_financial_bp.route("/api/families/<int:family_id>/financial-summary", methods=["GET"])
@require_api_key
def family_financial_summary(family_id):
    try:
        study_year = request.args.get("study_year", Config.CURRENT_YEAR).strip() or Config.CURRENT_YEAR
        data = get_single_family_financial_summary(family_id, study_year)
        if not data:
            return jsonify({
                "status": "error",
                "message": "Family not found or financial data unavailable"
            }), 404
        return jsonify(data)

    except Exception as e:
        current_app.logger.exception("Messaging financial API error")
        return jsonify({
            "status": "error",
            "message": "Internal server error: " + str(e)
        }), 500


@messaging_financial_bp.route("/api/families/<int:family_id>/payment-report", methods=["GET"])
@require_api_key
def family_payment_report(family_id):
    try:
        study_year = request.args.get("study_year", Config.CURRENT_YEAR).strip() or Config.CURRENT_YEAR
        data = get_family_payment_report_payload(family_id, study_year)
        if not data:
            return jsonify({
                "status": "error",
                "message": "Family not found"
            }), 404
        return jsonify(data)

    except Exception as e:
        current_app.logger.exception("Messaging financial API error")
        return jsonify({
            "status": "error",
            "message": "Internal server error: " + str(e)
        }), 500
