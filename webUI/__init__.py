# webUI/__init__.py

from flask import Flask
from webUI.auth_routes import auth_bp
from webUI.dashboard_routes import dashboard_bp
from webUI.update_personal_routes import update_personal_bp
from webUI.update_public_routes import update_public_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = b'\xe9/P\xedN\x1c-;\xde\xfa\xa26t\x9e\xfcr\x19\x07\x96r\x0e\xf5\x11\x10'

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(update_personal_bp)
    app.register_blueprint(update_public_bp)

    return app
