# app/auth.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.extensions import db
from app.models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({"msg": "Name, email, and password required"}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"msg": "Email already exists"}), 400
    
    new_user = User(
        name=data['name'], 
        email=data['email'], 
        role=data.get('role', 'Founder')
    )
    new_user.set_password(data['password'])
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        "message": "User created successfully",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "role": new_user.role
        }
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"msg": "Email and password required"}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None
            }
        }), 200
    
    return jsonify({"msg": "Invalid credentials"}), 401

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user profile"""
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
    
    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None
    }), 200