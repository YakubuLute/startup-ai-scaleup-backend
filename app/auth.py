# app/__init__.py
import os  # ← Required for getenv
from flask import Flask
from flask_cors import CORS  # ← Import at TOP of file
from app.extensions import db, jwt

def create_app():
    app = Flask(__name__)

    # 🔐 Config
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-jwt-key')

    # 🌐 CORS - MUST be after app = Flask(__name__) and before blueprints
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    # 🔌 Init extensions
    db.init_app(app)
    jwt.init_app(app)

    # 🗂 Register blueprints (your existing code)
    from app.auth import auth_bp
    # ... other imports ...
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    # ... other registrations ...

    with app.app_context():
        db.create_all()
    
    return app