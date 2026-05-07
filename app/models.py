# app/models.py
from datetime import datetime, timedelta
from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

# =============================================================================
# CORE MODELS (EP-01: User & Organization Management)
# =============================================================================

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='Founder')  # Founder, TeamMember, Investor, ProgramManager, Admin
    is_verified = db.Column(db.Boolean, default=False)
    
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
    stage = db.Column(db.String(20), default='Early')  # Early, Growth, Maturity
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


# =============================================================================
# EP-02: AI DOCUMENT GENERATION MODELS
# =============================================================================

class DocumentTemplate(db.Model):
    """FR-10: Admin-managed document templates & wizard questions"""
    __tablename__ = 'document_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Business Plan", "HR Policy"
    category = db.Column(db.String(50))  # Strategy, Operations, Compliance, etc.
    description = db.Column(db.Text)
    question_schema = db.Column(db.JSON, nullable=False)  # Wizard steps & questions
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    documents = db.relationship('BusinessDocument', backref='template', lazy=True)


class BusinessDocument(db.Model):
    """FR-11 to FR-14: Core document entity (REPLACES older definition)"""
    __tablename__ = 'business_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('document_templates.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='Draft')  # Draft, Generating, Ready, Archived
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    versions = db.relationship('DocumentVersion', backref='document', lazy=True, cascade='all, delete-orphan')
    shared_links = db.relationship('SharedDocumentLink', backref='document', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'startup_id': self.startup_id,
            'template_id': self.template_id,
            'title': self.title,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'version_count': len(self.versions)
        }


class DocumentVersion(db.Model):
    """FR-13: Version history for safe editing & reverting"""
    __tablename__ = 'document_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('business_documents.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)  # HTML/Rich text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'version_number': self.version_number,
            'content_preview': self.content[:200] + '...' if len(self.content) > 200 else self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SharedDocumentLink(db.Model):
    """FR-14: Secure read-only sharing with expiry (REPLACES DocumentShare)"""
    __tablename__ = 'shared_document_links'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('business_documents.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'token': self.token,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'share_url': f'/api/documents/shared/{self.token}'
        }


# =============================================================================
# EP-03: BUSINESS STAGE DIAGNOSTIC MODELS
# =============================================================================


# =============================================================================
# EP-04: BUSINESS VALUATION SUITE MODELS
# =============================================================================

class Valuation(db.Model):
    __tablename__ = 'valuation'
    
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    
    # Valuation metadata (FR-30)
    method = db.Column(db.String(20), nullable=False)  # DCF, Becker, Asset
    valuation_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='GHS')
    
    # Input assumptions (stored as JSON for flexibility - FR-30)
    assumptions = db.Column(db.JSON, nullable=False)
    
    # Results breakdown (stored as JSON - FR-31)
    results = db.Column(db.JSON, nullable=False)
    
    # Metadata (FR-33)
    confidence = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(20), default='completed')
    run_at = db.Column(db.DateTime, default=db.func.now())
    
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


# =============================================================================
# EP-05: DUE DILIGENCE & VERIFICATION MODELS
# =============================================================================

class VerificationCase(db.Model):
    __tablename__ = 'verification_case'
    
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    
    # Verification status (FR-41 workflow)
    status = db.Column(db.String(20), default='pending')  # pending, in_review, verified, rejected
    verified_at = db.Column(db.DateTime, nullable=True)
    
    # Submitted evidence (FR-40: Data Capture)
    documents_submitted = db.Column(db.JSON, nullable=False)  # [{type, file_url, uploaded_at}, ...]
    
    # Review details (FR-41: Audit Trail)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    review_notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Badge metadata (FR-42: Verified Badge)
    badge_issued = db.Column(db.Boolean, default=False)
    badge_valid_until = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    
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


# =============================================================================
# EP-06: PROGRAM & COHORT MANAGEMENT MODELS
# =============================================================================

class Program(db.Model):
    __tablename__ = 'program'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Agrico Hub Scaleup Program 2026"
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active')  # draft, active, completed, archived
    max_cohorts = db.Column(db.Integer, default=1)
    max_startups_per_cohort = db.Column(db.Integer, default=20)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    cohorts = db.relationship('Cohort', backref='program', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status
        }


