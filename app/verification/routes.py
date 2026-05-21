# app/verification/routes.py
"""
FR-40 to FR-44: Verification Module REST API
Endpoints for document submission, reviewer queue, decisions, and badge status.
"""

import os
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import VerificationCase, Startup, User, DocumentShare
from app.verification.utils import (
    validate_document_type, validate_file_upload, 
    generate_secure_filename, get_document_category_requirements,
    ALLOWED_DOCUMENT_TYPES, MAX_FILE_SIZE_MB
)
from app.verification.services import (
    process_verification_decision, get_verification_queue,
    calculate_verification_completeness, assign_reviewer
)

verification_bp = Blueprint('verification', __name__)

def _check_startup_ownership(startup_id, user_id):
    """Helper: verify user owns the startup"""
    startup = Startup.query.get(startup_id)
    if not startup or int(startup.owner_user_id) != int(user_id):
        return False
    return True

def _check_reviewer_role(user_id):
    """Helper: verify user has Program Manager or System Admin role"""
    user = User.query.get(user_id)
    return user and user.role in ['Program Manager', 'System Admin']

@verification_bp.route('/categories', methods=['GET'])
@jwt_required()
def list_document_categories():
    """
    FR-40: List available document categories with requirements
    """
    categories = []
    for category in ALLOWED_DOCUMENT_TYPES.keys():
        reqs = get_document_category_requirements(category)
        categories.append({
            "id": category,
            "name": category.replace('_', ' ').title(),
            "description": reqs["info"].get("description", ""),
            "required": reqs["info"].get("required_for_verification", False),
            "allowed_types": reqs["allowed_types"],
            "notes": reqs["info"].get("notes", "")
        })
    
    return jsonify({"categories": categories}), 200

@verification_bp.route('/<int:startup_id>/submit', methods=['POST'])
@jwt_required()
def submit_verification_documents(startup_id):
    """
    FR-40: Submit documents for verification review
    Handles file upload, validation, and case creation
    """
    current_user_id = int(get_jwt_identity())
    
    # Verify startup ownership
    if not _check_startup_ownership(startup_id, current_user_id):
        return jsonify({"msg": "Access denied"}), 403
    
    # Check if case already exists for this startup
    existing_case = VerificationCase.query.filter_by(
        startup_id=startup_id, status='pending'
    ).first()
    if existing_case:
        return jsonify({
            "msg": "Verification case already pending",
            "case_id": existing_case.id,
            "status": existing_case.status
        }), 409  # Conflict
    
    # Parse form data (multipart/form-data for file uploads)
    if 'documents' not in request.files:
        return jsonify({"msg": "No documents uploaded"}), 400
    
    files = request.files.getlist('documents')
    document_metadata = request.form.get('document_metadata', '[]')  # JSON string
    
    try:
        import json
        metadata_list = json.loads(document_metadata)
    except:
        metadata_list = []
    
    # Validate and process each file
    uploaded_docs = []
    for i, file in enumerate(files):
        # Validate file
        is_valid, error_msg = validate_file_upload(file)
        if not is_valid:
            return jsonify({"msg": f"File {i+1} invalid: {error_msg}"}), 400
        
        # Get metadata for this file
        file_meta = metadata_list[i] if i < len(metadata_list) else {}
        category = file_meta.get('category', 'operational')
        doc_name = file_meta.get('name', file.filename)
        
        # Validate document type matches category
        if not validate_document_type(category, doc_name):
            return jsonify({
                "msg": f"Document '{doc_name}' doesn't match category '{category}'",
                "allowed_types": ALLOWED_DOCUMENT_TYPES.get(category, [])
            }), 400
        
        # Generate secure filename and save (in production: use S3/cloud storage)
        secure_name = generate_secure_filename(file.filename)
        upload_dir = os.path.join('instance', 'verification_uploads', str(startup_id))
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, secure_name)
        file.save(file_path)
        
        uploaded_docs.append({
            "category": category,
            "original_name": doc_name,
            "stored_name": secure_name,
            "file_path": file_path,
            "uploaded_at": datetime.utcnow().isoformat()
        })
    
    # Create verification case
    case = VerificationCase(
        startup_id=startup_id,
        status='pending',
        documents_submitted=[d['category'] for d in uploaded_docs],  # Store categories for quick filtering
        submitted_at=datetime.utcnow()
    )
    
    # Store detailed document info in review_notes (JSON) for audit trail
    import json
    case.review_notes = json.dumps({
        "documents": uploaded_docs,
        "submission_metadata": {
            "submitted_by": current_user_id,
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get('User-Agent')
        }
    })
    
    db.session.add(case)
    db.session.commit()
    
    # Auto-assign reviewer if enabled
    assign_reviewer(case.id)
    
    # Calculate completeness for response
    required_categories = [cat for cat, info in [
        (cat, get_document_category_requirements(cat)["info"]) 
        for cat in ALLOWED_DOCUMENT_TYPES.keys()
    ] if info.get("required_for_verification", False)]
    
    completeness = calculate_verification_completeness(
        [d['category'] for d in uploaded_docs], 
        required_categories
    )
    
    return jsonify({
        "msg": "Documents submitted for verification",
        "case_id": case.id,
        "status": case.status,
        "completeness": completeness,
        "next_steps": [
            "Reviewers will assess within 3-5 business days",
            "You'll receive email notification of decision",
            "Check status at /api/verification/<case_id>"
        ]
    }), 201

