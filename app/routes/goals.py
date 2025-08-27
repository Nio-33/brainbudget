"""
ADHD-Friendly Goal Management API Routes for BrainBudge
Provides endpoints for creating, managing, and tracking financial goals
"""
from flask import Blueprint, request, jsonify, current_app
from firebase_admin import auth
import logging
from datetime import datetime, timedelta
from app.services.goals_service import GoalsService
from app.services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)

# Create blueprin
goals_bp = Blueprint('goals', __name__, url_prefix='/api/goals')

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


@goals_bp.route('/', methods=['GET'])
@require_auth
def get_goals():
    """Get all goals for the authenticated user."""
    try:
        status_filter = request.args.get('status')
        include_completed = request.args.get('include_completed', 'true').lower() == 'true'

        goals_service = GoalsService()
        goals = goals_service.get_user_goals_sync(
            request.user_id,
            status_filter=status_filter,
            include_completed=include_completed
        )

        return jsonify({
            'goals': goals,
            'total_count': len(goals)
        })

    except Exception as e:
        logger.error(f"Error getting goals: {str(e)}")
        return jsonify({'error': 'Failed to retrieve goals'}), 500


@goals_bp.route('/', methods=['POST'])
@require_auth
def create_goal():
    """Create a new ADHD-friendly goal."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Goal data is required'}), 400

        # Validate required fields
        required_fields = ['type', 'name', 'target_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Set ADHD-friendly defaults
        goal_data = {
            'type': data['type'],
            'name': data['name'],
            'description': data.get('description', ''),
            'category': data.get('category'),
            'target_amount': float(data.get('target_amount', 0)),
            'current_amount': float(data.get('current_amount', 0)),
            'target_date': data['target_date'],
            'difficulty': data.get('difficulty', 'moderate'),
            'allow_adjustments': data.get('allow_adjustments', True),
            'celebration_style': data.get('celebration_style', 'gentle'),
            'reminder_frequency': data.get('reminder_frequency', 'weekly'),
            'adhd_tips_enabled': data.get('adhd_tips_enabled', True),
            'template_id': data.get('template_id'),
            'creation_method': data.get('creation_method', 'manual'),
            'tags': data.get('tags', [])
        }

        goals_service = GoalsService()
        goal = goals_service.create_goal_sync(request.user_id, goal_data)

        return jsonify({
            'success': True,
            'goal': goal,
            'message': f'🎯 Goal "{goal["name"]}" created! Let\'s break it into manageable steps.'
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating goal: {str(e)}")
        return jsonify({'error': 'Failed to create goal'}), 500


@goals_bp.route('/<goal_id>', methods=['GET'])
@require_auth
def get_goal(goal_id):
    """Get a specific goal by ID."""
    try:
        goals_service = GoalsService()
        goals = goals_service.get_user_goals_sync(request.user_id)

        goal = next((g for g in goals if g.get('id') == goal_id), None)
        if not goal:
            return jsonify({'error': 'Goal not found'}), 404

        return jsonify({'goal': goal})

    except Exception as e:
        logger.error(f"Error getting goal {goal_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve goal'}), 500


@goals_bp.route('/<goal_id>/progress', methods=['POST'])
@require_auth
def update_goal_progress(goal_id):
    """Update progress for a specific goal."""
    try:
        data = request.get_json()

        new_amount = data.get('amount')
        transaction_data = data.get('transaction')

        if new_amount is None and transaction_data is None:
            return jsonify({'error': 'Either amount or transaction data is required'}), 400

        goals_service = GoalsService()
        updated_goal = goals_service.update_goal_progress_sync(
            request.user_id,
            goal_id,
            new_amount=new_amount,
            transaction_data=transaction_data
        )

        # Generate encouraging response message
        progress_pct = updated_goal.get('progress', {}).get('percentage', 0)

        if progress_pct >= 100:
            message = f"🎉 Incredible! You completed your goal: {updated_goal['name']}!"
        elif progress_pct >= 75:
            message = f"🌟 Amazing! You're at {progress_pct:.1f}% - almost there!"
        elif progress_pct >= 50:
            message = f"💪 Great progress! You're halfway to your goal at {progress_pct:.1f}%"
        elif progress_pct >= 25:
            message = f"🚀 Nice work! You've made solid progress at {progress_pct:.1f}%"
        else:
            message = f"🌱 Every step counts! You're at {progress_pct:.1f}% - keep going!"

        return jsonify({
            'success': True,
            'goal': updated_goal,
            'message': message
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating goal progress: {str(e)}")
        return jsonify({'error': 'Failed to update goal progress'}), 500


@goals_bp.route('/<goal_id>/adjust', methods=['PUT'])
@require_auth
def adjust_goal(goal_id):
    """ADHD-friendly goal adjustment without shame."""
    try:
        data = request.get_json()

        if not data or 'adjustments' not in data:
            return jsonify({'error': 'Adjustments data is required'}), 400

        adjustments = data['adjustments']
        reason = data.get('reason', 'user_adjustment')

        # Validate adjustments
        allowed_adjustments = ['target_amount', 'target_date', 'name', 'description']
        for key in adjustments.keys():
            if key not in allowed_adjustments:
                return jsonify({'error': f'Invalid adjustment field: {key}'}), 400

        goals_service = GoalsService()
        adjusted_goal = goals_service.adjust_goal_sync(
            request.user_id,
            goal_id,
            adjustments,
            reason
        )

        return jsonify({
            'success': True,
            'goal': adjusted_goal,
            'message': '✨ Goal adjusted perfectly! Flexibility is a strength, not a weakness.'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error adjusting goal: {str(e)}")
        return jsonify({'error': 'Failed to adjust goal'}), 500


@goals_bp.route('/<goal_id>/pause', methods=['POST'])
@require_auth
def pause_goal(goal_id):
    """Pause a goal without shame - ADHD brains sometimes need breaks!"""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'need_a_break')

        goals_service = GoalsService()
        paused_goal = goals_service.pause_goal_sync(
            request.user_id,
            goal_id,
            reason
        )

        return jsonify({
            'success': True,
            'goal': paused_goal,
            'message': '😌 Goal paused. Taking breaks is healthy and shows self-awareness. You can resume whenever you\'re ready!'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error pausing goal: {str(e)}")
        return jsonify({'error': 'Failed to pause goal'}), 500


@goals_bp.route('/<goal_id>/resume', methods=['POST'])
@require_auth
def resume_goal(goal_id):
    """Resume a paused goal with encouragement."""
    try:
        data = request.get_json() or {}
        extend_deadline = data.get('extend_deadline', True)

        goals_service = GoalsService()
        resumed_goal = goals_service.resume_goal_sync(
            request.user_id,
            goal_id,
            extend_deadline
        )

        return jsonify({
            'success': True,
            'goal': resumed_goal,
            'message': '🌅 Welcome back! You\'re showing incredible resilience by resuming your goal. Let\'s do this!'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error resuming goal: {str(e)}")
        return jsonify({'error': 'Failed to resume goal'}), 500


@goals_bp.route('/templates', methods=['GET'])
@require_auth
def get_goal_templates():
    """Get ADHD-friendly goal templates."""
    try:
        goals_service = GoalsService()
        templates = goals_service.get_goal_templates_sync()

        return jsonify({
            'templates': templates,
            'message': '🎯 Here are some proven goal templates to help you get started!'
        })

    except Exception as e:
        logger.error(f"Error getting goal templates: {str(e)}")
        return jsonify({'error': 'Failed to retrieve goal templates'}), 500


@goals_bp.route('/achievements', methods=['GET'])
@require_auth
def get_achievements():
    """Get user's achievements and progress."""
    try:
        goals_service = GoalsService()
        achievements = goals_service.get_user_achievements_sync(request.user_id)

        # Calculate achievement stats
        total_achievements = len(achievements)
        unlocked_achievements = len([a for a in achievements if a.get('unlocked')])
        progress_percentage = (unlocked_achievements / total_achievements * 100) if total_achievements > 0 else 0

        return jsonify({
            'achievements': achievements,
            'stats': {
                'total': total_achievements,
                'unlocked': unlocked_achievements,
                'progress_percentage': round(progress_percentage, 1)
            }
        })

    except Exception as e:
        logger.error(f"Error getting achievements: {str(e)}")
        return jsonify({'error': 'Failed to retrieve achievements'}), 500


