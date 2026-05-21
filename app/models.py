# app/models.py
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

# ============================================================================
# USER & ORGANIZATION (EP-01)
# ============================================================================
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='Founder')
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    startups = db.relationship('Startup', backref='owner', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'email': self.email, 'role': self.role}

class Startup(db.Model):
    __tablename__ = 'startup'
    id = db.Column(db.Integer, primary_key=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    sector = db.Column(db.String(50))
    stage = db.Column(db.String(20))
    country = db.Column(db.String(50), default='Ghana')
    profile_completion = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'sector': self.sector, 'stage': self.stage}

# ============================================================================
# DOCUMENTS (EP-02)
# ============================================================================
class BusinessDocument(db.Model):
    __tablename__ = 'business_document'
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    doc_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    version = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='draft')
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    startup = db.relationship('Startup', backref='documents')
    
    def to_dict(self):
        return {'id': self.id, 'title': self.title, 'doc_type': self.doc_type, 'version': self.version}

class DocumentShare(db.Model):
    __tablename__ = 'document_share'
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('business_document.id'))
    share_token = db.Column(db.String(100), unique=True)
    expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    allow_download = db.Column(db.Boolean, default=False)
    access_count = db.Column(db.Integer, default=0)
    last_accessed_at = db.Column(db.DateTime)
    created_by_user_id = db.Column(db.Integer)
    
    document = db.relationship('BusinessDocument', backref='shares')
    
    def to_dict(self):
        return {'id': self.id, 'is_active': self.is_active, 'access_count': self.access_count}

# ============================================================================
# DIAGNOSTICS (EP-03)
# ============================================================================
class DiagnosticSession(db.Model):
    __tablename__ = 'diagnostic_session'
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    overall_score = db.Column(db.Integer)
    stage = db.Column(db.String(20))
    sub_scores = db.Column(db.JSON)
    responses = db.Column(db.JSON)
    recommendations = db.Column(db.JSON)
    run_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    startup = db.relationship('Startup', backref='diagnostics')
    
    def to_dict(self):
        return {'id': self.id, 'stage': self.stage, 'overall_score': self.overall_score}

# ============================================================================
# VALUATIONS (EP-04)
# ============================================================================
class Valuation(db.Model):
    __tablename__ = 'valuation'
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    method = db.Column(db.String(20), nullable=False)
    valuation_amount = db.Column(db.Float)
    currency = db.Column(db.String(3), default='GHS')
    assumptions = db.Column(db.JSON)
    results = db.Column(db.JSON)
    confidence = db.Column(db.String(20), default='medium')  # ← Ensure this exists
    status = db.Column(db.String(20), default='completed')    # ← Ensure this exists
    run_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    startup = db.relationship('Startup', backref='valuations')
    
    def to_dict(self):
        """Serialize valuation for API response"""
        return {
            'id': self.id,
            'startup_id': self.startup_id,
            'method': self.method,
            'valuation_amount': self.valuation_amount,
            'currency': self.currency,
            'confidence': self.confidence,
            'status': self.status,
            'run_at': self.run_at.isoformat() if self.run_at else None
        }
# ============================================================================
# VERIFICATION (EP-05)
# ============================================================================
class VerificationCase(db.Model):
    __tablename__ = 'verification_case'
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, etc.
    documents_submitted = db.Column(db.JSON)  # List of document categories submitted
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    review_notes = db.Column(db.Text)  # Store JSON with detailed doc info + audit trail
    badge_issued = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    
    startup = db.relationship('Startup', backref='verifications')
    
    def to_dict(self):
        return {
            'id': self.id,
            'startup_id': self.startup_id,
            'status': self.status,
            'badge_issued': self.badge_issued,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None
        }

# ============================================================================
# PROGRAMS & COHORTS (EP-06)
# ============================================================================
class Program(db.Model):
    __tablename__ = 'program'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    max_cohorts = db.Column(db.Integer, default=5)
    
    def to_dict(self):
        return {'id': self.id, 'name': self.name}

class Cohort(db.Model):
    __tablename__ = 'cohort'
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    max_startups = db.Column(db.Integer, default=20)
    status = db.Column(db.String(20), default='active')
    
    program = db.relationship('Program', backref='cohorts')
    
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'program_id': self.program_id}

