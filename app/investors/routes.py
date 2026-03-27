"""
Investor Portal Routes (FR-70 to FR-72)
- Startup discovery & search (FR-70)
- Startup profile view (FR-71)
- Connection requests (FR-72)
- Notifications integration (FR-80)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import InvestorProfile, ConnectionRequest, Startup, User
from app.investors.services import (
    search_startups,
    get_startup_investor_view,
    create_connection_request,
    respond_to_connection_request,
    get_investor_profile
)
from app.notifications.services import (
    notify_connection_request,
    notify_connection_accepted
)

investors_bp = Blueprint('investors', __name__)

# ============================================================================
# PUBLIC ENDPOINTS (No Auth Required)
# ============================================================================

@investors_bp.route('/startups', methods=['GET'])
def discover_startups():
    """
    FR-70: Public startup discovery (limited info for non-authenticated users).
    Investors can browse without logging in, but need auth for full details.
    """
    # Get filter params from query string
    filters = {
        'sector': request.args.get('sector'),
        'stage': request.args.get('stage'),
        'country': request.args.get('country'),
        'verified_only': request.args.get('verified_only', 'false').lower() == 'true',
        'search_query': request.args.get('q')
    }
    
    # Pagination
    limit = min(int(request.args.get('limit', 20)), 50)  # Max 50
    offset = int(request.args.get('offset', 0))
    
    # Search
    startups, total = search_startups(filters, limit, offset)
    
    return jsonify({
        "startups": [
            {
                'id': s.id,
                'name': s.name,
                'sector': s.sector,
                'country': s.country,
                'stage': s.stage,
                'is_verified': s.is_verified
            }
            for s in startups
        ],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
    }), 200


# ============================================================================
# INVESTOR ENDPOINTS (Auth Required - Investor Role)
# ============================================================================

@investors_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_my_investor_profile():
    """Get current user's investor profile"""
    current_user_id = int(get_jwt_identity())
    profile = get_investor_profile(current_user_id)
    
    return jsonify({
        "profile": profile.to_dict()
    }), 200


@investors_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_investor_profile():
    """Update investor profile (focus areas, check size, etc.)"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    profile = get_investor_profile(current_user_id)
    
    # Update fields
    if 'firm_name' in data:
        profile.firm_name = data['firm_name']
    if 'investor_type' in data:
        profile.investor_type = data['investor_type']
    if 'focus_sectors' in data:
        profile.focus_sectors = data['focus_sectors']
    if 'focus_stages' in data:
        profile.focus_stages = data['focus_stages']
    if 'typical_check_size' in data:
        profile.typical_check_size = data['typical_check_size']
    if 'location_preference' in data:
        profile.location_preference = data['location_preference']
    
    db.session.commit()
    
    return jsonify({
        "msg": "Profile updated successfully",
        "profile": profile.to_dict()
    }), 200


@investors_bp.route('/startups/<int:startup_id>', methods=['GET'])
@jwt_required()
def view_startup_profile(startup_id):
    """
    FR-71: View detailed startup profile (investor view).
    Shows verified data, valuations, diagnostics (read-only).
    """
    current_user_id = int(get_jwt_identity())
    
    # Get investor profile
    investor_profile = get_investor_profile(current_user_id)
    
    # Get startup investor view
    startup_data = get_startup_investor_view(startup_id, investor_profile.id)
    
    if not startup_data:
        return jsonify({"msg": "Startup not found"}), 404
    
    return jsonify({
        "startup": startup_data
    }), 200


@investors_bp.route('/startups/<int:startup_id>/connect', methods=['POST'])
@jwt_required()
def send_connection_request(startup_id):
    """
    FR-72: Investor sends connection request to startup.
    FR-80: Triggers notification to startup owner.
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Get investor profile
    investor_profile = get_investor_profile(current_user_id)
    
    # Create connection request
    result = create_connection_request(
        investor_profile.id,
        startup_id,
        message=data.get('message')
    )
    
    if not result['success']:
        return jsonify({"msg": result['error']}), 400
    
    # ========================================================================
    # FR-80: Send notification to startup owner
    # ========================================================================
    startup = Startup.query.get(startup_id)
    if startup:
        notify_connection_request(
            investor_name=investor_profile.firm_name or "An investor",
            startup_name=startup.name,
            startup_owner_id=startup.owner_user_id,
            request_id=result['request_id']
        )
    
    return jsonify({
        "msg": result['message'],
        "request_id": result['request_id'],
        "status": result['status']
    }), 201


@investors_bp.route('/connections', methods=['GET'])
@jwt_required()
def get_my_connections():
    """Get all connection requests sent by this investor"""
    current_user_id = int(get_jwt_identity())
    investor_profile = get_investor_profile(current_user_id)
    
    # Get all connection requests
    requests = ConnectionRequest.query.filter_by(
        investor_id=investor_profile.id
    ).order_by(ConnectionRequest.created_at.desc()).all()
    
    return jsonify({
        "connections": [r.to_dict() for r in requests],
        "count": len(requests)
    }), 200


# ============================================================================
# STARTUP OWNER ENDPOINTS (Auth Required - Startup Founder)
# ============================================================================

@investors_bp.route('/requests', methods=['GET'])
@jwt_required()
def get_connection_requests():
    """Get all connection requests received by startup owner"""
    current_user_id = int(get_jwt_identity())
    
    # Get all startups owned by user
    startups = Startup.query.filter_by(owner_user_id=current_user_id).all()
    startup_ids = [s.id for s in startups]
    
    # Get all connection requests for these startups
    requests = ConnectionRequest.query.filter(
        ConnectionRequest.startup_id.in_(startup_ids)
    ).order_by(ConnectionRequest.created_at.desc()).all()
    
    return jsonify({
        "requests": [r.to_dict() for r in requests],
        "count": len(requests)
    }), 200


@investors_bp.route('/requests/<int:request_id>/respond', methods=['POST'])
@jwt_required()
def respond_to_request(request_id):
    """
    FR-72: Startup owner accepts or rejects connection request.
    FR-80: Triggers notification to investor when accepted.
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if 'decision' not in data:
        return jsonify({"msg": "decision is required ('accepted' or 'rejected')"}), 400
    
    result = respond_to_connection_request(
        request_id,
        current_user_id,
        data['decision']
    )
    
    if not result['success']:
        return jsonify({"msg": result['error']}), 400
    
    # ========================================================================
    # FR-80: Send notification to investor if accepted
    # ========================================================================
    if data['decision'] == 'accepted':
        request = ConnectionRequest.query.get(request_id)
        if request:
            notify_connection_accepted(
                startup_name=request.startup.name,
                investor_name=request.investor.firm_name or "An investor",
                investor_user_id=request.investor.user_id,
                request_id=request_id
            )
    
    return jsonify({
        "msg": result['message'],
        "request_id": result['request_id'],
        "status": result['status']
    }), 200