@goals_bp.route('/analytics', methods=['GET'])
@require_auth
def get_goal_analytics():
    """Get analytics data for user's goal progress."""
    try:
        goals_service = GoalsService()
        analytics = goals_service.get_goal_analytics_sync(request.user_id)

        return jsonify({
            'analytics': analytics,
            'message': '📊 Here\'s your goal journey so far - every step is progress!'
        })

    except Exception as e:
        logger.error(f"Error getting goal analytics: {str(e)}")
        return jsonify({'error': 'Failed to retrieve goal analytics'}), 500


@goals_bp.route('/<goal_id>/milestones/<milestone_id>/complete', methods=['POST'])
@require_auth
def complete_milestone(goal_id, milestone_id):
    """Mark a milestone as completed manually."""
    try:
        goals_service = GoalsService()

        # Get the goal
        goals = goals_service.get_user_goals_sync(request.user_id)
        goal = next((g for g in goals if g.get('id') == goal_id), None)

        if not goal:
            return jsonify({'error': 'Goal not found'}), 404

        # Find and complete the milestone
        milestones = goal.get('milestones', [])
        milestone = next((m for m in milestones if m.get('id') == milestone_id), None)

        if not milestone:
            return jsonify({'error': 'Milestone not found'}), 404

        if milestone.get('completed'):
            return jsonify({'error': 'Milestone already completed'}), 400

        # Mark as completed
        milestone['completed'] = True
        milestone['completed_date'] = datetime.utcnow().isoformat()
        milestone['celebration_sent'] = False

        # Update goal progress
        goal['progress']['milestones_completed'] = goal['progress'].get('milestones_completed', 0) + 1

        # Save updated goal
        firebase_service = FirebaseService()
        goal_ref = firebase_service.db.collection('user_goals').document(f"{request.user_id}_{goal_id}")
        goal_ref.set(goal)

        return jsonify({
            'success': True,
            'milestone': milestone,
            'message': f'🎉 Milestone completed: {milestone["title"]}! You\'re making amazing progress!'
        })

    except Exception as e:
        logger.error(f"Error completing milestone: {str(e)}")
        return jsonify({'error': 'Failed to complete milestone'}), 500


