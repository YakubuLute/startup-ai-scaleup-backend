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


#  Valuation class must be at TOP LEVEL (same indentation as User, Startup, BusinessDocument)
class Valuation(db.Model):
    __tablename__ = 'valuation'
    
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    
    # Valuation metadata
    method = db.Column(db.String(20), nullable=False)  # 'DCF', 'Becker', 'Asset'
    valuation_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='GHS')
    
    # Input assumptions (stored as JSON for flexibility)
    assumptions = db.Column(db.JSON, nullable=False)
    
    # Results breakdown (stored as JSON)
    results = db.Column(db.JSON, nullable=False)
    
    # Metadata
    confidence = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(20), default='completed')
    run_at = db.Column(db.DateTime, default=db.func.now())
    
    # Relationships
    startup = db.relationship('Startup', backref='valuations')
    
    def to_dict(self):
        return {
            'id': self.id,
            'startup_id': self.startup_id,
            'method': self.method,
            'valuation_amount': self.valuation_amount,
            'currency': self.currency,
            'confidence': self.confidence,
            'assumptions': self.assumptions,
            'results': self.results,
            'run_at': self.run_at.isoformat() if self.run_at else None
        }
    
class DiagnosticSession(db.Model):
    __tablename__ = 'diagnostic_session'
    
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    
    # Scoring results
    overall_score = db.Column(db.Integer, nullable=False)  # 0-100
    stage = db.Column(db.String(20), nullable=False)  # 'Early', 'Growth', 'Maturity'
    
    # Sub-scores (stored as JSON for flexibility)
    sub_scores = db.Column(db.JSON, nullable=False)  # {governance: 70, financial: 45, ...}
    
    # Responses (stored as JSON for audit/history)
    responses = db.Column(db.JSON, nullable=False)  # {question_id: answer, ...}
    
    # Recommendations generated
    recommendations = db.Column(db.JSON, nullable=False)  # List of suggested actions
    
    # Metadata
    run_at = db.Column(db.DateTime, default=db.func.now())
    version = db.Column(db.Integer, default=1)  # Allow re-runs
    
    # Relationships
    startup = db.relationship('Startup', backref='diagnostics')
    
    def to_dict(self):
        return {
            'id': self.id,
            'startup_id': self.startup_id,
            'overall_score': self.overall_score,
            'stage': self.stage,
            'sub_scores': self.sub_scores,
            'recommendations': self.recommendations,
            'run_at': self.run_at.isoformat() if self.run_at else None,
            'version': self.version
        }

class VerificationCase(db.Model):
    __tablename__ = 'verification_case'
    
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    
    # Verification status (FR-41 workflow)
    status = db.Column(db.String(20), default='pending')  # pending, in_review, verified, rejected
    verified_at = db.Column(db.DateTime, nullable=True)
    
    # Submitted evidence (FR-40: Data Capture)
    documents_submitted = db.Column(db.JSON, nullable=False)  # [{type, file_url, uploaded_at}, ...]
    
    # Review details (FR-41: Audit Trail per Spec 6.4)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    review_notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Badge metadata (FR-42: Verified Badge)
    badge_issued = db.Column(db.Boolean, default=False)
    badge_valid_until = db.Column(db.DateTime, nullable=True)  # Optional expiry
    
    # Timestamps
    submitted_at = db.Column(db.DateTime, default=db.func.now())
    reviewed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    startup = db.relationship('Startup', backref='verification_cases')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'startup_id': self.startup_id,
            'status': self.status,
            'documents_submitted': self.documents_submitted,
            'review_notes': self.review_notes,
            'rejection_reason': self.rejection_reason,
            'badge_issued': self.badge_issued,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None
        }