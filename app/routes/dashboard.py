"""
Dashboard routes for BrainBudget.
Handles spending visualizations, insights, and user dashboard data.
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

from app.routes.auth import require_auth
from app.services.firebase_service import FirebaseService
from app.services.plaid_service import PlaidService
from app.services.gemini_ai import GeminiAIService


logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/overview', methods=['GET'])
@require_auth
def get_dashboard_overview():
    """
    Get dashboard overview with spending summary and recent activity.
    
    Returns:
        Dashboard overview data
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase
        
        # Get recent analyses
        recent_analyses = firebase_service.get_user_analyses(uid, limit=5)
        
        # Calculate totals from all analyses
        total_spent = 0
        total_income = 0
        total_transactions = 0
        category_totals = {}
        
        for analysis in recent_analyses:
            result = analysis.get('analysis_result', {})
            summary = result.get('summary', {})
            
            total_spent += summary.get('total_spent', 0)
            total_income += summary.get('total_income', 0)
            total_transactions += summary.get('transaction_count', 0)
            
            # Aggregate category totals
            category_breakdown = summary.get('category_breakdown', {})
            for category, amount in category_breakdown.items():
                if category in category_totals:
                    category_totals[category] += amount
                else:
                    category_totals[category] = amount
        
        # Get top categories
        top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Calculate insights
        insights = []
        if recent_analyses:
            last_analysis = recent_analyses[0]
            last_result = last_analysis.get('analysis_result', {})
            insights = last_result.get('insights', {}).get('gentle_suggestions', [])
        
        overview = {
            'total_spent': round(total_spent, 2),
            'total_income': round(total_income, 2),
            'net_change': round(total_income - total_spent, 2),
            'total_transactions': total_transactions,
            'analysis_count': len(recent_analyses),
            'top_categories': [
                {'category': cat, 'amount': round(amount, 2)} 
                for cat, amount in top_categories
            ],
            'recent_insights': insights[:3],  # Top 3 insights
            'last_analysis_date': recent_analyses[0]['created_at'] if recent_analyses else None
        }
        
        logger.info(f"Dashboard overview generated for user {uid}")
        
        return jsonify({
            'success': True,
            'overview': overview,
            'message': f"You've analyzed {len(recent_analyses)} statements! Great progress! 📊"
        })
        
    except Exception as e:
        logger.error(f"Error generating dashboard overview: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't load your dashboard right now. Your data is safe! 💾"
        }), 500


@dashboard_bp.route('/spending-trends', methods=['GET'])
@require_auth
def get_spending_trends():
    """
    Get spending trends over time.
    
    Query parameters:
    - period: 'week', 'month', 'quarter' (default: 'month')
    
    Returns:
        Spending trends data
    """
    try:
        uid = request.user['uid']
        period = request.args.get('period', 'month')
        
        if period not in ['week', 'month', 'quarter']:
            raise BadRequest("Period must be 'week', 'month', or 'quarter'")
        
        firebase_service: FirebaseService = current_app.firebase
        
        # Get analyses based on period
        limit = {'week': 10, 'month': 30, 'quarter': 90}.get(period, 30)
        analyses = firebase_service.get_user_analyses(uid, limit)
        
        # Group analyses by time period
        trends = []
        for analysis in analyses:
            result = analysis.get('analysis_result', {})
            summary = result.get('summary', {})
            
            trends.append({
                'date': analysis['created_at'],
                'total_spent': summary.get('total_spent', 0),
                'total_income': summary.get('total_income', 0),
                'transaction_count': summary.get('transaction_count', 0),
                'top_category': summary.get('top_categories', [{}])[0].get('category', 'Unknown') if summary.get('top_categories') else 'Unknown'
            })
        
        logger.info(f"Spending trends retrieved for user {uid} (period: {period})")
        
        return jsonify({
            'success': True,
            'trends': trends,
            'period': period,
            'message': f"Here are your spending trends for the past {period}! 📈"
        })
        
    except BadRequest as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving spending trends: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't load your spending trends right now. Try again soon! 📊"
        }), 500


