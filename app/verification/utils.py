# app/verification/utils.py
"""
FR-40 + FR-43: Document Validation & File Handling Utilities
Validates uploaded documents, handles secure storage, and enforces type rules.
"""

import os
import secrets
import mimetypes
from datetime import datetime
from typing import List, Optional, Tuple
from werkzeug.utils import secure_filename

# Allowed document types per verification category (FR-40)
ALLOWED_DOCUMENT_TYPES = {
    "business_registration": [
        "CAC Certificate", "Business Name Registration", "Tax ID (TIN)", 
        "Memorandum & Articles", "Partnership Deed"
    ],
    "financial": [
        "Audited Financial Statements", "Bank Statements (6 months)",
        "Tax Clearance Certificate", "Management Accounts", "Cash Flow Projection"
    ],
    "operational": [
        "Business Plan", "SOPs", "Organizational Chart", "Key Contracts",
        "Insurance Policies", "Licenses & Permits"
    ],
    "legal": [
        "Shareholder Agreement", "IP Registration", "Employment Contracts",
        "Data Protection Compliance", "Industry-Specific Licenses"
    ],
    "team": [
        "Founder CVs", "Key Team Profiles", "Advisory Board Agreements",
        "Technical Certifications"
    ]
}

# Allowed file extensions (security + compatibility)
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png'}
MAX_FILE_SIZE_MB = 25  # 25MB limit per document

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_document_type(category: str, document_name: str) -> bool:
    """
    FR-40: Validate that uploaded document matches expected type for category
    
    Args:
        category: One of the keys in ALLOWED_DOCUMENT_TYPES
        document_name: User-provided document name/description
    
    Returns:
        True if document name matches an allowed type for the category
    """
    allowed_types = ALLOWED_DOCUMENT_TYPES.get(category, [])
    # Case-insensitive partial match for flexibility
    doc_lower = document_name.lower()
    return any(allowed.lower() in doc_lower for allowed in allowed_types)

def generate_secure_filename(original_filename: str) -> str:
    """
    Generate a secure, unique filename for storage
    
    Args:
        original_filename: Original uploaded filename
    
    Returns:
        Secure filename with timestamp + random token
    """
    # Extract extension
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'bin'
    
    # Generate secure name: timestamp + random token + extension
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    token = secrets.token_urlsafe(16)
    
    return f"doc_{timestamp}_{token}.{ext}"

def validate_file_upload(file, max_size_mb: int = MAX_FILE_SIZE_MB) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded file meets security and size requirements
    
    Args:
        file: Werkzeug FileStorage object from request.files
        max_size_mb: Maximum allowed file size in MB
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file or file.filename == '':
        return False, "No file selected"
    
    if not allowed_file(file.filename):
        return False, f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Check file size (read first chunk to avoid loading entire file)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset pointer
    
    if file_size > max_size_mb * 1024 * 1024:
        return False, f"File too large. Max: {max_size_mb}MB"
    
    # Optional: Check MIME type matches extension (basic security)
    mime_type, _ = mimetypes.guess_type(file.filename)
    if mime_type and mime_type.startswith('application/x-'):
        # Suspicious MIME type - could be executable disguised
        return False, "Suspicious file type detected"
    
    return True, None

def get_document_category_requirements(category: str) -> dict:
    """
    FR-40: Get requirements/guidance for a document category
    
    Args:
        category: One of the keys in ALLOWED_DOCUMENT_TYPES
    
    Returns:
        Dict with category info and allowed document types
    """
    category_info = {
        "business_registration": {
            "description": "Legal registration and tax documentation",
            "required_for_verification": True,
            "notes": "Must be issued within last 12 months"
        },
        "financial": {
            "description": "Financial statements and tax compliance",
            "required_for_verification": True,
            "notes": "Audited statements preferred for Growth/Maturity stage"
        },
        "operational": {
            "description": "Business processes and operational documentation",
            "required_for_verification": False,
            "notes": "Helps demonstrate scalability and process maturity"
        },
        "legal": {
            "description": "Legal agreements and compliance documentation",
            "required_for_verification": False,
            "notes": "Important for investor due diligence"
        },
        "team": {
            "description": "Founder and key team credentials",
            "required_for_verification": False,
            "notes": "Strengthens credibility for early-stage startups"
        }
    }
    
    return {
        "category": category,
        "info": category_info.get(category, {}),
        "allowed_types": ALLOWED_DOCUMENT_TYPES.get(category, [])
    }