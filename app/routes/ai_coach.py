"""
AI Coach API Routes for BrainBudge
Provides endpoints for conversational AI financial coaching
"""
from flask import Blueprint, request, jsonify, current_app
from firebase_admin import auth
import logging
from datetime import datetime
from app.services.ai_coach_service import AICoachService
from app.services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)

# Create blueprin
ai_coach_bp = Blueprint('ai_coach', __name__, url_prefix='/api/coach')

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


@ai_coach_bp.route('/start', methods=['POST'])
@require_auth
def start_conversation():
    """Start a new conversation with the AI coach."""
    try:
        coach_service = AICoachService()
        session_id = coach_service.start_conversation_sync(request.user_id)

        # Get initial conversation history
        history = coach_service.get_conversation_history_sync(session_id, limit=1)

        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': '🎉 Your AI financial coach is ready to help! Starting a supportive conversation...',
            'welcome_message': history[0] if history else None
        }), 201

    except Exception as e:
        logger.error(f"Error starting AI coach conversation: {str(e)}")
        return jsonify({
            'error': True,
            'message': "I'm having trouble starting our conversation right now, but don't worry! Please try again in a moment. 💙"
        }), 500


@ai_coach_bp.route('/chat/<session_id>', methods=['POST'])
@require_auth
def send_message(session_id):
    """Send a message to the AI coach."""
    try:
        data = request.get_json()

        if not data or 'message' not in data:
            return jsonify({
                'error': True,
                'message': "I didn't receive your message clearly. Could you try sending it again? 🤗"
            }), 400

        user_message = data['message'].strip()
        quick_action = data.get('quick_action')

        if not user_message and not quick_action:
            return jsonify({
                'error': True,
                'message': "It looks like your message was empty. What would you like to talk about? 💭"
            }), 400

        # Limit message length
        if len(user_message) > 2000:
            return jsonify({
                'error': True,
                'message': "Your message is a bit long for me to process easily. Could you break it into smaller parts? My ADHD brain appreciates shorter chunks! 😊"
            }), 400

        coach_service = AICoachService()
        response = coach_service.send_message_sync(session_id, user_message, quick_action)

        return jsonify({
            'success': True,
            'response': response,
            'message': 'Message sent successfully! 💬'
        })

    except ValueError as e:
        return jsonify({
            'error': True,
            'message': "I couldn't find our conversation. Let's start a fresh one! 🔄"
        }), 404
    except Exception as e:
        logger.error(f"Error processing AI coach message: {str(e)}")
        return jsonify({
            'error': True,
            'message': "I'm having trouble processing your message right now. Give me a moment to get back on track! 🔧"
        }), 500


@ai_coach_bp.route('/history/<session_id>', methods=['GET'])
@require_auth
def get_conversation_history(session_id):
    """Get conversation history for a session."""
    try:
        limit = int(request.args.get('limit', 20))
        limit = min(limit, 100)  # Cap at 100 messages

        coach_service = AICoachService()
        history = coach_service.get_conversation_history_sync(session_id, limit)

        return jsonify({
            'success': True,
            'history': history,
            'total_messages': len(history)
        })

    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        return jsonify({
            'error': True,
            'message': "I'm having trouble loading our conversation history right now. 📚"
        }), 500


@ai_coach_bp.route('/feedback/<session_id>', methods=['POST'])
@require_auth
def rate_conversation(session_id):
    """Rate the conversation quality."""
    try:
        data = request.get_json()

        if not data or 'rating' not in data:
            return jsonify({
                'error': True,
                'message': "I need a rating to process your feedback. How would you rate our conversation?"
            }), 400

        rating = data['rating']
        feedback = data.get('feedback', '')

        # Validate rating
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({
                'error': True,
                'message': "Please provide a rating between 1 and 5. ⭐"
            }), 400

        coach_service = AICoachService()
        coach_service.rate_conversation_sync(session_id, rating, feedback)

        # Personalized response based on rating
        if rating >= 4:
            response_message = "Thank you so much for the positive feedback! It means a lot to know I could help. 🌟"
        elif rating >= 3:
            response_message = "Thanks for the feedback! I'm always working to be more helpful. 💪"
        else:
            response_message = "Thank you for the honest feedback. I'll use this to improve and be more supportive next time! 💙"

        return jsonify({
            'success': True,
            'message': response_message
        })

    except Exception as e:
        logger.error(f"Error processing conversation feedback: {str(e)}")
        return jsonify({
            'error': True,
            'message': "I appreciate your feedback, even though I'm having trouble processing it right now!"
        }), 500


@ai_coach_bp.route('/quick-actions', methods=['GET'])
@require_auth
def get_quick_actions():
    """Get available quick action buttons."""
    try:
        coach_service = AICoachService()

        # Return organized quick actions
        quick_actions = {
            'common': [
                {'id': 'spending_review', 'text': 'Review My Spending', 'icon': '📊', 'category': 'analysis'},
                {'id': 'budget_help', 'text': 'Budget Help', 'icon': '💰', 'category': 'planning'},
                {'id': 'goal_progress', 'text': 'Goal Check-In', 'icon': '🎯', 'category': 'goals'},
                {'id': 'motivation', 'text': 'I Need Encouragement', 'icon': '💪', 'category': 'support'}
            ],
            'learning': [
                {'id': 'explain_concept', 'text': 'Explain Something', 'icon': '💡', 'category': 'education'},
                {'id': 'adhd_tips', 'text': 'ADHD Money Tips', 'icon': '🧠', 'category': 'education'},
                {'id': 'save_money', 'text': 'How to Save More', 'icon': '🐷', 'category': 'advice'}
            ],
            'celebration': [
                {'id': 'celebrate', 'text': 'Celebrate a Win!', 'icon': '🎉', 'category': 'positive'}
            ]
        }

        return jsonify({
            'success': True,
            'quick_actions': quick_actions
        })

    except Exception as e:
        logger.error(f"Error getting quick actions: {str(e)}")
        return jsonify({
            'error': True,
            'message': "I'm having trouble loading the quick actions right now."
        }), 500


