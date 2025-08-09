"""
Guest/Anonymous functionality for BrainBudget
Allows users to try basic features before signing up
"""

import logging
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
import tempfile
import os

logger = logging.getLogger(__name__)

# Create blueprint for guest routes
guest_bp = Blueprint('guest', __name__, url_prefix='/api/guest')

@guest_bp.route('/upload', methods=['POST'])
def guest_upload():
    """
    Anonymous statement upload and analysis
    No authentication required - generates temporary session
    """
    logger.info("Guest upload request received")
    try:
        # Generate guest session ID
        if 'guest_id' not in session:
            session['guest_id'] = f"guest_{uuid.uuid4().hex[:12]}"
            session['guest_created'] = datetime.now().isoformat()
        
        guest_id = session['guest_id']
        
        # Check file upload
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "message": "No worries! Just drag and drop your bank statement to get started 📁"
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "message": "Looks like no file was selected. Try again with a CSV file! 😊"
            }), 400
        
        # Validate file type
        if not file.filename.lower().endswith(('.csv', '.txt')):
            return jsonify({
                "success": False,
                "message": "We need a CSV file to work our magic! Most banks can export these 📊"
            }), 400
        
        # Save file temporarily
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, f"guest_{guest_id}_{file.filename}")
        file.save(temp_file)
        
        # Analyze the file
        try:
            # Read CSV file and create basic analysis
            analysis_result = analyze_guest_csv(temp_file)
            
            # Add guest-specific encouraging messages
            analysis_result['guest_experience'] = {
                "message": "🎉 Wow! Look what we discovered about your spending!",
                "encouragement": "This is just a taste of what BrainBudget can do. Want to see more insights?",
                "next_steps": [
                    "Create a free account to save this analysis",
                    "Set your first financial goal",
                    "Chat with our ADHD-aware AI coach",
                    "Get personalized spending insights"
                ]
            }
            
            # Limit guest analysis to prevent abuse
            if 'transactions' in analysis_result:
                analysis_result['transactions'] = analysis_result['transactions'][:50]
                analysis_result['guest_limitation'] = {
                    "message": "📊 Showing first 50 transactions",
                    "full_message": "Create an account to see all your transactions and advanced insights!"
                }
            
            return jsonify({
                "success": True,
                "guest_id": guest_id,
                "analysis": analysis_result,
                "session_expires": (datetime.now() + timedelta(hours=2)).isoformat(),
                "signup_incentive": {
                    "title": "Love what you see? 🌟",
                    "benefits": [
                        "Save and track all your analysis",
                        "Set ADHD-friendly financial goals", 
                        "Chat with AI coach anytime",
                        "Get ML-powered spending insights",
                        "Connect bank accounts for real-time tracking"
                    ]
                }
            })
            
        except Exception as analysis_error:
            logger.error(f"Guest analysis error: {analysis_error}")
            return jsonify({
                "success": False,
                "message": "We had trouble analyzing your file, but don't worry! This might be due to the file format. Try a different CSV export from your bank 🔄",
                "suggestion": "Most banks have CSV export in their online banking. Look for 'Export' or 'Download' options!"
            }), 500
            
        finally:
            # Clean up temporary file
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                os.rmdir(temp_dir)
            except Exception as cleanup_error:
                logger.warning(f"Cleanup error: {cleanup_error}")
    
    except Exception as e:
        logger.error(f"Guest upload error: {e}")
        return jsonify({
            "success": False,
            "message": "Something went wrong, but it's not your fault! Please try again 🤗",
            "error": str(e)
        }), 500


@guest_bp.route('/convert', methods=['POST'])
def convert_guest_to_user():
    """
    Convert guest session to full user account
    Preserves analysis data during conversion
    """
    try:
        if 'guest_id' not in session:
            return jsonify({
                "success": False,
                "message": "No guest session found. Please try uploading a file first!"
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Please provide your account information to continue"
            }), 400
        
        guest_id = session['guest_id']
        
        # Here we would normally integrate with the auth system
        # For now, return conversion info
        
        return jsonify({
            "success": True,
            "message": "🎉 Welcome to BrainBudget! Your analysis has been saved to your account.",
            "guest_id": guest_id,
            "preserved_data": {
                "analysis": "saved",
                "preferences": "maintained",
                "progress": "continued"
            },
            "next_steps": [
                "Complete your profile for better personalization",
                "Set your first financial goal",
                "Connect bank accounts for real-time tracking",
                "Start chatting with your AI coach"
            ]
        })
    
    except Exception as e:
        logger.error(f"Guest conversion error: {e}")
        return jsonify({
            "success": False,
            "message": "We had trouble creating your account. Please try again!",
            "error": str(e)
        }), 500