class Cohort(db.Model):
    __tablename__ = 'cohort'
    
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Cohort A - 2026 Q1"
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active')  # draft, active, completed, archived
    max_startups = db.Column(db.Integer, default=20)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    enrollments = db.relationship('CohortEnrollment', backref='cohort', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'program_id': self.program_id,
            'name': self.name,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'max_startups': self.max_startups,
            'enrolled_count': len(self.enrollments)
        }


class CohortEnrollment(db.Model):
    __tablename__ = 'cohort_enrollment'
    
    id = db.Column(db.Integer, primary_key=True)
    cohort_id = db.Column(db.Integer, db.ForeignKey('cohort.id'), nullable=False)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    
    # Enrollment details
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, withdrawn, graduated
    enrolled_at = db.Column(db.DateTime, default=db.func.now())
    
    # FR-51: Progress tracking (FR-51)
    overall_progress = db.Column(db.Integer, default=0)  # 0-100%
    milestones_completed = db.Column(db.JSON, nullable=True)  # List of completed milestone IDs
    
    # Notes
    admin_notes = db.Column(db.Text, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    startup = db.relationship('Startup', backref='cohort_enrollments')
    
    def to_dict(self):
        return {
            'id': self.id,
            'cohort_id': self.cohort_id,
            'cohort_name': self.cohort.name if self.cohort else None,
            'startup_id': self.startup_id,
            'startup_name': self.startup.name if self.startup else None,
            'status': self.status,
            'overall_progress': self.overall_progress,
            'milestones_completed': self.milestones_completed or [],
            'admin_notes': self.admin_notes,
            'enrolled_at': self.enrolled_at.isoformat() if self.enrolled_at else None
        }


class ProgramMilestone(db.Model):
    __tablename__ = 'program_milestone'
    
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Complete Business Plan"
    description = db.Column(db.Text, nullable=True)
    
    # Milestone details
    order = db.Column(db.Integer, nullable=False)  # Sequence in program
    is_required = db.Column(db.Boolean, default=True)
    
    # Link to platform features (auto-verify completion)
    linked_feature = db.Column(db.String(50), nullable=True)  # 'document', 'valuation', 'diagnostic', 'verification'
    linked_feature_id = db.Column(db.Integer, nullable=True)  # Optional: specific resource ID
    
    # Metadata
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    # Relationships
    program = db.relationship('Program', backref='milestones')
    
    def to_dict(self):
        return {
            'id': self.id,
            'program_id': self.program_id,
            'name': self.name,
            'description': self.description,
            'order': self.order,
            'is_required': self.is_required,
            'linked_feature': self.linked_feature,
            'linked_feature_id': self.linked_feature_id
        }


# =============================================================================
# EP-07: SUBSCRIPTION & BILLING MODELS
# =============================================================================

class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plan'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # Free, Starter, Growth, Enterprise
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=True)
    currency = db.Column(db.String(3), default='GHS')
    billing_cycle = db.Column(db.String(20), default='monthly')
    
    # Usage limits (FR-60)
    max_documents_per_month = db.Column(db.Integer, default=1)
    max_valuations_per_month = db.Column(db.Integer, default=0)
    max_diagnostics_per_month = db.Column(db.Integer, default=1)
    max_team_members = db.Column(db.Integer, default=1)
    max_storage_mb = db.Column(db.Integer, default=100)
    
    features = db.Column(db.JSON, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'billing_cycle': self.billing_cycle,
            'limits': {
                'documents_per_month': self.max_documents_per_month,
                'valuations_per_month': self.max_valuations_per_month,
                'diagnostics_per_month': self.max_diagnostics_per_month
            },
            'features': self.features
        }


