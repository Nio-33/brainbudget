"""
Notification management routes for BrainBudget.
Handles user notification preferences, FCM token registration, and notification history.
"""
from flask import Blueprint, request, jsonify, current_app
from firebase_admin import auth
import logging
from datetime import datetime, timedelta
from app.services.notification_service import NotificationService, NotificationType, NotificationPriority
from app.services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)

# Create blueprint
notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

def require_auth(f):
    """Decorator to require Firebase authentication."""
    def decorated_function(*args, **kwargs):
        try:
            # Get ID token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Missing or invalid authorization header'}), 401
            
            id_token = auth_header.split('Bearer ')[1]
            
            # Verify the ID token
            decoded_token = auth.verify_id_token(id_token)
            request.user_id = decoded_token['uid']
            
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return jsonify({'error': 'Invalid authentication token'}), 401
    
    decorated_function.__name__ = f.__name__
    return decorated_function


@notifications_bp.route('/register-token', methods=['POST'])
@require_auth
def register_fcm_token():
    """Register or update FCM token for push notifications."""
    try:
        data = request.get_json()
        token = data.get('token')
        device_info = data.get('device_info', {})
        
        if not token:
            return jsonify({'error': 'FCM token is required'}), 400
        
        firebase_service = FirebaseService()
        
        # Store or update FCM token
        token_data = {
            'token': token,
            'device_info': device_info,
            'registered_at': datetime.utcnow(),
            'active': True
        }
        
        # Use user_id as document ID and store tokens in a subcollection or map
        tokens_ref = firebase_service.db.collection('user_fcm_tokens').document(request.user_id)
        
        # Get existing tokens
        tokens_doc = tokens_ref.get()
        if tokens_doc.exists:
            existing_tokens = tokens_doc.to_dict().get('tokens', {})
        else:
            existing_tokens = {}
        
        # Add or update this token
        existing_tokens[token] = token_data
        
        # Update document
        tokens_ref.set({
            'user_id': request.user_id,
            'tokens': existing_tokens,
            'updated_at': datetime.utcnow()
        })
        
        return jsonify({
            'success': True,
            'message': 'FCM token registered successfully',
            'token_count': len(existing_tokens)
        })
        
    except Exception as e:
        logger.error(f"Error registering FCM token: {str(e)}")
        return jsonify({'error': 'Failed to register token'}), 500


@notifications_bp.route('/preferences', methods=['GET'])
@require_auth
def get_notification_preferences():
    """Get user's notification preferences."""
    try:
        firebase_service = FirebaseService()
        prefs_ref = firebase_service.db.collection('user_preferences').document(request.user_id)
        prefs_doc = prefs_ref.get()
        
        if not prefs_doc.exists:
            # Return ADHD-friendly defaults
            default_prefs = {
                'notifications': {
                    'enabled': True,
                    'types': {
                        'spending_alert': {
                            'enabled': True,
                            'threshold': 80,
                            'frequency': 'moderate'
                        },
                        'unusual_pattern': {
                            'enabled': True,
                            'frequency': 'moderate'
                        },
                        'goal_achievement': {
                            'enabled': True,
                            'frequency': 'all'
                        },
                        'weekly_summary': {
                            'enabled': True,
                            'day': 'sunday',
                            'time': '09:00'
                        },
                        'bill_reminder': {
                            'enabled': False,  # Opt-in
                            'days_before': [3, 1]
                        },
                        'encouragement': {
                            'enabled': True,
                            'frequency': 'moderate'
                        }
                    },
                    'quiet_hours': {
                        'enabled': True,
                        'start': 22,  # 10 PM
                        'end': 8     # 8 AM
                    },
                    'timezone': 'UTC',
                    'tone': 'gentle',  # gentle, encouraging, direct
                    'frequency': 'moderate',  # minimal, moderate, frequent
                    'max_daily': 10
                }
            }
            
            # Save defaults
            prefs_ref.set(default_prefs)
            return jsonify(default_prefs['notifications'])
        
        notifications_prefs = prefs_doc.to_dict().get('notifications', {})
        return jsonify(notifications_prefs)
        
    except Exception as e:
        logger.error(f"Error getting notification preferences: {str(e)}")
        return jsonify({'error': 'Failed to get preferences'}), 500


