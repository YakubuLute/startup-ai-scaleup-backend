from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import DiagnosticSession, Startup
from app.diagnostics.services import run_diagnostic
from app.diagnostics.questions import DIAGNOSTIC_QUESTIONS

diagnostics_bp = Blueprint('diagnostics', __name__)

@diagnostics_bp.route('/questions', methods=['GET'])
@jwt_required()
def get_questions():
    """FR-20: Get diagnostic questions organized by dimension"""
    return jsonify({
        "dimensions": [
            {
                "id": dim,
                "name": dim.title(),
                "questions": questions
            }
            for dim, questions in DIAGNOSTIC_QUESTIONS.items()
        ]
    }), 200

@diagnostics_bp.route('/run', methods=['POST'])
@jwt_required()
def run_diagnostic_endpoint():
    """
    FR-20 + FR-21 + FR-22: Run diagnostic assessment and get results.
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Validate required fields
    required = ['startup_id', 'responses']
    for field in required:
        if field not in data:
            return jsonify({"msg": f"Missing required field: {field}"}), 400
    
    # Verify startup ownership
    startup = Startup.query.get(data['startup_id'])
    if not startup or startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    # Run diagnostic calculation
    result = run_diagnostic(data['responses'])
    
    # Save diagnostic session to database
    session = DiagnosticSession(
        startup_id=data['startup_id'],
        overall_score=result['overall_score'],
        stage=result['stage'],
        sub_scores=result['sub_scores'],
        responses=data['responses'],
        recommendations=result['recommendations'],
        version=1  # Could increment for re-runs
    )
    
    db.session.add(session)
    db.session.commit()
    
    return jsonify({
        "msg": "Diagnostic completed successfully",
        "result": {
            "overall_score": result['overall_score'],
            "stage": result['stage'],
            "sub_scores": result['sub_scores'],
            "recommendations": result['recommendations']
        },
        "session_id": session.id
    }), 201

@diagnostics_bp.route('', methods=['GET'])
@jwt_required()
def list_diagnostics():
    """Get all diagnostic sessions for the current user's startups"""
    current_user_id = int(get_jwt_identity())
    
    # Get all startups owned by user
    startups = Startup.query.filter_by(owner_user_id=current_user_id).all()
    startup_ids = [s.id for s in startups]
    
    # Get diagnostics for those startups
    sessions = DiagnosticSession.query.filter(
        DiagnosticSession.startup_id.in_(startup_ids)
    ).order_by(DiagnosticSession.run_at.desc()).all()
    
    return jsonify({
        "sessions": [s.to_dict() for s in sessions],
        "count": len(sessions)
    }), 200

@diagnostics_bp.route('/<int:session_id>', methods=['GET'])
@jwt_required()
def get_diagnostic(session_id):
    """Get a specific diagnostic session (with ownership check)"""
    current_user_id = int(get_jwt_identity())
    session = DiagnosticSession.query.get_or_404(session_id)
    
    # Verify access: user must own the startup
    if session.startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    return jsonify({"session": session.to_dict()}), 200

@diagnostics_bp.route('/stages', methods=['GET'])
@jwt_required()
def get_stage_info():
    """FR-21: Get information about business stages"""
    stages = [
        {
            "id": "Early",
            "name": "Early Stage",
            "score_range": "0-49",
            "description": "Validating idea, building product, finding first customers"
        },
        {
            "id": "Growth",
            "name": "Growth Stage",
            "score_range": "50-79",
            "description": "Scaling operations, expanding market, optimizing processes"
        },
        {
            "id": "Maturity",
            "name": "Maturity Stage",
            "score_range": "80-100",
            "description": "Established business, ready for investment or expansion"
        }
    ]
    
    return jsonify({"stages": stages}), 200