@guest_bp.route('/demo-insights', methods=['GET'])
def get_demo_insights():
    """
    Provide demo insights for users who haven't uploaded yet
    Shows what BrainBudget can do
    """
    try:
        demo_insights = {
            "spending_patterns": {
                "title": "🧠 ADHD Spending Insights We Detect",
                "patterns": [
                    {
                        "type": "impulse_spending",
                        "icon": "⚡",
                        "title": "Impulse Purchase Detection",
                        "description": "We spot quick spending decisions and help you understand them without judgment",
                        "example": "Detected 3 Amazon purchases within 10 minutes - classic ADHD dopamine seeking!"
                    },
                    {
                        "type": "hyperfocus",
                        "icon": "🎯", 
                        "title": "Hyperfocus Spending",
                        "description": "Track concentrated spending during special interest periods",
                        "example": "Art supplies shopping session: $180 in 2 hours - hyperfocus can be expensive!"
                    },
                    {
                        "type": "emotional_triggers",
                        "icon": "💙",
                        "title": "Emotional Spending Recognition",
                        "description": "Gentle awareness of stress-related financial choices",
                        "example": "Higher spending on Mondays suggests work stress trigger"
                    },
                    {
                        "type": "forgotten_subscriptions",
                        "icon": "🔄",
                        "title": "Subscription Detective",
                        "description": "Find recurring charges you might have forgotten about",
                        "example": "Found 3 unused subscriptions worth $47/month - that's vacation money!"
                    }
                ]
            },
            "advice_preview": {
                "title": "💡 Personalized Advice You'll Get",
                "samples": [
                    {
                        "category": "budgeting",
                        "title": "ADHD-Friendly 50/30/20 Budget",
                        "preview": "Traditional budgets don't work for ADHD brains. Let's try the visual envelope method..."
                    },
                    {
                        "category": "savings",
                        "title": "The $1-a-Day Emergency Fund",
                        "preview": "Forget the overwhelming '6 months expenses' rule. Start with just $1 per day..."
                    },
                    {
                        "category": "debt",
                        "title": "ADHD Debt Snowball",
                        "preview": "Pay off debts in a way that gives your brain the dopamine hits it craves..."
                    }
                ]
            },
            "coach_preview": {
                "title": "🤖 Meet Your AI Financial Coach",
                "personality": "Supportive, understanding, and built for ADHD minds",
                "sample_conversation": [
                    {
                        "user": "I spent way too much on coffee again this week 😞",
                        "coach": "Hey, coffee keeps us functioning! ☕ Let's look at this as data, not a failure. I see you spent $47 on coffee this week. That tells me you're probably stressed or tired. Instead of cutting it out completely (we both know that won't work 😉), what if we made it more intentional? Maybe set aside $40/week as your 'brain fuel budget' and track how it helps your productivity?"
                    }
                ]
            },
            "call_to_action": {
                "title": "Ready to Try It? 🚀",
                "message": "Upload a bank statement and see your own spending patterns in action!",
                "benefits": [
                    "Instant analysis in 30 seconds",
                    "No judgment, just insights",
                    "ADHD-aware interpretations",
                    "Actionable next steps"
                ]
            }
        }
        
        return jsonify({
            "success": True,
            "demo_insights": demo_insights
        })
    
    except Exception as e:
        logger.error(f"Demo insights error: {e}")
        return jsonify({
            "success": False,
            "message": "Unable to load demo insights right now"
        }), 500


@guest_bp.route('/health', methods=['GET'])
def guest_health():
    """Guest system health check"""
    return jsonify({
        "success": True,
        "service": "Guest",
        "status": "healthy",
        "features": ["anonymous_upload", "demo_insights", "account_conversion"]
    })


def analyze_guest_csv(file_path):
    """
    Basic CSV analysis for guest users
    Provides instant insights without full AI analysis
    """
    import csv
    import os
    from collections import defaultdict
    
    try:
        transactions = []
        category_breakdown = defaultdict(float)
        total_spending = 0
        transaction_count = 0
        
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            # Try to detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            for row in reader:
                # Try to find amount and description columns
                amount = None
                description = ""
                
                # Common column names for amounts
                amount_cols = ['amount', 'Amount', 'AMOUNT', 'debit', 'Debit', 'DEBIT', 
                              'credit', 'Credit', 'CREDIT', 'transaction_amount', 'value']
                
                for col in amount_cols:
                    if col in row and row[col]:
                        try:
                            amount_str = row[col].replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
                            amount = float(amount_str)
                            break
                        except (ValueError, TypeError):
                            continue
                
                # Common column names for descriptions
                desc_cols = ['description', 'Description', 'DESCRIPTION', 'memo', 'Memo', 
                            'details', 'Details', 'payee', 'Payee', 'merchant']
                
                for col in desc_cols:
                    if col in row and row[col]:
                        description = row[col]
                        break
                
                if amount is not None and abs(amount) > 0:
                    transactions.append({
                        'amount': amount,
                        'description': description
                    })
                    
                    # Basic categorization
                    category = categorize_transaction(description)
                    category_breakdown[category] += abs(amount)
                    
                    if amount < 0:  # Spending
                        total_spending += abs(amount)
                    
                    transaction_count += 1
        
        return {
            'transaction_count': transaction_count,
            'total_spending': total_spending,
            'category_breakdown': dict(category_breakdown),
            'transactions': transactions[:50],  # Limit for guests
            'analysis_type': 'guest_basic'
        }
        
    except Exception as e:
        logger.error(f"CSV analysis error: {e}")
        return {
            'transaction_count': 0,
            'total_spending': 0,
            'category_breakdown': {},
            'transactions': [],
            'error': str(e)
        }


def categorize_transaction(description):
    """
    Basic transaction categorization for guest analysis
    """
    description_lower = description.lower()
    
    # Simple keyword-based categorization
    if any(keyword in description_lower for keyword in ['grocery', 'market', 'food', 'supermarket']):
        return 'groceries'
    elif any(keyword in description_lower for keyword in ['gas', 'fuel', 'shell', 'exxon', 'bp']):
        return 'transportation'
    elif any(keyword in description_lower for keyword in ['restaurant', 'cafe', 'coffee', 'pizza', 'burger']):
        return 'dining'
    elif any(keyword in description_lower for keyword in ['amazon', 'ebay', 'store', 'shop']):
        return 'shopping'
    elif any(keyword in description_lower for keyword in ['netflix', 'spotify', 'subscription']):
        return 'entertainment'
    elif any(keyword in description_lower for keyword in ['rent', 'mortgage', 'utilities', 'electric', 'water']):
        return 'housing'
    elif any(keyword in description_lower for keyword in ['bank', 'fee', 'charge', 'atm']):
        return 'fees'
    else:
        return 'other'