@verification_bp.route('/queue', methods=['GET'])
@jwt_required()
def get_reviewer_queue():
    """
    FR-42: Get pending verification cases for Program Manager review
    Requires Program Manager or System Admin role
    """
    current_user_id = int(get_jwt_identity())
    
    # Check reviewer role
    if not _check_reviewer_role(current_user_id):
        return jsonify({"msg": "Access denied: Program Manager role required"}), 403
    
    # Parse filters from query params
    filters = {}
    if request.args.get('stage'):
        filters['startup_stage'] = request.args.get('stage')
    if request.args.get('status'):
        filters['status'] = request.args.get('status')
    
    # Get prioritized queue
    queue = get_verification_queue(filters)
    
    return jsonify({
        "queue": queue,
        "count": len(queue),
        "filters_applied": filters
    }), 200

@verification_bp.route('/<int:case_id>/decide', methods=['POST'])
@jwt_required()
def record_verification_decision(case_id):
    """
    FR-43: Record verification decision with audit trail
    Requires Program Manager or System Admin role
    """
    current_user_id = int(get_jwt_identity())
    
    # Check reviewer role
    if not _check_reviewer_role(current_user_id):
        return jsonify({"msg": "Access denied: Program Manager role required"}), 403
    
    data = request.get_json()
    
    # Validate required fields
    if 'decision' not in data or 'review_notes' not in data:
        return jsonify({"msg": "Missing required fields: decision, review_notes"}), 400
    
    # Process decision
    result = process_verification_decision(
        case_id=case_id,
        decision=data['decision'],
        review_notes=data['review_notes'],
        reviewer_id=current_user_id
    )
    
    if result.get('error'):
        return jsonify({"msg": result['error']}), 400
    
    return jsonify({
        "msg": "Verification decision recorded",
        "result": result
    }), 200

@verification_bp.route('/<int:case_id>', methods=['GET'])
@jwt_required()
def get_verification_status(case_id):
    """
    FR-43: Get verification case status and details
    Accessible by startup owner or assigned reviewer
    """
    current_user_id = int(get_jwt_identity())
    case = VerificationCase.query.get_or_404(case_id)
    
    # Check access: owner or assigned reviewer or admin
    is_owner = _check_startup_ownership(case.startup_id, current_user_id)
    is_reviewer = case.reviewer_id == current_user_id
    is_admin = _check_reviewer_role(current_user_id)
    
    if not (is_owner or is_reviewer or is_admin):
        return jsonify({"msg": "Access denied"}), 403
    
    # Build response (hide sensitive reviewer notes from startup owner)
    response = {
        "case": {
            "id": case.id,
            "startup_id": case.startup_id,
            "status": case.status,
            "submitted_at": case.submitted_at.isoformat() if case.submitted_at else None,
            "reviewed_at": case.reviewed_at.isoformat() if case.reviewed_at else None,
            "badge_issued": case.badge_issued,
            "documents_submitted": case.documents_submitted
        }
    }
    
    # Include reviewer notes only for reviewers/admins
    if is_reviewer or is_admin:
        response["case"]["review_notes"] = case.review_notes
        response["case"]["reviewer_id"] = case.reviewer_id
    
    # If approved, include badge info
    if case.badge_issued and case.status in ['approved', 'approved_with_conditions']:
        response["badge"] = {
            "text": "Verified by Agrico Hub",
            "issued_at": case.reviewed_at.isoformat() if case.reviewed_at else None,
            "valid_until": (case.reviewed_at + timedelta(days=365)).isoformat() if case.reviewed_at else None
        }
    
    return jsonify(response), 200

@verification_bp.route('/badge/<int:startup_id>', methods=['GET'])
def get_verification_badge(startup_id):
    """
    FR-44: Public endpoint to check verification badge status
    No auth required - used by investor portal to display badge
    """
    # Get most recent completed verification case for startup
    case = VerificationCase.query.filter_by(
        startup_id=startup_id
    ).filter(
        VerificationCase.status.in_(['approved', 'approved_with_conditions', 'rejected'])
    ).order_by(VerificationCase.reviewed_at.desc()).first()
    
    if not case or not case.badge_issued:
        return jsonify({
            "verified": False,
            "badge": None,
            "message": "Not verified by Agrico Hub"
        }), 200
    
    # Return public badge info
    return jsonify({
        "verified": True,
        "badge": {
            "text": "Verified by Agrico Hub",
            "verified_at": case.reviewed_at.isoformat() if case.reviewed_at else None,
            "valid_until": (case.reviewed_at + timedelta(days=365)).isoformat() if case.reviewed_at else None,
            "verification_level": case.status  # approved vs approved_with_conditions
        },
        "startup_id": startup_id
    }), 200

@verification_bp.route('/<int:startup_id>/resubmit', methods=['POST'])
@jwt_required()
def resubmit_verification_documents(startup_id):
    """
    FR-43: Allow resubmission after rejection or request for more info
    Creates new case or updates existing rejected case
    """
    current_user_id = int(get_jwt_identity())
    
    if not _check_startup_ownership(startup_id, current_user_id):
        return jsonify({"msg": "Access denied"}), 403
    
    # Find existing case (rejected or pending_more_info)
    existing_case = VerificationCase.query.filter_by(
        startup_id=startup_id
    ).filter(
        VerificationCase.status.in_(['rejected', 'pending_more_info'])
    ).order_by(VerificationCase.reviewed_at.desc()).first()
    
    if not existing_case:
        return jsonify({
            "msg": "No eligible case for resubmission. Submit new verification first."
        }), 400
    
    # For simplicity, create new case on resubmit (could update existing in production)
    # Reuse the submit logic but link to original case for audit trail
    return submit_verification_documents(startup_id)