from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='Founder')  # Founder, Investor, Admin
    is_verified = db.Column(db.Boolean, default=False)
    
    # Relationships
    startups = db.relationship('Startup', backref='owner', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'is_verified': self.is_verified
        }


class Startup(db.Model):
    __tablename__ = 'startup'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Profile fields (FR-04: Profile Completion Tracking)
    sector = db.Column(db.String(50))  # e.g., "Agriculture & Agritech"
    country = db.Column(db.String(50), default='Ghana')
    registration_number = db.Column(db.String(100))
    stage = db.Column(db.String(20), default='Early')  # Early, Growth, Maturity
    description = db.Column(db.Text)
    
    # Metadata
    profile_completion = db.Column(db.Integer, default=0)  # 0-100%
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'sector': self.sector,
            'country': self.country,
            'stage': self.stage,
            'profile_completion': self.profile_completion,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'owner_id': self.owner_user_id
        }