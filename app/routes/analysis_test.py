"""
Test endpoint for the bank statement analysis service.
Provides a simple way to test AI analysis without file uploads.
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from datetime import date, datetime

from app.services.statement_analyzer import StatementAnalyzer, Transaction, AnalysisResult

logger = logging.getLogger(__name__)

# Create blueprint for analysis testing
analysis_test_bp = Blueprint('analysis_test', __name__)

@analysis_test_bp.route('/test', methods=['GET', 'POST'])
def test_analysis():
    """
    Test endpoint for AI analysis service.
    Can be used to verify Gemini API integration.
    """
    try:
        # Check if Gemini API is configured
        gemini_api_key = current_app.config.get('GEMINI_API_KEY')
        if not gemini_api_key or gemini_api_key.startswith('your_'):
            return jsonify({
                'error': True,
                'message': 'AI analysis is not configured yet. Please add your Gemini API key! ⚙️',
                'code': 'CONFIG_ERROR'
            }), 500

        # Sample bank statement text for testing
        sample_statement = """
        Bank Statement - January 2025
        
        Date        Description                    Amount    Balance
        2025-01-01  PAYCHECK DEPOSIT              +2500.00  2500.00
        2025-01-02  RENT PAYMENT                  -1200.00  1300.00  
        2025-01-03  GROCERY STORE                  -85.50   1214.50
        2025-01-04  STARBUCKS                      -4.25    1210.25
        2025-01-05  GAS STATION                    -45.00   1165.25
        2025-01-06  AMAZON PURCHASE                -29.99   1135.26
        2025-01-07  NETFLIX SUBSCRIPTION           -15.99   1119.27
        2025-01-08  PHARMACY                       -12.50   1106.77
        2025-01-09  RESTAURANT                     -45.75   1061.02
        2025-01-10  ATM WITHDRAWAL                 -40.00   1021.02
        """
        
        # Initialize analyzer
        analyzer = StatementAnalyzer(gemini_api_key)
        
        logger.info("Testing AI analysis with sample data")
        
        # Analyze sample statement
        analysis_result = analyzer.analyze_text_statement(sample_statement)
        
        # Format response
        response_data = {
            'success': True,
            'message': 'AI analysis is working perfectly! 🎉',
            'test_results': {
                'transactions_found': len(analysis_result.transactions),
                'categories_identified': len(analysis_result.spending_breakdown),
                'insights_generated': len(analysis_result.insights),
                'confidence_score': analysis_result.confidence_score,
                'total_income': analysis_result.total_income,
                'total_expenses': analysis_result.total_expenses,
                'net_flow': analysis_result.net_flow
            },
            'sample_transactions': [
                {
                    'date': txn.date.isoformat(),
                    'description': txn.description,
                    'amount': txn.amount,
                    'category': txn.category,
                    'confidence': txn.confidence
                }
                for txn in analysis_result.transactions[:5]  # First 5 transactions
            ],
            'spending_breakdown': analysis_result.spending_breakdown,
            'sample_insights': [
                {
                    'title': insight.title,
                    'message': insight.message,
                    'type': insight.insight_type
                }
                for insight in analysis_result.insights[:3]  # First 3 insights
            ]
        }
        
        logger.info(f"Test analysis completed successfully with {len(analysis_result.transactions)} transactions")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error in test analysis: {e}", exc_info=True)
        return jsonify({
            'error': True,
            'message': f'Test failed: {str(e)} 🔧',
            'code': 'TEST_ERROR',
            'debug_info': str(e) if current_app.debug else None
        }), 500

@analysis_test_bp.route('/categories', methods=['GET'])
def get_categories():
    """
    Get available spending categories.
    Useful for frontend category selection.
    """
    try:
        categories = {
            'Housing': {
                'description': 'Rent, mortgage, utilities, home repairs',
                'keywords': ['rent', 'mortgage', 'property tax', 'home insurance', 'utilities', 'repairs'],
                'color': '#4A90E2'
            },
            'Transportation': {
                'description': 'Gas, rideshares, public transit, car payments',
                'keywords': ['gas', 'fuel', 'uber', 'lyft', 'taxi', 'bus', 'train', 'car payment'],
                'color': '#7ED321'
            },
            'Food & Dining': {
                'description': 'Restaurants, groceries, food delivery',
                'keywords': ['restaurant', 'fast food', 'coffee', 'groceries', 'supermarket', 'food delivery'],
                'color': '#F5A623'
            },
            'Entertainment': {
                'description': 'Movies, streaming, games, hobbies',
                'keywords': ['movie', 'streaming', 'games', 'concerts', 'events', 'books', 'hobbies'],
                'color': '#BD10E0'
            },
            'Shopping': {
                'description': 'Retail purchases, online shopping, clothing',
                'keywords': ['amazon', 'store', 'clothing', 'electronics', 'online shopping', 'retail'],
                'color': '#B8E986'
            },
            'Healthcare': {
                'description': 'Medical expenses, pharmacy, therapy',
                'keywords': ['doctor', 'medical', 'pharmacy', 'prescription', 'dental', 'therapy'],
                'color': '#50E3C2'
            },
            'Bills & Utilities': {
                'description': 'Phone, internet, subscriptions',
                'keywords': ['phone', 'internet', 'electricity', 'water', 'cable', 'insurance'],
                'color': '#9013FE'
            },
            'Income': {
                'description': 'Salary, payments received, refunds',
                'keywords': ['salary', 'paycheck', 'deposit', 'refund', 'interest', 'dividend'],
                'color': '#4BD863'
            },
            'Other': {
                'description': 'ATM fees, transfers, unclear transactions',
                'keywords': ['atm', 'fee', 'transfer', 'cash', 'miscellaneous'],
                'color': '#95A5A6'
            }
        }
        
        return jsonify({
            'success': True,
            'categories': categories,
            'total_categories': len(categories)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return jsonify({
            'error': True,
            'message': 'Error retrieving categories',
            'code': 'CATEGORIES_ERROR'
        }), 500

@analysis_test_bp.route('/health', methods=['GET'])
def analysis_health():
    """
    Health check for analysis service.
    """
    try:
        # Check Gemini API configuration
        gemini_api_key = current_app.config.get('GEMINI_API_KEY')
        gemini_configured = bool(gemini_api_key and not gemini_api_key.startswith('your_'))
        
        # Check optional dependencies
        from app.routes.analysis import (
            PYPDF2_AVAILABLE, PYMUPDF_AVAILABLE, 
            PANDAS_AVAILABLE, PILLOW_AVAILABLE
        )
        
        return jsonify({
            'status': 'healthy',
            'service': 'bank_statement_analysis',
            'features': {
                'gemini_ai': gemini_configured,
                'pdf_processing': PYPDF2_AVAILABLE or PYMUPDF_AVAILABLE,
                'image_processing': PILLOW_AVAILABLE,
                'spreadsheet_processing': PANDAS_AVAILABLE
            },
            'supported_formats': _get_supported_formats(),
            'ready': gemini_configured,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Analysis health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'service': 'bank_statement_analysis',
            'error': str(e)
        }), 503

def _get_supported_formats():
    """Get list of supported file formats based on available libraries."""
    from app.routes.analysis import (
        PYPDF2_AVAILABLE, PYMUPDF_AVAILABLE, 
        PANDAS_AVAILABLE, PILLOW_AVAILABLE
    )
    
    formats = []
    
    # Text formats (always supported via Gemini Vision)
    formats.append('txt')
    
    # Image formats
    if PILLOW_AVAILABLE:
        formats.extend(['png', 'jpg', 'jpeg'])
    else:
        # Still supported via Gemini Vision, just without validation
        formats.extend(['png', 'jpg', 'jpeg'])
    
    # PDF formats
    if PYPDF2_AVAILABLE or PYMUPDF_AVAILABLE:
        formats.append('pdf')
    else:
        # Still supported via Gemini Vision
        formats.append('pdf')
    
    # Spreadsheet formats
    if PANDAS_AVAILABLE:
        formats.extend(['csv', 'xlsx', 'xls'])
    
    return formats

@analysis_test_bp.route('/sample', methods=['POST'])
def analyze_sample_text():
    """
    Analyze custom sample text provided by user.
    Useful for testing with specific bank statement formats.
    """
    try:
        data = request.get_json()
        
        if not data or 'statement_text' not in data:
            return jsonify({
                'error': True,
                'message': 'Please provide statement_text in the request body',
                'code': 'NO_TEXT'
            }), 400
        
        statement_text = data['statement_text']
        
        if not statement_text.strip():
            return jsonify({
                'error': True,
                'message': 'Statement text cannot be empty',
                'code': 'EMPTY_TEXT'
            }), 400
        
        # Check Gemini API configuration
        gemini_api_key = current_app.config.get('GEMINI_API_KEY')
        if not gemini_api_key or gemini_api_key.startswith('your_'):
            return jsonify({
                'error': True,
                'message': 'AI analysis is not configured yet. Please add your Gemini API key! ⚙️',
                'code': 'CONFIG_ERROR'
            }), 500
        
        # Initialize analyzer and process text
        analyzer = StatementAnalyzer(gemini_api_key)
        analysis_result = analyzer.analyze_text_statement(statement_text)
        
        # Format response
        response_data = {
            'success': True,
            'message': 'Sample analysis completed successfully! 🎉',
            'analysis': {
                'summary': {
                    'transactions_found': len(analysis_result.transactions),
                    'categories_identified': len(analysis_result.spending_breakdown),
                    'insights_generated': len(analysis_result.insights),
                    'confidence_score': analysis_result.confidence_score,
                    'total_income': analysis_result.total_income,
                    'total_expenses': analysis_result.total_expenses,
                    'net_flow': analysis_result.net_flow
                },
                'transactions': [
                    {
                        'id': f"txn_{i}",
                        'date': txn.date.isoformat(),
                        'description': txn.description,
                        'amount': txn.amount,
                        'type': txn.transaction_type,
                        'category': txn.category,
                        'confidence': txn.confidence
                    }
                    for i, txn in enumerate(analysis_result.transactions)
                ],
                'spending_breakdown': analysis_result.spending_breakdown,
                'insights': [
                    {
                        'title': insight.title,
                        'message': insight.message,
                        'category': insight.category,
                        'type': insight.insight_type,
                        'recommendation': insight.recommendation
                    }
                    for insight in analysis_result.insights
                ]
            }
        }
        
        logger.info(f"Sample analysis completed with {len(analysis_result.transactions)} transactions")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error in sample analysis: {e}", exc_info=True)
        return jsonify({
            'error': True,
            'message': f'Sample analysis failed: {str(e)} 🔧',
            'code': 'SAMPLE_ERROR',
            'debug_info': str(e) if current_app.debug else None
        }), 500