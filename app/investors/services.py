"""
Investor portal services for FR-70 to FR-72.
"""

from app.models import Startup, InvestorProfile, ConnectionRequest, VerificationCase
from app.extensions import db


def search_startups(filters: dict, limit: int = 20, offset: int = 0) -> tuple:
    """
    FR-70: Search and filter startups for investor discovery.
    
    Args:
        filters: Dict with optional filters:
            - sector: str
            - stage: str (Early, Growth, Maturity)
            - country: str
            - verified_only: bool
            - min_valuation: float
            - search_query: str (search in name/description)
        limit: Max results to return
        offset: Pagination offset
    
    Returns:
        (startups: list, total_count: int)
    """
    query = Startup.query
    
    # Apply filters
    if filters.get('sector'):
        query = query.filter(Startup.sector.ilike(f"%{filters['sector']}%"))
    
    if filters.get('stage'):
        query = query.filter(Startup.stage == filters['stage'])
    
    if filters.get('country'):
        query = query.filter(Startup.country == filters['country'])
    
    if filters.get('search_query'):
        search = f"%{filters['search_query']}%"
        query = query.filter(
            (Startup.name.ilike(search)) | (Startup.description.ilike(search))
        )
    
    # Get all results first for counting
    all_results = query.all()
    
    # Filter by verification status (requires checking VerificationCase table)
    if filters.get('verified_only'):
        verified_startup_ids = []
        for startup in all_results:
            verification = VerificationCase.query.filter_by(
                startup_id=startup.id,
                status='verified'
            ).first()
            if verification:
                verified_startup_ids.append(startup.id)
        all_results = [s for s in all_results if s.id in verified_startup_ids]
    
    # Get total count
    total_count = len(all_results)
    
    # Apply pagination
    paginated_results = all_results[offset:offset + limit]
    
    return paginated_results, total_count


def get_startup_investor_view(startup_id: int, investor_id: int = None) -> dict:
    """
    FR-71: Get startup profile as visible to investors.
    Shows public info + verified data (hides sensitive info).
    
    Args:
        startup_id: Startup to view
        investor_id: Viewing investor's ID (for access control)
    
    Returns:
        Dict with startup info visible to investors
    """
    startup = Startup.query.get(startup_id)
    if not startup:
        return None
    
    # Check verification status
    verification = VerificationCase.query.filter_by(
        startup_id=startup_id,
        status='verified'
    ).first()
    
    is_verified = verification is not None
    
    # Get latest diagnostic score (if any)
    from app.models import DiagnosticSession
    diagnostic = DiagnosticSession.query.filter_by(
        startup_id=startup_id
    ).order_by(DiagnosticSession.run_at.desc()).first()
    
    # Get latest valuation (if any)
    from app.models import Valuation
    valuation = Valuation.query.filter_by(
        startup_id=startup_id
    ).order_by(Valuation.run_at.desc()).first()
    
    # Get document list (not full content - just metadata)
    from app.models import BusinessDocument
    documents = BusinessDocument.query.filter_by(
        startup_id=startup_id,
        status='published'
    ).all()
    
    # Check if there's an existing connection request
    existing_request = None
    if investor_id:
        existing_request = ConnectionRequest.query.filter_by(
            investor_id=investor_id,
            startup_id=startup_id,
            status='pending'
        ).first()
    
    return {
        'startup': {
            'id': startup.id,
            'name': startup.name,
            'sector': startup.sector,
            'country': startup.country,
            'stage': startup.stage,
            'description': startup.description,
            'is_verified': is_verified,
            'profile_completion': startup.profile_completion
        },
        'diagnostic': {
            'stage': diagnostic.stage if diagnostic else None,
            'overall_score': diagnostic.overall_score if diagnostic else None,
            'run_at': diagnostic.run_at.isoformat() if diagnostic and diagnostic.run_at else None
        } if diagnostic else None,
        'valuation': {
            'method': valuation.method if valuation else None,
            'amount': valuation.valuation_amount if valuation else None,
            'currency': valuation.currency if valuation else None,
            'run_at': valuation.run_at.isoformat() if valuation and valuation.run_at else None
        } if valuation else None,
        'documents': [
            {
                'id': d.id,
                'title': d.title,
                'doc_type': d.doc_type,
                'generated_at': d.generated_at.isoformat() if d.generated_at else None
            }
            for d in documents
        ],
        'connection_request': {
            'id': existing_request.id,
            'status': existing_request.status
        } if existing_request else None,
        'contact_info': startup.owner.to_dict() if is_verified and startup.owner else None
    }


def create_connection_request(investor_id: int, startup_id: int, message: str = None) -> dict:
    """
    FR-72: Investor sends connection request to startup.
    
    Args:
        investor_id: InvestorProfile ID
        startup_id: Startup ID
        message: Optional intro message
    
    Returns:
        Dict with result and request details
    """
    # Check for existing pending request
    existing = ConnectionRequest.query.filter_by(
        investor_id=investor_id,
        startup_id=startup_id,
        status='pending'
    ).first()
    
    if existing:
        return {
            'success': False,
            'error': 'Connection request already pending',
            'request_id': existing.id
        }
    
    # Create new request
    request = ConnectionRequest(
        investor_id=investor_id,
        startup_id=startup_id,
        message=message,
        status='pending'
    )
    
    db.session.add(request)
    db.session.commit()
    
    return {
        'success': True,
        'request_id': request.id,
        'status': 'pending',
        'message': 'Connection request sent. Awaiting startup approval.'
    }


def respond_to_connection_request(request_id: int, startup_owner_id: int, decision: str) -> dict:
    """
    FR-72: Startup owner accepts or rejects connection request.
    
    Args:
        request_id: ConnectionRequest ID
        startup_owner_id: User ID of startup owner (for authorization)
        decision: 'accepted' or 'rejected'
    
    Returns:
        Dict with result
    """
    request = ConnectionRequest.query.get(request_id)
    if not request:
        return {'success': False, 'error': 'Request not found'}
    
    # Verify startup ownership
    if request.startup.owner_user_id != startup_owner_id:
        return {'success': False, 'error': 'Access denied'}
    
    if request.status != 'pending':
        return {'success': False, 'error': f'Request already {request.status}'}
    
    # Update status
    from datetime import datetime
    request.status = 'accepted' if decision == 'accepted' else 'rejected'
    request.responded_at = datetime.now()
    
    # If accepted, share contact info
    if decision == 'accepted':
        request.contact_info_shared = {
            'email': request.startup.owner.email,
            'name': request.startup.owner.name
        }
    
    db.session.commit()
    
    return {
        'success': True,
        'request_id': request_id,
        'status': request.status,
        'message': f'Connection request {decision}'
    }


def get_investor_profile(user_id: int) -> InvestorProfile:
    """
    Get or create investor profile for a user.
    """
    profile = InvestorProfile.query.filter_by(user_id=user_id).first()
    
    if not profile:
        # Auto-create basic profile
        profile = InvestorProfile(
            user_id=user_id,
            is_active=True
        )
        db.session.add(profile)
        db.session.commit()
    
    return profile