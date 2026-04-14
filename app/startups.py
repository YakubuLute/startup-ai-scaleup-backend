# app/startups.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Startup, User

startups_bp = Blueprint('startups', __name__)

@startups_bp.route('', methods=['POST'])
@jwt_required()
def create_startup():
    """FR-02: Create a new startup"""
    # ✅ Convert JWT identity (string) to int for DB consistency
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({"msg": "Startup name is required"}), 400
    
    new_startup = Startup(
        name=data['name'],
        owner_user_id=current_user_id,  # Now int, matches DB column
        sector=data.get('sector'),
        country=data.get('country', 'Ghana'),
        registration_number=data.get('registration_number'),
        stage=data.get('stage', 'Early'),
        description=data.get('description')
    )
    
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
    current_user_id = int(get_jwt_identity())  # ✅ Already correct
    startups = Startup.query.filter_by(owner_user_id=current_user_id).all()
    
    return jsonify({
        "startups": [s.to_dict() for s in startups],
        "count": len(startups)
    }), 200

@startups_bp.route('/<int:startup_id>', methods=['GET'])
@jwt_required()
def get_startup(startup_id):
    """Get a specific startup (with ownership check)"""
    # ✅ Convert JWT identity (string) to int for comparison
    current_user_id = int(get_jwt_identity())
    startup = Startup.query.get_or_404(startup_id)
    
    if startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    return jsonify({"startup": startup.to_dict()}), 200

@startups_bp.route('/<int:startup_id>', methods=['PUT'])
@jwt_required()
def update_startup(startup_id):
    """FR-04: Update an existing startup (owner only)"""
    # ✅ Convert JWT identity (string) to int for comparison
    current_user_id = int(get_jwt_identity())
    startup = Startup.query.get_or_404(startup_id)
    
    if startup.owner_user_id != current_user_id:
        return jsonify({"msg": "Access denied"}), 403
    
    data = request.get_json()
    
    if data.get('name'):
        startup.name = data['name']
    if data.get('sector'):
        startup.sector = data['sector']
    if data.get('country'):
        startup.country = data['country']
    if data.get('registration_number'):
        startup.registration_number = data['registration_number']
    if data.get('stage'):
        startup.stage = data['stage']
    if data.get('description'):
        startup.description = data['description']
    
    fields_filled = sum([
        bool(startup.name),
        bool(startup.sector),
        bool(startup.country),
        bool(startup.registration_number),
        bool(startup.description)
    ])
    startup.profile_completion = min(100, int((fields_filled / 5) * 100))
    
    db.session.commit()
    
    return jsonify({"msg": "Startup updated", "startup": startup.to_dict()}), 200

# ⚠️ NO PROXY ROUTES HERE - they're registered via add_url_rule in app/__init__.py