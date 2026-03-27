"""
Analytics & Reporting Routes (FR-90 to FR-91)
- Platform analytics dashboard
- Growth metrics
- Program performance
- Stakeholder reports
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User
from app.analytics.services import (
    get_platform_overview,
    get_growth_metrics,
    get_program_analytics,
    get_billing_analytics,
    get_top_performers,
    generate_stakeholder_report
)

analytics_bp = Blueprint('analytics', __name__)

# ============================================================================
# ADMIN ENDPOINTS (Program Manager / System Admin Only)
# ============================================================================

@analytics_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_admin_dashboard():
    """
    FR-90: Main admin dashboard with all platform metrics.
    """
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    overview = get_platform_overview()
    growth = get_growth_metrics(30)
    programs = get_program_analytics()
    
    return jsonify({
        "dashboard": {
            "overview": overview,
            "growth": growth,
            "programs": programs
        }
    }), 200

@analytics_bp.route('/overview', methods=['GET'])
@jwt_required()
def get_platform_overview_endpoint():
    """FR-90: High-level platform metrics"""
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    return jsonify(get_platform_overview()), 200

@analytics_bp.route('/growth', methods=['GET'])
@jwt_required()
def get_growth_metrics_endpoint():
    """FR-90: Growth trends over time"""
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    days = request.args.get('days', 30, type=int)
    return jsonify(get_growth_metrics(days)), 200

@analytics_bp.route('/programs', methods=['GET'])
@jwt_required()
def get_program_analytics_endpoint():
    """FR-90: Program performance metrics"""
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    return jsonify(get_program_analytics()), 200

@analytics_bp.route('/billing', methods=['GET'])
@jwt_required()
def get_billing_analytics_endpoint():
    """FR-90: Subscription & revenue metrics"""
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    return jsonify(get_billing_analytics()), 200

@analytics_bp.route('/top-performers', methods=['GET'])
@jwt_required()
def get_top_performers_endpoint():
    """FR-90: Top performing startups"""
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    limit = request.args.get('limit', 10, type=int)
    return jsonify(get_top_performers(limit)), 200

@analytics_bp.route('/report', methods=['GET'])
@jwt_required()
def generate_report():
    """
    FR-91: Generate comprehensive stakeholder report.
    """
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    program_id = request.args.get('program_id', type=int)
    report = generate_stakeholder_report(program_id)
    
    return jsonify({
        "report": report
    }), 200

@analytics_bp.route('/report/export', methods=['POST'])
@jwt_required()
def export_report():
    """
    FR-91: Export report as JSON (for external systems).
    """
    current_user_id = int(get_jwt_identity())
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role not in ['Program Manager', 'System Admin']:
        return jsonify({"msg": "Access denied"}), 403
    
    data = request.get_json() or {}
    program_id = data.get('program_id')
    
    report = generate_stakeholder_report(program_id)
    
    return jsonify({
        "msg": "Report generated successfully",
        "format": "json",
        "report": report
    }), 200