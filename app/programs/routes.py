# app/programs/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Program, Cohort, CohortEnrollment, Startup, User, ProgramMilestone
from app.programs.engine import calculate_startup_progress, get_milestone_completion

programs_bp = Blueprint('programs', __name__)

def _check_program_manager_permission(user_id):
    user = User.query.get_or_404(user_id)
    if user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied: Program Manager permissions required"}), 403
    return user

@programs_bp.route('/programs', methods=['GET'])
@jwt_required()
def list_programs():
    """FR-50: List available programs"""
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    
    # Program Managers and Admins see all; others see only active
    query = Program.query
    if user.role not in ['Program Manager', 'System Admin']:
        query = query.filter_by(status='active')
    
    programs = query.order_by(Program.start_date.desc()).all()
    return jsonify({
        "programs": [p.to_dict() for p in programs],
        "count": len(programs)
    }), 200

# app/programs/routes.py

# 🔹 ADD THIS IMPORT AT THE VERY TOP OF THE FILE (if not already present):
from datetime import datetime

# ... other imports ...

# 🔹 REPLACE THE ENTIRE create_cohort FUNCTION WITH THIS:
@programs_bp.route('/programs/<int:program_id>/cohorts', methods=['POST'])
@jwt_required()
def create_cohort(program_id):
    """FR-50 / US-50: Create a new cohort within a program"""
    user_id = int(get_jwt_identity())
    _check_program_manager_permission(user_id)
    
    program = Program.query.get_or_404(program_id)
    data = request.get_json()
    
    # Validate required fields
    required = ['name', 'start_date', 'end_date']
    for field in required:
        if field not in data:
            return jsonify({"msg": f"Missing required field: {field}"}), 400
    
    # 🔧 FIX: Parse ISO date strings to Python datetime objects
    try:
        # Handle 'Z' suffix for UTC compatibility
        start_str = data['start_date']
        end_str = data['end_date']
        
        # Replace 'Z' with '+00:00' for fromisoformat compatibility
        if start_str and start_str.endswith('Z'):
            start_str = start_str[:-1] + '+00:00'
        if end_str and end_str.endswith('Z'):
            end_str = end_str[:-1] + '+00:00'
        
        start_date = datetime.fromisoformat(start_str)
        end_date = datetime.fromisoformat(end_str)
    except (ValueError, AttributeError, KeyError) as e:
        return jsonify({
            "msg": f"Invalid date format. Use ISO 8601 (e.g., '2026-01-15T00:00:00Z'). Error: {str(e)}"
        }), 400
    
    # Check capacity
    existing_cohorts = Cohort.query.filter_by(program_id=program_id).count()
    if existing_cohorts >= program.max_cohorts:
        return jsonify({"msg": "Program has reached maximum cohort limit"}), 400
    
    # Create cohort WITH DATETIME OBJECTS (not strings!)
    new_cohort = Cohort(
        program_id=program_id,
        name=data['name'],
        description=data.get('description', ''),
        start_date=start_date,  # ← datetime object, NOT string
        end_date=end_date,      # ← datetime object, NOT string
        max_startups=data.get('max_startups', 20)
    )
    db.session.add(new_cohort)
    db.session.commit()
    
    return jsonify({
        "msg": "Cohort created successfully",
        "cohort": new_cohort.to_dict()
    }), 201

@programs_bp.route('/cohorts/<int:cohort_id>/assign', methods=['POST'])
@jwt_required()
def assign_startup_to_cohort(cohort_id):
    """FR-50 / US-51: Assign a startup to a cohort"""
    user_id = int(get_jwt_identity())
    _check_program_manager_permission(user_id)
    
    cohort = Cohort.query.get_or_404(cohort_id)
    data = request.get_json()
    
    startup_id = data.get('startup_id')
    if not startup_id:
        return jsonify({"msg": "Missing startup_id"}), 400
    
    startup = Startup.query.get_or_404(startup_id)
    
    # Check cohort capacity
    current_enrollments = CohortEnrollment.query.filter_by(cohort_id=cohort_id).count()
    if current_enrollments >= cohort.max_startups:
        return jsonify({"msg": "Cohort has reached maximum startup limit"}), 400
    
    # Check if already enrolled
    existing = CohortEnrollment.query.filter_by(cohort_id=cohort_id, startup_id=startup_id).first()
    if existing:
        return jsonify({"msg": "Startup already enrolled in this cohort"}), 400
    
    # Create enrollment
    enrollment = CohortEnrollment(
        cohort_id=cohort_id,
        startup_id=startup_id,
        status='accepted',  # Auto-accept for program manager assignments
        overall_progress=calculate_startup_progress(startup)
    )
    db.session.add(enrollment)
    db.session.commit()
    
    return jsonify({
        "msg": "Startup assigned to cohort",
        "enrollment": enrollment.to_dict()
    }), 201

