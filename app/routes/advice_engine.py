"""
Financial Advice Engine API Routes
ADHD-aware personalized financial guidance
"""

import logging
from flask import Blueprint, request, jsonify
from firebase_admin import auth
from datetime import datetime
from functools import wraps

from app.services.advice_engine_service import AdviceEngineService, AdviceCategory, AdviceUrgency

logger = logging.getLogger(__name__)

# Create blueprint for advice engine routes
advice_engine_bp = Blueprint('advice_engine', __name__, url_prefix='/api/advice')

def require_auth(f):
    """Decorator to require Firebase authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({
                    "success": False,
                    "message": "You'll need to log in first to access personalized advice! 🔑"
                }), 401

            # Extract and verify token
            token = auth_header.split('Bearer ')[1]
            decoded_token = auth.verify_id_token(token)
            request.user_id = decoded_token['uid']
            request.user_email = decoded_token.get('email')

            return f(*args, **kwargs)

        except auth.InvalidIdTokenError:
            return jsonify({
                "success": False,
                "message": "Your session has expired. Please log in again! 🔄"
            }), 401
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({
                "success": False,
                "message": "Authentication error. Please try logging in again! 🛠️"
            }), 401

    return decorated_function

# Initialize service
advice_service = AdviceEngineService()

@advice_engine_bp.route('/personalized', methods=['GET'])
@require_auth
def get_personalized_advice():
    """
    Get personalized financial advice for the authenticated user

    Query Parameters:
    - category: Optional advice category (budgeting, debt_reduction, savings, investment, emergency_fund)
    - limit: Number of advice pieces to return (default: 3, max: 10)
    - urgency: Filter by urgency level (low, medium, high, critical)

    Returns:
        JSON response with personalized advice and user contex
    """
    try:
        user_id = request.user_id

        # Parse query parameters
        category = request.args.get('category')
        limit = min(int(request.args.get('limit', 3)), 10)
        urgency = request.args.get('urgency')

        # Validate category
        category_enum = None
        if category:
            try:
                category_enum = AdviceCategory(category)
            except ValueError:
                return jsonify({
                    "success": False,
                    "message": f"Invalid category. Valid options: {[c.value for c in AdviceCategory]}"
                }), 400

        # Validate urgency
        urgency_enum = None
        if urgency:
            try:
                urgency_enum = AdviceUrgency(urgency)
            except ValueError:
                return jsonify({
                    "success": False,
                    "message": f"Invalid urgency. Valid options: {[u.value for u in AdviceUrgency]}"
                }), 400

        # Get personalized advice
        result = advice_service.get_personalized_advice_sync(
            user_id=user_id,
            category=category,
            limit=limit
        )

        if not result.get("success"):
            return jsonify({
                "success": False,
                "message": result.get("message", "Unable to generate personalized advice"),
                "suggestion": "Try uploading more transaction data or setting up your financial goals first"
            }), 500

        return jsonify({
            "success": True,
            "advice": result["advice"],
            "user_profile": result.get("user_profile_summary", {}),
            "personalization_notes": result.get("personalization_notes", []),
            "total_available": result.get("advice_count", 0),
            "generated_at": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting personalized advice for user {request.user_id}: {e}")
        return jsonify({
            "success": False,
            "message": "We're having trouble generating your personalized advice right now. Please try again in a few minutes! 🤗",
            "error": str(e) if request.args.get('debug') else None
        }), 500


@advice_engine_bp.route('/categories', methods=['GET'])
@require_auth
def get_advice_categories():
    """
    Get available advice categories

    Returns:
        JSON response with category information
    """
    try:
        categories = advice_service.get_advice_categories()

        return jsonify({
            "success": True,
            "categories": categories,
            "total_categories": len(categories)
        })

    except Exception as e:
        logger.error(f"Error getting advice categories: {e}")
        return jsonify({
            "success": False,
            "message": "Unable to load advice categories right now",
            "error": str(e) if request.args.get('debug') else None
        }), 500


@advice_engine_bp.route('/interaction', methods=['POST'])
@require_auth
def record_advice_interaction():
    """
    Record user interaction with advice (for improvement and analytics)

    Request Body:
    {
        "advice_id": "string",
        "action": "viewed|started|completed|dismissed|helpful|not_helpful",
        "feedback": {
            "rating": 1-5,
            "comments": "string",
            "helpful": boolean,
            "too_complex": boolean,
            "not_relevant": boolean
        }
    }

    Returns:
        JSON response confirming interaction recording
    """
    try:
        user_id = request.user_id
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body required"
            }), 400

        # Validate required fields
        advice_id = data.get('advice_id')
        action = data.get('action')

        if not advice_id or not action:
            return jsonify({
                "success": False,
                "message": "advice_id and action are required"
            }), 400

        # Validate action
        valid_actions = ['viewed', 'started', 'completed', 'dismissed', 'helpful', 'not_helpful']
        if action not in valid_actions:
            return jsonify({
                "success": False,
                "message": f"Invalid action. Valid options: {valid_actions}"
            }), 400

        # Get optional feedback
        feedback = data.get('feedback', {})

        # Record the interaction
        import asyncio
        asyncio.run(advice_service.record_advice_interaction(
            user_id=user_id,
            advice_id=advice_id,
            action=action,
            feedback=feedback
        ))

        # Provide encouraging response based on action
        response_messages = {
            'viewed': "Thanks for checking out the advice! 👀",
            'started': "Great job taking the first step! You've got this! 💪",
            'completed': "Awesome work completing that advice! Way to go! 🎉",
            'dismissed': "No worries! We'll keep improving our suggestions for you 📝",
            'helpful': "So glad that advice was helpful! Thanks for letting us know! 😊",
            'not_helpful': "Thanks for the feedback - we'll work on making better suggestions! 🛠️"
        }

        return jsonify({
            "success": True,
            "message": response_messages.get(action, "Thanks for your feedback!"),
            "recorded_at": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error recording advice interaction: {e}")
        return jsonify({
            "success": False,
            "message": "Unable to record interaction right now",
            "error": str(e) if request.args.get('debug') else None
        }), 500


@advice_engine_bp.route('/by-category/<category>', methods=['GET'])
@require_auth
def get_advice_by_category(category):
    """
    Get advice for a specific category

    Path Parameters:
    - category: Advice category

    Query Parameters:
    - limit: Number of advice pieces (default: 5, max: 10)

    Returns:
        JSON response with category-specific advice
    """
    try:
        user_id = request.user_id
        limit = min(int(request.args.get('limit', 5)), 10)

        # Validate category
        try:
            category_enum = AdviceCategory(category)
        except ValueError:
            return jsonify({
                "success": False,
                "message": f"Invalid category '{category}'. Valid options: {[c.value for c in AdviceCategory]}"
            }), 400

        # Get category-specific advice
        result = advice_service.get_personalized_advice_sync(
            user_id=user_id,
            category=category,
            limit=limit
        )

        if not result.get("success"):
            return jsonify({
                "success": False,
                "message": f"Unable to generate {category.replace('_', ' ')} advice at this time",
                "suggestion": "Make sure you have sufficient transaction data for personalized recommendations"
            }), 500

        # Add category-specific contex
        category_info = next(
            (cat for cat in advice_service.get_advice_categories() if cat['category'] == category),
            {}
        )

        return jsonify({
            "success": True,
            "category": category_info,
            "advice": result["advice"],
            "user_context": result.get("user_profile_summary", {}),
            "personalization_notes": result.get("personalization_notes", []),
            "total_available": result.get("advice_count", 0)
        })

    except Exception as e:
        logger.error(f"Error getting {category} advice for user {request.user_id}: {e}")
        return jsonify({
            "success": False,
            "message": f"Unable to load {category.replace('_', ' ')} advice right now",
            "error": str(e) if request.args.get('debug') else None
        }), 500


@advice_engine_bp.route('/urgent', methods=['GET'])
@require_auth
def get_urgent_advice():
    """
    Get high-priority/urgent advice for the user

    Query Parameters:
    - limit: Number of advice pieces (default: 3, max: 5)

    Returns:
        JSON response with urgent financial advice
    """
    try:
        user_id = request.user_id
        limit = min(int(request.args.get('limit', 3)), 5)

        # Get personalized advice filtered for high/critical urgency
        result = advice_service.get_personalized_advice_sync(
            user_id=user_id,
            category=None,
            limit=limit
        )

        if not result.get("success"):
            return jsonify({
                "success": False,
                "message": "Unable to analyze urgent financial priorities",
                "suggestion": "Add more transaction data for better priority analysis"
            }), 500

        # Filter for urgent advice only
        urgent_advice = [
            advice for advice in result["advice"]
            if advice.get("urgency") in ["high", "critical"]
        ]

        return jsonify({
            "success": True,
            "urgent_advice": urgent_advice[:limit],
            "total_urgent": len(urgent_advice),
            "user_context": result.get("user_profile_summary", {}),
            "priority_explanation": "These items need your attention to improve your financial stability"
        })

    except Exception as e:
        logger.error(f"Error getting urgent advice for user {request.user_id}: {e}")
        return jsonify({
            "success": False,
            "message": "Unable to analyze urgent priorities right now",
            "error": str(e) if request.args.get('debug') else None
        }), 500


@advice_engine_bp.route('/quick-tips', methods=['GET'])
@require_auth
def get_quick_tips():
    """
    Get quick, actionable ADHD-friendly financial tips

    Query Parameters:
    - limit: Number of tips (default: 5, max: 10)

    Returns:
        JSON response with quick financial tips
    """
    try:
        user_id = request.user_id
        limit = min(int(request.args.get('limit', 5)), 10)

        # Get personalized advice and extract quick tips
        result = advice_service.get_personalized_advice_sync(
            user_id=user_id,
            category=None,
            limit=limit * 2  # Get more to extract tips from
        )

        if not result.get("success"):
            # Provide default ADHD-friendly tips if personalization fails
            default_tips = [
                {
                    "tip": "Set up one automatic transfer to savings, even if it's just $5/week",
                    "category": "savings",
                    "time_needed": "5 minutes to set up",
                    "adhd_friendly": True
                },
                {
                    "tip": "Use the 'envelope method' with three categories: needs, wants, savings",
                    "category": "budgeting",
                    "time_needed": "15 minutes to start",
                    "adhd_friendly": True
                },
                {
                    "tip": "Start an emergency fund with just $1 per day - that's $365 in a year!",
                    "category": "emergency_fund",
                    "time_needed": "2 minutes daily",
                    "adhd_friendly": True
                }
            ]

            return jsonify({
                "success": True,
                "quick_tips": default_tips[:limit],
                "message": "General ADHD-friendly tips (personalized tips available with more data)"
            })

        # Extract quick tips from advice
        quick_tips = []
        for advice in result["advice"]:
            # Create quick tip from advice
            tip = {
                "tip": advice.get("summary", ""),
                "category": advice.get("category", "general"),
                "time_needed": advice.get("time_to_implement", "varies"),
                "confidence": advice.get("confidence_score", 0.5),
                "adhd_tips": advice.get("adhd_tips", [])[:2],  # First 2 ADHD tips
                "from_advice_id": advice.get("advice_id")
            }
            quick_tips.append(tip)

        return jsonify({
            "success": True,
            "quick_tips": quick_tips[:limit],
            "total_available": len(quick_tips),
            "personalized": True
        })

    except Exception as e:
        logger.error(f"Error getting quick tips for user {request.user_id}: {e}")
        return jsonify({
            "success": False,
            "message": "Unable to load quick tips right now",
            "error": str(e) if request.args.get('debug') else None
        }), 500


@advice_engine_bp.route('/progress-check', methods=['POST'])
@require_auth
def progress_check():
    """
    Check user's progress on financial advice and provide encouragemen

    Request Body:
    {
        "advice_id": "string",
        "progress_status": "not_started|in_progress|completed|stuck",
        "notes": "string",
        "challenges": ["string"]
    }

    Returns:
        JSON response with progress feedback and next steps
    """
    try:
        user_id = request.user_id
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body required"
            }), 400

        advice_id = data.get('advice_id')
        progress_status = data.get('progress_status')
        notes = data.get('notes', '')
        challenges = data.get('challenges', [])

        if not advice_id or not progress_status:
            return jsonify({
                "success": False,
                "message": "advice_id and progress_status are required"
            }), 400

        # Validate progress status
        valid_statuses = ['not_started', 'in_progress', 'completed', 'stuck']
        if progress_status not in valid_statuses:
            return jsonify({
                "success": False,
                "message": f"Invalid progress_status. Valid options: {valid_statuses}"
            }), 400

        # Record progress
        progress_data = {
            "status": progress_status,
            "notes": notes,
            "challenges": challenges,
            "timestamp": datetime.now().isoformat()
        }

        import asyncio
        asyncio.run(advice_service.record_advice_interaction(
            user_id=user_id,
            advice_id=advice_id,
            action=f"progress_{progress_status}",
            feedback=progress_data
        ))

        # Generate encouraging response based on progress
        responses = {
            'not_started': {
                "message": "That's okay! Sometimes the hardest part is just beginning. Let's break it down into smaller steps! 🌱",
                "encouragement": "You've already taken the first step by checking in - that shows you care about your financial health!",
                "next_steps": [
                    "Pick just ONE small action from the advice to try this week",
                    "Set a 15-minute timer to work on it",
                    "Remember: progress > perfection!"
                ]
            },
            'in_progress': {
                "message": "You're doing great! Progress isn't always linear, especially with ADHD brains. Keep going! 💪",
                "encouragement": "Every small step counts, and you're building momentum!",
                "next_steps": [
                    "Celebrate what you've accomplished so far",
                    "Identify the next smallest step you can take",
                    "Set up a reward for when you complete the next milestone"
                ]
            },
            'completed': {
                "message": "Amazing work! You completed the advice - that's a huge win! Time to celebrate! 🎉",
                "encouragement": "You've proven to yourself that you can achieve your financial goals!",
                "next_steps": [
                    "Take a moment to celebrate this achievement",
                    "Reflect on what worked well for you",
                    "Consider what financial goal you want to tackle next"
                ]
            },
            'stuck': {
                "message": "It's totally normal to feel stuck sometimes - ADHD brains work differently, and that's okay! Let's troubleshoot together! 🤝",
                "encouragement": "Getting stuck doesn't mean you've failed - it means you need a different approach!",
                "next_steps": [
                    "Break the task into even smaller pieces",
                    "Try a different approach or tool",
                    "Ask for help from a friend or our AI coach",
                    "Remember: it's okay to pause and come back to it later"
                ]
            }
        }

        response_data = responses.get(progress_status, responses['in_progress'])

        # Add specific help for challenges
        challenge_tips = []
        for challenge in challenges:
            if 'overwhelm' in challenge.lower():
                challenge_tips.append("Try working in 10-minute focused sessions with breaks")
            elif 'forget' in challenge.lower() or 'remember' in challenge.lower():
                challenge_tips.append("Set up phone reminders or calendar alerts")
            elif 'motivat' in challenge.lower():
                challenge_tips.append("Connect this goal to something you really care about")
            elif 'time' in challenge.lower():
                challenge_tips.append("Start with just 5 minutes - you can do anything for 5 minutes!")

        return jsonify({
            "success": True,
            "progress_status": progress_status,
            "response": response_data,
            "challenge_tips": challenge_tips,
            "recorded_at": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error processing progress check: {e}")
        return jsonify({
            "success": False,
            "message": "Unable to process progress check right now",
            "error": str(e) if request.args.get('debug') else None
        }), 500


@advice_engine_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for advice engine"""
    try:
        health_status = advice_service.health_check()

        import asyncio
        health_data = asyncio.run(health_status)

        return jsonify({
            "success": True,
            "health": health_data,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "success": False,
            "message": "Health check failed",
            "error": str(e)
        }), 500


# Error handlers specific to advice engine
@advice_engine_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors with ADHD-friendly messaging"""
    return jsonify({
        "success": False,
        "message": "Oops! Something wasn't quite right with that request. Let's try again! 🤗",
        "suggestion": "Double-check the required fields and try again"
    }), 400


@advice_engine_bp.errorhandler(500)
def internal_error(error):
    """Handle internal errors with encouraging messaging"""
    return jsonify({
        "success": False,
        "message": "We're having a temporary hiccup with our advice engine. Don't worry - we're on it! 🔧",
        "suggestion": "Please try again in a few minutes, or contact support if the issue persists"
    }), 500
