from flask import Flask
from app.extensions import db, jwt  

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'your-jwt-secret-key'

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    
    # Register blueprints
    from app.routes import main_bp
    from app.auth import auth_bp
    from app.startups import startups_bp
    from app.documents.routes import documents_bp  
    from app.valuations.routes import valuations_bp
    from app.diagnostics.routes import diagnostics_bp
    from app.verification.routes import verification_bp
    from app.billing.routes import billing_bp
    from app.investors.routes import investors_bp


    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(startups_bp, url_prefix='/api/startups')
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    app.register_blueprint(diagnostics_bp, url_prefix='/api/diagnostics')
    app.register_blueprint(verification_bp, url_prefix='/api/verification')
    app.register_blueprint(valuations_bp, url_prefix='/api/valuations')
    app.register_blueprint(billing_bp, url_prefix='/api/billing')
    app.register_blueprint(investors_bp, url_prefix='/api/investors')

        # Create tables
    with app.app_context():
        db.create_all()
    
    return app