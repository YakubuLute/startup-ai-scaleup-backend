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
    
class DocumentShare(db.Model):
    __tablename__ = 'document_share'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('business_document.id'), nullable=False)
    
    # Share link metadata
    share_token = db.Column(db.String(100), unique=True, nullable=False)  # Unique token for URL
    expires_at = db.Column(db.DateTime, nullable=True)  # Optional expiry
    is_active = db.Column(db.Boolean, default=True)
    
    # Access tracking (FR-14: Audit)
    access_count = db.Column(db.Integer, default=0)
    last_accessed_at = db.Column(db.DateTime, nullable=True)
    
    # Permissions
    allow_download = db.Column(db.Boolean, default=False)  # Can viewer download?
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=db.func.now())
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    document = db.relationship('BusinessDocument', backref='shares')
    creator = db.relationship('User', foreign_keys=[created_by_user_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'share_token': self.share_token,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'access_count': self.access_count,
            'allow_download': self.allow_download,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'share_url': f'/api/documents/shared/{self.share_token}'  # Relative URL
 
        }   



class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plan'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # 'Free', 'Starter', 'Growth', 'Enterprise'
    description = db.Column(db.Text, nullable=True)
    
    # Pricing
    price = db.Column(db.Float, nullable=True)  # Null for free tier
    currency = db.Column(db.String(3), default='GHS')
    billing_cycle = db.Column(db.String(20), default='monthly')  # monthly, yearly
    
    # Usage limits (FR-60: Plan Configuration)
    max_documents_per_month = db.Column(db.Integer, default=1)
    max_valuations_per_month = db.Column(db.Integer, default=0)
    max_diagnostics_per_month = db.Column(db.Integer, default=1)
    max_team_members = db.Column(db.Integer, default=1)
    max_storage_mb = db.Column(db.Integer, default=100)
    
    # Features
    features = db.Column(db.JSON, nullable=False)  # List of feature flags
    is_active = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'currency': self.currency,
            'billing_cycle': self.billing_cycle,
            'limits': {
                'documents_per_month': self.max_documents_per_month,
                'valuations_per_month': self.max_valuations_per_month,
                'diagnostics_per_month': self.max_diagnostics_per_month,
                'team_members': self.max_team_members,
                'storage_mb': self.max_storage_mb
            },
            'features': self.features,
            'is_active': self.is_active
        }


class Subscription(db.Model):
    __tablename__ = 'subscription'
    
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False, unique=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'), nullable=False)
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, cancelled, expired, past_due
    current_period_start = db.Column(db.DateTime, nullable=False)
    current_period_end = db.Column(db.DateTime, nullable=False)
    
    # Payment info (stored securely - in production, use Stripe/Paystack tokens)
    payment_provider = db.Column(db.String(50), nullable=True)  # 'stripe', 'paystack', 'manual'
    provider_subscription_id = db.Column(db.String(100), nullable=True)  # External ID
    
    # Metadata
    cancelled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    # Relationships
    startup = db.relationship('Startup', backref='subscription')
    plan = db.relationship('SubscriptionPlan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'startup_id': self.startup_id,
            'plan': self.plan.to_dict() if self.plan else None,
            'status': self.status,
            'current_period_start': self.current_period_start.isoformat() if self.current_period_start else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'payment_provider': self.payment_provider
        }


class UsageRecord(db.Model):
    __tablename__ = 'usage_record'
    
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    
    # Usage type (FR-62: Track specific actions)
    resource_type = db.Column(db.String(50), nullable=False)  # 'document', 'valuation', 'diagnostic', 'team_member'
    resource_id = db.Column(db.Integer, nullable=True)  # ID of the specific resource created
    
    # Timestamp for billing cycle calculation
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    # Metadata
    extra_data = db.Column(db.JSON, nullable=True)
    
    # Relationships
    startup = db.relationship('Startup', backref='usage_records')
    
    def to_dict(self):
        return {
            'id': self.id,
            'startup_id': self.startup_id,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'extra_data': self.extra_data
        }
    
 
class InvestorProfile(db.Model):
    __tablename__ = 'investor_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    
    # Investor details
    firm_name = db.Column(db.String(100), nullable=True)
    investor_type = db.Column(db.String(50), nullable=True)  # 'Angel', 'VC', 'Corporate', 'Family Office'
    focus_sectors = db.Column(db.JSON, nullable=True)  # ['Agritech', 'Fintech', ...]
    focus_stages = db.Column(db.JSON, nullable=True)  # ['Early', 'Growth', 'Maturity']
    typical_check_size = db.Column(db.String(50), nullable=True)  # '$10K-$50K', '$100K+', etc.
    
    # Verification (for investor credibility)
    is_accredited = db.Column(db.Boolean, default=False)
    accreditation_docs = db.Column(db.JSON, nullable=True)
    
    # Preferences
    location_preference = db.Column(db.String(100), nullable=True)  # 'Ghana', 'West Africa', 'Global'
    is_active = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    connection_requests = db.relationship('ConnectionRequest', backref='investor', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'firm_name': self.firm_name,
            'investor_type': self.investor_type,
            'focus_sectors': self.focus_sectors,
            'focus_stages': self.focus_stages,
            'typical_check_size': self.typical_check_size,
            'is_accredited': self.is_accredited,
            'location_preference': self.location_preference
        }


class ConnectionRequest(db.Model):
    __tablename__ = 'connection_request'
    
    id = db.Column(db.Integer, primary_key=True)
    investor_id = db.Column(db.Integer, db.ForeignKey('investor_profile.id'), nullable=False)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    
    # Request details
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, withdrawn
    
    # Contact info shared (after acceptance)
    contact_info_shared = db.Column(db.JSON, nullable=True)  # What info was shared
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=db.func.now())
    responded_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    startup = db.relationship('Startup', backref='connection_requests')
    
    def to_dict(self):
        return {
            'id': self.id,
            'investor_id': self.investor_id,
            'investor_firm': self.investor.firm_name if self.investor else None,
            'startup_id': self.startup_id,
            'startup_name': self.startup.name if self.startup else None,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None
        }    