"""
Program & Cohort Management Routes (FR-50 to FR-52)
- Program creation & management (FR-50)
- Cohort enrollment (FR-51)
- Progress tracking & graduation (FR-52)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Program, Cohort, CohortEnrollment, ProgramMilestone, Startup, User
from app.programs.services import (
    get_program_dashboard,
    enroll_startup_in_cohort,
    update_enrollment_status,
    update_milestone_progress,
    check_milestone_auto_complete
)

programs_bp = Blueprint('programs', __name__)

# ============================================================================
# PUBLIC ENDPOINTS (No Auth Required)
# ============================================================================

@programs_bp.route('', methods=['GET'])
def list_programs():
    """
    FR-50: List all active programs (public view).
    """
    programs = Program.query.filter_by(status='active').all()
    
    return jsonify({
        "programs": [p.to_dict() for p in programs],
        "count": len(programs)
    }), 200

@programs_bp.route('/<int:program_id>', methods=['GET'])
def get_program_details(program_id):
    """
    FR-50: Get program details with cohorts.
    """
    program = Program.query.get_or_404(program_id)
    
    cohorts = Cohort.query.filter_by(
        program_id=program_id,
        status='active'
    ).all()
    
    return jsonify({
        "program": program.to_dict(),
        "cohorts": [c.to_dict() for c in cohorts]
    }), 200

# ============================================================================
# ADMIN ENDPOINTS (Program Manager / System Admin)
# ============================================================================

@programs_bp.route('/admin', methods=['POST'])
@jwt_required()
def create_program():
    """
    FR-50: Admin creates a new program.
    """
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    data = request.get_json()
    
    # Validate required fields
    required = ['name', 'start_date', 'end_date']
    for field in required:
        if field not in data:
            return jsonify({"msg": f"{field} is required"}), 400
    
    from datetime import datetime
    program = Program(
        name=data['name'],
        description=data.get('description'),
        start_date=datetime.fromisoformat(data['start_date']),
        end_date=datetime.fromisoformat(data['end_date']),
        status=data.get('status', 'active'),
        max_cohorts=data.get('max_cohorts', 1),
        max_startups_per_cohort=data.get('max_startups_per_cohort', 20)
    )
    
    db.session.add(program)
    db.session.commit()
    
    return jsonify({
        "msg": "Program created successfully",
        "program": program.to_dict()
    }), 201

@programs_bp.route('/admin/<int:program_id>/dashboard', methods=['GET'])
@jwt_required()
def get_admin_dashboard(program_id):
    """
    FR-90: Admin dashboard for program statistics.
    """
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    dashboard = get_program_dashboard(program_id)
    
    if not dashboard:
        return jsonify({"msg": "Program not found"}), 404
    
    return jsonify(dashboard), 200

@programs_bp.route('/admin/cohorts', methods=['POST'])
@jwt_required()
def create_cohort():
    """
    FR-50: Admin creates a new cohort within a program.
    """
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    data = request.get_json()
    
    # Validate required fields
    required = ['program_id', 'name', 'start_date', 'end_date']
    for field in required:
        if field not in data:
            return jsonify({"msg": f"{field} is required"}), 400
    
    from datetime import datetime
    cohort = Cohort(
        program_id=data['program_id'],
        name=data['name'],
        description=data.get('description'),
        start_date=datetime.fromisoformat(data['start_date']),
        end_date=datetime.fromisoformat(data['end_date']),
        status=data.get('status', 'active'),
        max_startups=data.get('max_startups', 20)
    )
    
    db.session.add(cohort)
    db.session.commit()
    
    return jsonify({
        "msg": "Cohort created successfully",
        "cohort": cohort.to_dict()
    }), 201

@programs_bp.route('/admin/enrollments/<int:enrollment_id>/status', methods=['PUT'])
@jwt_required()
def admin_update_enrollment(enrollment_id):
    """
    FR-51: Admin approves/rejects enrollment.
    """
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    data = request.get_json()
    
    if 'status' not in data:
        return jsonify({"msg": "status is required"}), 400
    
    result = update_enrollment_status(
        enrollment_id,
        data['status'],
        admin_notes=data.get('admin_notes')
    )
    
    if not result['success']:
        return jsonify({"msg": result['error']}), 400
    
    return jsonify(result), 200

@programs_bp.route('/admin/milestones', methods=['POST'])
@jwt_required()
def create_milestone():
    """
    FR-52: Admin creates a program milestone.
    """
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    data = request.get_json()
    
    # Validate required fields
    required = ['program_id', 'name', 'order']
    for field in required:
        if field not in data:
            return jsonify({"msg": f"{field} is required"}), 400
    
    milestone = ProgramMilestone(
        program_id=data['program_id'],
        name=data['name'],
        description=data.get('description'),
        order=data['order'],
        is_required=data.get('is_required', True),
        linked_feature=data.get('linked_feature'),
        linked_feature_id=data.get('linked_feature_id')
    )
    
    db.session.add(milestone)
    db.session.commit()
    
    return jsonify({
        "msg": "Milestone created successfully",
        "milestone": milestone.to_dict()
    }), 201

# ============================================================================
# STARTUP ENDPOINTS (Auth Required - Startup Founder)
# ============================================================================

@programs_bp.route('/enroll', methods=['POST'])
@jwt_required()
def enroll_in_cohort():
    """
    FR-51: Startup applies to join a cohort.
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if 'cohort_id' not in data:
        return jsonify({"msg": "cohort_id is required"}), 400
    
    if 'startup_id' not in data:
        return jsonify({"msg": "startup_id is required"}), 400
    
    # Verify startup ownership
    startup = Startup.query.get(data['startup_id'])
    if not startup or startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    result = enroll_startup_in_cohort(data['cohort_id'], data['startup_id'])
    
    if not result['success']:
        return jsonify({"msg": result['error']}), 400
    
    return jsonify(result), 201

