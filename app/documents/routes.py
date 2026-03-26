from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import BusinessDocument, Startup
from app.documents.services import generate_document

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