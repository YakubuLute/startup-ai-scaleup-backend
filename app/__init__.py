# app/__init__.py
import os
from flask import Flask
from flask_cors import CORS
from app.extensions import db, jwt
from app.documents.routes import documents_bp


def create_app():
    app = Flask(__name__)

    # 🔐 Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-jwt-key-change-in-production')

    # 🌐 CORS Configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:3000",
                "http://127.0.0.1:3000"
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    # 🔌 Initialize extensions
    db.init_app(app)
    jwt.init_app(app)

    # 🗂 Register Blueprints (ALL imports INSIDE create_app)
    from app.routes import main_bp
    from app.auth import auth_bp
    from app.startups import startups_bp
    from app.documents.routes import documents_bp
    from app.valuations.routes import valuations_bp
    from app.diagnostics.routes import diagnostics_bp
    from app.verification.routes import verification_bp
    from app.billing.routes import billing_bp
    from app.investors.routes import investors_bp
    from app.notifications.routes import notifications_bp
    from app.programs.routes import programs_bp
    from app.analytics.routes import analytics_bp
   
    
    # Register with URL prefixes
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    # ✅ Register startups blueprint (STANDARD path)
    app.register_blueprint(startups_bp, url_prefix='/api/startups')
    
    # ✅ Register proxy aliases for startups (using add_url_rule)
    from app.startups import (
        create_startup,
        get_user_startups,
        get_startup,
        update_startup,
    )

    # Register proxy routes directly on the app (exact URLs frontend expects)
    app.add_url_rule('/api/proxy/startups', 'list_startups_proxy', get_user_startups, methods=['GET'])
    app.add_url_rule('/api/proxy/startups', 'create_startup_proxy', create_startup, methods=['POST'])
    app.add_url_rule('/api/proxy/startups/<int:startup_id>', 'get_startup_proxy', get_startup, methods=['GET'])
    app.add_url_rule('/api/proxy/startups/<int:startup_id>', 'update_startup_proxy', update_startup, methods=['PUT'])
    
    # Register other blueprints (standard paths only) - EACH ONCE, INSIDE create_app
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    app.register_blueprint(diagnostics_bp, url_prefix='/api/diagnostics')
    app.register_blueprint(verification_bp, url_prefix='/api/verification')
    app.register_blueprint(valuations_bp, url_prefix='/api/valuations')
    app.register_blueprint(billing_bp, url_prefix='/api/billing')
    app.register_blueprint(investors_bp, url_prefix='/api/investors')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(programs_bp, url_prefix='/api/programs')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')


    # 🗄 Create database tables
    with app.app_context():
        db.create_all()

    return app