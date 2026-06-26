from flask import Blueprint, jsonify, request, current_app
from auth import require_api_key
from config import Config

messaging_financial_bp = Blueprint("messaging_financial", __name__)

MOCK_RECIPIENTS = [
    {
        "family_id": 20,
        "oracle_family_id": "20",
        "sponsor_name": "محمد رفيق صالح",
        "father_name": "محمد رفيق صالح",
        "father_mobile": "0791234567",
        "mother_name": "ناديا صالح",
        "mother_mobile": "0791112223",
        "students": [
            {"student_id": 201, "student_name": "سوار محمد رفيق صالح", "class_id": 1, "class_name": "تمهيدي", "section_id": 1, "section_name": "أ"},
            {"student_id": 202, "student_name": "عصام محمد رفيق صالح", "class_id": 2, "class_name": "خامس أساسي", "section_id": 1, "section_name": "أ"},
            {"student_id": 203, "student_name": "زينة محمد رفيق صالح", "class_id": 3, "class_name": "ثامن اساسي", "section_id": 1, "section_name": "أ"},
            {"student_id": 204, "student_name": "عدي محمد رفيق صالح", "class_id": 4, "class_name": "عاشر اساسي", "section_id": 1, "section_name": "أ"}
        ],
        "balance": 150.00,
        "monthly_due": 50.0,
        "monthly_due_source": "current_month_due",
        "currency": "JOD",
        "financial_available": True
    },
    {
        "family_id": 38,
        "oracle_family_id": "38",
        "sponsor_name": "محمد لافي طالب الشدفان",
        "father_name": "محمد لافي طالب الشدفان",
        "father_mobile": "0797654321",
        "mother_name": "فاطمة الشدفان",
        "mother_mobile": "0792223334",
        "students": [
            {"student_id": 381, "student_name": "محمود محمد لافي الشدفان", "class_id": 5, "class_name": "ثالث أساسي", "section_id": 1, "section_name": "أ"},
            {"student_id": 382, "student_name": "سوار محمد لافي الشدفان", "class_id": 6, "class_name": "سابع اساسي", "section_id": 1, "section_name": "أ"},
            {"student_id": 383, "student_name": "احمد محمد لافي الشدفان", "class_id": 7, "class_name": "تاسع اساسي", "section_id": 1, "section_name": "أ"}
        ],
        "balance": 350.00,
        "monthly_due": 100.00,
        "monthly_due_source": "current_month_due",
        "currency": "JOD",
        "financial_available": True
    },
    {
        "family_id": 44,
        "oracle_family_id": "44",
        "sponsor_name": "علي سمير عيد الزعبي",
        "father_name": "علي سمير عيد الزعبي",
        "father_mobile": "0795556667",
        "mother_name": "منى الزعبي",
        "mother_mobile": "0793334445",
        "students": [
            {"student_id": 441, "student_name": "سلمى علي سمير الزعبي", "class_id": 6, "class_name": "سابع اساسي", "section_id": 1, "section_name": "أ"},
            {"student_id": 442, "student_name": "ريان علي سمير الزعبي", "class_id": 7, "class_name": "تاسع اساسي", "section_id": 1, "section_name": "أ"}
        ],
        "balance": 0.00,
        "monthly_due": 0.00,
        "monthly_due_source": "unavailable",
        "currency": "JOD",
        "financial_available": True
    },
    {
        "family_id": 47,
        "oracle_family_id": "47",
        "sponsor_name": "عبدالرحمن صادق عريدي",
        "father_name": "عبدالرحمن صادق عريدي",
        "father_mobile": "0798889990",
        "mother_name": "رنا عريدي",
        "mother_mobile": "0794445556",
        "students": [
            {"student_id": 471, "student_name": "ريتال عبدالرحمن صادق عريدي", "class_id": 7, "class_name": "تاسع اساسي", "section_id": 1, "section_name": "أ"}
        ],
        "balance": -50.00,
        "monthly_due": 0.00,
        "monthly_due_source": "unavailable",
        "currency": "JOD",
        "financial_available": True
    },
    {
        "family_id": 55,
        "oracle_family_id": "55",
        "sponsor_name": "خلود عبدالرحمن مفلح الحنيطي",
        "father_name": "حاتم عبدالكريم القيسي",
        "father_mobile": "0799990000",
        "mother_name": "خلود عبدالرحمن مفلح الحنيطي",
        "mother_mobile": "0795556667",
        "students": [
            {"student_id": 551, "student_name": "حورالعين حاتم عبدالكريم القيسي", "class_id": 8, "class_name": "أول أساسي", "section_id": 1, "section_name": "أ"}
        ],
        "balance": 120.00,
        "monthly_due": 40.00,
        "monthly_due_source": "current_month_due",
        "currency": "JOD",
        "financial_available": True
    },
    {
        "family_id": 57,
        "oracle_family_id": "57",
        "sponsor_name": "ابراهيم سليمان عامر سليمان",
        "father_name": "ابراهيم سليمان عامر سليمان",
        "father_mobile": "0797778889",
        "mother_name": "هدى سليمان",
        "mother_mobile": "0796667778",
        "students": [
            {"student_id": 571, "student_name": "محمود ابراهيم سليمان سليمان", "class_id": 7, "class_name": "تاسع اساسي", "section_id": 1, "section_name": "أ"}
        ],
        "balance": 210.00,
        "monthly_due": 70.00,
        "monthly_due_source": "current_month_due",
        "currency": "JOD",
        "financial_available": True
    },
    {
        "family_id": 62,
        "oracle_family_id": "62",
        "sponsor_name": "محمد وليد الطقاطقه",
        "father_name": "محمد وليد الطقاطقه",
        "father_mobile": "0794441112",
        "mother_name": "أمل طقاطقة",
        "mother_mobile": "0797773334",
        "students": [
            {"student_id": 621, "student_name": "كرم محمد وليد طقاطقة", "class_id": 1, "class_name": "تمهيدي", "section_id": 1, "section_name": "أ"},
            {"student_id": 622, "student_name": "احمد محمد وليد الطقاطقه", "class_id": 9, "class_name": "سادس أساسي", "section_id": 1, "section_name": "أ"}
        ],
        "balance": 0.00,
        "monthly_due": 0.00,
        "monthly_due_source": "unavailable",
        "currency": "JOD",
        "financial_available": True
    }
]

