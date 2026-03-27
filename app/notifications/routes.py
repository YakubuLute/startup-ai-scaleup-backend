"""
Notification Routes (FR-80 to FR-81)
- In-app notifications
- Notification preferences
- Mark as read/archive
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Notification, NotificationPreference
from app.notifications.services import (
    get_or_create_preferences,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    get_unread_count
)

notifications_bp = Blueprint('notifications', __name__)

# ============================================================================
# USER ENDPOINTS (Auth Required)
# ============================================================================

@notifications_bp.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    """
    FR-80: Get user's notifications with pagination and filters.
    """
    current_user_id = int(get_jwt_identity())
    
    # Query params
    notification_type = request.args.get('type')
    is_read = request.args.get('is_read')
    is_archived = request.args.get('is_archived', 'false')
    
    limit = min(int(request.args.get('limit', 20)), 50)
    offset = int(request.args.get('offset', 0))
    
    # Build query
    query = Notification.query.filter_by(
        user_id=current_user_id,
        is_archived=(is_archived.lower() == 'true')
    )
    
    if notification_type:
        query = query.filter_by(notification_type=notification_type)
    
    if is_read is not None:
        query = query.filter_by(is_read=(is_read.lower() == 'true'))
    
    # Order by newest first
    query = query.order_by(Notification.created_at.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    notifications = query.offset(offset).limit(limit).all()
    
    return jsonify({
        "notifications": [n.to_dict() for n in notifications],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        },
        "unread_count": get_unread_count(current_user_id)
    }), 200


@notifications_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_notification_count():
    """
    FR-80: Get count of unread notifications (for badge display).
    """
    current_user_id = int(get_jwt_identity())
    count = get_unread_count(current_user_id)
    
    return jsonify({
        "unread_count": count
    }), 200


@notifications_bp.route('/<int:notification_id>/read', methods=['POST'])
@jwt_required()
def mark_as_read(notification_id):
    """
    FR-80: Mark a single notification as read.
    """
    current_user_id = int(get_jwt_identity())
    
    success = mark_notification_as_read(notification_id, current_user_id)
    
    if not success:
        return jsonify({"msg": "Notification not found or access denied"}), 404
    
    return jsonify({
        "msg": "Notification marked as read",
        "notification_id": notification_id
    }), 200


@notifications_bp.route('/read-all', methods=['POST'])
@jwt_required()
def mark_all_as_read():
    """
    FR-80: Mark all notifications as read.
    """
    current_user_id = int(get_jwt_identity())
    count = mark_all_notifications_as_read(current_user_id)
    
    return jsonify({
        "msg": f"Marked {count} notification(s) as read",
        "count": count
    }), 200


@notifications_bp.route('/<int:notification_id>/archive', methods=['POST'])
@jwt_required()
def archive_notification(notification_id):
    """
    FR-80: Archive a notification (hide from main list).
    """
    current_user_id = int(get_jwt_identity())
    notification = Notification.query.get(notification_id)
    
    if not notification or notification.user_id != current_user_id:
        return jsonify({"msg": "Notification not found or access denied"}), 404
    
    notification.is_archived = True
    db.session.commit()
    
    return jsonify({
        "msg": "Notification archived",
        "notification_id": notification_id
    }), 200


@notifications_bp.route('/preferences', methods=['GET'])
@jwt_required()
def get_notification_preferences():
    """
    FR-80: Get user's notification preferences.
    """
    current_user_id = int(get_jwt_identity())
    prefs = get_or_create_preferences(current_user_id)
    
    return jsonify({
        "preferences": prefs.to_dict()
    }), 200


@notifications_bp.route('/preferences', methods=['PUT'])
@jwt_required()
def update_notification_preferences():
    """
    FR-80: Update user's notification preferences.
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    prefs = get_or_create_preferences(current_user_id)
    
    # Update email preferences
    if 'email' in data:  # 
        prefs.email_enabled = data['email'].get('enabled', prefs.email_enabled)
        prefs.email_connection_requests = data['email'].get('connection_requests', prefs.email_connection_requests)
        prefs.email_verification_updates = data['email'].get('verification_updates', prefs.email_verification_updates)
        prefs.email_billing_alerts = data['email'].get('billing_alerts', prefs.email_billing_alerts)
        prefs.email_document_ready = data['email'].get('document_ready', prefs.email_document_ready)
    
    # Update SMS preferences
    if 'sms' in data:  # 
        prefs.sms_enabled = data['sms'].get('enabled', prefs.sms_enabled)
        prefs.sms_connection_requests = data['sms'].get('connection_requests', prefs.sms_connection_requests)
        prefs.sms_verification_updates = data['sms'].get('verification_updates', prefs.sms_verification_updates)
        prefs.sms_billing_alerts = data['sms'].get('billing_alerts', prefs.sms_billing_alerts)
    
    # Update in-app preferences
    if 'in_app' in data:  # 
        prefs.in_app_enabled = data['in_app'].get('enabled', prefs.in_app_enabled)
    
    # Update contact info
    if 'contact' in data:  # 
        prefs.email_address = data['contact'].get('email_address', prefs.email_address)
        prefs.phone_number = data['contact'].get('phone_number', prefs.phone_number)
    
    db.session.commit()
    
    return jsonify({
        "msg": "Preferences updated successfully",
        "preferences": prefs.to_dict()
    }), 200