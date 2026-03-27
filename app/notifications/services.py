"""
Notification services for FR-80 to FR-81.
Handles in-app, email, and SMS notifications.
"""

from datetime import datetime
from app.extensions import db
from app.models import Notification, NotificationPreference, User


def get_or_create_preferences(user_id: int) -> NotificationPreference:
    """
    Get or create notification preferences for a user.
    """
    prefs = NotificationPreference.query.filter_by(user_id=user_id).first()
    
    if not prefs:
        user = User.query.get(user_id)
        prefs = NotificationPreference(
            user_id=user_id,
            email_address=user.email if user else None,
            email_enabled=True,
            in_app_enabled=True,
            sms_enabled=False  # SMS opt-in by default
        )
        db.session.add(prefs)
        db.session.commit()
    
    return prefs


def create_notification(user_id: int, title: str, message: str, 
                        notification_type: str, related_type: str = None, 
                        related_id: int = None, send_email: bool = False,
                        send_sms: bool = False) -> Notification:
    """
    Create a notification for a user.
    
    Args:
        user_id: User to notify
        title: Notification title
        message: Notification message
        notification_type: Type ('connection', 'verification', 'document', 'billing', 'system')
        related_type: Related entity type (for deep linking)
        related_id: Related entity ID
        send_email: Whether to send email (checks preferences)
        send_sms: Whether to send SMS (checks preferences)
    
    Returns:
        Created Notification object
    """
    # Get user preferences
    prefs = get_or_create_preferences(user_id)
    
    # Create notification (in-app always if enabled)
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        related_type=related_type,
        related_id=related_id,
        is_read=False,
        sent_email=False,
        sent_sms=False
    )
    
    db.session.add(notification)
    
    # Send email if enabled and user prefers it
    if send_email and prefs.email_enabled:
        # Check type-specific preference
        if notification_type == 'connection' and prefs.email_connection_requests:
            send_email_notification(user_id, title, message)
            notification.sent_email = True
        elif notification_type == 'verification' and prefs.email_verification_updates:
            send_email_notification(user_id, title, message)
            notification.sent_email = True
        elif notification_type == 'billing' and prefs.email_billing_alerts:
            send_email_notification(user_id, title, message)
            notification.sent_email = True
        elif notification_type == 'document' and prefs.email_document_ready:
            send_email_notification(user_id, title, message)
            notification.sent_email = True
    
    # Send SMS if enabled and user prefers it
    if send_sms and prefs.sms_enabled:
        if notification_type == 'connection' and prefs.sms_connection_requests:
            send_sms_notification(user_id, title, message)
            notification.sent_sms = True
        elif notification_type == 'verification' and prefs.sms_verification_updates:
            send_sms_notification(user_id, title, message)
            notification.sent_sms = True
        elif notification_type == 'billing' and prefs.sms_billing_alerts:
            send_sms_notification(user_id, title, message)
            notification.sent_sms = True
    
    db.session.commit()
    
    return notification


def send_email_notification(user_id: int, subject: str, body: str) -> bool:
    """
    Send email notification (placeholder for actual email service).
    
    In production, integrate with:
    - SendGrid
    - AWS SES
    - Mailgun
    - SMTP server
    
    Returns:
        True if sent successfully (always True for now - placeholder)
    """
    # TODO: Integrate with actual email service
    # For now, just log that we would send an email
    user = User.query.get(user_id)
    if user:
        print(f"[EMAIL] To: {user.email} | Subject: {subject} | Body: {body[:100]}...")
        return True
    return False


def send_sms_notification(user_id: int, title: str, message: str) -> bool:
    """
    Send SMS notification (placeholder for actual SMS service).
    
    In production, integrate with:
    - Twilio
    - Africa's Talking (for Africa)
    - Vonage
    
    Returns:
        True if sent successfully (always True for now - placeholder)
    """
    # TODO: Integrate with actual SMS service
    prefs = get_or_create_preferences(user_id)
    if prefs.phone_number:
        print(f"[SMS] To: {prefs.phone_number} | Message: {title} - {message[:50]}...")
        return True
    return False


