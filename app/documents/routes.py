# app/documents/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import BusinessDocument, DocumentTemplate, DocumentVersion, SharedDocumentLink, Startup
from datetime import datetime, timedelta
import secrets

documents_bp = Blueprint('documents', __name__)

def _check_doc_ownership(doc_id, user_id):
    """Helper: Ensure user owns the startup that owns this document"""
    doc = BusinessDocument.query.get_or_404(doc_id)
    startup = Startup.query.get(doc.startup_id)
    if not startup or startup.owner_user_id != user_id:
        return jsonify({"msg": "Access denied: You do not own this document"}), 403
    return doc

# =============================================================================
# FR-10 / US-10: Template Catalog
# =============================================================================
@documents_bp.route('/templates', methods=['GET'])
@jwt_required()
def get_templates():
    """List active document templates with wizard schema"""
    templates = DocumentTemplate.query.filter_by(is_active=True).all()
    return jsonify({
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "question_schema": t.question_schema
            }
            for t in templates
        ]
    }), 200

# =============================================================================
# FR-11 / US-11: Create Document Draft (Wizard Answers)
# =============================================================================
@documents_bp.route('', methods=['POST'])
@jwt_required()
def create_document():
    """Initialize document + save wizard draft"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    template = DocumentTemplate.query.get_or_404(data.get('template_id'))
    startup = Startup.query.get_or_404(data.get('startup_id'))
    
    if startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied: You do not own this startup"}), 403
    
    doc = BusinessDocument(
        startup_id=startup.id,
        template_id=template.id,
        title=data.get('title', template.name),
        status='Draft',
        created_by=current_user_id
    )
    db.session.add(doc)
    db.session.flush()  # Get ID before commit
    
    # Save initial wizard answers as version 0
    if data.get('wizard_answers'):
        ver = DocumentVersion(
            document_id=doc.id,
            version_number=0,
            content=str(data['wizard_answers']),
            created_by=current_user_id
        )
        db.session.add(ver)
    
    db.session.commit()
    return jsonify({
        "msg": "Document draft created",
        "document": {"id": doc.id, "title": doc.title, "status": doc.status}
    }), 201

# =============================================================================
# FR-12 / US-12: AI Draft Generation
# =============================================================================
@documents_bp.route('/<int:doc_id>/generate', methods=['POST'])
@jwt_required()
def generate_ai_draft(doc_id):
    """Trigger AI generation (sync for now → async queue later per Spec 6.1)"""
    current_user_id = int(get_jwt_identity())
    doc = _check_doc_ownership(doc_id, current_user_id)
    
    if doc.status not in ('Draft', 'Generating'):
        return jsonify({"msg": "Document already generated"}), 400
    
    doc.status = 'Generating'
    db.session.commit()
    
    #  TODO: Replace with actual LLM API call (OpenAI, Anthropic, etc.)
    # Placeholder simulates AI output based on template + wizard answers
    latest_ver = DocumentVersion.query.filter_by(document_id=doc.id).order_by(DocumentVersion.version_number.desc()).first()
    wizard_data = latest_ver.content if latest_ver else "{}"
    
    ai_content = f"""# {doc.title} (AI Generated Draft)

## Executive Summary
Based on your inputs: {wizard_data}

## Business Model
- Revenue Streams: [Auto-populated from wizard]
- Target Market: [Auto-populated from wizard]

## Operations & Compliance
- Recommended SOPs: [Generated from template rules]
- HR Policy Outline: [Generated from industry sector]

