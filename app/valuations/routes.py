# app/valuations/routes.py
"""
FR-30 to FR-33: Valuation Module REST API
Endpoints for methods, calculation, results, and history.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from app.extensions import db
from app.models import Valuation, Startup
from app.valuations.services import run_valuation

valuations_bp = Blueprint('valuations', __name__)

def _check_startup_ownership(startup_id, user_id):
    """Helper: verify user owns the startup"""
    startup = Startup.query.get(startup_id)
    if not startup or int(startup.owner_user_id) != int(user_id):
        return False
    return True

@valuations_bp.route('/methods', methods=['GET'])
@jwt_required()
def list_methods():
    """
    FR-30: List available valuation methods with requirements
    """
    methods = [
        {
            "id": "DCF",
            "name": "Discounted Cash Flow",
            "description": "Best for startups with revenue history and reliable projections",
            "best_for": "Growth-stage startups with 3+ years financial data",
            "required_inputs": [
                {"field": "revenue_history", "type": "array", "description": "Last 3 years revenue [y-3, y-2, y-1]"},
                {"field": "projected_growth", "type": "decimal", "description": "Annual growth rate (e.g., 0.25 for 25%)"},
                {"field": "operating_margin", "type": "decimal", "description": "Expected operating margin (e.g., 0.15)"},
                {"field": "capex_percent", "type": "decimal", "description": "CapEx as % of revenue"},
                {"field": "working_capital_change", "type": "decimal", "description": "Annual WC change as % of revenue"},
                {"field": "discount_rate", "type": "decimal", "description": "WACC (e.g., 0.18 for 18%)"},
                {"field": "terminal_growth", "type": "decimal", "description": "Perpetual growth rate (e.g., 0.03)"},
                {"field": "tax_rate", "type": "decimal", "description": "Corporate tax rate"}
            ],
            "outputs": ["enterprise_value", "irr", "sensitivity_analysis", "confidence_score"]
        },
        {
            "id": "Becker",
            "name": "Becker Method",
            "description": "Simplified method for early-stage startups (revenue + qualitative factors)",
            "best_for": "Early-stage startups with <3 years revenue history",
            "required_inputs": [
                {"field": "revenue_history", "type": "array", "description": "Last 2 years revenue"},
                {"field": "industry_multiple", "type": "decimal", "description": "Industry revenue multiple (e.g., 3.5)"},
                {"field": "team_score", "type": "integer", "description": "Team quality 1-10"},
                {"field": "market_score", "type": "integer", "description": "Market attractiveness 1-10"},
                {"field": "traction_score", "type": "integer", "description": "Customer traction 1-10"}
            ],
            "outputs": ["adjusted_valuation", "multiple_breakdown", "sensitivity_range", "confidence_score"]
        },
        {
            "id": "Asset",
            "name": "Asset-Based Method",
            "description": "Net asset value approach for asset-heavy businesses",
            "best_for": "Manufacturing, agriculture, or capital-intensive startups",
            "required_inputs": [
                {"field": "total_assets", "type": "decimal", "description": "Total assets in GHS"},
                {"field": "total_liabilities", "type": "decimal", "description": "Total liabilities in GHS"},
                {"field": "intangible_assets", "type": "decimal", "description": "Optional intangible asset value", "optional": True},
                {"field": "asset_quality", "type": "string", "description": "Asset quality: high/medium/low", "optional": True}
            ],
            "outputs": ["net_asset_value", "quality_adjustment", "sensitivity_range", "confidence_score"]
        }
    ]
    
    return jsonify({"methods": methods}), 200

@valuations_bp.route('/calculate', methods=['POST'])
@jwt_required()
def calculate_valuation():
    """
    FR-30 + FR-31: Calculate business valuation using selected method
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Validate required fields
    required = ['startup_id', 'method', 'financials']
    for field in required:
        if field not in data:
            return jsonify({"msg": f"Missing required field: {field}"}), 400
    
    # Verify startup ownership (FR-03 / US-06)
    if not _check_startup_ownership(data['startup_id'], current_user_id):
        return jsonify({"msg": "Access denied"}), 403
    
    # Run valuation calculation
    result = run_valuation(data['method'], data['financials'])
    
    if result.get('error'):
        return jsonify({"msg": result['error']}), 400
    
    # Save valuation to database (FR-33)
    valuation = Valuation(
        startup_id=data['startup_id'],
        method=data['method'],
        valuation_amount=result['valuation'],
        currency=result.get('currency', 'GHS'),
        assumptions=data['financials'],
        results=result.get('breakdown', {}),
        confidence=result.get('confidence', 'medium'),
        status='completed',
        run_at=datetime.utcnow()
    )
    
    db.session.add(valuation)
    db.session.commit()
    
    return jsonify({
        "msg": "Valuation calculated successfully",
        "valuation": {
            "id": valuation.id,
            "method": valuation.method,
            "valuation_amount": valuation.valuation_amount,
            "currency": valuation.currency,
            "confidence": valuation.confidence,
            "breakdown": valuation.results,
            "sensitivity": result.get('sensitivity'),
            "run_at": valuation.run_at.isoformat() if valuation.run_at else None
        }
    }), 201

@valuations_bp.route('', methods=['GET'])
@jwt_required()
def list_valuations():
    """
    FR-33: Get all valuations for the current user's startups
    Supports history comparison view
    """
    current_user_id = int(get_jwt_identity())
    
    # Get all startups owned by user
    startups = Startup.query.filter_by(owner_user_id=current_user_id).all()
    startup_ids = [s.id for s in startups]
    
    # Get valuations for those startups, ordered by most recent
    valuations = Valuation.query.filter(
        Valuation.startup_id.in_(startup_ids)
    ).order_by(Valuation.run_at.desc()).all()
    
    return jsonify({
        "valuations": [
            {
                "id": v.id,
                "startup_id": v.startup_id,
                "startup_name": v.startup.name if v.startup else None,
                "method": v.method,
                "valuation_amount": v.valuation_amount,
                "currency": v.currency,
                "confidence": v.confidence,
                "run_at": v.run_at.isoformat() if v.run_at else None
            }
            for v in valuations
        ],
        "count": len(valuations)
    }), 200

@valuations_bp.route('/<int:valuation_id>', methods=['GET'])
@jwt_required()
def get_valuation(valuation_id):
    """
    FR-33: Get a specific valuation with full details
    For review and comparison
    """
    current_user_id = int(get_jwt_identity())
    valuation = Valuation.query.get_or_404(valuation_id)
    
    # Verify access: user must own the startup
    if valuation.startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    return jsonify({
        "valuation": {
            "id": valuation.id,
            "startup_id": valuation.startup_id,
            "method": valuation.method,
            "valuation_amount": valuation.valuation_amount,
            "currency": valuation.currency,
            "confidence": valuation.confidence,
            "breakdown": valuation.results,
            "assumptions": valuation.assumptions,
            "status": valuation.status,
            "run_at": valuation.run_at.isoformat() if valuation.run_at else None
        }
    }), 200