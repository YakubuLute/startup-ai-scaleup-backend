from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import SubscriptionPlan, Subscription, Startup, User
from app.billing.services import (
    initialize_default_plans,
    check_usage_limit,
    record_usage,
    get_subscription_status,
    upgrade_subscription
)

billing_bp = Blueprint('billing', __name__)

# ============================================================================
# PUBLIC ENDPOINTS (No Auth Required)
# ============================================================================

@billing_bp.route('/plans', methods=['GET'])
def list_plans():
    """FR-60: List all available subscription plans (public)"""
    plans = SubscriptionPlan.query.filter_by(is_active=True).all()
    
    return jsonify({
        "plans": [p.to_dict() for p in plans]
    }), 200

# ============================================================================
# USER ENDPOINTS (Auth Required - Startup Founder)
# ============================================================================

@billing_bp.route('/subscription', methods=['GET'])
@jwt_required()
def get_my_subscription():
    """FR-61: Get current subscription status and usage for authenticated user's startup"""
    current_user_id = int(get_jwt_identity())
    
    # Get user's primary startup (simplified - in production, handle multiple startups)
    startup = Startup.query.filter_by(owner_user_id=current_user_id).first()
    if not startup:
        return jsonify({"msg": "No startup found for this user"}), 404
    
    status = get_subscription_status(startup.id)
    return jsonify(status), 200

@billing_bp.route('/subscription/upgrade', methods=['POST'])
@jwt_required()
def upgrade_plan():
    """FR-61: Upgrade or downgrade subscription plan"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if 'plan_id' not in data:
        return jsonify({"msg": "plan_id is required"}), 400
    
    # Get user's startup
    startup = Startup.query.filter_by(owner_user_id=current_user_id).first()
    if not startup:
        return jsonify({"msg": "No startup found"}), 404
    
    # Perform upgrade
    result = upgrade_subscription(startup.id, data['plan_id'])
    
    if not result['success']:
        return jsonify({"msg": result['error']}), 400
    
    return jsonify(result), 200

@billing_bp.route('/usage/check', methods=['POST'])
@jwt_required()
def check_usage():
    """FR-62: Check if a specific action is allowed under current plan"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if 'resource_type' not in data:
        return jsonify({"msg": "resource_type is required"}), 400
    
    # Get user's startup
    startup = Startup.query.filter_by(owner_user_id=current_user_id).first()
    if not startup:
        return jsonify({"msg": "No startup found"}), 404
    
    # Get active subscription
    subscription = Subscription.query.filter_by(startup_id=startup.id, status='active').first()
    if not subscription:
        # No subscription = Free tier by default
        plan = SubscriptionPlan.query.filter_by(name='Free').first()
    else:
        plan = subscription.plan
    
    # Check limit
    is_allowed, message, current, limit = check_usage_limit(
        startup.id, 
        data['resource_type'], 
        plan
    )
    
    return jsonify({
        "allowed": is_allowed,
        "message": message,
        "current_usage": current,
        "limit": limit if limit != -1 else "unlimited",
        "resource_type": data['resource_type']
    }), 200

# ============================================================================
# ADMIN ENDPOINTS (Program Manager / System Admin)
# ============================================================================

@billing_bp.route('/admin/plans', methods=['POST'])
@jwt_required()
def create_plan():
    """Admin: Create or update a subscription plan"""
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    data = request.get_json()
    
    # Validate required fields
    if 'name' not in data or 'limits' not in data:
        return jsonify({"msg": "name and limits are required"}), 400
    
    # Create or update plan
    plan = SubscriptionPlan.query.filter_by(name=data['name']).first()
    
    if plan:
        # Update existing
        plan.description = data.get('description', plan.description)
        plan.price = data.get('price')
        plan.max_documents_per_month = data['limits'].get('documents', 1)
        plan.max_valuations_per_month = data['limits'].get('valuations', 0)
        plan.max_diagnostics_per_month = data['limits'].get('diagnostics', 1)
        plan.max_team_members = data['limits'].get('team_members', 1)
        plan.max_storage_mb = data['limits'].get('storage_mb', 100)
        plan.features = data.get('features', plan.features)
        plan.is_active = data.get('is_active', True)
    else:
        # Create new
        plan = SubscriptionPlan(
            name=data['name'],
            description=data.get('description'),
            price=data.get('price'),
            max_documents_per_month=data['limits'].get('documents', 1),
            max_valuations_per_month=data['limits'].get('valuations', 0),
            max_diagnostics_per_month=data['limits'].get('diagnostics', 1),
            max_team_members=data['limits'].get('team_members', 1),
            max_storage_mb=data['limits'].get('storage_mb', 100),
            features=data.get('features', []),
            is_active=data.get('is_active', True)
        )
        db.session.add(plan)
    
    db.session.commit()
    
    return jsonify({"msg": "Plan saved successfully", "plan": plan.to_dict()}), 201

@billing_bp.route('/admin/initialize', methods=['POST'])
@jwt_required()
def initialize_plans():
    """Admin: Seed default plans into database"""
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    success = initialize_default_plans()
    
    return jsonify({
        "msg": "Default plans initialized" if success else "Failed to initialize plans",
        "success": success
    }), 200