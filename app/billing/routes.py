# app/billing/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Startup, Subscription, SubscriptionPlan, UsageRecord, BillingTransaction
from app.billing.engine import get_current_plan_limits, check_and_track_usage

billing_bp = Blueprint('billing', __name__)

def _check_startup_ownership(startup_id, user_id):
    """Helper: verify user owns the startup"""
    startup = Startup.query.get(startup_id)
    if not startup or int(startup.owner_user_id) != int(user_id):
        return False
    return True

@billing_bp.route('/plans', methods=['GET'])
@jwt_required()
def list_plans():
    """FR-60 / US-60: List available subscription plans"""
    plans = SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.price_ghs).all()
    return jsonify({"plans": [p.to_dict() for p in plans]}), 200

@billing_bp.route('/<int:startup_id>/usage', methods=['GET'])
@jwt_required()
def get_usage(startup_id):
    """FR-62 / US-62: Get current usage vs plan limits"""
    current_user_id = get_jwt_identity()
    
    if not _check_startup_ownership(startup_id, current_user_id):
        return jsonify({"msg": "Access denied"}), 403
    
    # 🔧 Use SAME period logic as check_and_track_usage() in engine.py
    sub = Subscription.query.filter_by(startup_id=startup_id, status='active').first()
    if not sub:
        # Fallback to monthly cycle for untracked startups
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0)
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    else:
        period_start = sub.current_period_start
        period_end = sub.current_period_end
    
    # Get plan limits
    limits = get_current_plan_limits(startup_id)
    
    # Get actual usage records for this EXACT period
    usage_records = UsageRecord.query.filter_by(
        startup_id=startup_id,
        period_start=period_start,
        period_end=period_end
    ).all()
    
    # Build usage summary
    usage_summary = {}
    for resource_type in ['documents', 'valuations', 'diagnostics', 'shares']:
        record = next((r for r in usage_records if r.resource_type == resource_type), None)
        usage_summary[resource_type] = {
            "used": record.count if record else 0,
            "limit": limits.get(resource_type, 0)
        }
    
    return jsonify({
        "billing_cycle": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat()
        },
        "usage": usage_summary
    }), 200

@billing_bp.route('/<int:startup_id>/history', methods=['GET'])
@jwt_required()
def get_billing_history(startup_id):
    """FR-63 / US-63: Get billing transaction history"""
    current_user_id = get_jwt_identity()
    
    if not _check_startup_ownership(startup_id, current_user_id):
        return jsonify({"msg": "Access denied"}), 403
    
    transactions = BillingTransaction.query.filter_by(
        startup_id=startup_id
    ).order_by(BillingTransaction.transaction_date.desc()).all()
    
    return jsonify({
        "transactions": [t.to_dict() for t in transactions]
    }), 200