@notifications_bp.route('/preferences', methods=['PUT'])
@require_auth
def update_notification_preferences():
    """Update user's notification preferences."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Notification preferences data is required'}), 400
        
        firebase_service = FirebaseService()
        prefs_ref = firebase_service.db.collection('user_preferences').document(request.user_id)
        
        # Get existing preferences
        prefs_doc = prefs_ref.get()
        if prefs_doc.exists:
            existing_prefs = prefs_doc.to_dict()
        else:
            existing_prefs = {}
        
        # Update notification preferences
        existing_prefs['notifications'] = data
        existing_prefs['updated_at'] = datetime.utcnow()
        
        prefs_ref.set(existing_prefs)
        
        # Log preference change for analytics
        firebase_service.db.collection('notification_preference_changes').add({
            'user_id': request.user_id,
            'changes': data,
            'timestamp': datetime.utcnow()
        })
        
        return jsonify({
            'success': True,
            'message': 'Notification preferences updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating notification preferences: {str(e)}")
        return jsonify({'error': 'Failed to update preferences'}), 500


@notifications_bp.route('/test', methods=['POST'])
@require_auth
def send_test_notification():
    """Send a test notification to verify setup."""
    try:
        data = request.get_json() or {}
        notification_type = data.get('type', 'encouragement')
        
        notification_service = NotificationService()
        
        # Send test notification based on type
        if notification_type == 'spending_alert':
            success = notification_service.send_spending_alert(
                request.user_id,
                category="Dining",
                percentage=75,
                amount_spent=150.0,
                budget_limit=200.0
            )
        elif notification_type == 'goal_achievement':
            success = notification_service.send_goal_achievement(
                request.user_id,
                goal_name="Stay under dining budget",
                achievement_type="milestone"
            )
        else:
            success = notification_service.send_encouragement(
                request.user_id,
                message_type="daily"
            )
        
        return jsonify({
            'success': success,
            'message': 'Test notification sent' if success else 'Failed to send test notification'
        })
        
    except Exception as e:
        logger.error(f"Error sending test notification: {str(e)}")
        return jsonify({'error': 'Failed to send test notification'}), 500


@notifications_bp.route('/history', methods=['GET'])
@require_auth
def get_notification_history():
    """Get user's notification history."""
    try:
        firebase_service = FirebaseService()
        
        # Get pagination parameters
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        notification_type = request.args.get('type')
        
        # Build query
        query = firebase_service.db.collection('notification_logs').where('user_id', '==', request.user_id)
        
        if notification_type:
            query = query.where('type', '==', notification_type)
        
        query = query.order_by('timestamp', direction='DESCENDING')
        query = query.limit(limit).offset(offset)
        
        # Execute query
        docs = query.stream()
        notifications = []
        
        for doc in docs:
            notification_data = doc.to_dict()
            notification_data['id'] = doc.id
            
            # Convert timestamp to ISO string
            if 'timestamp' in notification_data:
                notification_data['timestamp'] = notification_data['timestamp'].isoformat()
            
            notifications.append(notification_data)
        
        return jsonify({
            'notifications': notifications,
            'total': len(notifications),
            'offset': offset,
            'limit': limit
        })
        
    except Exception as e:
        logger.error(f"Error getting notification history: {str(e)}")
        return jsonify({'error': 'Failed to get notification history'}), 500


@notifications_bp.route('/stats', methods=['GET'])
@require_auth
def get_notification_stats():
    """Get user's notification engagement statistics."""
    try:
        firebase_service = FirebaseService()
        
        # Get stats for last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        # Query notification logs
        query = firebase_service.db.collection('notification_logs')
        query = query.where('user_id', '==', request.user_id)
        query = query.where('timestamp', '>=', start_date)
        query = query.where('timestamp', '<=', end_date)
        
        docs = query.stream()
        
        # Calculate statistics
        total_sent = 0
        total_successful = 0
        type_counts = {}
        
        for doc in docs:
            data = doc.to_dict()
            total_sent += 1
            
            if data.get('success', False):
                total_successful += 1
            
            notification_type = data.get('type', 'unknown')
            type_counts[notification_type] = type_counts.get(notification_type, 0) + 1
        
        success_rate = (total_successful / total_sent * 100) if total_sent > 0 else 0
        
        return jsonify({
            'period_days': 30,
            'total_sent': total_sent,
            'total_successful': total_successful,
            'success_rate': round(success_rate, 1),
            'type_breakdown': type_counts,
            'average_daily': round(total_sent / 30, 1)
        })
        
    except Exception as e:
        logger.error(f"Error getting notification stats: {str(e)}")
        return jsonify({'error': 'Failed to get notification stats'}), 500


