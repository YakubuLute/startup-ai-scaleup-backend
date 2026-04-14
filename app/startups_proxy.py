# app/startups_proxy.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Startup, User
# Import the view functions from the main startups module
from app.startups import (
    create_startup,
    get_user_startups, 
    get_startup,
    update_startup,  # ← You'll need to create this if it doesn't exist
    delete_startup   # ← You'll need to create this if it doesn't exist
)

# Create a NEW blueprint for proxy routes
startups_proxy_bp = Blueprint('startups_proxy', __name__)

# Register the SAME view functions but they'll be served at /api/proxy/startups/*
# because of the url_prefix in app/__init__.py

@startups_proxy_bp.route('', methods=['GET'])
@jwt_required()
def list_startups_proxy():
    """Proxy alias: GET /api/proxy/startups"""
    return get_user_startups()

@startups_proxy_bp.route('/<int:startup_id>', methods=['GET'])
@jwt_required()
def get_startup_proxy(startup_id):
    """Proxy alias: GET /api/proxy/startups/<id>"""
    return get_startup(startup_id)

@startups_proxy_bp.route('', methods=['POST'])
@jwt_required()
def create_startup_proxy():
    """Proxy alias: POST /api/proxy/startups"""
    return create_startup()

@startups_proxy_bp.route('/<int:startup_id>', methods=['PUT'])
@jwt_required()
def update_startup_proxy(startup_id):
    """Proxy alias: PUT /api/proxy/startups/<id>"""
    return update_startup(startup_id)

@startups_proxy_bp.route('/<int:startup_id>', methods=['DELETE'])
@jwt_required()
def delete_startup_proxy(startup_id):
    """Proxy alias: DELETE /api/proxy/startups/<id>"""
    return delete_startup(startup_id)