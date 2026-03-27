"""
Billing services for FR-60 to FR-62: Plans, Subscriptions, Usage Tracking.
"""

from datetime import datetime, timedelta
from app.extensions import db
from app.models import SubscriptionPlan, Subscription, UsageRecord, Startup
from app.billing.plans import DEFAULT_PLANS, check_limit


def initialize_default_plans():
    """
    Seed default plans into database if they don't exist.
    Run once during setup or admin panel.
    """
    for plan_data in DEFAULT_PLANS:
        existing = SubscriptionPlan.query.filter_by(name=plan_data['name']).first()
        if not existing:
            plan = SubscriptionPlan(
                name=plan_data['name'],
                description=plan_data['description'],
                price=plan_data['price'],
                currency=plan_data.get('currency', 'GHS'),
                billing_cycle=plan_data['billing_cycle'],
                max_documents_per_month=plan_data['limits']['max_documents_per_month'],
                max_valuations_per_month=plan_data['limits']['max_valuations_per_month'],
                max_diagnostics_per_month=plan_data['limits']['max_diagnostics_per_month'],
                max_team_members=plan_data['limits']['max_team_members'],
                max_storage_mb=plan_data['limits']['max_storage_mb'],
                features=plan_data['features'],
                is_active=plan_data['is_active']
            )
            db.session.add(plan)
    
    db.session.commit()
    return True


def get_current_usage(startup_id: int, resource_type: str, period_start: datetime, period_end: datetime) -> int:
    """
    Count usage of a specific resource within the current billing period.
    """
    return UsageRecord.query.filter(
        UsageRecord.startup_id == startup_id,
        UsageRecord.resource_type == resource_type,
        UsageRecord.created_at >= period_start,
        UsageRecord.created_at <= period_end
    ).count()


def check_usage_limit(startup_id: int, resource_type: str, plan: SubscriptionPlan) -> tuple:
    """
    Check if startup has exceeded their plan limit for a resource.
    
    Returns:
        (is_allowed: bool, message: str or None, current_usage: int, limit: int)
    """
    # Get current billing period
    subscription = Subscription.query.filter_by(startup_id=startup_id, status='active').first()
    if not subscription:
        return False, "No active subscription found", 0, 0
    
    period_start = subscription.current_period_start
    period_end = subscription.current_period_end
    
    # Get current usage
    current_usage = get_current_usage(startup_id, resource_type, period_start, period_end)
    
    # Get limit from plan
    limit_map = {
        'document': plan.max_documents_per_month,
        'valuation': plan.max_valuations_per_month,
        'diagnostic': plan.max_diagnostics_per_month,
        'team_member': plan.max_team_members
    }
    
    limit = limit_map.get(resource_type, 0)
    
    # Check if within limit
    if check_limit(current_usage, limit):
        return True, None, current_usage, limit
    else:
        return False, f"Plan limit exceeded: {current_usage}/{limit if limit != -1 else '∞'} {resource_type}(s) used", current_usage, limit


def record_usage(startup_id: int, resource_type: str, resource_id: int = None, metadata: dict = None):
    """
    Record a usage event for billing tracking (FR-62).
    """
    usage = UsageRecord(
        startup_id=startup_id,
        resource_type=resource_type,
        resource_id=resource_id,
        extra_data=metadata or {}
    )
    db.session.add(usage)
    db.session.commit()
    return usage


def get_subscription_status(startup_id: int) -> dict:
    """
    Get current subscription status and usage summary for a startup.
    """
    subscription = Subscription.query.filter_by(startup_id=startup_id, status='active').first()
    
    if not subscription:
        return {
            'has_subscription': False,
            'plan': None,
            'usage': {}
        }
    
    plan = subscription.plan
    period_start = subscription.current_period_start
    period_end = subscription.current_period_end
    
    # Get usage for each resource type
    usage = {}
    for resource_type in ['document', 'valuation', 'diagnostic', 'team_member']:
        current = get_current_usage(startup_id, resource_type, period_start, period_end)
        limit = getattr(plan, f'max_{resource_type}s_per_month', 0)
        usage[resource_type] = {
            'current': current,
            'limit': limit if limit != -1 else 'unlimited',
            'percentage': round(current / limit * 100) if limit > 0 else 0
        }
    
    return {
        'has_subscription': True,
        'plan': plan.to_dict(),
        'status': subscription.status,
        'period': {
            'start': period_start.isoformat(),
            'end': period_end.isoformat()
        },
        'usage': usage
    }


def upgrade_subscription(startup_id: int, new_plan_id: int) -> dict:
    """
    Upgrade or downgrade a startup's subscription (FR-61).
    In production, this would integrate with payment gateway.
    """
    startup = Startup.query.get(startup_id)
    if not startup:
        return {'error': 'Startup not found', 'success': False}
    
    new_plan = SubscriptionPlan.query.get(new_plan_id)
    if not new_plan or not new_plan.is_active:
        return {'error': 'Invalid plan', 'success': False}
    
    # Get or create subscription
    subscription = Subscription.query.filter_by(startup_id=startup_id).first()
    
    now = datetime.now()
    
    if subscription:
        # Update existing subscription
        subscription.plan_id = new_plan_id
        subscription.updated_at = now
        # In production: handle proration, payment gateway update, etc.
    else:
        # Create new subscription
        subscription = Subscription(
            startup_id=startup_id,
            plan_id=new_plan_id,
            status='active',
            current_period_start=now,
            current_period_end=now + timedelta(days=30),  # Simplified: 30-day cycle
            payment_provider='manual'  # Placeholder
        )
        db.session.add(subscription)
    
    db.session.commit()
    
    return {
        'success': True,
        'subscription': subscription.to_dict(),
        'message': f"Successfully upgraded to {new_plan.name} plan"
    }