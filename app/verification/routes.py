# app/verification/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import VerificationCase, Startup, User, DiagnosticSession, Valuation
from app.verification.engine import get_checklist, validate_submission, calculate_badge_validity, generate_due_diligence_summary

verification_bp = Blueprint('verification', __name__)

def _check_startup_ownership(startup_id, user_id):
    startup = Startup.query.get_or_404(startup_id)
    if startup.owner_user_id != int(user_id):
        return jsonify({"msg": "Access denied: You do not own this startup"}), 403
    return startup

def _check_reviewer_permission(user_id):
    user = User.query.get_or_404(user_id)
    if user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied: Reviewer permissions required"}), 403
    return user

@verification_bp.route('/<int:startup_id>/checklist', methods=['GET'])
@jwt_required()
def get_verification_checklist(startup_id):
    """FR-40 / US-40: Get required documents for verification"""
    _check_startup_ownership(startup_id, int(get_jwt_identity()))
    startup = Startup.query.get_or_404(startup_id)
    
    checklist = get_checklist(startup.country)
    return jsonify({
        "country": startup.country,
        "checklist": checklist
    }), 200

@verification_bp.route('/<int:startup_id>/submit', methods=['POST'])
@jwt_required()
def submit_verification(startup_id):
    """FR-40 / US-40: Submit documents for verification"""
    user_id = int(get_jwt_identity())
    startup = _check_startup_ownership(startup_id, user_id)
    
    data = request.get_json()
    documents_submitted = data.get('documents_submitted', [])
    
    # Validate submission completeness
    validation = validate_submission(documents_submitted, startup.country)
    if not validation['is_complete']:
        return jsonify({
            "msg": "Missing required documents",
            "missing": validation['missing_required']
        }), 400
    
    # Check for existing pending case
    existing = VerificationCase.query.filter_by(
        startup_id=startup_id, 
        status='pending'
    ).first()
    if existing:
        return jsonify({"msg": "Verification already pending"}), 400
    
    # Create new verification case
    new_case = VerificationCase(
        startup_id=startup_id,
        documents_submitted=documents_submitted,
        status='pending'
    )
    db.session.add(new_case)
    db.session.commit()
    
    return jsonify({
        "msg": "Verification submitted successfully",
        "case_id": new_case.id,
        "status": new_case.status
    }), 201

@verification_bp.route('/<int:startup_id>/status', methods=['GET'])
@jwt_required()
def get_verification_status(startup_id):
    """FR-41 / US-41: View current verification status"""
    _check_startup_ownership(startup_id, int(get_jwt_identity()))
    
    latest = VerificationCase.query.filter_by(
        startup_id=startup_id
    ).order_by(VerificationCase.submitted_at.desc()).first()
    
    if not latest:
        return jsonify({"msg": "No verification case found"}), 404
    
    return jsonify({"verification": latest.to_dict()}), 200

@verification_bp.route('/queue', methods=['GET'])
@jwt_required()
def get_verification_queue():
    """FR-41 / US-42: Reviewer queue of pending cases"""
    user_id = int(get_jwt_identity())
    _check_reviewer_permission(user_id)
    
    # Filter by optional query params
    country = request.args.get('country')
    sector = request.args.get('sector')
    
    query = VerificationCase.query.filter_by(status='pending')
    if country:
        query = query.join(Startup).filter(Startup.country == country)
    if sector:
        query = query.join(Startup).filter(Startup.sector == sector)
    
    cases = query.order_by(VerificationCase.submitted_at.asc()).all()
    
    return jsonify({
        "cases": [
            {
                "id": c.id,
                "startup_name": c.startup.name,
                "sector": c.startup.sector,
                "country": c.startup.country,
                "submitted_at": c.submitted_at.isoformat(),
                "documents_count": len(c.documents_submitted)
            } for c in cases
        ],
        "count": len(cases)
    }), 200