@goals_bp.route('/share/<goal_id>', methods=['POST'])
@require_auth
def share_goal_progress(goal_id):
    """Share goal progress (future feature for accountability partners)."""
    try:
        data = request.get_json() or {}
        share_type = data.get('type', 'achievement')  # achievement, milestone, progress
        message = data.get('message', '')

        # For now, just return a success message
        # In the future, this would integrate with social features

        return jsonify({
            'success': True,
            'message': '📢 Goal progress shared! (Feature coming soon - we\'ll add social sharing options)'
        })

    except Exception as e:
        logger.error(f"Error sharing goal progress: {str(e)}")
        return jsonify({'error': 'Failed to share goal progress'}), 500


@goals_bp.route('/<goal_id>/celebrate', methods=['POST'])
@require_auth
def celebrate_goal(goal_id):
    """Trigger a celebration for goal or milestone completion."""
    try:
        data = request.get_json() or {}
        celebration_type = data.get('type', 'milestone')  # milestone, goal, achievemen

        # This would trigger celebration animations and sounds in the frontend
        # For now, return encouragemen

        celebrations = {
            'milestone': '🎉 Amazing work on reaching this milestone! Every step forward is a victory!',
            'goal': '🏆 INCREDIBLE! You completed your goal! This is a huge achievement and you should be so proud!',
            'achievement': '🌟 You unlocked an achievement! Your consistency and dedication are paying off!'
        }

        message = celebrations.get(celebration_type, '🎊 Celebration time! You\'re doing fantastic!')

        return jsonify({
            'success': True,
            'celebration_type': celebration_type,
            'message': message,
            'confetti': True,  # Trigger confetti animation in frontend
            'sound': 'success'  # Play success sound
        })

    except Exception as e:
        logger.error(f"Error celebrating goal: {str(e)}")
        return jsonify({'error': 'Failed to celebrate goal'}), 500


# Health check for goals system
@goals_bp.route('/health', methods=['GET'])
def goals_health():
    """Health check for goals system."""
    try:
        goals_service = GoalsService()

        # Test basic functionality
        templates = goals_service.get_goal_templates_sync()

        return jsonify({
            'status': 'healthy',
            'component': 'goals',
            'timestamp': datetime.utcnow().isoformat(),
            'template_count': sum(len(tmpl) for tmpl in templates.values())
        }), 200

    except Exception as e:
        logger.error(f"Goals health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'component': 'goals',
            'error': str(e)
        }), 503


# Error handlers specific to goals
@goals_bp.errorhandler(400)
def goals_bad_request(error):
    """Handle 400 errors with ADHD-friendly messaging."""
    return jsonify({
        'error': True,
        'message': "Something wasn't quite right with your goal request. Let's try again - you've got this! 🎯",
        'status_code': 400
    }), 400


@goals_bp.errorhandler(404)
def goals_not_found(error):
    """Handle 404 errors with ADHD-friendly messaging."""
    return jsonify({
        'error': True,
        'message': "We couldn't find that goal. It might have been moved or deleted. No worries - let's find what you need! 🔍",
        'status_code': 404
    }), 404


@goals_bp.errorhandler(500)
def goals_server_error(error):
    """Handle 500 errors with ADHD-friendly messaging."""
    return jsonify({
        'error': True,
        'message': "Something went wrong on our end with your goal. Don't worry - your progress is safe and we're fixing this! 🔧",
        'status_code': 500
    }), 500
