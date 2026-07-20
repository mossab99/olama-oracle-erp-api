from flask import Flask, jsonify
from flask_cors import CORS
from config import Config

from routes.health import health_bp
from routes.families import families_bp
from routes.students import students_bp
from routes.students_crosswalk import students_crosswalk_bp
from routes.financial import financial_bp
from routes.transportation import transportation_bp
from routes.family_card import family_card_bp
from routes.student_card import student_card_bp
from routes.messaging_financial import messaging_financial_bp
from routes.messaging_transportation import messaging_transportation_bp
from routes.financial_contract import financial_contract_bp


def create_app():
    app = Flask(__name__)

    if Config.API_ALLOWED_ORIGINS:
        CORS(
            app,
            resources={r"/api/*": {"origins": Config.API_ALLOWED_ORIGINS}},
        )

    app.register_blueprint(health_bp)
    app.register_blueprint(families_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(students_crosswalk_bp)
    app.register_blueprint(financial_bp)
    app.register_blueprint(transportation_bp)
    app.register_blueprint(family_card_bp)
    app.register_blueprint(student_card_bp)
    app.register_blueprint(messaging_financial_bp)
    app.register_blueprint(messaging_transportation_bp)
    app.register_blueprint(financial_contract_bp)

    @app.route("/", methods=["GET"])
    def index():
        return jsonify({
            "status": "ok",
            "message": "Oracle ERP API Bridge is running",
            "architecture": {
                "oracle_server": f"{Config.ORACLE_HOST}:{Config.ORACLE_PORT}",
                "oracle_sid": Config.ORACLE_SID,
                "api_bind_host": Config.API_HOST,
                "api_port": Config.API_PORT,
                "lan_api_url": "http://192.168.0.13:5000"
            },
            "endpoints": {
                "health": "/api/health",
                "families": "/api/families",
                "family_financial_card": "/api/families/<family_id>/financial-card",
                "family_transportation": "/api/families/<family_id>/transportation?study_year=2025/2026",
                "transportation_students": "/api/transportation/students?study_year=2025/2026&limit=500&offset=0",
                "transportation_buses": "/api/transportation/buses?include_inactive=1",
                "transportation_regions": "/api/transportation/regions?study_year=2025/2026",
                "transportation_employees": "/api/transportation/employees",
                "transportation_summary": "/api/transportation/summary?study_year=2025/2026",
                "student_card": "/api/families/<family_id>/students/<student_id>/card?study_year=2026-2027",
                "students": "/api/students",
                "student_search": "/api/students/search?q=name",
                "student_crosswalk": "/api/students/crosswalk?study_year=2025/2026&include_inactive=1",
                "messaging_recipients": "/api/messaging/recipients?study_year=2025/2026",
                "messaging_transportation_recipients": "/api/messaging/transportation/recipients?study_year=2025/2026",
                "messaging_transportation_options": "/api/messaging/transportation/options?study_year=2025/2026",
                "messaging_family_financial_summary": "/api/families/<family_id>/financial-summary?study_year=2025/2026",
                "messaging_family_payment_report": "/api/families/<family_id>/payment-report?study_year=2025/2026",
                "financial_diagnostics": "/api/financial/diagnostics?study_year=2025/2026"
            }
        })

    return app


if __name__ == "__main__":
    app = create_app()

    app.run(
        host=Config.API_HOST,
        port=Config.API_PORT,
        debug=Config.API_DEBUG
    )