class CohortEnrollment(db.Model):
    __tablename__ = 'cohort_enrollment'
    id = db.Column(db.Integer, primary_key=True)
    cohort_id = db.Column(db.Integer, db.ForeignKey('cohort.id'), nullable=False)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    overall_progress = db.Column(db.Integer, default=0)
    milestones_completed = db.Column(db.JSON)
    enrollment_status = db.Column(db.String(20), default='active')
    
    startup = db.relationship('Startup', backref='enrollments')
    cohort = db.relationship('Cohort', backref='enrollments')

# ============================================================================
# BILLING & SUBSCRIPTIONS (EP-07) ← ADD THIS SECTION
# ============================================================================
class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plan'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    price_ghs = db.Column(db.Float, default=0.0)  # ← THIS WAS MISSING!
    billing_cycle = db.Column(db.String(20), default='monthly')
    limits = db.Column(db.JSON, nullable=False)  # {"documents": 5, "valuations": 2, ...}
    features = db.Column(db.JSON, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'price_ghs': self.price_ghs,
            'billing_cycle': self.billing_cycle, 'limits': self.limits,
            'features': self.features, 'is_active': self.is_active
        }

class Subscription(db.Model):
    __tablename__ = 'subscription'
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'), nullable=False)
    status = db.Column(db.String(20), default='active')
    current_period_start = db.Column(db.DateTime, nullable=False)
    current_period_end = db.Column(db.DateTime, nullable=False)
    payment_provider_ref = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    startup = db.relationship('Startup', backref='subscription')
    plan = db.relationship('SubscriptionPlan', backref='subscriptions')
    
    def to_dict(self):
        return {
            'id': self.id, 'startup_id': self.startup_id, 
            'plan_name': self.plan.name if self.plan else None,
            'status': self.status, 'current_period_end': self.current_period_end.isoformat()
        }

class UsageRecord(db.Model):
    __tablename__ = 'usage_record'
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)  # document, valuation, diagnostic
    count = db.Column(db.Integer, default=0)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'resource_type': self.resource_type,
            'count': self.count,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None
        }

class BillingTransaction(db.Model):  # ← THIS WAS MISSING!
    __tablename__ = 'billing_transaction'
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=True)
    amount_ghs = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(30), nullable=False)  # plan_upgrade, renewal, refund
    status = db.Column(db.String(20), default='pending')
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_metadata = db.Column(db.JSON, nullable=True)  # ← Renamed from 'metadata' (reserved word)
    
    startup = db.relationship('Startup', backref='billing_transactions')
    
    def to_dict(self):
        return {
            'id': self.id, 'startup_id': self.startup_id, 'amount_ghs': self.amount_ghs,
            'type': self.type, 'status': self.status, 'transaction_date': self.transaction_date.isoformat()
        }
    


# ✅ Keep this version (complete with all fields):
class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200))
    message = db.Column(db.Text)
    payload = db.Column(db.JSON)
    channel = db.Column(db.String(20), default='in-app')
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='notifications')
    
    def to_dict(self):
        return {
            'id': self.id, 'type': self.type, 'title': self.title,
            'message': self.message, 'channel': self.channel,
            'is_read': self.is_read, 'created_at': self.created_at.isoformat()
        }

class NotificationPreference(db.Model):
    __tablename__ = 'notification_preference'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    email_enabled = db.Column(db.Boolean, default=True)
    sms_enabled = db.Column(db.Boolean, default=False)
    in_app_enabled = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='notification_preferences')
    
    def to_dict(self):
        return {
            'id': self.id, 'notification_type': self.notification_type,
            'email_enabled': self.email_enabled, 'sms_enabled': self.sms_enabled,
            'in_app_enabled': self.in_app_enabled
        }
    

class ProgramMilestone(db.Model):
    """Stub for EP-06 Phase 2: Mentorship Tasks (US-54)"""
    __tablename__ = 'program_milestone'
    id = db.Column(db.Integer, primary_key=True)
    cohort_id = db.Column(db.Integer, db.ForeignKey('cohort.id'))
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')   