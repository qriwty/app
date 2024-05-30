from flask import Flask
from flask_migrate import Migrate
from config import Config
from db import db


migrate = Migrate()

from control import core

core_service = core.DroneCoreService(
    mavlink_address="udp:0.0.0.0:14550",
    stream_host="192.168.0.107",
    stream_port=5588,
    model_path="control/analysis/yolov8n-visdrone.pt",
    dem_path="control/analysis/S36E149.hgt"
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    from controllers.auth_controller import auth_bp
    from controllers.dashboard_controller import dashboard_bp
    from controllers.navigation_controller import navigation_bp
    from controllers.profile_controller import profile_bp
    from controllers.settings_controller import settings_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(navigation_bp, url_prefix='/navigation')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