@verification_bp.route('/<int:case_id>/decision', methods=['PUT'])
@jwt_required()
def record_verification_decision(case_id):
    """FR-41, FR-42, FR-43 / US-43: Record Verified/Rejected decision"""
    user_id = int(get_jwt_identity())
    _check_reviewer_permission(user_id)
    
    case = VerificationCase.query.get_or_404(case_id)
    data = request.get_json()
    
    new_status = data.get('status')  # 'verified' or 'rejected'
    notes = data.get('notes', '')
    
    if new_status not in ['verified', 'rejected']:
        return jsonify({"msg": "Status must be 'verified' or 'rejected'"}), 400
    
    # Update case
    case.status = new_status
    case.reviewed_at = db.func.now()
    case.reviewer_id = user_id
    case.review_notes = notes
    
    if new_status == 'rejected':
        case.rejection_reason = data.get('rejection_reason', 'No reason provided')
        case.badge_issued = False
    else:  # verified
        # FR-42: Issue badge with validity based on startup stage
        stage = case.startup.stage or 'Early'
        case.badge_issued = True
        case.badge_valid_until = calculate_badge_validity(stage, case.reviewed_at)
    
    db.session.commit()
    
    # FR-43: Generate due diligence summary for verified cases
    summary = None
    if new_status == 'verified':
        diagnostics = DiagnosticSession.query.filter_by(
            startup_id=case.startup_id
        ).order_by(DiagnosticSession.run_at.desc()).first()
        valuation = Valuation.query.filter_by(
            startup_id=case.startup_id
        ).order_by(Valuation.run_at.desc()).first()
        summary = generate_due_diligence_summary(case, case.startup, diagnostics, valuation)
    
    return jsonify({
        "msg": f"Verification {new_status}",
        "verification": case.to_dict(),
        "due_diligence_summary": summary
    }), 200

@verification_bp.route('/<int:startup_id>/badge', methods=['GET'])
def get_verification_badge(startup_id):
    """FR-42 / US-44: Public endpoint for badge status (no auth required)"""
    startup = Startup.query.get_or_404(startup_id)
    
    # Get latest verified case with valid badge
    latest = VerificationCase.query.filter_by(
        startup_id=startup_id,
        status='verified',
        badge_issued=True
    ).order_by(VerificationCase.reviewed_at.desc()).first()
    
    if not latest or (latest.badge_valid_until and latest.badge_valid_until < db.func.now()):
        return jsonify({"verified": False}), 200
    
    return jsonify({
        "verified": True,
        "badge_text": "Verified by Agrico Hub",
        "valid_until": latest.badge_valid_until.isoformat() if latest.badge_valid_until else None,
        "verified_at": latest.reviewed_at.isoformat()
    }), 200

@verification_bp.route('/<int:startup_id>/due-diligence', methods=['GET'])
@jwt_required()
def get_due_diligence_summary(startup_id):
    """FR-43 / US-45: Generate/download due diligence summary"""
    user_id = int(get_jwt_identity())
    _check_startup_ownership(startup_id, user_id)
    
    # Get latest verified case
    case = VerificationCase.query.filter_by(
        startup_id=startup_id,
        status='verified'
    ).order_by(VerificationCase.reviewed_at.desc()).first()
    
    if not case or not case.badge_issued:
        return jsonify({"msg": "Startup must be verified to generate due diligence summary"}), 400
    
    diagnostics = DiagnosticSession.query.filter_by(
        startup_id=startup_id
    ).order_by(DiagnosticSession.run_at.desc()).first()
    valuation = Valuation.query.filter_by(
        startup_id=startup_id
    ).order_by(Valuation.run_at.desc()).first()
    
    summary = generate_due_diligence_summary(case, case.startup, diagnostics, valuation)
    
    return jsonify({
        "msg": "Due diligence summary generated",
        "summary": summary,
        "download_url": f"/api/verification/{case.id}/download.pdf"  # Stub for PDF generation
    }), 200