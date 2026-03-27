"""
Program & Cohort Management services for FR-50 to FR-52.
"""

from datetime import datetime
from app.extensions import db
from app.models import Program, Cohort, CohortEnrollment, ProgramMilestone, Startup


def get_program_dashboard(program_id: int) -> dict:
    """
    FR-90: Get program dashboard with stats.
    """
    program = Program.query.get(program_id)
    if not program:
        return None
    
    cohorts = Cohort.query.filter_by(program_id=program_id).all()
    
    total_startups = 0
    active_startups = 0
    graduated_startups = 0
    
    for cohort in cohorts:
        enrollments = CohortEnrollment.query.filter_by(cohort_id=cohort.id).all()
        total_startups += len(enrollments)
        active_startups += len([e for e in enrollments if e.status in ['pending', 'accepted']])
        graduated_startups += len([e for e in enrollments if e.status == 'graduated'])
    
    return {
        'program': program.to_dict(),
        'stats': {
            'total_cohorts': len(cohorts),
            'total_startups': total_startups,
            'active_startups': active_startups,
            'graduated_startups': graduated_startups,
            'completion_rate': round(graduated_startups / total_startups * 100, 1) if total_startups > 0 else 0
        },
        'cohorts': [c.to_dict() for c in cohorts]
    }


def enroll_startup_in_cohort(cohort_id: int, startup_id: int) -> dict:
    """
    FR-51: Enroll a startup in a cohort.
    """
    # Check for existing enrollment
    existing = CohortEnrollment.query.filter_by(
        cohort_id=cohort_id,
        startup_id=startup_id
    ).first()
    
    if existing:
        return {
            'success': False,
            'error': 'Startup already enrolled in this cohort',
            'enrollment_id': existing.id
        }
    
    # Check cohort capacity
    cohort = Cohort.query.get(cohort_id)
    if not cohort:
        return {'success': False, 'error': 'Cohort not found'}
    
    current_enrollments = CohortEnrollment.query.filter_by(
        cohort_id=cohort_id,
        status='accepted'
    ).count()
    
    if current_enrollments >= cohort.max_startups:
        return {'success': False, 'error': 'Cohort is at capacity'}
    
    # Create enrollment
    enrollment = CohortEnrollment(
        cohort_id=cohort_id,
        startup_id=startup_id,
        status='pending',  # Requires admin approval
        milestones_completed=[]
    )
    
    db.session.add(enrollment)
    db.session.commit()
    
    return {
        'success': True,
        'enrollment_id': enrollment.id,
        'status': 'pending',
        'message': 'Enrollment request submitted. Awaiting admin approval.'
    }


def update_enrollment_status(enrollment_id: int, status: str, admin_notes: str = None) -> dict:
    """
    FR-51: Admin approves/rejects enrollment.
    """
    enrollment = CohortEnrollment.query.get(enrollment_id)
    if not enrollment:
        return {'success': False, 'error': 'Enrollment not found'}
    
    if status not in ['pending', 'accepted', 'rejected', 'withdrawn', 'graduated']:
        return {'success': False, 'error': 'Invalid status'}
    
    enrollment.status = status
    if admin_notes:
        enrollment.admin_notes = admin_notes
    
    db.session.commit()
    
    return {
        'success': True,
        'enrollment_id': enrollment_id,
        'status': status,
        'message': f'Enrollment {status}'
    }


def update_milestone_progress(enrollment_id: int, milestone_id: int, completed: bool = True) -> dict:
    """
    FR-52: Track milestone completion for a startup.
    """
    enrollment = CohortEnrollment.query.get(enrollment_id)
    if not enrollment:
        return {'success': False, 'error': 'Enrollment not found'}
    
    milestone = ProgramMilestone.query.get(milestone_id)
    if not milestone or milestone.program_id != enrollment.cohort.program_id:
        return {'success': False, 'error': 'Invalid milestone for this program'}
    
    # Get current milestones
    milestones = enrollment.milestones_completed or []
    
    if completed:
        if milestone_id not in milestones:
            milestones.append(milestone_id)
    else:
        if milestone_id in milestones:
            milestones.remove(milestone_id)
    
    enrollment.milestones_completed = milestones
    
    # Calculate overall progress
    all_milestones = ProgramMilestone.query.filter_by(
        program_id=enrollment.cohort.program_id
    ).all()
    
    required_milestones = [m for m in all_milestones if m.is_required]
    completed_required = len([m for m in required_milestones if m.id in milestones])
    
    enrollment.overall_progress = round(
        completed_required / len(required_milestones) * 100
    ) if required_milestones else 0
    
    # Auto-graduate if 100% complete
    if enrollment.overall_progress >= 100 and enrollment.status != 'graduated':
        enrollment.status = 'graduated'
    
    db.session.commit()
    
    return {
        'success': True,
        'enrollment_id': enrollment_id,
        'overall_progress': enrollment.overall_progress,
        'status': enrollment.status,
        'milestones_completed': milestones
    }


def check_milestone_auto_complete(startup_id: int, program_id: int) -> list:
    """
    FR-52: Check if any milestones should be auto-completed based on platform activity.
    Call this when user completes documents, valuations, etc.
    
    Returns:
        List of milestone IDs that were auto-completed
    """
    auto_completed = []
    
    # Get all enrollments for this startup in this program
    enrollments = CohortEnrollment.query.join(Cohort).filter(
        Cohort.program_id == program_id,
        CohortEnrollment.startup_id == startup_id,
        CohortEnrollment.status.in_(['pending', 'accepted'])
    ).all()
    
    for enrollment in enrollments:
        milestones = ProgramMilestone.query.filter_by(
            program_id=program_id,
            is_required=True
        ).all()
        
        for milestone in milestones:
            if milestone.linked_feature and milestone.id not in (enrollment.milestones_completed or []):
                # Check if feature is completed
                is_complete = False
                
                if milestone.linked_feature == 'document':
                    from app.models import BusinessDocument
                    count = BusinessDocument.query.filter_by(
                        startup_id=startup_id,
                        doc_type=milestone.linked_feature_id
                    ).count()
                    is_complete = count > 0
                    
                elif milestone.linked_feature == 'valuation':
                    from app.models import Valuation
                    count = Valuation.query.filter_by(
                        startup_id=startup_id
                    ).count()
                    is_complete = count > 0
                    
                elif milestone.linked_feature == 'diagnostic':
                    from app.models import DiagnosticSession
                    count = DiagnosticSession.query.filter_by(
                        startup_id=startup_id
                    ).count()
                    is_complete = count > 0
                    
                elif milestone.linked_feature == 'verification':
                    from app.models import VerificationCase
                    verification = VerificationCase.query.filter_by(
                        startup_id=startup_id,
                        status='verified'
                    ).first()
                    is_complete = verification is not None
                
                if is_complete:
                    update_milestone_progress(enrollment.id, milestone.id, completed=True)
                    auto_completed.append(milestone.id)
    
    return auto_completed