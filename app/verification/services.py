# app/verification/services.py
"""
FR-42 + FR-43: Verification Queue Management + Decision Logic
Handles reviewer assignment, priority sorting, and audit trail recording.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.extensions import db
from app.models import VerificationCase, Startup, User

# Reviewer assignment rules (FR-42)
REVIEWER_ASSIGNMENT_RULES = {
    "auto_assign": True,  # Auto-assign to available Program Manager
    "priority_factors": {
        "stage": {"Maturity": 3, "Growth": 2, "Early": 1, "Ideation": 1},
        "completeness": {"high": 2, "medium": 1, "low": 0},
        "urgency": {"high": 3, "medium": 1, "low": 0}
    }
}

# Verification decision options (FR-43)
VERIFICATION_DECISIONS = {
    "approved": {
        "badge_issued": True,
        "badge_text": "Verified by Agrico Hub",
        "next_steps": ["Profile visible to investors", "Eligible for EP-08 discovery"]
    },
    "approved_with_conditions": {
        "badge_issued": True,
        "badge_text": "Verified (Conditional)",
        "next_steps": ["Address conditions within 30 days", "Re-review if conditions not met"]
    },
    "rejected": {
        "badge_issued": False,
        "badge_text": None,
        "next_steps": ["Address feedback and resubmit", "Contact support for guidance"]
    },
    "pending_more_info": {
        "badge_issued": False,
        "badge_text": None,
        "next_steps": ["Provide requested additional documents", "Respond to reviewer questions"]
    }
}

def calculate_case_priority(startup: Startup, completeness_score: float, urgency: str) -> int:
    """
    FR-42: Calculate priority score for reviewer queue sorting
    
    Args:
        startup: Startup object with stage attribute
        completeness_score: 0-100 score for submission completeness
        urgency: 'high', 'medium', or 'low'
    
    Returns:
        Priority score (higher = more urgent)
    """
    priority = 0
    
    # Stage factor
    stage = getattr(startup, 'stage', 'Ideation')
    priority += REVIEWER_ASSIGNMENT_RULES["priority_factors"]["stage"].get(stage, 1)
    
    # Completeness factor (convert to 0-2 scale)
    if completeness_score >= 80:
        priority += REVIEWER_ASSIGNMENT_RULES["priority_factors"]["completeness"]["high"]
    elif completeness_score >= 50:
        priority += REVIEWER_ASSIGNMENT_RULES["priority_factors"]["completeness"]["medium"]
    else:
        priority += REVIEWER_ASSIGNMENT_RULES["priority_factors"]["completeness"]["low"]
    
    # Urgency factor
    priority += REVIEWER_ASSIGNMENT_RULES["priority_factors"]["urgency"].get(urgency, 0)
    
    return priority

def assign_reviewer(case_id: int) -> Optional[int]:
    """
    FR-42: Auto-assign case to available Program Manager reviewer
    
    Args:
        case_id: VerificationCase ID
    
    Returns:
        Assigned reviewer user_id or None if no reviewers available
    """
    if not REVIEWER_ASSIGNMENT_RULES["auto_assign"]:
        return None
    
    # Find available Program Managers (role-based, not currently overloaded)
    # Simplified: just pick first available Program Manager
    reviewer = User.query.filter_by(role='Program Manager').first()
    
    if reviewer:
        case = VerificationCase.query.get(case_id)
        if case:
            case.reviewer_id = reviewer.id
            case.assigned_at = datetime.utcnow()
            db.session.commit()
            return reviewer.id
    
    return None

def process_verification_decision(case_id: int, decision: str, review_notes: str, reviewer_id: int) -> Dict:
    """
    FR-43: Record verification decision with full audit trail
    
    Args:
        case_id: VerificationCase ID
        decision: One of the keys in VERIFICATION_DECISIONS
        review_notes: Reviewer's detailed notes/feedback
        reviewer_id: ID of the reviewing user
    
    Returns:
        Dict with decision result and next steps
    """
    case = VerificationCase.query.get_or_404(case_id)
    
    # Validate decision
    if decision not in VERIFICATION_DECISIONS:
        return {"error": f"Invalid decision: {decision}. Available: {list(VERIFICATION_DECISIONS.keys())}"}
    
    decision_config = VERIFICATION_DECISIONS[decision]
    
    # Update case with decision
    case.status = decision
    case.review_notes = review_notes
    case.reviewer_id = reviewer_id
    case.reviewed_at = datetime.utcnow()
    case.badge_issued = decision_config["badge_issued"]
    
    # If approved, update startup profile completion (FR-44)
    if decision_config["badge_issued"] and case.startup:
        # Increase profile completion to reflect verified status
        current_completion = case.startup.profile_completion or 0
        case.startup.profile_completion = min(current_completion + 20, 100)  # Cap at 100%
    
    db.session.commit()
    
    return {
        "decision": decision,
        "badge_issued": decision_config["badge_issued"],
        "badge_text": decision_config["badge_text"],
        "next_steps": decision_config["next_steps"],
        "review_notes": review_notes,
        "reviewed_at": case.reviewed_at.isoformat() if case.reviewed_at else None
    }

def get_verification_queue(filters: Optional[Dict] = None) -> List[Dict]:
    """
    FR-42: Get pending verification cases for reviewer queue
    
    Args:
        filters: Optional dict with filter criteria (status, startup_stage, etc.)
    
    Returns:
        List of case summaries sorted by priority
    """
    # Base query: pending cases with startup info
    query = VerificationCase.query.filter_by(status='pending').join(Startup)
    
    # Apply filters
    if filters:
        if filters.get('status'):
            query = query.filter(VerificationCase.status == filters['status'])
        if filters.get('startup_stage'):
            query = query.filter(Startup.stage == filters['startup_stage'])
        if filters.get('submitted_after'):
            query = query.filter(VerificationCase.submitted_at >= filters['submitted_after'])
    
    # Get cases with startup info
    cases = query.order_by(VerificationCase.submitted_at.asc()).all()
    
    # Calculate priority and build response
    result = []
    for case in cases:
        startup = case.startup
        priority = calculate_case_priority(
            startup, 
            completeness_score=len(case.documents_submitted or []) * 20,  # Simple completeness metric
            urgency='medium'  # Could be user-set field
        )
        
        result.append({
            "case_id": case.id,
            "startup_name": startup.name if startup else "Unknown",
            "startup_stage": startup.stage if startup else "Unknown",
            "submitted_at": case.submitted_at.isoformat() if case.submitted_at else None,
            "documents_count": len(case.documents_submitted or []) if case.documents_submitted else 0,
            "priority": priority,
            "assigned_to": case.reviewer_id
        })
    
    # Sort by priority (descending) then by submission time (ascending)
    result.sort(key=lambda x: (-x['priority'], x['submitted_at'] or ''))
    
    return result

def calculate_verification_completeness(documents_submitted: List[str], required_categories: List[str]) -> Dict:
    """
    FR-40: Calculate submission completeness score
    
    Args:
        documents_submitted: List of document category names submitted
        required_categories: List of categories required for full verification
    
    Returns:
        Dict with completeness percentage and missing items
    """
    if not required_categories:
        return {"percentage": 100, "missing": [], "status": "complete"}
    
    submitted_set = set(documents_submitted or [])
    required_set = set(required_categories)
    
    missing = list(required_set - submitted_set)
    percentage = round((len(submitted_set & required_set) / len(required_set)) * 100) if required_set else 100
    
    status = "complete" if percentage == 100 else ("partial" if percentage >= 50 else "minimal")
    
    return {
        "percentage": percentage,
        "missing": missing,
        "status": status,
        "submitted": list(submitted_set),
        "required": list(required_set)
    }