@ai_coach_bp.route('/sessions', methods=['GET'])
@require_auth
def get_user_sessions():
    """Get user's recent conversation sessions."""
    try:
        firebase_service = FirebaseService()
        db = firebase_service.db

        # Query recent sessions for this user
        sessions_query = db.collection('ai_conversations').where('user_id', '==', request.user_id).order_by('updated_at', direction='DESCENDING').limit(10)

        sessions = []
        for doc in sessions_query.stream():
            session_data = doc.to_dict()

            # Get last message preview
            last_message = ""
            if session_data.get('messages'):
                last_user_message = None
                for msg in reversed(session_data['messages']):
                    if msg.get('role') == 'user':
                        last_user_message = msg.get('content', '')
                        break

                if last_user_message:
                    last_message = last_user_message[:100] + "..." if len(last_user_message) > 100 else last_user_message

            sessions.append({
                'session_id': session_data['session_id'],
                'created_at': session_data['created_at'].isoformat() if session_data.get('created_at') else None,
                'updated_at': session_data['updated_at'].isoformat() if session_data.get('updated_at') else None,
                'total_messages': session_data.get('total_messages', 0),
                'satisfaction_rating': session_data.get('satisfaction_rating'),
                'last_message_preview': last_message
            })

        return jsonify({
            'success': True,
            'sessions': sessions,
            'total_count': len(sessions)
        })

    except Exception as e:
        logger.error(f"Error getting user sessions: {str(e)}")
        return jsonify({
            'error': True,
            'message': "I'm having trouble loading your conversation history."
        }), 500


@ai_coach_bp.route('/analytics', methods=['GET'])
@require_auth
def get_coach_analytics():
    """Get analytics for AI coach usage."""
    try:
        firebase_service = FirebaseService()
        db = firebase_service.db

        # Get user's conversation stats
        sessions_query = db.collection('ai_conversations').where('user_id', '==', request.user_id)

        total_sessions = 0
        total_messages = 0
        ratings = []

        for doc in sessions_query.stream():
            session_data = doc.to_dict()
            total_sessions += 1
            total_messages += session_data.get('total_messages', 0)

            if session_data.get('satisfaction_rating'):
                ratings.append(session_data['satisfaction_rating'])

        # Calculate average rating
        avg_rating = sum(ratings) / len(ratings) if ratings else None

        analytics = {
            'total_sessions': total_sessions,
            'total_messages': total_messages,
            'average_rating': round(avg_rating, 1) if avg_rating else None,
            'ratings_count': len(ratings),
            'avg_messages_per_session': round(total_messages / total_sessions, 1) if total_sessions > 0 else 0
        }

        return jsonify({
            'success': True,
            'analytics': analytics
        })

    except Exception as e:
        logger.error(f"Error getting coach analytics: {str(e)}")
        return jsonify({
            'error': True,
            'analytics': {
                'total_sessions': 0,
                'total_messages': 0,
                'average_rating': None,
                'ratings_count': 0
            }
        }), 200


# Health check for AI coach system
@ai_coach_bp.route('/health', methods=['GET'])
def coach_health():
    """Health check for AI coach system."""
    try:
        import os

        # Check Gemini API key availability
        gemini_key_available = bool(os.getenv('GEMINI_API_KEY'))

        # Test basic service initialization
        coach_service = AICoachService()

        return jsonify({
            'status': 'healthy',
            'component': 'ai_coach',
            'timestamp': datetime.utcnow().isoformat(),
            'gemini_configured': gemini_key_available,
            'quick_actions_count': len(coach_service.quick_actions)
        }), 200

    except Exception as e:
        logger.error(f"AI coach health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'component': 'ai_coach',
            'error': str(e)
        }), 503


# Error handlers specific to AI coach
@ai_coach_bp.errorhandler(400)
def coach_bad_request(error):
    """Handle 400 errors with supportive messaging."""
    return jsonify({
        'error': True,
        'message': "I didn't quite understand your request, but that's okay! Could you try again? I'm here to help. 🤗",
        'status_code': 400
    }), 400


@ai_coach_bp.errorhandler(404)
def coach_not_found(error):
    """Handle 404 errors with supportive messaging."""
    return jsonify({
        'error': True,
        'message': "I couldn't find what you're looking for. Let's start fresh - I'm always here to help! 💙",
        'status_code': 404
    }), 404


@ai_coach_bp.errorhandler(500)
def coach_server_error(error):
    """Handle 500 errors with supportive messaging."""
    return jsonify({
        'error': True,
        'message': "I'm experiencing some technical difficulties, but don't worry - your progress and conversations are safe. Please try again in a moment! 🔧",
        'status_code': 500
    }), 500


@ai_coach_bp.errorhandler(429)
def coach_rate_limit(error):
    """Handle rate limiting with ADHD-friendly messaging."""
    return jsonify({
        'error': True,
        'message': "You're chatting with me pretty actively, which is great! Just give me a quick moment to catch up, and then we can continue our conversation. 😊",
        'status_code': 429
    }), 429