# app/billing/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Startup, SubscriptionPlan, Subscription, BillingTransaction, User
from app.billing.engine import (
    get_current_plan_limits, check_and_track_usage,
    create_or_upgrade_subscription, record_billing_transaction
)

billing_bp = Blueprint('billing', __name__)

def _check_startup_ownership(startup_id, user_id):
    startup = Startup.query.get_or_404(startup_id)
    if startup.owner_user_id != int(user_id):
        return jsonify({"msg": "Access denied: You do not own this startup"}), 403
    return startup

@billing_bp.route('/plans', methods=['GET'])
@jwt_required()
def list_plans():
    """FR-60 / US-60: View available plans & limits"""
    plans = SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.price_ghs).all()
    return jsonify({"plans": [p.to_dict() for p in plans]}), 200

@billing_bp.route('/<int:startup_id>/subscribe', methods=['POST'])
@jwt_required()
def subscribe_to_plan(startup_id):
    """FR-61 / US-61: Upgrade/downgrade plan (payment stub ready)"""
    user_id = int(get_jwt_identity())
    _check_startup_ownership(startup_id, user_id)
    
    data = request.get_json()
    plan_id = data.get('plan_id')
    if not plan_id:
        return jsonify({"msg": "Missing plan_id"}), 400
        
    # 🔧 TODO: Integrate Paystack/Stripe here
    # payment_ref = paystack.create_transaction(...)
    payment_ref = f"mock_ref_{startup_id}_{int(datetime.utcnow().timestamp())}"
    
    result = create_or_upgrade_subscription(startup_id, plan_id, payment_ref)
    record_billing_transaction(startup_id, None, 0.0, 'plan_upgrade', metadata={'plan_id': plan_id})
    
    return jsonify(result), 200

@billing_bp.route('/<int:startup_id>/usage', methods=['GET'])
@jwt_required()
def get_usage(startup_id):
    """FR-62 / US-62: Check current usage vs plan limits"""
    _check_startup_ownership(startup_id, int(get_jwt_identity()))
    limits = get_current_plan_limits(startup_id)
    
    # Get current usage records
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0)
    period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    
    usage = UsageRecord.query.filter_by(
        startup_id=startup_id, period_start=period_start, period_end=period_end
    ).all()
    
    usage_map = {u.resource_type: u.count for u in usage}
    usage_summary = {
        res: {"used": usage_map.get(res, 0), "limit": limit}
        for res, limit in limits.items()
    }
    
    return jsonify({"billing_cycle": {"start": period_start.isoformat(), "end": period_end.isoformat()}, "usage": usage_summary}), 200

@billing_bp.route('/<int:startup_id>/history', methods=['GET'])
@jwt_required()
def get_billing_history(startup_id):
    """FR-63 / US-63: View billing transactions & invoices"""
    _check_startup_ownership(startup_id, int(get_jwt_identity()))
    txns = BillingTransaction.query.filter_by(startup_id=startup_id).order_by(BillingTransaction.transaction_date.desc()).all()
    return jsonify({"transactions": [t.to_dict() for t in txns]}), 200

@billing_bp.route('/webhook/paystack', methods=['POST'])
def paystack_webhook():
    """FR-61: Stub for payment gateway webhook (Phase 2 integration)"""
    data = request.get_json()
    # TODO: Verify webhook signature, update subscription status, handle grace period
    return jsonify({"msg": "Webhook received (stub)"}), 200

@billing_bp.route('/admin/plans', methods=['POST', 'PUT'])
@jwt_required()
def admin_configure_plan():
    """FR-65 / US-65: Admin create/update plans"""
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    if user.role not in ['System Admin', 'Program Manager']:
        return jsonify({"msg": "Admin access required"}), 403
        
    data = request.get_json()
    plan_id = data.get('id')
    plan = SubscriptionPlan.query.get(plan_id) if plan_id else None
    
    if plan:
        plan.name = data.get('name', plan.name)
        plan.price_ghs = data.get('price_ghs', plan.price_ghs)
        plan.limits = data.get('limits', plan.limits)
        plan.features = data.get('features', plan.features)
    else:
        plan = SubscriptionPlan(**data)
        db.session.add(plan)
    
    db.session.commit()
    return jsonify({"msg": "Plan saved", "plan": plan.to_dict()}), 201 if not plan_id else 200