@notifications_bp.route('/unsubscribe', methods=['POST'])
@require_auth
def unsubscribe_from_notifications():
    """Unsubscribe from all notifications (nuclear option)."""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'user_request')
        
        firebase_service = FirebaseService()
        
        # Disable all notifications
        prefs_ref = firebase_service.db.collection('user_preferences').document(request.user_id)
        prefs_doc = prefs_ref.get()
        
        if prefs_doc.exists:
            prefs = prefs_doc.to_dict()
        else:
            prefs = {}
        
        # Set notifications to disabled
        prefs['notifications'] = prefs.get('notifications', {})
        prefs['notifications']['enabled'] = False
        prefs['notifications']['unsubscribed_at'] = datetime.utcnow()
        prefs['notifications']['unsubscribe_reason'] = reason
        
        prefs_ref.set(prefs)
        
        # Log unsubscribe for analytics
        firebase_service.db.collection('notification_unsubscribes').add({
            'user_id': request.user_id,
            'reason': reason,
            'timestamp': datetime.utcnow()
        })
        
        return jsonify({
            'success': True,
            'message': 'Successfully unsubscribed from all notifications'
        })
        
    except Exception as e:
        logger.error(f"Error unsubscribing from notifications: {str(e)}")
        return jsonify({'error': 'Failed to unsubscribe'}), 500


@notifications_bp.route('/resubscribe', methods=['POST'])
@require_auth  
def resubscribe_to_notifications():
    """Resubscribe to notifications with ADHD-friendly defaults."""
    try:
        firebase_service = FirebaseService()
        
        prefs_ref = firebase_service.db.collection('user_preferences').document(request.user_id)
        prefs_doc = prefs_ref.get()
        
        if prefs_doc.exists:
            prefs = prefs_doc.to_dict()
        else:
            prefs = {}
        
        # Re-enable with gentle defaults
        prefs['notifications'] = {
            'enabled': True,
            'types': {
                'spending_alert': {'enabled': True, 'threshold': 85},  # Higher threshold
                'goal_achievement': {'enabled': True},
                'weekly_summary': {'enabled': True},
                'encouragement': {'enabled': True},
                'unusual_pattern': {'enabled': False},  # Start disabled
                'bill_reminder': {'enabled': False}     # Start disabled
            },
            'quiet_hours': {'enabled': True, 'start': 22, 'end': 8},
            'tone': 'gentle',
            'frequency': 'minimal',  # Start with minimal
            'max_daily': 5,          # Lower limit
            'resubscribed_at': datetime.utcnow()
        }
        
        prefs_ref.set(prefs)
        
        return jsonify({
            'success': True,
            'message': 'Welcome back! Notifications re-enabled with gentle settings.'
        })
        
    except Exception as e:
        logger.error(f"Error resubscribing to notifications: {str(e)}")
        return jsonify({'error': 'Failed to resubscribe'}), 500


# Health check for notification system
@notifications_bp.route('/health', methods=['GET'])
def notification_health():
    """Health check for notification system."""
    try:
        # Basic health check
        firebase_service = FirebaseService()
        
        # Test Firestore connection
        test_doc = firebase_service.db.collection('health_check').document('notification_test')
        test_doc.set({'timestamp': datetime.utcnow(), 'status': 'healthy'})
        
        return jsonify({
            'status': 'healthy',
            'component': 'notifications',
            'timestamp': datetime.utcnow().isoformat(),
            'fcm_configured': bool(current_app.config.get('FCM_SERVER_KEY'))
        }), 200
        
    except Exception as e:
        logger.error(f"Notification health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'component': 'notifications',
            'error': str(e)
        }), 503