@programs_bp.route('/my-enrollments', methods=['GET'])
@jwt_required()
def get_my_enrollments():
    """
    FR-51: Get all cohort enrollments for user's startups.
    """
    current_user_id = int(get_jwt_identity())
    
    # Get all startups owned by user
    startups = Startup.query.filter_by(owner_user_id=current_user_id).all()
    startup_ids = [s.id for s in startups]
    
    # Get all enrollments for these startups
    enrollments = CohortEnrollment.query.filter(
        CohortEnrollment.startup_id.in_(startup_ids)
    ).all()
    
    return jsonify({
        "enrollments": [e.to_dict() for e in enrollments],
        "count": len(enrollments)
    }), 200

@programs_bp.route('/enrollments/<int:enrollment_id>/progress', methods=['GET'])
@jwt_required()
def get_enrollment_progress(enrollment_id):
    """
    FR-52: Get progress for a specific enrollment.
    """
    current_user_id = int(get_jwt_identity())
    enrollment = CohortEnrollment.query.get_or_404(enrollment_id)
    
    # Verify startup ownership
    if enrollment.startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    # Get program milestones
    milestones = ProgramMilestone.query.filter_by(
        program_id=enrollment.cohort.program_id
    ).order_by(ProgramMilestone.order).all()
    
    completed_ids = enrollment.milestones_completed or []
    
    return jsonify({
        "enrollment": {
            "id": enrollment.id,
            "cohort_name": enrollment.cohort.name,
            "status": enrollment.status,
            "overall_progress": enrollment.overall_progress
        },
        "milestones": [
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "is_required": m.is_required,
                "completed": m.id in completed_ids
            }
            for m in milestones
        ]
    }), 200

@programs_bp.route('/enrollments/<int:enrollment_id>/milestone', methods=['POST'])
@jwt_required()
def update_progress(enrollment_id):
    """
    FR-52: Manually mark a milestone as complete.
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    enrollment = CohortEnrollment.query.get_or_404(enrollment_id)
    
    # Verify startup ownership
    if enrollment.startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    if 'milestone_id' not in data:
        return jsonify({"msg": "milestone_id is required"}), 400
    
    result = update_milestone_progress(
        enrollment_id,
        data['milestone_id'],
        completed=data.get('completed', True)
    )
    
    if not result['success']:
        return jsonify({"msg": result['error']}), 400
    
    # Check for auto-complete opportunities
    auto_completed = check_milestone_auto_complete(
        enrollment.startup_id,
        enrollment.cohort.program_id
    )
    
    return jsonify({
        **result,
        "auto_completed_milestones": auto_completed
    }), 200