class Subscription(db.Model):
    __tablename__ = 'subscription'
    
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False, unique=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, cancelled, expired, past_due
    current_period_start = db.Column(db.DateTime, nullable=False)
    current_period_end = db.Column(db.DateTime, nullable=False)
    payment_provider = db.Column(db.String(50), nullable=True)
    provider_subscription_id = db.Column(db.String(100), nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    startup = db.relationship('Startup', backref='subscription')
    plan = db.relationship('SubscriptionPlan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'startup_id': self.startup_id,
            'plan': self.plan.to_dict() if self.plan else None,
            'status': self.status,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None
        }


class UsageRecord(db.Model):
    __tablename__ = 'usage_record'
    
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)  # document, valuation, diagnostic, team_member
    resource_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    extra_data = db.Column(db.JSON, nullable=True)
    
    startup = db.relationship('Startup', backref='usage_records')
    
    def to_dict(self):
        return {
            'id': self.id,
            'startup_id': self.startup_id,
            'resource_type': self.resource_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# =============================================================================
# EP-08: INVESTOR & PARTNER PORTAL MODELS
# =============================================================================

class InvestorProfile(db.Model):
    __tablename__ = 'investor_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    firm_name = db.Column(db.String(100), nullable=True)
    investor_type = db.Column(db.String(50), nullable=True)  # Angel, VC, Corporate, Family Office
    focus_sectors = db.Column(db.JSON, nullable=True)
    focus_stages = db.Column(db.JSON, nullable=True)
    typical_check_size = db.Column(db.String(50), nullable=True)
    is_accredited = db.Column(db.Boolean, default=False)
    accreditation_docs = db.Column(db.JSON, nullable=True)
    location_preference = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', foreign_keys=[user_id])
    connection_requests = db.relationship('ConnectionRequest', backref='investor', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'firm_name': self.firm_name,
            'investor_type': self.investor_type,
            'focus_sectors': self.focus_sectors,
            'focus_stages': self.focus_stages,
            'is_accredited': self.is_accredited
        }


class ConnectionRequest(db.Model):
    __tablename__ = 'connection_request'
    
    id = db.Column(db.Integer, primary_key=True)
    investor_id = db.Column(db.Integer, db.ForeignKey('investor_profile.id'), nullable=False)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, withdrawn
    contact_info_shared = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime, nullable=True)
    
    startup = db.relationship('Startup', backref='connection_requests')
    
    def to_dict(self):
        return {
            'id': self.id,
            'investor_firm': self.investor.firm_name if self.investor else None,
            'startup_name': self.startup.name if self.startup else None,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# =============================================================================
# EP-09: NOTIFICATIONS MODELS
# =============================================================================

class Notification(db.Model):
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # connection, verification, document, billing, system
    is_read = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    related_type = db.Column(db.String(50), nullable=True)
    related_id = db.Column(db.Integer, nullable=True)
    sent_email = db.Column(db.Boolean, default=False)
    sent_sms = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship('User', backref='notifications')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.notification_type,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NotificationPreference(db.Model):
    __tablename__ = 'notification_preference'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    
    # Email preferences
    email_enabled = db.Column(db.Boolean, default=True)
    email_connection_requests = db.Column(db.Boolean, default=True)
    email_verification_updates = db.Column(db.Boolean, default=True)
    email_billing_alerts = db.Column(db.Boolean, default=True)
    email_document_ready = db.Column(db.Boolean, default=True)
    
    # SMS preferences
    sms_enabled = db.Column(db.Boolean, default=False)
    sms_connection_requests = db.Column(db.Boolean, default=False)
    sms_verification_updates = db.Column(db.Boolean, default=False)
    sms_billing_alerts = db.Column(db.Boolean, default=True)
    
    # In-app preferences
    in_app_enabled = db.Column(db.Boolean, default=True)
    
    email_address = db.Column(db.String(120), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='notification_preferences')
    
    def to_dict(self):
        return {
            'id': self.id,
            'email_enabled': self.email_enabled,
            'sms_enabled': self.sms_enabled,
            'in_app_enabled': self.in_app_enabled,
            'contact': {
                'email_address': self.email_address,
                'phone_number': self.phone_number
            }
        }
    
    
class DiagnosticSession(db.Model):
    __tablename__ = 'diagnostic_session'
    
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    
    # Scoring results (FR-21)
    overall_score = db.Column(db.Integer, nullable=False)  # 0-100
    stage = db.Column(db.String(20), nullable=False)       # Early, Growth, Maturity
    sub_scores = db.Column(db.JSON, nullable=False)        # {governance: 60, financial: 45, operations: 70, market: 50}
    
    # Responses & recommendations (FR-20, FR-22)
    responses = db.Column(db.JSON, nullable=False)         # {question_id: answer}
    recommendations = db.Column(db.JSON, nullable=False)   # List of prioritized actions
    
    # Metadata (FR-23)
    run_at = db.Column(db.DateTime, default=db.func.now())
    version = db.Column(db.Integer, default=1)
    
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

