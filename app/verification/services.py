"""
Verification workflow services for FR-40 to FR-42.
"""

from datetime import datetime, timedelta


# Valid document types for verification (FR-40)
VALID_DOCUMENT_TYPES = [
    'business_registration',
    'tax_certificate',
    'bank_letter',
    'id_document',
    'proof_of_address',
    'financial_statements',
    'other'
]

# Verification status options (FR-41 workflow)
VERIFICATION_STATUSES = ['pending', 'in_review', 'verified', 'rejected']


def validate_submission_documents(documents: list) -> tuple:
    """
    Validate submitted verification documents (FR-40).
    
    Returns:
        (is_valid: bool, error_message: str or None)
    """
    if not documents or len(documents) == 0:
        return False, "At least one document must be submitted"
    
    for doc in documents:
        if not isinstance(doc, dict):
            return False, "Each document must be an object"
        
        doc_type = doc.get('type')
        file_url = doc.get('file_url')
        
        if not doc_type:
            return False, "Document type is required"
        
        if doc_type not in VALID_DOCUMENT_TYPES:
            return False, f"Invalid document type: {doc_type}. Valid types: {VALID_DOCUMENT_TYPES}"
        
        if not file_url:
            return False, "Document file_url is required"
    
    return True, None


def calculate_verification_score(documents: list) -> int:
    """
    Calculate a simple verification completeness score (0-100).
    Higher score = more document types submitted.
    
    Recommended minimum for verification: business_registration + tax_certificate
    """
    required_docs = ['business_registration', 'tax_certificate']
    optional_docs = ['bank_letter', 'id_document', 'proof_of_address', 'financial_statements']
    
    submitted_types = [doc.get('type') for doc in documents]
    
    # Required docs: 60 points total (30 each)
    required_score = sum(30 for doc in required_docs if doc in submitted_types)
    
    # Optional docs: 40 points total (10 each)
    optional_score = sum(10 for doc in optional_docs if doc in submitted_types)
    
    return min(100, required_score + optional_score)


def determine_verification_status(completeness_score: int, manual_override: str = None) -> str:
    """
    Determine verification status based on completeness score.
    This is a helper - actual approval requires Program Manager review (FR-41).
    """
    if manual_override and manual_override in VERIFICATION_STATUSES:
        return manual_override
    
    # Auto-suggest status based on completeness
    if completeness_score >= 60:  # Has required docs
        return 'in_review'  # Ready for human review
    else:
        return 'pending'  # Incomplete submission


def generate_review_recommendations(completeness_score: int, submitted_types: list) -> list:
    """
    Generate recommendations for improving verification chances.
    """
    recommendations = []
    
    required_docs = ['business_registration', 'tax_certificate']
    missing_required = [doc for doc in required_docs if doc not in submitted_types]
    
    if missing_required:
        recommendations.append(f"Submit missing required documents: {', '.join(missing_required)}")
    
    if completeness_score < 80:
        recommendations.append("Add optional documents (bank letter, ID, proof of address) to strengthen verification")
    
    if completeness_score >= 80:
        recommendations.append("Your submission is complete. A Program Manager will review within 3-5 business days.")
    
    return recommendations


def create_verification_case(startup_id: int, documents: list) -> dict:
    """
    Create a new verification case (FR-40).
    
    Returns:
        Dict with case data, status, and recommendations
    """
    # Validate documents
    is_valid, error = validate_submission_documents(documents)
    if not is_valid:
        return {'error': error, 'success': False}
    
    # Calculate completeness score
    completeness_score = calculate_verification_score(documents)
    
    # Determine initial status
    status = determine_verification_status(completeness_score)
    
    # Generate recommendations
    submitted_types = [doc.get('type') for doc in documents]
    recommendations = generate_review_recommendations(completeness_score, submitted_types)
    
    return {
        'success': True,
        'startup_id': startup_id,
        'documents_submitted': documents,
        'status': status,
        'completeness_score': completeness_score,
        'recommendations': recommendations,
        'badge_issued': False
    }


def review_verification_case(case_id: int, decision: str, reviewer_id: int, notes: str = None) -> dict:
    """
    Review and make decision on verification case (FR-41).
    
    Args:
        case_id: Verification case ID
        decision: 'verified' or 'rejected'
        reviewer_id: Program Manager user ID
        notes: Review notes (required for audit per Spec 6.4)
    
    Returns:
        Dict with updated case data
    """
    if decision not in ['verified', 'rejected']:
        return {'error': "Decision must be 'verified' or 'rejected'", 'success': False}
    
    if not notes or len(notes.strip()) == 0:
        return {'error': "Review notes are required for audit trail", 'success': False}
    
    return {
        'success': True,
        'case_id': case_id,
        'decision': decision,
        'reviewer_id': reviewer_id,
        'review_notes': notes,
        'badge_issued': decision == 'verified',
        'status': decision
    }