@dashboard_bp.route('/category-breakdown', methods=['GET'])
@require_auth
def get_category_breakdown():
    """
    Get detailed category breakdown from recent analyses.
    
    Returns:
        Category breakdown data
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase
        
        # Get recent analyses
        analyses = firebase_service.get_user_analyses(uid, limit=10)
        
        # Aggregate category data
        category_totals = {}
        category_transactions = {}
        
        for analysis in analyses:
            result = analysis.get('analysis_result', {})
            transactions = result.get('transactions', [])
            
            for transaction in transactions:
                category = transaction.get('category', 'Other')
                amount = abs(transaction.get('amount', 0))
                
                if category not in category_totals:
                    category_totals[category] = 0
                    category_transactions[category] = 0
                
                if transaction.get('amount', 0) < 0:  # Only count spending
                    category_totals[category] += amount
                    category_transactions[category] += 1
        
        # Calculate percentages and sort
        total_spent = sum(category_totals.values())
        
        categories = []
        for category, amount in category_totals.items():
            if amount > 0:  # Only include categories with spending
                categories.append({
                    'category': category,
                    'amount': round(amount, 2),
                    'percentage': round((amount / total_spent) * 100, 1) if total_spent > 0 else 0,
                    'transaction_count': category_transactions[category]
                })
        
        # Sort by amount (descending)
        categories.sort(key=lambda x: x['amount'], reverse=True)
        
        logger.info(f"Category breakdown generated for user {uid}")
        
        return jsonify({
            'success': True,
            'categories': categories,
            'total_spent': round(total_spent, 2),
            'message': f"Your spending across {len(categories)} categories! 🏷️"
        })
        
    except Exception as e:
        logger.error(f"Error generating category breakdown: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't load your category breakdown right now. Try again! 📊"
        }), 500


@dashboard_bp.route('/insights', methods=['GET'])
@require_auth
def get_insights():
    """
    Get personalized financial insights and tips.
    
    Returns:
        AI-generated insights and recommendations
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase
        
        # Get recent analysis for insights
        analyses = firebase_service.get_user_analyses(uid, limit=1)
        
        if not analyses:
            return jsonify({
                'success': True,
                'insights': {
                    'key_patterns': [],
                    'gentle_suggestions': ["Upload your first bank statement to get personalized insights! 🎉"],
                    'achievements': ["You're here and ready to take control of your finances! 🌟"],
                    'adhd_tips': [
                        "Start small - even tracking one week of expenses is progress! 🎯",
                        "Set up automatic transfers to make saving effortless 💰"
                    ],
                    'motivation': "You've taken the first step by being here! That's already amazing progress! 🚀"
                },
                'message': "Ready to discover insights about your spending? Upload a statement! 📊"
            })
        
        # Get insights from most recent analysis
        latest_analysis = analyses[0]
        result = latest_analysis.get('analysis_result', {})
        insights = result.get('insights', {})
        
        logger.info(f"Insights retrieved for user {uid}")
        
        return jsonify({
            'success': True,
            'insights': insights,
            'analysis_date': latest_analysis['created_at'],
            'message': "Here are your personalized insights! You're doing great! ✨"
        })
        
    except Exception as e:
        logger.error(f"Error retrieving insights: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't load your insights right now. Your progress is still amazing! 🌟"
        }), 500


@dashboard_bp.route('/ask-coach', methods=['POST'])
@require_auth
def ask_financial_coach():
    """
    Ask the AI financial coach a question.
    
    Expected JSON:
    {
        "question": "User's financial question"
    }
    
    Returns:
        AI coach response
    """
    try:
        uid = request.user['uid']
        data = request.get_json()
        
        if not data or 'question' not in data:
            raise BadRequest("Please ask a question! I'm here to help! 💭")
        
        question = data['question'].strip()
        if not question:
            raise BadRequest("Your question seems empty. What would you like to know? 🤔")
        
        firebase_service: FirebaseService = current_app.firebase
        
        # Get user's spending data for context
        analyses = firebase_service.get_user_analyses(uid, limit=3)
        spending_data = {}
        
        if analyses:
            latest_analysis = analyses[0]
            result = latest_analysis.get('analysis_result', {})
            spending_data = {
                'summary': result.get('summary', {}),
                'recent_transactions': result.get('transactions', [])[:10]
            }
        
        # Generate AI response
        gemini_service = GeminiAIService(current_app.config['GEMINI_API_KEY'])
        advice = gemini_service.generate_spending_advice(question, spending_data)
        
        logger.info(f"Financial coach question answered for user {uid}")
        
        return jsonify({
            'success': True,
            'question': question,
            'advice': advice,
            'message': "Hope this helps! Feel free to ask me anything else! 🤗"
        })
        
    except BadRequest as e:
        raise e
    except Exception as e:
        logger.error(f"Error with financial coach: {e}")
        return jsonify({
            'success': False,
            'error': "I'm having trouble thinking right now. Try asking again in a moment! 🤖"
        }), 500


@dashboard_bp.route('/goals', methods=['GET'])
@require_auth
def get_goals():
    """
    Get user's financial goals (placeholder for Level 3).
    
    Returns:
        User's financial goals
    """
    try:
        uid = request.user['uid']
        
        # TODO: Implement goal tracking in Level 3
        # For now, return placeholder data
        
        goals = [
            {
                'id': 'emergency_fund',
                'title': 'Emergency Fund',
                'description': 'Build an emergency fund',
                'target_amount': 1000,
                'current_amount': 0,
                'progress': 0,
                'status': 'not_started'
            }
        ]
        
        logger.info(f"Goals retrieved for user {uid}")
        
        return jsonify({
            'success': True,
            'goals': goals,
            'message': "Goal tracking is coming soon! For now, focus on understanding your spending! 🎯"
        })
        
    except Exception as e:
        logger.error(f"Error retrieving goals: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't load your goals right now. Keep up the great work anyway! 🌟"
        }), 500


@dashboard_bp.route('/export', methods=['POST'])
@require_auth
def export_data():
    """
    Export user's financial data (placeholder for future feature).
    
    Expected JSON:
    {
        "format": "csv" | "pdf" | "json",
        "date_range": "30d" | "90d" | "1y" | "all"
    }
    
    Returns:
        Export status and download link
    """
    try:
        uid = request.user['uid']
        data = request.get_json()
        
        format_type = data.get('format', 'csv')
        date_range = data.get('date_range', '30d')
        
        # TODO: Implement data export functionality
        
        logger.info(f"Data export requested for user {uid} (format: {format_type}, range: {date_range})")
        
        return jsonify({
            'success': False,
            'error': "Data export is coming soon! For now, you can view all your data in the dashboard. 📊",
            'message': "We're working on making it easy to export your financial insights! 🚀"
        }), 501
        
    except Exception as e:
        logger.error(f"Error with data export: {e}")
        return jsonify({
            'success': False,
            'error': "Export isn't ready yet, but your data is always accessible here! 💾"
        }), 500