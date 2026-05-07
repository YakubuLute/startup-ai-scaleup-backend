# app/verification/engine.py
from datetime import datetime, timedelta

# FR-40: Required document checklist per region (expandable)
VERIFICATION_CHECKLIST = {
    "Ghana": [
        {"type": "registration", "name": "Business Registration Certificate", "required": True},
        {"type": "tax_id", "name": "Tax Identification Number (TIN)", "required": True},
        {"type": "bank_letter", "name": "Bank Account Verification Letter", "required": False},
        {"type": "founder_id", "name": "Founder Government ID", "required": True}
    ],
    "Nigeria": [
        {"type": "cac", "name": "CAC Registration Document", "required": True},
        {"type": "tin", "name": "Tax Identification Number", "required": True},
        {"type": "bank_statement", "name": "6-Month Bank Statement", "required": False}
    ],
    "Default": [
        {"type": "registration", "name": "Business Registration", "required": True},
        {"type": "tax_id", "name": "Tax ID / VAT Number", "required": True},
        {"type": "founder_id", "name": "Founder ID", "required": True}
    ]
}

def get_checklist(country):
    """FR-40: Return region-specific document checklist"""
    return VERIFICATION_CHECKLIST.get(country, VERIFICATION_CHECKLIST["Default"])

def validate_submission(documents_submitted, country):
    """FR-40: Check if required documents are present"""
    checklist = get_checklist(country)
    submitted_types = [doc.get("type") for doc in documents_submitted]
    
    missing = [item["type"] for item in checklist if item.get("required", False) and item["type"] not in submitted_types]
    
    return {
        "is_complete": len(missing) == 0,
        "missing_required": missing,
        "submitted_count": len(submitted_types),
        "required_count": len([i for i in checklist if i.get("required", False)])
    }

def calculate_badge_validity(stage, verification_date):
    """FR-42: Determine badge expiry based on startup stage"""
    validity_map = {
        "Early": 180,    # 6 months
        "Growth": 365,   # 1 year
        "Maturity": 730  # 2 years
    }
    days = validity_map.get(stage, 365)
    return verification_date + timedelta(days=days)

def generate_due_diligence_summary(verification_case, startup, diagnostics, valuation):
    """FR-43: Compile investor-ready due diligence summary"""
    return {
        "startup_name": startup.name,
        "verification_status": verification_case.status,
        "verified_at": verification_case.reviewed_at.isoformat() if verification_case.reviewed_at else None,
        "documents_verified": [
            {"type": doc["type"], "verified": True} for doc in verification_case.documents_submitted
        ],
        "business_stage": diagnostics.stage if diagnostics else "Not assessed",
        "diagnostic_score": diagnostics.overall_score if diagnostics else None,
        "valuation_summary": {
            "amount": valuation.valuation_amount if valuation else None,
            "currency": valuation.currency if valuation else "GHS",
            "method": valuation.method if valuation else "Not run"
        } if valuation else None,
        "reviewer_notes": verification_case.review_notes,
        "badge_valid_until": verification_case.badge_valid_until.isoformat() if verification_case.badge_valid_until else None,
        "generated_at": datetime.utcnow().isoformat()
    }