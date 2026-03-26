from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='Founder')
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
    sector = db.Column(db.String(50))
    country = db.Column(db.String(50), default='Ghana')
    registration_number = db.Column(db.String(100))
    stage = db.Column(db.String(20), default='Early')
    description = db.Column(db.Text)
    
    # Metadata
    profile_completion = db.Column(db.Integer, default=0)
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


# ✅ BusinessDocument should be at TOP LEVEL (same indentation as User and Startup)
class BusinessDocument(db.Model):
    __tablename__ = 'business_document'
    
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    
    # Document metadata
    title = db.Column(db.String(200), nullable=False)
    doc_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    version = db.Column(db.Integer, default=1)
    
    # Status & metadata
    status = db.Column(db.String(20), default='draft')
    generated_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    # Relationships
    startup = db.relationship('Startup', backref='documents')
    
    def to_dict(self):
        return {
            'id': self.id,
            'startup_id': self.startup_id,
            'title': self.title,
            'doc_type': self.doc_type,
            'content': self.content[:200] + '...' if len(self.content) > 200 else self.content,
            'version': self.version,
            'status': self.status,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None
        }