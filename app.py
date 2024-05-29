from flask import Flask
from flask_migrate import Migrate
from config import Config
from db import db


migrate = Migrate()

from services.control import core

core_service = core.DroneCoreService(
    mavlink_address="udp:0.0.0.0:14550",
    stream_host="192.168.0.107",
    stream_port=5588,
    model_path="services/control/analysis/yolov8n-visdrone.pt",
    dem_path="services/control/analysis/S36E149.hgt"
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    from views.auth_view import auth_bp
    from views.dashboard_view import dashboard_bp
    from views.navigation_view import navigation_bp
    from views.profile_view import profile_bp
    from views.settings_view import settings_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(navigation_bp, url_prefix='/navigation')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
