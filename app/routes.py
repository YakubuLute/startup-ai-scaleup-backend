from flask import Blueprint, jsonify

# Create a Blueprint for organizing routes
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return jsonify({"message": "Welcome to Startup AI Scaleup Backend!"})

@main_bp.route('/health')
def health():
    return jsonify({"status": "ok", "version": "1.0.0"})