@programs_bp.route('/cohorts/<int:cohort_id>/dashboard', methods=['GET'])
@jwt_required()
def get_cohort_dashboard(cohort_id):
    """FR-51 / US-52: Aggregated progress metrics for cohort"""
    user_id = int(get_jwt_identity())
    _check_program_manager_permission(user_id)
    
    cohort = Cohort.query.get_or_404(cohort_id)
    enrollments = CohortEnrollment.query.filter_by(cohort_id=cohort_id).all()
    
    # Aggregate metrics
    total = len(enrollments)
    if total == 0:
        return jsonify({
            "cohort": cohort.to_dict(),
            "metrics": {
                "total_startups": 0,
                "avg_profile_completion": 0,
                "avg_diagnostic_score": None,
                "verified_count": 0,
                "valuations_run": 0,
                "documents_generated": 0
            }
        }), 200
    
    # Calculate aggregates
    profile_completions = [e.startup.profile_completion for e in enrollments if e.startup]
    diagnostic_scores = []
    verified_count = 0
    valuations_run = 0
    documents_generated = 0
    
    for e in enrollments:
        if not e.startup:
            continue
        # Diagnostic score
        from app.models import DiagnosticSession
        diag = DiagnosticSession.query.filter_by(startup_id=e.startup_id).order_by(DiagnosticSession.run_at.desc()).first()
        if diag:
            diagnostic_scores.append(diag.overall_score)
        # Verification
        from app.models import VerificationCase
        if VerificationCase.query.filter_by(startup_id=e.startup_id, status='verified', badge_issued=True).first():
            verified_count += 1
        # Valuations
        from app.models import Valuation
        if Valuation.query.filter_by(startup_id=e.startup_id).first():
            valuations_run += 1
        # Documents
        from app.models import BusinessDocument
        documents_generated += BusinessDocument.query.filter_by(startup_id=e.startup_id, status='Ready').count()
    
    metrics = {
        "total_startups": total,
        "avg_profile_completion": round(sum(profile_completions) / len(profile_completions), 1) if profile_completions else 0,
        "avg_diagnostic_score": round(sum(diagnostic_scores) / len(diagnostic_scores), 1) if diagnostic_scores else None,
        "verified_count": verified_count,
        "verified_percentage": round(verified_count / total * 100, 1),
        "valuations_run": valuations_run,
        "documents_generated": documents_generated
    }
    
    return jsonify({
        "cohort": cohort.to_dict(),
        "metrics": metrics
    }), 200

@programs_bp.route('/cohorts/<int:cohort_id>/startups', methods=['GET'])
@jwt_required()
def get_cohort_startups(cohort_id):
    """FR-51, FR-53 / US-53: List startups in cohort with progress indicators"""
    user_id = int(get_jwt_identity())
    _check_program_manager_permission(user_id)
    
    # Optional filters
    status = request.args.get('status')
    min_progress = request.args.get('min_progress', type=int)
    
    enrollments = CohortEnrollment.query.filter_by(cohort_id=cohort_id)
    if status:
        enrollments = enrollments.filter_by(status=status)
    
    enrollments = enrollments.order_by(CohortEnrollment.overall_progress.desc()).all()
    
    startups = []
    for e in enrollments:
        if not e.startup:
            continue
        # Recalculate progress if needed
        progress = calculate_startup_progress(e.startup)
        if progress != e.overall_progress:
            e.overall_progress = progress
            db.session.commit()
        
        # Filter by min_progress
        if min_progress and progress < min_progress:
            continue
            
        startups.append({
            "enrollment_id": e.id,
            "startup": e.startup.to_dict(),
            "enrollment_status": e.status,
            "overall_progress": progress,
            "milestones_completed": e.milestones_completed or [],
            "enrolled_at": e.enrolled_at.isoformat() if e.enrolled_at else None
        })
    
    return jsonify({
        "startups": startups,
        "count": len(startups)
    }), 200

@programs_bp.route('/cohorts/<int:cohort_id>/startups/<int:enrollment_id>/progress', methods=['PUT'])
@jwt_required()
def update_startup_progress(cohort_id, enrollment_id):
    """FR-52 / US-54: Update milestone completion for a startup in cohort"""
    user_id = int(get_jwt_identity())
    _check_program_manager_permission(user_id)
    
    enrollment = CohortEnrollment.query.get_or_404(enrollment_id)
    if enrollment.cohort_id != cohort_id:
        return jsonify({"msg": "Enrollment does not belong to this cohort"}), 400
    
    data = request.get_json()
    
    # Update milestones if provided
    if 'milestones_completed' in data:
        enrollment.milestones_completed = data['milestones_completed']
    
    # Recalculate overall progress
    if enrollment.startup:
        enrollment.overall_progress = calculate_startup_progress(enrollment.startup)
    
    # Optional admin notes
    if 'admin_notes' in data:
        enrollment.admin_notes = data['admin_notes']
    
    db.session.commit()
    
    return jsonify({
        "msg": "Progress updated",
        "enrollment": enrollment.to_dict()
    }), 200

@programs_bp.route('/programs/<int:program_id>/milestones', methods=['GET', 'POST'])
@jwt_required()
def manage_program_milestones(program_id):
    """FR-52 / US-54: List or create program milestones"""
    user_id = int(get_jwt_identity())
    _check_program_manager_permission(user_id)
    
    if request.method == 'GET':
        milestones = ProgramMilestone.query.filter_by(program_id=program_id).order_by(ProgramMilestone.order).all()
        return jsonify({
            "milestones": [m.to_dict() for m in milestones],
            "count": len(milestones)
        }), 200
    
    # POST: Create milestone
    data = request.get_json()
    required = ['name', 'order']
    for field in required:
        if field not in data:
            return jsonify({"msg": f"Missing required field: {field}"}), 400
    
    milestone = ProgramMilestone(
        program_id=program_id,
        name=data['name'],
        description=data.get('description', ''),
        order=data['order'],
        is_required=data.get('is_required', True),
        linked_feature=data.get('linked_feature'),
        linked_feature_id=data.get('linked_feature_id')
    )
    db.session.add(milestone)
    db.session.commit()
    
    return jsonify({
        "msg": "Milestone created",
        "milestone": milestone.to_dict()
    }), 201