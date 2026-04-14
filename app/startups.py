from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Startup, User

startups_bp = Blueprint('startups', __name__)

@startups_bp.route('', methods=['POST'])
@jwt_required()
def create_startup():
    """FR-02: Create a new startup"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({"msg": "Startup name is required"}), 400
    
    new_startup = Startup(
        name=data['name'],
        owner_user_id=current_user_id,
        sector=data.get('sector'),
        country=data.get('country', 'Ghana'),
        registration_number=data.get('registration_number'),
        stage=data.get('stage', 'Early'),
        description=data.get('description')
    )
    
    # Calculate initial profile completion (simple logic)
    fields_filled = sum([
        bool(new_startup.name),
        bool(new_startup.sector),
        bool(new_startup.country),
        bool(new_startup.registration_number),
        bool(new_startup.description)
    ])
    new_startup.profile_completion = min(100, int((fields_filled / 5) * 100))
    
    db.session.add(new_startup)
    db.session.commit()
    
    return jsonify({"msg": "Startup created", "startup": new_startup.to_dict()}), 201

@startups_bp.route('', methods=['GET'])
@jwt_required()
def get_user_startups():
    """Get all startups owned by the current user"""
    current_user_id =int(get_jwt_identity())
    startups = Startup.query.filter_by(owner_user_id=current_user_id).all()
    
    return jsonify({
        "startups": [s.to_dict() for s in startups],
        "count": len(startups)
    }), 200

@startups_bp.route('/<int:startup_id>', methods=['GET'])
@jwt_required()
def get_startup(startup_id):
    """Get a specific startup (with ownership check)"""
    current_user_id = get_jwt_identity()
    startup = Startup.query.get_or_404(startup_id)
    
    # Security: Only owner or team member can access
    if startup.owner_user_id != current_user_id:
        # TODO: Add team member check here (FR-03)
        return jsonify({"msg": "Access denied"}), 403
    
    return jsonify({"startup": startup.to_dict()}), 200

## =============================================================================
# PROXY ALIAS ROUTES (for frontend proxy configuration)
# Register these AFTER all standard routes
# =============================================================================

# Helper: Get the blueprint's url_prefix dynamically (Flask magic)
def _get_proxy_route(path):
    """Convert /api/startups/X to /api/proxy/startups/X"""
    return f'/proxy{path}' if path else '/proxy'

# GET /api/proxy/startups
@startups_bp.route(_get_proxy_route(''), methods=['GET'])
@jwt_required()
def list_startups_proxy():
    return get_user_startups()

# GET /api/proxy/startups/<id>
@startups_bp.route(_get_proxy_route('/<int:startup_id>'), methods=['GET'])
@jwt_required()
def get_startup_proxy(startup_id):
    return get_startup(startup_id)

# POST /api/proxy/startups
@startups_bp.route(_get_proxy_route(''), methods=['POST'])
@jwt_required()
def create_startup_proxy():
    return create_startup()

# ⚠️ PUT/DELETE: Only add these if update_startup/delete_startup functions exist
# @startups_bp.route(_get_proxy_route('/<int:startup_id>'), methods=['PUT'])
# @jwt_required()
# def update_startup_proxy(startup_id):
#     return update_startup(startup_id)

# @startups_bp.route(_get_proxy_route('/<int:startup_id>'), methods=['DELETE'])
# @jwt_required()
# def delete_startup_proxy(startup_id):
#     return delete_startup(startup_id)