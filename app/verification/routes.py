from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import VerificationCase, Startup, User
from app.verification.services import (
    create_verification_case,
    review_verification_case,
    VERIFICATION_STATUSES
)

verification_bp = Blueprint('verification', __name__)

@verification_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit_verification():
    """
    FR-40: Startup submits verification documents.
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Validate required fields
    if 'startup_id' not in data:
        return jsonify({"msg": "startup_id is required"}), 400
    
    if 'documents' not in data or not data['documents']:
        return jsonify({"msg": "At least one document must be submitted"}), 400
    
    # Verify startup ownership
    startup = Startup.query.get(data['startup_id'])
    if not startup or startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    # Check if there's already a pending/active verification
    existing = VerificationCase.query.filter_by(
        startup_id=data['startup_id'],
        status='pending'
    ).first()
    if existing:
        return jsonify({"msg": "You already have a pending verification submission"}), 400
    
    # Create verification case
    result = create_verification_case(data['startup_id'], data['documents'])
    
    if not result['success']:
        return jsonify({"msg": result['error']}), 400
    
    # Save to database
    case = VerificationCase(
        startup_id=data['startup_id'],
        documents_submitted=data['documents'],
        status=result['status'],
        badge_issued=result['badge_issued']
    )
    
    db.session.add(case)
    db.session.commit()
    
    return jsonify({
        "msg": "Verification submitted successfully",
        "case_id": case.id,
        "status": case.status,
        "completeness_score": result['completeness_score'],
        "recommendations": result['recommendations']
    }), 201

@verification_bp.route('/status', methods=['GET'])
@jwt_required()
def get_verification_status():
    """FR-42: Get current verification status for a startup"""
    current_user_id = int(get_jwt_identity())
    startup_id = request.args.get('startup_id', type=int)
    
    if not startup_id:
        return jsonify({"msg": "startup_id query parameter is required"}), 400
    
    # Verify startup ownership
    startup = Startup.query.get(startup_id)
    if not startup or startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    # Get latest verification case
    case = VerificationCase.query.filter_by(
        startup_id=startup_id
    ).order_by(VerificationCase.submitted_at.desc()).first()
    
    if not case:
        return jsonify({
            "verified": False,
            "status": "not_submitted",
            "badge_issued": False
        }), 200
    
    return jsonify({
        "verified": case.status == 'verified',
        "status": case.status,
        "badge_issued": case.badge_issued,
        "submitted_at": case.submitted_at.isoformat() if case.submitted_at else None,
        "reviewed_at": case.reviewed_at.isoformat() if case.reviewed_at else None,
        "case_id": case.id
    }), 200

@verification_bp.route('/<int:case_id>', methods=['GET'])
@jwt_required()
def get_verification_case(case_id):
    """Get details of a specific verification case"""
    current_user_id = int(get_jwt_identity())
    case = VerificationCase.query.get_or_404(case_id)
    
    # Verify access: user must own the startup
    if case.startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    return jsonify({"case": case.to_dict()}), 200

# ============================================================================
# PROGRAM MANAGER / ADMIN ENDPOINTS (FR-41: Verification Workflows)
# ============================================================================

@verification_bp.route('/admin/queue', methods=['GET'])
@jwt_required()
def get_verification_queue():
    """
    FR-41: Program Managers see queue of startups awaiting verification.
    Requires role: Program Manager or Admin
    """
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    # Check role (only Program Manager or Admin can access)
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied. Program Manager role required."}), 403
    
    # Get all pending/in_review cases
    cases = VerificationCase.query.filter(
        VerificationCase.status.in_(['pending', 'in_review'])
    ).order_by(VerificationCase.submitted_at.asc()).all()
    
    return jsonify({
        "queue": [
            {
                "case_id": c.id,
                "startup_id": c.startup_id,
                "startup_name": c.startup.name,
                "status": c.status,
                "submitted_at": c.submitted_at.isoformat() if c.submitted_at else None,
                "completeness_score": len(c.documents_submitted) * 10  # Simple score
            }
            for c in cases
        ],
        "count": len(cases)
    }), 200

@verification_bp.route('/admin/<int:case_id>/review', methods=['POST'])
@jwt_required()
def review_verification(case_id):
    """
    FR-41: Program Manager reviews and makes decision on verification case.
    Audit trail stored per Spec 6.4 Security.
    """
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    # Check role
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied. Program Manager role required."}), 403
    
    data = request.get_json()
    
    # Validate required fields
    if 'decision' not in data:
        return jsonify({"msg": "decision is required ('verified' or 'rejected')"}), 400
    
    if data['decision'] not in ['verified', 'rejected']:
        return jsonify({"msg": "decision must be 'verified' or 'rejected'"}), 400
    
    if 'notes' not in data or not data['notes'].strip():
        return jsonify({"msg": "Review notes are required for audit trail"}), 400
    
    # Get the case
    case = VerificationCase.query.get_or_404(case_id)
    
    # Update case
    case.status = data['decision']
    case.reviewer_id = current_user_id
    case.review_notes = data['notes']
    case.rejection_reason = data.get('rejection_reason')
    case.reviewed_at = db.func.now()
    case.badge_issued = data['decision'] == 'verified'
    
    if data['decision'] == 'verified':
        case.verified_at = db.func.now()
    
    db.session.commit()
    
    return jsonify({
        "msg": f"Verification {data['decision']} successfully",
        "case_id": case.id,
        "status": case.status,
        "badge_issued": case.badge_issued,
        "reviewer": current_user.name
    }), 200

@verification_bp.route('/admin/stats', methods=['GET'])
@jwt_required()
def get_verification_stats():
    """FR-90: Admin dashboard - verification statistics"""
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    # Check role
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    # Calculate stats
    total = VerificationCase.query.count()
    pending = VerificationCase.query.filter_by(status='pending').count()
    in_review = VerificationCase.query.filter_by(status='in_review').count()
    verified = VerificationCase.query.filter_by(status='verified').count()
    rejected = VerificationCase.query.filter_by(status='rejected').count()
    
    return jsonify({
        "total": total,
        "pending": pending,
        "in_review": in_review,
        "verified": verified,
        "rejected": rejected,
        "verification_rate": round(verified / total * 100, 1) if total > 0 else 0
    }), 200