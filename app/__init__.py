from flask import Flask
from app.config import Config
from app.extensions import mongo, cors
from app.routes.auth import auth_bp
from app.routes.assessments import assessments_bp
from app.routes.ai import ai_bp
from app.routes.counseling import counseling_bp
from app.routes.community import community_bp
from app.routes.admin import admin_bp
from app.routes.wellness import wellness_bp
from app.routes.whatsapp import whatsapp_bp
from app.services.ai_service import genai

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    # PyMongo(app) # We are using a helper get_db which uses the mongo object if initialized?
    # Actually standard Flask-PyMongo use:
    mongo.init_app(app)
    cors.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(assessments_bp, url_prefix='/api/assessments')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(counseling_bp, url_prefix='/api/counseling')
    app.register_blueprint(community_bp, url_prefix='/api/community')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(wellness_bp, url_prefix='/api/wellness')
    app.register_blueprint(whatsapp_bp, url_prefix='/api/whatsapp')

    @app.route('/')
    def home():
        return "Mindly Flask API is running!"

    return app
