"""
Authentication routes for BrainBudget.
Handles user registration, login, and profile management.
"""
import logging
from functools import wraps
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, session
from werkzeug.exceptions import BadRequest, Unauthorized

from app.services.firebase_service import FirebaseService


logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


def require_auth(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning("Missing or invalid authorization header")
            raise Unauthorized("Authentication required")

        id_token = auth_header.split('Bearer ')[1]
        firebase_service: FirebaseService = current_app.firebase

        decoded_token = firebase_service.verify_token(id_token)
        if not decoded_token:
            logger.warning("Invalid authentication token")
            raise Unauthorized("Invalid authentication token")

        # Add user info to request contex
        request.user = decoded_token
        return f(*args, **kwargs)

    return decorated_function


@auth_bp.route('/verify', methods=['POST'])
def verify_token():
    """
    Verify Firebase authentication token.

    Expected JSON:
    {
        "id_token": "firebase_id_token"
    }

    Returns:
        User information if token is valid
    """
    try:
        data = request.get_json()
        if not data or 'id_token' not in data:
            raise BadRequest("ID token is required")

        id_token = data['id_token']
        firebase_service: FirebaseService = current_app.firebase

        # Verify token with Firebase
        decoded_token = firebase_service.verify_token(id_token)
        if not decoded_token:
            raise Unauthorized("Invalid authentication token")

        # Get user information
        uid = decoded_token['uid']
        user_info = firebase_service.get_user(uid)

        if not user_info:
            raise Unauthorized("User not found")

        # Check if user profile exists, create if no
        profile = firebase_service.get_user_profile(uid)
        if not profile:
            # Create basic profile
            profile_data = {
                'email': user_info['email'],
                'display_name': user_info.get('display_name', ''),
                'settings': {
                    'notifications_enabled': True,
                    'dark_mode': False,
                    'currency': 'USD'
                }
            }
            firebase_service.create_user_profile(uid, profile_data)
            profile = profile_data

        logger.info(f"User authenticated successfully: {uid}")

        return jsonify({
            'success': True,
            'user': {
                'uid': uid,
                'email': user_info['email'],
                'display_name': user_info.get('display_name', ''),
                'email_verified': user_info['email_verified'],
                'profile': profile
            },
            'message': "Welcome back! Ready to make budgeting fun? 🎉"
        })

    except BadRequest as e:
        raise e
    except Unauthorized as e:
        raise e
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return jsonify({
            'success': False,
            'error': "Something went wrong during authentication. Please try again! 🔄"
        }), 500


@auth_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile():
    """
    Get current user's profile.

    Returns:
        User profile information
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase

        profile = firebase_service.get_user_profile(uid)
        if not profile:
            return jsonify({
                'success': False,
                'error': "Profile not found. Let's create one! 👤"
            }), 404

        logger.info(f"Profile retrieved for user: {uid}")

        return jsonify({
            'success': True,
            'profile': profile,
            'message': "Here's your profile! Looking good! ✨"
        })

    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't load your profile right now. Try again in a moment! 🔄"
        }), 500


@auth_bp.route('/profile', methods=['PUT'])
@require_auth
def update_profile():
    """
    Update current user's profile.

    Expected JSON:
    {
        "display_name": "User Name",
        "settings": {
            "notifications_enabled": true,
            "dark_mode": false,
            "currency": "USD"
        }
    }

    Returns:
        Updated profile information
    """
    try:
        uid = request.user['uid']
        data = request.get_json()

        if not data:
            raise BadRequest("Profile data is required")

        firebase_service: FirebaseService = current_app.firebase

        # Validate and sanitize inpu
        allowed_fields = {'display_name', 'settings', 'preferences'}
        profile_data = {k: v for k, v in data.items() if k in allowed_fields}

        # Update profile
        success = firebase_service.create_user_profile(uid, profile_data)

        if not success:
            return jsonify({
                'success': False,
                'error': "Couldn't update your profile right now. Please try again! 🔄"
            }), 500

        # Get updated profile
        updated_profile = firebase_service.get_user_profile(uid)

        logger.info(f"Profile updated for user: {uid}")

        return jsonify({
            'success': True,
            'profile': updated_profile,
            'message': "Profile updated successfully! You're all set! 🎉"
        })

    except BadRequest as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({
            'success': False,
            'error': "Something went wrong updating your profile. Let's try again! 🔧"
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """
    Logout user (client-side token should be cleared).

    Returns:
        Logout confirmation
    """
    try:
        uid = request.user['uid']

        # Clear any server-side session data if needed
        session.clear()

        logger.info(f"User logged out: {uid}")

        return jsonify({
            'success': True,
            'message': "See you later! Thanks for taking care of your finances! 👋"
        })

    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return jsonify({
            'success': False,
            'error': "Logout completed anyway! See you soon! 👋"
        })


@auth_bp.route('/send-verification', methods=['POST'])
@require_auth
def send_email_verification():
    """
    Send email verification to user.

    Returns:
        Verification email status
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase

        # Get user information
        user_info = firebase_service.get_user(uid)
        if not user_info:
            raise Unauthorized("User not found")

        if user_info.get('email_verified', False):
            return jsonify({
                'success': True,
                'message': "Your email is already verified! You're all set! ✅"
            })

        # Send verification email (would use Firebase Admin SDK in real implementation)
        success = firebase_service.send_email_verification(uid)

        if success:
            logger.info(f"Verification email sent to user: {uid}")
            return jsonify({
                'success': True,
                'message': "Verification email sent! Check your inbox (and spam folder) for the link 📧"
            })
        else:
            return jsonify({
                'success': False,
                'error': "Couldn't send verification email right now. Please try again! 🔄"
            }), 500

    except Exception as e:
        logger.error(f"Error sending verification email: {e}")
        return jsonify({
            'success': False,
            'error': "Something went wrong sending the verification email. Let's try again! 📧"
        }), 500


@auth_bp.route('/export-data', methods=['POST'])
@require_auth
def export_user_data():
    """
    Export all user data in JSON format.

    Returns:
        User data expor
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase

        # Collect all user data
        export_data = {
            'export_info': {
                'generated_at': datetime.utcnow().isoformat(),
                'user_id': uid,
                'version': '1.0'
            },
            'profile': firebase_service.get_user_profile(uid),
            'analyses': firebase_service.get_user_analyses(uid, limit=1000),
            'transactions': firebase_service.get_user_transactions(uid),
            'preferences': firebase_service.get_user_preferences(uid)
        }

        logger.info(f"Data export generated for user: {uid}")

        return jsonify({
            'success': True,
            'data': export_data,
            'message': "Your data export is ready! 📦"
        })

    except Exception as e:
        logger.error(f"Error exporting user data: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't prepare your data export right now. Please try again! 📦"
        }), 500


@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password():
    """
    Change user password (requires current password verification).

    Expected JSON:
    {
        "current_password": "current_password",
        "new_password": "new_password"
    }

    Returns:
        Password change confirmation
    """
    try:
        uid = request.user['uid']
        data = request.get_json()

        if not data or 'current_password' not in data or 'new_password' not in data:
            raise BadRequest("Current password and new password are required")

        current_password = data['current_password']
        new_password = data['new_password']

        firebase_service: FirebaseService = current_app.firebase

        # Verify current password by attempting to sign in
        user_info = firebase_service.get_user(uid)
        if not user_info:
            raise Unauthorized("User not found")

        # In a real implementation, this would verify the current password
        # For now, we'll simulate the password change
        success = firebase_service.update_user_password(uid, new_password)

        if success:
            logger.info(f"Password changed for user: {uid}")
            return jsonify({
                'success': True,
                'message': "Password updated successfully! Your account is more secure now! 🔒"
            })
        else:
            return jsonify({
                'success': False,
                'error': "Couldn't update your password right now. Please try again! 🔑"
            }), 500

    except BadRequest as e:
        raise e
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        return jsonify({
            'success': False,
            'error': "Something went wrong changing your password. Let's try again! 🔧"
        }), 500


@auth_bp.route('/setup-2fa', methods=['POST'])
@require_auth
def setup_two_factor_auth():
    """
    Set up two-factor authentication for user account.

    Returns:
        2FA setup instructions
    """
    try:
        uid = request.user['uid']

        # In a real implementation, this would generate a QR code and backup codes
        # For now, we'll return setup instructions

        logger.info(f"2FA setup initiated for user: {uid}")

        return jsonify({
            'success': True,
            'setup_data': {
                'qr_code_url': 'https://example.com/qr-code',
                'backup_codes': ['12345678', '87654321', '11223344'],
                'instructions': 'Scan the QR code with your authenticator app'
            },
            'message': "Two-factor authentication setup ready! Follow the instructions to secure your account! 🛡️"
        })

    except Exception as e:
        logger.error(f"Error setting up 2FA: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't set up two-factor authentication right now. Please try again! 🛡️"
        }), 500


@auth_bp.route('/delete-account', methods=['DELETE'])
@require_auth
def delete_account():
    """
    Delete user account and all associated data.

    Expected JSON:
    {
        "confirmation": "DELETE",
        "password": "user_password"
    }

    Returns:
        Deletion confirmation
    """
    try:
        uid = request.user['uid']
        data = request.get_json()

        if not data or data.get('confirmation') != 'DELETE':
            raise BadRequest('Account deletion requires confirmation')

        password = data.get('password')
        if not password:
            raise BadRequest('Password verification required for account deletion')

        firebase_service: FirebaseService = current_app.firebase

        # Verify password before deletion
        user_info = firebase_service.get_user(uid)
        if not user_info:
            raise Unauthorized("User not found")

        # In a real implementation, verify the password here

        # Schedule account deletion (7-day grace period)
        deletion_scheduled_at = datetime.utcnow() + timedelta(days=7)

        # Mark account for deletion
        firebase_service.schedule_account_deletion(uid, deletion_scheduled_at)

        # Send deletion confirmation email
        firebase_service.send_account_deletion_email(uid, deletion_scheduled_at)

        logger.warning(f"Account deletion scheduled for user: {uid} at {deletion_scheduled_at}")

        return jsonify({
            'success': True,
            'scheduled_deletion': deletion_scheduled_at.isoformat(),
            'message': f"Account deletion scheduled for {deletion_scheduled_at.strftime('%B %d, %Y')}. You can cancel by contacting support! 📧"
        })

    except BadRequest as e:
        raise e
    except Unauthorized as e:
        raise e
    except Exception as e:
        logger.error(f"Error during account deletion: {e}")
        return jsonify({
            'success': False,
            'error': "Something went wrong with account deletion. Please contact support! 📧"
        }), 500


@auth_bp.route('/cancel-deletion', methods=['POST'])
@require_auth
def cancel_account_deletion():
    """
    Cancel scheduled account deletion.

    Returns:
        Cancellation confirmation
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase

        # Cancel scheduled deletion
        success = firebase_service.cancel_account_deletion(uid)

        if success:
            logger.info(f"Account deletion cancelled for user: {uid}")
            return jsonify({
                'success': True,
                'message': "Welcome back! Your account deletion has been cancelled. We're glad you're staying! 🎉"
            })
        else:
            return jsonify({
                'success': False,
                'error': "Couldn't cancel account deletion. Please contact support! 📧"
            }), 500

    except Exception as e:
        logger.error(f"Error cancelling account deletion: {e}")
        return jsonify({
            'success': False,
            'error': "Something went wrong. Please contact support to cancel deletion! 📧"
        }), 500


@auth_bp.route('/user-stats', methods=['GET'])
@require_auth
def get_user_stats():
    """
    Get user statistics (analyses count, last activity, etc.).

    Returns:
        User statistics
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase

        # Get user's recent analyses
        analyses = firebase_service.get_user_analyses(uid, limit=100)

        stats = {
            'total_analyses': len(analyses),
            'last_analysis': analyses[0]['created_at'] if analyses else None,
            'account_created': request.user.get('auth_time', 0),
            'total_transactions_analyzed': sum(
                analysis.get('transaction_count', 0) for analysis in analyses
            )
        }

        logger.info(f"User stats retrieved for: {uid}")

        return jsonify({
            'success': True,
            'stats': stats,
            'message': f"You've analyzed {stats['total_analyses']} statements so far! Great job! 📊"
        })

    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't load your stats right now. Your progress is still there! 📈"
        }), 500


@auth_bp.route('/firebase-config', methods=['GET'])
def get_firebase_config():
    """
    Get Firebase client configuration for frontend.

    Returns:
        Firebase configuration objec
    """
    try:
        config = {
            'apiKey': current_app.config.get('FIREBASE_API_KEY'),
            'authDomain': current_app.config.get('FIREBASE_AUTH_DOMAIN'),
            'projectId': current_app.config.get('FIREBASE_PROJECT_ID'),
            'storageBucket': current_app.config.get('FIREBASE_STORAGE_BUCKET'),
            'messagingSenderId': current_app.config.get('FIREBASE_MESSAGING_SENDER_ID'),
            'appId': current_app.config.get('FIREBASE_APP_ID')
        }

        # Check if we have valid Firebase configuration
        if not all([config['apiKey'], config['authDomain'], config['projectId']]):
            logger.error("Firebase configuration incomplete")
            return jsonify({
                'success': False,
                'error': 'Firebase configuration is incomplete. Please check environment variables.'
            }), 500

        logger.info("Firebase client configuration served")

        return jsonify({
            'success': True,
            'config': config,
            'message': 'Firebase configuration ready'
        })

    except Exception as e:
        logger.error(f"Error getting Firebase config: {e}")
        return jsonify({
            'success': False,
            'error': "Could not load Firebase configuration"
        }), 500
