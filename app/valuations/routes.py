from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Valuation, Startup
from app.valuations.services import run_valuation

valuations_bp = Blueprint('valuations', __name__)

@valuations_bp.route('/calculate', methods=['POST'])
@jwt_required()
def calculate_valuation():
    """
    FR-30 + FR-31: Calculate business valuation using selected method.
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Validate required fields
    required = ['startup_id', 'method', 'financials']
    for field in required:
        if field not in data:
            return jsonify({"msg": f"Missing required field: {field}"}), 400
    
    # Verify startup ownership
    startup = Startup.query.get(data['startup_id'])
    if not startup or startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    # Run valuation calculation
    result = run_valuation(data['method'], data['financials'])
    
    if result.get('error'):
        return jsonify({"msg": result['error']}), 400
    
    # Save valuation to database
    valuation = Valuation(
        startup_id=data['startup_id'],
        method=data['method'],
        valuation_amount=result['valuation'],
        currency='GHS',  # Default to Ghana Cedi
        assumptions=data['financials'],
        results=result.get('breakdown', {}),
        confidence=result.get('confidence', 'medium'),
        status='completed'
    )
    
    db.session.add(valuation)
    db.session.commit()
    
    return jsonify({
        "msg": "Valuation calculated successfully",
        "valuation": valuation.to_dict()
    }), 201

@valuations_bp.route('', methods=['GET'])
@jwt_required()
def list_valuations():
    """Get all valuations for the current user's startups"""
    current_user_id = int(get_jwt_identity())
    
    # Get all startups owned by user
    startups = Startup.query.filter_by(owner_user_id=current_user_id).all()
    startup_ids = [s.id for s in startups]
    
    # Get valuations for those startups
    valuations = Valuation.query.filter(Valuation.startup_id.in_(startup_ids)).all()
    
    return jsonify({
        "valuations": [v.to_dict() for v in valuations],
        "count": len(valuations)
    }), 200

@valuations_bp.route('/<int:valuation_id>', methods=['GET'])
@jwt_required()
def get_valuation(valuation_id):
    """Get a specific valuation (with ownership check)"""
    current_user_id = int(get_jwt_identity())
    valuation = Valuation.query.get_or_404(valuation_id)
    
    # Verify access: user must own the startup
    if valuation.startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    return jsonify({"valuation": valuation.to_dict()}), 200

@valuations_bp.route('/methods', methods=['GET'])
@jwt_required()
def list_methods():
    """FR-30: List available valuation methods"""
    methods = [
        {
            "id": "DCF",
            "name": "Discounted Cash Flow",
            "description": "Best for startups with revenue history and projections",
            "required_inputs": ["revenue_history", "projected_growth", "discount_rate", "terminal_growth"]
        },
        {
            "id": "Becker",
            "name": "Becker Method",
            "description": "Simplified method for early-stage startups (revenue + team quality)",
            "required_inputs": ["revenue_history", "industry_multiple", "team_score"]
        },
        {
            "id": "Asset",
            "name": "Asset-Based Method",
            "description": "For asset-heavy businesses (total assets - liabilities)",
            "required_inputs": ["total_assets", "total_liabilities"]
        }
    ]
    
    return jsonify({"methods": methods}), 200