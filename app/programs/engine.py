# app/programs/engine.py
from app.models import DiagnosticSession, Valuation, VerificationCase, BusinessDocument

def calculate_startup_progress(startup):
    """FR-51: Aggregate progress across all modules for cohort dashboard"""
    milestones = [
        ("profile", startup.profile_completion >= 80, 15),
        ("diagnostic", DiagnosticSession.query.filter_by(startup_id=startup.id).first() is not None, 20),
        ("documents", BusinessDocument.query.filter_by(startup_id=startup.id, status='Ready').first() is not None, 20),
        ("valuation", Valuation.query.filter_by(startup_id=startup.id).first() is not None, 15),
        ("verification_submitted", VerificationCase.query.filter_by(startup_id=startup.id).first() is not None, 15),
        ("verification_verified", VerificationCase.query.filter_by(startup_id=startup.id, status='verified', badge_issued=True).first() is not None, 15),
    ]
    progress = sum(weight for _, completed, weight in milestones if completed)
    return min(100, progress)


def get_milestone_completion(startup, program_milestones):
    """FR-52: Check which program milestones a startup has completed"""
    completed = []
    for milestone in program_milestones:
        if milestone.linked_feature == 'document':
            has_doc = BusinessDocument.query.filter_by(
                startup_id=startup.id, 
                template_id=milestone.linked_feature_id,
                status='Ready'
            ).first() is not None
            if has_doc:
                completed.append(milestone.id)
        elif milestone.linked_feature == 'diagnostic':
            has_diag = DiagnosticSession.query.filter_by(startup_id=startup.id).first() is not None
            if has_diag:
                completed.append(milestone.id)
        elif milestone.linked_feature == 'valuation':
            has_val = Valuation.query.filter_by(startup_id=startup.id).first() is not None
            if has_val:
                completed.append(milestone.id)
        elif milestone.linked_feature == 'verification':
            has_verif = VerificationCase.query.filter_by(startup_id=startup.id, status='verified').first() is not None
            if has_verif:
                completed.append(milestone.id)
    return completed