*Note: This is an AI-assisted draft. Please review and customize before sharing.*
"""
    
    new_ver = DocumentVersion(
        document_id=doc.id,
        version_number=DocumentVersion.query.filter_by(document_id=doc.id).count(),
        content=ai_content,
        created_by=current_user_id
    )
    db.session.add(new_ver)
    doc.status = 'Ready'
    db.session.commit()
    
    return jsonify({
        "msg": "Document generated successfully",
        "version": new_ver.version_number,
        "preview": ai_content[:300] + "..."
    }), 200

# =============================================================================
# FR-13 / US-13: Get Document + Version History
# =============================================================================
@documents_bp.route('/<int:doc_id>', methods=['GET'])
@jwt_required()
def get_document(doc_id):
    """Get latest version + metadata"""
    current_user_id = int(get_jwt_identity())
    doc = _check_doc_ownership(doc_id, current_user_id)
    
    latest = DocumentVersion.query.filter_by(document_id=doc.id).order_by(DocumentVersion.version_number.desc()).first()
    versions = DocumentVersion.query.filter_by(document_id=doc.id).all()
    
    return jsonify({
        "document": {
            "id": doc.id,
            "title": doc.title,
            "status": doc.status,
            "template_id": doc.template_id,
            "current_version": latest.version_number if latest else 0,
            "content": latest.content if latest else None,
            "version_history": [
                {"version": v.version_number, "created_at": v.created_at.isoformat(), "created_by": v.created_by}
                for v in versions
            ]
        }
    }), 200

@documents_bp.route('/<int:doc_id>', methods=['PUT'])
@jwt_required()
def update_document(doc_id):
    """Save manual edits → creates new version"""
    current_user_id = int(get_jwt_identity())
    doc = _check_doc_ownership(doc_id, current_user_id)
    data = request.get_json()
    
    if not data.get('content'):
        return jsonify({"msg": "Content is required for version update"}), 400
    
    new_ver = DocumentVersion(
        document_id=doc.id,
        version_number=DocumentVersion.query.filter_by(document_id=doc.id).count(),
        content=data['content'],
        created_by=current_user_id
    )
    db.session.add(new_ver)
    doc.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({"msg": "Document updated", "version": new_ver.version_number}), 200

# =============================================================================
# FR-14 / US-15: Secure Sharing
# =============================================================================
@documents_bp.route('/<int:doc_id>/share', methods=['POST'])
@jwt_required()
def create_share_link(doc_id):
    """Generate read-only share link with optional expiry"""
    current_user_id = int(get_jwt_identity())
    doc = _check_doc_ownership(doc_id, current_user_id)
    data = request.get_json() or {}
    
    days = data.get('expires_in_days', 7)
    link = SharedDocumentLink(
        document_id=doc.id,
        expires_at=datetime.utcnow() + timedelta(days=days)
    )
    db.session.add(link)
    db.session.commit()
    
    return jsonify({
        "share_url": f"/api/documents/shared/{link.token}",
        "expires_at": link.expires_at.isoformat(),
        "token": link.token
    }), 201

@documents_bp.route('/shared/<token>', methods=['GET'])
def view_shared_document(token):
    """Public read-only access (no auth required)"""
    link = SharedDocumentLink.query.filter_by(token=token, is_active=True).first_or_404()
    
    if link.expires_at and link.expires_at < datetime.utcnow():
        link.is_active = False
        db.session.commit()
        return jsonify({"msg": "Share link expired"}), 403
    
    latest = DocumentVersion.query.filter_by(document_id=link.document_id).order_by(DocumentVersion.version_number.desc()).first()
    return jsonify({
        "title": latest.document.title,
        "content": latest.content if latest else "",
        "shared_at": link.created_at.isoformat()
    }), 200

# =============================================================================
# FR-14 / US-14: Export Stub (PDF/Docx)
# =============================================================================
@documents_bp.route('/<int:doc_id>/export', methods=['POST'])
@jwt_required()
def export_document(doc_id):
    """Export to PDF/Docx (stub → integrate WeasyPrint/python-docx next)"""
    current_user_id = int(get_jwt_identity())
    doc = _check_doc_ownership(doc_id, current_user_id)
    data = request.get_json() or {}
    fmt = data.get('format', 'pdf').lower()
    
    if fmt not in ('pdf', 'docx'):
        return jsonify({"msg": "Unsupported format. Use 'pdf' or 'docx'"}), 400
    
    # 📦 TODO: Actual export logic
    # - pdf: weasyprint.HTML(string=content).write_pdf()
    # - docx: python-docx Document() + add_paragraphs()
    return jsonify({
        "msg": f"{fmt.upper()} export queued (integration pending)",
        "download_url": f"/api/documents/{doc_id}/download.{fmt}",
        "note": "Install weasyprint or python-docx to enable actual file generation"
    }), 202