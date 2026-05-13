# app/__init__.py
import os
from datetime import timedelta

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from app.extensions import db, jwt

def create_app():
    app = Flask(__name__)
    
    # 🔧 Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-in-prod')
    
    # 🔧 Windows-compatible database path
    basedir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(basedir)
    db_path = os.path.join(project_root, 'instance', 'db.sqlite3')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{db_path}')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-change-in-prod')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 🔧 Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    CORS(app)
    
    # 🔹 Blueprint imports (inside function to avoid circular imports)
    from app.auth import auth_bp
    
    try:
        from app.documents.routes import documents_bp
        from app.diagnostics.routes import diagnostics_bp
        from app.valuations.routes import valuations_bp
        from app.verification.routes import verification_bp
        from app.programs.routes import programs_bp
        from app.billing.routes import billing_bp
    except ImportError:
        pass
    
    try:
        from app.investors.routes import investors_bp
        from app.notifications.routes import notifications_bp
        from app.analytics.routes import analytics_bp
    except ImportError:
        pass
    
    # 🔹 Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    if 'documents_bp' in locals():
        app.register_blueprint(documents_bp, url_prefix='/api/documents')
    if 'diagnostics_bp' in locals():
        app.register_blueprint(diagnostics_bp, url_prefix='/api/diagnostics')
    if 'valuations_bp' in locals():
        app.register_blueprint(valuations_bp, url_prefix='/api/valuations')
    if 'verification_bp' in locals():
        app.register_blueprint(verification_bp, url_prefix='/api/verification')
    if 'programs_bp' in locals():
        app.register_blueprint(programs_bp, url_prefix='/api/programs')
    if 'billing_bp' in locals():
        app.register_blueprint(billing_bp, url_prefix='/api/billing')
    if 'investors_bp' in locals():
        app.register_blueprint(investors_bp, url_prefix='/api/investors')
    if 'notifications_bp' in locals():
        app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    if 'analytics_bp' in locals():
        app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    
    # 🔹 Create DB tables
    with app.app_context():
        db.create_all()
        
        if 'billing_bp' in locals():
            from app.models import SubscriptionPlan
            if not SubscriptionPlan.query.filter_by(name='Free').first():
                free_plan = SubscriptionPlan(
                    name='Free', 
                    price_ghs=0.0, 
                    limits={"documents": 3, "valuations": 1, "diagnostics": 1}
                )
                db.session.add(free_plan)
                db.session.commit()
    
    return app