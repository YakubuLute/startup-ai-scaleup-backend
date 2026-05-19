# app/billing/engine.py
from datetime import datetime, timedelta
from app.extensions import db
from app.models import SubscriptionPlan, Subscription, UsageRecord, BillingTransaction

# 🔹 Map singular resource types to plural keys in limits dict
RESOURCE_TYPE_MAP = {
    'document': 'documents',
    'valuation': 'valuations',
    'diagnostic': 'diagnostics',
    'share': 'shares'
}

def get_current_plan_limits(startup_id):
    """FR-60 / US-60: Get active plan limits for a startup"""
    sub = Subscription.query.filter_by(startup_id=startup_id, status='active').first()
    if not sub:
        # Default to Free plan limits if no subscription
        free_plan = SubscriptionPlan.query.filter_by(name='Free').first()
        return free_plan.limits if free_plan else {'documents': 3, 'valuations': 1, 'diagnostics': 2, 'shares': 5}
    return sub.plan.limits

def check_and_track_usage(startup_id, resource_type):
    """FR-62 / US-62: Check limits & increment usage for current billing cycle"""
    limits = get_current_plan_limits(startup_id)
    
    # 🔧 Map singular → plural for limits lookup
    limit_key = RESOURCE_TYPE_MAP.get(resource_type, resource_type)
    limit = limits.get(limit_key, 0)
    
    # Get current billing period
    sub = Subscription.query.filter_by(startup_id=startup_id, status='active').first()
    if not sub:
        # Fallback to monthly cycle for untracked startups
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0)
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    else:
        period_start = sub.current_period_start
        period_end = sub.current_period_end
    
    # Get or create usage record (use plural key for storage consistency)
    usage = UsageRecord.query.filter_by(
        startup_id=startup_id, resource_type=limit_key,
        period_start=period_start, period_end=period_end
    ).first()
    
    if not usage:
        usage = UsageRecord(
            startup_id=startup_id, 
            resource_type=limit_key,  # Store plural for consistency
            count=0,
            period_start=period_start, 
            period_end=period_end
        )
        db.session.add(usage)
    
    # Enforce limit
    if usage.count >= limit:
        return {'allowed': False, 'current': usage.count, 'limit': limit}
    
    # Increment & commit
    usage.count += 1
    db.session.commit()
    return {'allowed': True, 'current': usage.count, 'limit': limit}

def create_or_upgrade_subscription(startup_id, plan_id, payment_ref=None):
    """FR-61 / US-61: Handle plan upgrade/downgrade with cycle reset"""
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    existing = Subscription.query.filter_by(startup_id=startup_id, status='active').first()
    now = datetime.utcnow()
    cycle_days = 30 if plan.billing_cycle == 'monthly' else 365
    period_end = now + timedelta(days=cycle_days)
    
    if existing:
        existing.plan_id = plan_id
        existing.status = 'active'
        existing.current_period_start = now
        existing.current_period_end = period_end
        existing.updated_at = now
        if payment_ref:
            existing.payment_provider_ref = payment_ref
    else:
        new_sub = Subscription(
            startup_id=startup_id, plan_id=plan_id, status='active',
            current_period_start=now, current_period_end=period_end,
            payment_provider_ref=payment_ref
        )
        db.session.add(new_sub)
    
    db.session.commit()
    return {'msg': f"Subscribed to {plan.name}", 'status': 'active'}

def record_billing_transaction(startup_id, subscription_id, amount, type_, status='completed', payment_metadata=None):
    """FR-63 / US-63: Log billing history"""
    txn = BillingTransaction(
        startup_id=startup_id, 
        subscription_id=subscription_id,
        amount_ghs=amount, 
        type=type_, 
        status=status, 
        payment_metadata=payment_metadata  # 🔧 Fixed: was 'metadata' (reserved word)
    )
    db.session.add(txn)
    db.session.commit()
    return txn.to_dict()