@messaging_financial_bp.route("/api/messaging/recipients", methods=["GET"])
@require_api_key
def messaging_recipients():
    try:
        study_year = request.args.get("study_year", Config.CURRENT_YEAR).strip() or Config.CURRENT_YEAR
        min_balance = request.args.get("min_balance")
        
        # Filtering logic
        recipients = MOCK_RECIPIENTS[:]
        
        family_id = request.args.get("family_id")
        if family_id:
            recipients = [r for r in recipients if str(r["family_id"]) == str(family_id)]
            
        if min_balance is not None and min_balance.strip() != "":
            try:
                min_b = float(min_balance)
                recipients = [r for r in recipients if r["balance"] >= min_b - 0.001]
            except ValueError:
                pass

        total_count = len(recipients)
        
        try:
            limit = max(1, int(request.args.get("limit", 50)))
        except ValueError:
            limit = 50

        try:
            offset = max(0, int(request.args.get("offset", 0)))
        except ValueError:
            offset = 0

        sliced = recipients[offset:offset + limit]

        return jsonify({
            "status": "ok",
            "study_year": study_year,
            "count": total_count,
            "limit": limit,
            "offset": offset,
            "financial_available": True,
            "recipients": sliced
        })

    except Exception as e:
        current_app.logger.exception("Messaging financial API error")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@messaging_financial_bp.route("/api/families/<int:family_id>/financial-summary", methods=["GET"])
@require_api_key
def family_financial_summary(family_id):
    try:
        study_year = request.args.get("study_year", Config.CURRENT_YEAR).strip() or Config.CURRENT_YEAR
        fam = next((r for r in MOCK_RECIPIENTS if r["family_id"] == family_id), None)
        
        if not fam:
            return jsonify({
                "status": "ok",
                "family_id": family_id,
                "financial_available": False,
                "message": "Financial data is not available for this family/study_year"
            })

        return jsonify({
            "status": "ok",
            "family_id": family_id,
            "oracle_family_id": str(family_id),
            "study_year": study_year,
            "balance": fam["balance"],
            "monthly_due": fam["monthly_due"],
            "monthly_due_source": fam["monthly_due_source"],
            "last_payment_date": "2026-06-01",
            "last_payment_amount": 50.0,
            "currency": "JOD",
            "financial_available": True
        })

    except Exception as e:
        current_app.logger.exception("Messaging financial API error")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@messaging_financial_bp.route("/api/families/<int:family_id>/payment-report", methods=["GET"])
@require_api_key
def family_payment_report(family_id):
    try:
        study_year = request.args.get("study_year", Config.CURRENT_YEAR).strip() or Config.CURRENT_YEAR
        fam = next((r for r in MOCK_RECIPIENTS if r["family_id"] == family_id), None)

        if not fam:
            return jsonify({
                "status": "error",
                "message": "Family not found"
            }), 404

        return jsonify({
            "status": "ok",
            "family_id": family_id,
            "oracle_family_id": str(family_id),
            "study_year": study_year,
            "sponsor_name": fam["sponsor_name"],
            "father_name": fam["father_name"],
            "father_mobile": fam["father_mobile"],
            "mother_name": fam["mother_name"],
            "mother_mobile": fam["mother_mobile"],
            "students": fam["students"],
            "financial": {
                "balance": fam["balance"],
                "monthly_due": fam["monthly_due"],
                "monthly_due_source": fam["monthly_due_source"],
                "currency": "JOD",
                "financial_available": True,
                "last_payment": {
                    "date": "2026-06-01",
                    "amount": 50.0,
                    "receipt_no": "12345"
                },
                "due_items": [
                    {
                        "title": "القسط المدرسي",
                        "due_date": "2026-06-05",
                        "amount": fam["monthly_due"] or 100.0,
                        "paid": 0.0,
                        "remaining": fam["monthly_due"] or 100.0,
                        "status": "unpaid"
                    }
                ]
            }
        })

    except Exception as e:
        current_app.logger.exception("Messaging financial API error")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500