def mark_notification_as_read(notification_id: int, user_id: int) -> bool:
    """
    Mark a notification as read.
    """
    from datetime import datetime
    notification = Notification.query.get(notification_id)
    
    if not notification or notification.user_id != user_id:
        return False
    
    notification.is_read = True
    notification.read_at = datetime.now()
    db.session.commit()
    
    return True


def mark_all_notifications_as_read(user_id: int) -> int:
    """
    Mark all notifications as read for a user.
    Returns count of notifications marked.
    """
    from datetime import datetime
    notifications = Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).all()
    
    count = 0
    for notification in notifications:
        notification.is_read = True
        notification.read_at = datetime.now()
        count += 1
    
    db.session.commit()
    return count


def get_unread_count(user_id: int) -> int:
    """
    Get count of unread notifications for a user.
    """
    return Notification.query.filter_by(
        user_id=user_id,
        is_read=False,
        is_archived=False
    ).count()


# ============================================================================
# NOTIFICATION TRIGGERS (Call these from other modules)
# ============================================================================

def notify_connection_request(investor_name: str, startup_name: str, 
                               startup_owner_id: int, request_id: int):
    """
    Notify startup owner when investor sends connection request.
    """
    create_notification(
        user_id=startup_owner_id,
        title="New Connection Request",
        message=f"{investor_name} wants to connect with {startup_name}",
        notification_type='connection',
        related_type='connection_request',
        related_id=request_id,
        send_email=True,
        send_sms=False
    )


def notify_connection_accepted(startup_name: str, investor_name: str, 
                                investor_user_id: int, request_id: int):
    """
    Notify investor when startup accepts connection request.
    """
    create_notification(
        user_id=investor_user_id,
        title="Connection Accepted!",
        message=f"{startup_name} accepted your connection request. You can now contact them.",
        notification_type='connection',
        related_type='connection_request',
        related_id=request_id,
        send_email=True,
        send_sms=False
    )


def notify_verification_approved(startup_name: str, user_id: int, case_id: int):
    """
    Notify startup when verification is approved.
    """
    create_notification(
        user_id=user_id,
        title="Verification Approved! ✅",
        message=f"Congratulations! {startup_name} is now verified by Agrico Hub.",
        notification_type='verification',
        related_type='verification_case',
        related_id=case_id,
        send_email=True,
        send_sms=True  # Important news - send SMS too
    )


def notify_verification_rejected(startup_name: str, user_id: int, 
                                  case_id: int, reason: str):
    """
    Notify startup when verification is rejected.
    """
    create_notification(
        user_id=user_id,
        title="Verification Update",
        message=f"Your verification for {startup_name} needs attention. Reason: {reason}",
        notification_type='verification',
        related_type='verification_case',
        related_id=case_id,
        send_email=True,
        send_sms=False
    )


def notify_document_ready(document_title: str, user_id: int, doc_id: int):
    """
    Notify user when document generation is complete.
    """
    create_notification(
        user_id=user_id,
        title="Document Ready! 📄",
        message=f"Your document '{document_title}' is ready for download.",
        notification_type='document',
        related_type='document',
        related_id=doc_id,
        send_email=False,  # Usually not critical enough for email
        send_sms=False
    )


def notify_billing_limit_warning(user_id: int, resource_type: str, 
                                  current: int, limit: int):
    """
    Notify user when approaching billing limit.
    """
    create_notification(
        user_id=user_id,
        title="Usage Alert ⚠️",
        message=f"You've used {current}/{limit} {resource_type}(s) this month. Consider upgrading your plan.",
        notification_type='billing',
        related_type=None,
        related_id=None,
        send_email=True,
        send_sms=False
    )