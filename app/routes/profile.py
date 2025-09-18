"""
Profile management routes for BrainBudget.
Handles user profile information, editing, achievements, and timeline.
"""
from flask import Blueprint, request, jsonify, session, current_app
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import json

logger = logging.getLogger(__name__)

# Create blueprint for profile routes
profile_bp = Blueprint('profile', __name__, url_prefix='/api/profile')


def require_auth():
    """Check if user is authenticated."""
    if not session.get('user_id'):
        return False
    return True


def get_current_user_id():
    """Get current user ID from session."""
    return session.get('user_id')


def get_current_user_email():
    """Get current user email from session."""
    return session.get('user_email')


def get_current_user_name():
    """Get current user name from session."""
    return session.get('user_name', '')


@profile_bp.route('/info', methods=['GET'])
def get_profile_info():
    """Get user profile information."""
    try:
        if not require_auth():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user_id = get_current_user_id()
        user_email = get_current_user_email()
        user_name = get_current_user_name()
        
        # Get Firebase service
        firebase_service = current_app.firebase
        
        # Try to get user profile from Firebase
        profile_data = None
        if firebase_service and firebase_service._initialized:
            profile_data = firebase_service.get_user_profile(user_id)
            
            # Get additional Firebase user info
            firebase_user = firebase_service.get_user(user_id)
            if firebase_user:
                user_email = firebase_user.get('email', user_email)
                user_name = firebase_user.get('display_name', user_name)
        
        # Create profile info with defaults
        profile_info = {
            'uid': user_id,
            'email': user_email,
            'display_name': user_name or user_email.split('@')[0].title() if user_email else 'User',
            'first_name': '',
            'last_name': '',
            'profile_picture': None,
            'join_date': datetime.now().strftime('%B %d, %Y'),
            'profile_type': 'Balanced User',
            'primary_challenges': ['Budget tracking', 'Goal setting'],
            'learning_style': 'Visual + Interactive',
            'preferences': {
                'currency': 'USD',
                'notifications': True,
                'theme': 'light'
            }
        }
        
        # Merge with Firebase data if available
        if profile_data:
            profile_info.update(profile_data)
            
            # Handle join date from Firebase
            if 'created_at' in profile_data:
                try:
                    join_date = profile_data['created_at']
                    if hasattr(join_date, 'strftime'):
                        profile_info['join_date'] = join_date.strftime('%B %d, %Y')
                    elif isinstance(join_date, str):
                        parsed_date = datetime.fromisoformat(join_date.replace('Z', '+00:00'))
                        profile_info['join_date'] = parsed_date.strftime('%B %d, %Y')
                except Exception as e:
                    logger.warning(f"Error parsing join date: {e}")
        
        # Split display name into first/last if not set
        if profile_info['display_name'] and not profile_info.get('first_name'):
            name_parts = profile_info['display_name'].split(' ', 1)
            profile_info['first_name'] = name_parts[0]
            profile_info['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
        
        return jsonify({
            'success': True,
            'profile': profile_info
        })
        
    except Exception as e:
        logger.error(f"Error getting profile info: {e}")
        return jsonify({'success': False, 'error': 'Failed to load profile information'}), 500


@profile_bp.route('/update', methods=['POST'])
def update_profile():
    """Update user profile information."""
    try:
        if not require_auth():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user_id = get_current_user_id()
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['first_name', 'last_name']
        for field in required_fields:
            if field not in data or not data[field].strip():
                return jsonify({'success': False, 'error': f'{field.replace("_", " ").title()} is required'}), 400
        
        # Prepare profile update data
        profile_data = {
            'first_name': data['first_name'].strip(),
            'last_name': data['last_name'].strip(),
            'display_name': f"{data['first_name'].strip()} {data['last_name'].strip()}",
            'profile_type': data.get('profile_type', 'Balanced User'),
            'primary_challenges': data.get('primary_challenges', []),
            'learning_style': data.get('learning_style', 'Visual + Interactive'),
            'preferences': data.get('preferences', {}),
            'updated_at': datetime.now(timezone.utc)
        }
        
        # Update Firebase profile
        firebase_service = current_app.firebase
        success = False
        
        if firebase_service and firebase_service._initialized:
            success = firebase_service.create_user_profile(user_id, profile_data)
        
        if success:
            # Update session data
            session['user_name'] = profile_data['display_name']
            session.permanent = True
            
            logger.info(f"Profile updated for user {user_id}")
            return jsonify({
                'success': True, 
                'message': 'Profile updated successfully!',
                'profile': profile_data
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update profile'}), 500
        
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({'success': False, 'error': 'Failed to update profile'}), 500


@profile_bp.route('/achievements', methods=['GET'])
def get_achievements():
    """Get user achievements and stats."""
    try:
        if not require_auth():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user_id = get_current_user_id()
        
        # Get user data for calculating achievements
        firebase_service = current_app.firebase
        user_data = {}
        
        if firebase_service and firebase_service._initialized:
            # Get user transactions and analyses to calculate real stats
            transactions = firebase_service.get_user_transactions(user_id, limit=1000)
            analyses = firebase_service.get_user_analyses(user_id, limit=50)
            profile = firebase_service.get_user_profile(user_id)
            
            user_data = {
                'transactions': transactions,
                'analyses': analyses,
                'profile': profile or {}
            }
        
        # Calculate achievements based on real data
        achievements = calculate_user_achievements(user_data)
        
        return jsonify({
            'success': True,
            'achievements': achievements
        })
        
    except Exception as e:
        logger.error(f"Error getting achievements: {e}")
        return jsonify({'success': False, 'error': 'Failed to load achievements'}), 500


@profile_bp.route('/timeline', methods=['GET'])
def get_timeline():
    """Get user's financial journey timeline."""
    try:
        if not require_auth():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user_id = get_current_user_id()
        
        # Get user data for timeline
        firebase_service = current_app.firebase
        timeline_events = []
        
        if firebase_service and firebase_service._initialized:
            # Get user profile and data
            profile = firebase_service.get_user_profile(user_id)
            analyses = firebase_service.get_user_analyses(user_id, limit=20)
            
            # Generate timeline from real data
            timeline_events = generate_user_timeline(profile, analyses)
        
        # If no real data, provide demo timeline
        if not timeline_events:
            timeline_events = get_demo_timeline()
        
        return jsonify({
            'success': True,
            'timeline': timeline_events
        })
        
    except Exception as e:
        logger.error(f"Error getting timeline: {e}")
        return jsonify({'success': False, 'error': 'Failed to load timeline'}), 500


@profile_bp.route('/stats', methods=['GET'])
def get_profile_stats():
    """Get user profile statistics."""
    try:
        if not require_auth():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user_id = get_current_user_id()
        
        # Calculate stats from real data
        firebase_service = current_app.firebase
        stats = {
            'days_active': 1,
            'goals_achieved': 0,
            'user_score': 75,
            'total_saved': 0,
            'avg_monthly_save': 0,
            'total_analyses': 0,
            'last_activity': datetime.now().strftime('%B %d, %Y')
        }
        
        if firebase_service and firebase_service._initialized:
            # Get real user data
            profile = firebase_service.get_user_profile(user_id)
            analyses = firebase_service.get_user_analyses(user_id, limit=100)
            transactions = firebase_service.get_user_transactions(user_id, limit=500)
            
            # Calculate real stats
            stats = calculate_user_stats(profile, analyses, transactions)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting profile stats: {e}")
        return jsonify({'success': False, 'error': 'Failed to load statistics'}), 500


@profile_bp.route('/upload-avatar', methods=['POST'])
def upload_avatar():
    """Upload user profile picture."""
    try:
        if not require_auth():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user_id = get_current_user_id()
        
        # Check if file was uploaded
        if 'avatar' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['avatar']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'error': 'Invalid file type. Please use PNG, JPG, JPEG, or GIF.'}), 400
        
        # Validate file size (max 5MB)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            return jsonify({'success': False, 'error': 'File too large. Maximum size is 5MB.'}), 400
        
        # Upload file
        firebase_service = current_app.firebase
        file_url = None
        
        if firebase_service and firebase_service._initialized:
            file_data = file.read()
            filename = f"avatar.{file_ext}"
            file_url = firebase_service.upload_file(file_data, filename, user_id)
        
        if file_url:
            # Update user profile with new avatar URL
            profile_data = {'profile_picture': file_url}
            firebase_service.create_user_profile(user_id, profile_data)
            
            return jsonify({
                'success': True,
                'message': 'Profile picture updated successfully!',
                'avatar_url': file_url
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to upload file'}), 500
        
    except Exception as e:
        logger.error(f"Error uploading avatar: {e}")
        return jsonify({'success': False, 'error': 'Failed to upload profile picture'}), 500


def calculate_user_achievements(user_data: Dict[str, Any]) -> list:
    """Calculate user achievements based on their data."""
    achievements = []
    
    transactions = user_data.get('transactions', [])
    analyses = user_data.get('analyses', [])
    profile = user_data.get('profile', {})
    
    # First Goal Achievement
    if len(analyses) > 0:
        achievements.append({
            'id': 'first_analysis',
            'title': 'First Steps',
            'description': 'Completed first spending analysis',
            'icon': '🎯',
            'color': 'green',
            'unlocked': True,
            'date': 'Recent'
        })
    
    # Analysis Streak
    if len(analyses) >= 5:
        achievements.append({
            'id': 'analysis_streak',
            'title': 'Insight Seeker',
            'description': 'Completed 5+ spending analyses',
            'icon': '🔥',
            'color': 'orange',
            'unlocked': True,
            'date': 'Recent'
        })
    
    # Budget Warrior
    if len(transactions) > 50:
        achievements.append({
            'id': 'transaction_master',
            'title': 'Budget Warrior',
            'description': 'Tracked 50+ transactions',
            'icon': '🧠',
            'color': 'purple',
            'unlocked': True,
            'date': 'Recent'
        })
    
    # Community Helper (placeholder)
    achievements.append({
        'id': 'community_helper',
        'title': 'Getting Started',
        'description': 'Joined BrainBudget community',
        'icon': '🤝',
        'color': 'blue',
        'unlocked': True,
        'date': 'Recent'
    })
    
    return achievements


def calculate_user_stats(profile: Dict[str, Any], analyses: list, transactions: list) -> Dict[str, Any]:
    """Calculate user statistics from their data."""
    
    # Calculate days active
    days_active = 1
    if profile and 'created_at' in profile:
        try:
            join_date = profile['created_at']
            if hasattr(join_date, 'date'):
                days_active = (datetime.now().date() - join_date.date()).days + 1
            elif isinstance(join_date, str):
                parsed_date = datetime.fromisoformat(join_date.replace('Z', '+00:00'))
                days_active = (datetime.now(timezone.utc) - parsed_date).days + 1
        except Exception as e:
            logger.warning(f"Error calculating days active: {e}")
    
    # Calculate financial metrics from transactions
    total_saved = 0.0
    avg_monthly_save = 0.0
    
    if transactions:
        # Simple calculation - count positive transactions as savings
        positive_transactions = [t for t in transactions if t.get('amount', 0) > 0]
        total_saved = sum(t.get('amount', 0) for t in positive_transactions)
        
        # Calculate monthly average (rough estimation)
        if days_active > 30:
            avg_monthly_save = total_saved / (days_active / 30)
        else:
            avg_monthly_save = total_saved
    
    # Calculate user score based on activity
    user_score = min(75 + len(analyses) * 2 + min(len(transactions) // 10, 20), 100)
    
    return {
        'days_active': max(days_active, 1),
        'goals_achieved': len(analyses),
        'user_score': user_score,
        'total_saved': total_saved,
        'avg_monthly_save': avg_monthly_save,
        'total_analyses': len(analyses),
        'last_activity': datetime.now().strftime('%B %d, %Y')
    }


def generate_user_timeline(profile: Dict[str, Any], analyses: list) -> list:
    """Generate user timeline from their actual data."""
    timeline = []
    
    # Add join event
    if profile and 'created_at' in profile:
        timeline.append({
            'id': 'joined',
            'title': 'Joined BrainBudget',
            'description': 'Started your smart budgeting journey',
            'date': profile['created_at'],
            'status': 'completed',
            'icon': '🎉',
            'badge': 'Welcome Milestone'
        })
    
    # Add analysis milestones
    for i, analysis in enumerate(analyses[:5]):  # Show first 5 analyses
        timeline.append({
            'id': f'analysis_{i}',
            'title': f'Analysis #{i+1} Complete',
            'description': 'Generated spending insights and recommendations',
            'date': analysis.get('created_at', datetime.now()),
            'status': 'completed',
            'icon': '📊',
            'badge': 'Insight Generated'
        })
    
    # Add current goal (placeholder)
    timeline.append({
        'id': 'current_goal',
        'title': 'Building Smart Habits',
        'description': 'Continue using BrainBudget for financial insights',
        'date': datetime.now() + datetime.timedelta(days=30),
        'status': 'in_progress',
        'icon': '🎯',
        'badge': 'Current Goal'
    })
    
    # Sort by date
    timeline.sort(key=lambda x: x['date'], reverse=True)
    
    return timeline


def get_demo_timeline() -> list:
    """Get demo timeline for new users."""
    return [
        {
            'id': 'joined',
            'title': 'Joined BrainBudget',
            'description': 'Welcome to your smart budgeting journey!',
            'date': datetime.now().strftime('%B %d, %Y'),
            'status': 'completed',
            'icon': '🎉',
            'badge': 'Welcome!'
        },
        {
            'id': 'first_goal',
            'title': 'Set Your First Goal',
            'description': 'Upload a bank statement or connect your bank',
            'date': 'Coming up',
            'status': 'upcoming',
            'icon': '🎯',
            'badge': 'Next Step'
        }
    ]


# Error handlers for the profile blueprint
@profile_bp.errorhandler(404)
def profile_not_found(error):
    """Handle 404 errors in profile routes."""
    return jsonify({'success': False, 'error': 'Profile endpoint not found'}), 404


@profile_bp.errorhandler(500)
def profile_internal_error(error):
    """Handle 500 errors in profile routes."""
    logger.error(f"Profile route error: {error}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500