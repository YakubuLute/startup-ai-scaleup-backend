from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import BusinessDocument, Startup, DocumentShare
from app.documents.services import generate_document
from app.documents.export import generate_pdf_from_markdown, generate_docx_from_markdown  

documents_bp = Blueprint('documents', __name__)

@documents_bp.route('/templates', methods=['GET'])
@jwt_required()
def list_templates():
    """FR-10: List available document templates"""
    from app.documents.services import TEMPLATES
    return jsonify({
        "templates": [
            {"type": key, "name": key.replace('_', ' ').title()}
            for key in TEMPLATES.keys()
        ]
    }), 200

@documents_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_document_endpoint():
    """FR-11 + FR-12: Generate a new document from template + inputs"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Validate required fields
    required = ['startup_id', 'doc_type', 'title', 'inputs']
    for field in required:
        if field not in data:
            return jsonify({"msg": f"Missing required field: {field}"}), 400
    
    # Verify startup ownership
    startup = Startup.query.get(data['startup_id'])
    if not startup or startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    try:
        inputs_with_title = data['inputs'].copy()
        inputs_with_title['title'] = data['title']
        
        # Generate content using template engine (placeholder for AI)
        content = generate_document(data['doc_type'], inputs_with_title)
            
        # Save to database
        new_doc = BusinessDocument(
            startup_id=data['startup_id'],
            title=data['title'],
            doc_type=data['doc_type'],
            content=content,
            version=1,
            status='draft'
        )
        db.session.add(new_doc)
        db.session.commit()
        
        return jsonify({
            "msg": "Document generated successfully",
            "document": new_doc.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Failed to generate document", "error": str(e)}), 500

@documents_bp.route('', methods=['GET'])
@jwt_required()
def list_documents():
    """List all documents for the current user's startups"""
    current_user_id = int(get_jwt_identity())
    
    # Get all startups owned by user
    startups = Startup.query.filter_by(owner_user_id=current_user_id).all()
    startup_ids = [s.id for s in startups]
    
    # Get documents for those startups
    docs = BusinessDocument.query.filter(BusinessDocument.startup_id.in_(startup_ids)).all()
    
    return jsonify({
        "documents": [d.to_dict() for d in docs],
        "count": len(docs)
    }), 200

@documents_bp.route('/<int:doc_id>', methods=['GET'])
@jwt_required()
def get_document(doc_id):
    """Get a specific document (with ownership check)"""
    current_user_id = int(get_jwt_identity())
    doc = BusinessDocument.query.get_or_404(doc_id)
    
    # Verify access: user must own the startup
    if doc.startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    return jsonify({"document": doc.to_dict()}), 200



import os
import io
import secrets
from datetime import datetime, timedelta
from flask import send_file, jsonify, request, url_for
from app.models import DocumentShare

@documents_bp.route('/<int:doc_id>/export', methods=['POST'])
@jwt_required()
def export_document(doc_id):
    """
    FR-14: Export document as PDF or Docx.
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Validate format
    export_format = data.get('format', 'pdf').lower()
    if export_format not in ['pdf', 'docx']:
        return jsonify({"msg": "Format must be 'pdf' or 'docx'"}), 400
    
    # Get document and verify ownership
    doc = BusinessDocument.query.get_or_404(doc_id)
    if doc.startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    try:
        # ✅ EXPORT LOGIC MUST BE INSIDE THIS FUNCTION:
        if export_format == 'pdf':
            # Use reportlab-based PDF generator (Windows-compatible)
            file_bytes = generate_pdf_from_markdown(doc.content, title=doc.title)
            mimetype = 'application/pdf'
            extension = 'pdf'
        else:  # docx
            file_bytes = generate_docx_from_markdown(doc.content, title=doc.title)
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            extension = 'docx'
        
        # Send file as download
        filename = f"{doc.title.replace(' ', '_').lower()}.{extension}"
        
        return send_file(
            io.BytesIO(file_bytes),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
    except ImportError as e:
        return jsonify({"msg": f"Export library not installed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"msg": "Failed to export document", "error": str(e)}), 500

@documents_bp.route('/<int:doc_id>/share', methods=['POST'])
@jwt_required()
def create_share_link(doc_id):
    """
    FR-14: Create a shareable link for investors/mentors with expiry.
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Get document and verify ownership
    doc = BusinessDocument.query.get_or_404(doc_id)
    if doc.startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    # Parse expiry (default: 7 days)
    expiry_days = data.get('expiry_days', 7)
    expires_at = datetime.now() + timedelta(days=expiry_days) if expiry_days else None
    
    # Generate unique share token
    share_token = secrets.token_urlsafe(32)
    
    # Create share record
    share = DocumentShare(
        document_id=doc_id,
        share_token=share_token,
        expires_at=expires_at,
        allow_download=data.get('allow_download', False),
        created_by_user_id=current_user_id
    )
    
    db.session.add(share)
    db.session.commit()
    
    # Build full share URL (in production, use your actual domain)
    share_url = f"http://127.0.0.1:5000/api/documents/shared/{share_token}"
    
    return jsonify({
        "msg": "Share link created successfully",
        "share_id": share.id,
        "share_url": share_url,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "allow_download": share.allow_download
    }), 201

@documents_bp.route('/shared/<share_token>', methods=['GET'])
def access_shared_document(share_token):
    """
    FR-14: Public endpoint for accessing shared documents (no auth required).
    Investors/mentors use this link.
    """
    # Find share record
    share = DocumentShare.query.filter_by(share_token=share_token).first()
    
    if not share:
        return jsonify({"msg": "Share link not found"}), 404
    
    # Check if active
    if not share.is_active:
        return jsonify({"msg": "This share link has been deactivated"}), 403
    
    # Check if expired
    if share.expires_at and datetime.now() > share.expires_at:
        return jsonify({"msg": "This share link has expired"}), 403
    
    # Update access tracking (audit trail per Spec 6.4)
    share.access_count += 1
    share.last_accessed_at = db.func.now()
    db.session.commit()
    
    # Return document content (view-only)
    doc = share.document
    return jsonify({
        "document": {
            "title": doc.title,
            "doc_type": doc.doc_type,
            "content": doc.content,
            "generated_at": doc.generated_at.isoformat() if doc.generated_at else None
        },
        "share_info": {
            "allow_download": share.allow_download,
            "access_count": share.access_count,
            "expires_at": share.expires_at.isoformat() if share.expires_at else None
        }
    }), 200

@documents_bp.route('/<int:doc_id>/shares', methods=['GET'])
@jwt_required()
def list_document_shares(doc_id):
    """
    FR-14: List all active share links for a document.
    """
    current_user_id = int(get_jwt_identity())
    
    # Get document and verify ownership
    doc = BusinessDocument.query.get_or_404(doc_id)
    if doc.startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    # Get all shares for this document
    shares = DocumentShare.query.filter_by(document_id=doc_id).order_by(DocumentShare.created_at.desc()).all()
    
    return jsonify({
        "shares": [s.to_dict() for s in shares],
        "count": len(shares)
    }), 200

@documents_bp.route('/shares/<int:share_id>/revoke', methods=['POST'])
@jwt_required()
def revoke_share_link(share_id):
    """
    FR-14: Revoke/deactivate a share link.
    """
    current_user_id = int(get_jwt_identity())
    
    # Get share and verify ownership
    share = DocumentShare.query.get_or_404(share_id)
    if share.document.startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    # Deactivate
    share.is_active = False
    db.session.commit()
    
    return jsonify({
        "msg": "Share link revoked successfully",
        "share_id": share.id,
        "is_active": share.is_active
    }), 200