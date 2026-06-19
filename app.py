from flask import Flask, jsonify
from flask_cors import CORS
from config import Config

from routes.health import health_bp
from routes.families import families_bp
from routes.students import students_bp


def create_app():
    app = Flask(__name__)

    CORS(app)

    app.register_blueprint(health_bp)
    app.register_blueprint(families_bp)
    app.register_blueprint(students_bp)

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
                "students": "/api/students",
                "student_search": "/api/students/search?q=name"
            }
        })

    return app


if __name__ == "__main__":
    app = create_app()

    app.run(
        host=Config.API_HOST,
        port=Config.API_PORT,
        debug=True
    )
