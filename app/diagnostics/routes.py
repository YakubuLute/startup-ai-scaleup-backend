# app/diagnostics/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import DiagnosticSession, Startup
from app.diagnostics.engine import DIAGNOSTIC_SCHEMA, calculate_scores, generate_recommendations

diagnostics_bp = Blueprint('diagnostics', __name__)

def _check_startup_ownership(startup_id, user_id):
    """FR-03 / Spec 6.4: Ensure user owns the startup before accessing diagnostics"""
    startup = Startup.query.get_or_404(startup_id)
    if startup.owner_user_id != int(user_id):
        return jsonify({"msg": "Access denied: You do not own this startup"}), 403
    return startup

@diagnostics_bp.route('/questions', methods=['GET'])
@jwt_required()
def get_diagnostic_questions():
    """FR-20 / US-20: Fetch dynamic questionnaire schema"""
    return jsonify({"schema": DIAGNOSTIC_SCHEMA}), 200

@diagnostics_bp.route('/<int:startup_id>/run', methods=['POST'])
@jwt_required()
def run_diagnostic(startup_id):
    """FR-20, FR-21, FR-22 / US-20: Run assessment & generate results"""
    user_id = int(get_jwt_identity())
    _check_startup_ownership(startup_id, user_id)
    
    data = request.get_json()
    responses = data.get("responses", {})
    
    # Validate required fields
    required_ids = [q["id"] for cat in DIAGNOSTIC_SCHEMA.values() for q in cat["questions"]]
    missing = [qid for qid in required_ids if qid not in responses]
    if missing:
        return jsonify({"msg": f"Missing responses for: {', '.join(missing)}"}), 400
        
    # FR-21: Calculate scores & stage
    overall_score, stage, sub_scores = calculate_scores(responses)
    
    # FR-22: Generate tailored recommendations
    recommendations = generate_recommendations(sub_scores, stage)
    
    # FR-23: Save diagnostic session
    new_session = DiagnosticSession(
        startup_id=startup_id,
        overall_score=overall_score,
        stage=stage,
        sub_scores=sub_scores,
        responses=responses,
        recommendations=recommendations,
        version=DiagnosticSession.query.filter_by(startup_id=startup_id).count() + 1
    )
    db.session.add(new_session)
    db.session.commit()
    
    return jsonify({
        "msg": "Diagnostic completed",
        "results": new_session.to_dict()
    }), 201

@diagnostics_bp.route('/<int:startup_id>/latest', methods=['GET'])
@jwt_required()
def get_latest_diagnostic(startup_id):
    """FR-21 / US-21: View latest results"""
    _check_startup_ownership(startup_id, int(get_jwt_identity()))
    latest = DiagnosticSession.query.filter_by(startup_id=startup_id).order_by(DiagnosticSession.run_at.desc()).first()
    if not latest:
        return jsonify({"msg": "No diagnostic run found"}), 404
    return jsonify({"results": latest.to_dict()}), 200

@diagnostics_bp.route('/<int:startup_id>/history', methods=['GET'])
@jwt_required()
def get_diagnostic_history(startup_id):
    """FR-23 / US-23: Compare past runs"""
    _check_startup_ownership(startup_id, int(get_jwt_identity()))
    history = DiagnosticSession.query.filter_by(startup_id=startup_id).order_by(DiagnosticSession.run_at.desc()).all()
    return jsonify({
        "history": [s.to_dict() for s in history],
        "count": len(history)
    }), 200