# app/valuations/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Valuation, Startup
from app.valuations.engine import run_valuation

valuations_bp = Blueprint('valuations', __name__)

def _check_startup_ownership(startup_id, user_id):
    startup = Startup.query.get_or_404(startup_id)
    if startup.owner_user_id != int(user_id):
        return jsonify({"msg": "Access denied: You do not own this startup"}), 403
    return startup

@valuations_bp.route('/<int:startup_id>/run', methods=['POST'])
@jwt_required()
def run_valuation_endpoint(startup_id):
    """FR-30, FR-31 / US-30, US-31: Input financials + run selected valuation methods"""
    user_id = int(get_jwt_identity())
    _check_startup_ownership(startup_id, user_id)
    
    data = request.get_json()
    
    # Validate required fields (FR-30)
    required = ['financials', 'assumptions', 'methods']
    for field in required:
        if field not in data:
            return jsonify({"msg": f"Missing required field: {field}"}), 400
    
    financials = data['financials']
    assumptions = data['assumptions']
    methods = data['methods']  # e.g., ['DCF', 'Becker']
    
    # Run valuation engine (FR-31)
    try:
        results = run_valuation(financials, assumptions, methods)
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    
    # Save valuation record (FR-33)
    new_valuation = Valuation(
        startup_id=startup_id,
        method=','.join(methods),  # Store which methods were run
        valuation_amount=results['consensus_valuation'],
        currency=assumptions.get('currency', 'GHS'),
        assumptions=assumptions,
        results=results,
        confidence=results['confidence']
    )
    db.session.add(new_valuation)
    db.session.commit()
    
    return jsonify({
        "msg": "Valuation completed successfully",
        "valuation": new_valuation.to_dict()
    }), 201

@valuations_bp.route('/<int:startup_id>/latest', methods=['GET'])
@jwt_required()
def get_latest_valuation(startup_id):
    """FR-31 / US-32: View most recent valuation results"""
    _check_startup_ownership(startup_id, int(get_jwt_identity()))
    latest = Valuation.query.filter_by(startup_id=startup_id).order_by(Valuation.run_at.desc()).first()
    if not latest:
        return jsonify({"msg": "No valuation found for this startup"}), 404
    return jsonify({"valuation": latest.to_dict()}), 200

@valuations_bp.route('/<int:startup_id>/history', methods=['GET'])
@jwt_required()
def get_valuation_history(startup_id):
    """FR-33 / US-32: Compare past valuation runs"""
    _check_startup_ownership(startup_id, int(get_jwt_identity()))
    history = Valuation.query.filter_by(startup_id=startup_id).order_by(Valuation.run_at.desc()).all()
    return jsonify({
        "valuations": [v.to_dict() for v in history],
        "count": len(history)
    }), 200

@valuations_bp.route('/<int:valuation_id>/export', methods=['POST'])
@jwt_required()
def export_valuation_report(valuation_id):
    """FR-33 / US-32: Generate standardized valuation report (PDF stub)"""
    user_id = int(get_jwt_identity())
    valuation = Valuation.query.get_or_404(valuation_id)
    
    # Verify ownership
    if valuation.startup.owner_user_id != user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    # 📦 TODO: Actual PDF generation (weasyprint/reportlab)
    # For now, return structured data ready for frontend PDF rendering
    report = {
        "title": f"Valuation Report - {valuation.startup.name}",
        "generated_at": datetime.utcnow().isoformat(),
        "method": valuation.method,
        "valuation_amount": valuation.valuation_amount,
        "currency": valuation.currency,
        "confidence": valuation.confidence,
        "assumptions_summary": {
            k: v for k, v in valuation.assumptions.items() 
            if k in ['discount_rate', 'terminal_growth', 'stage', 'sector']
        },
        "results_summary": valuation.results.get('individual_results', {})
    }
    
    return jsonify({
        "msg": "Report generated",
        "report": report,
        "download_url": f"/api/valuations/{valuation_id}/download.pdf"  # Stub endpoint
    }), 200