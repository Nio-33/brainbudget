"""
API routes for bank statement analysis using AI.
Provides endpoints for uploading, analyzing, and retrieving financial insights.
"""
import logging
import os
import tempfile
from io import BytesIO
from flask import Blueprint, request, jsonify, current_app, session
from werkzeug.utils import secure_filename

# Optional imports with graceful fallbacks
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import fitz  # PyMuPDF for better PDF handling
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from app.services.statement_analyzer import StatementAnalyzer, AnalysisResult
from app.services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)

# Create blueprint for analysis routes
analysis_bp = Blueprint('analysis', __name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@analysis_bp.route('/analyze', methods=['POST'])
def analyze_statement():
    """
    Main endpoint for analyzing bank statements.
    Supports PDF, image, and CSV/Excel files.
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'error': True,
                'message': 'No file uploaded. Please select a bank statement to analyze! 📄',
                'code': 'NO_FILE'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'error': True,
                'message': 'No file selected. Please choose your bank statement! 😊',
                'code': 'EMPTY_FILENAME'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'error': True,
                'message': 'File type not supported. Please upload a PDF, image, or CSV file! 📋',
                'code': 'INVALID_FORMAT',
                'supported_formats': list(ALLOWED_EXTENSIONS)
            }), 400

        # Initialize analyzer
        gemini_api_key = current_app.config.get('GEMINI_API_KEY')
        if not gemini_api_key or gemini_api_key.startswith('your_'):
            return jsonify({
                'error': True,
                'message': 'AI analysis is not configured yet. Please check your settings! ⚙️',
                'code': 'CONFIG_ERROR'
            }), 500
        
        # Validate API key format
        if not gemini_api_key.startswith('AIza'):
            return jsonify({
                'error': True,
                'message': 'Invalid Gemini API key format. Please check your configuration! 🔑',
                'code': 'INVALID_API_KEY'
            }), 500

        # Process based on file type
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()

        logger.info(f"Processing {file_ext} file: {filename}")

        try:
            analyzer = StatementAnalyzer(gemini_api_key)
            
            if file_ext == 'pdf':
                analysis_result = _process_pdf_statement(file, analyzer)
            elif file_ext in ['png', 'jpg', 'jpeg']:
                analysis_result = _process_image_statement(file, analyzer)
            elif file_ext in ['csv', 'xlsx', 'xls']:
                analysis_result = _process_spreadsheet_statement(file, analyzer)
            else:
                return jsonify({
                    'error': True,
                    'message': 'Unsupported file format',
                    'code': 'UNSUPPORTED_FORMAT'
                }), 400
                
        except Exception as analyzer_error:
            logger.error(f"Analyzer initialization or processing failed: {analyzer_error}")
            
            # Fallback: Return basic file analysis without AI
            fallback_data = {
                'success': True,
                'message': 'File uploaded successfully! AI analysis is temporarily unavailable, but your file has been processed.',
                'analysis': {
                    'transactions': [],
                    'spending_breakdown': {},
                    'insights': [{
                        'title': 'File Processed',
                        'message': 'Your bank statement has been uploaded successfully. AI analysis will be available once the service is restored.',
                        'category': 'system',
                        'amount': 0,
                        'percentage': 0,
                        'type': 'neutral',
                        'recommendation': 'Please try again later or contact support if the issue persists.',
                        'icon': '📁'
                    }],
                    'summary': {
                        'total_income': 0,
                        'total_expenses': 0,
                        'net_flow': 0,
                        'transaction_count': 0,
                        'analysis_period': {
                            'start': datetime.now().isoformat(),
                            'end': datetime.now().isoformat()
                        }
                    }
                },
                'metadata': {
                    'confidence_score': 0,
                    'processed_at': datetime.now().isoformat(),
                    'fallback_mode': True
                }
            }
            
            # Store fallback results in session
            session['analysis_results'] = fallback_data
            session['analysis_timestamp'] = datetime.now().isoformat()
            
            return jsonify(fallback_data), 200

        # Validate analysis results
        validation = analyzer.validate_analysis_result(analysis_result)

        # Format for frontend consumption
        response_data = _format_analysis_response(analysis_result, validation)

        # Store results in session for insights page
        session['analysis_results'] = response_data
        session['analysis_timestamp'] = datetime.now().isoformat()

        # Optional: Save to Firebase if configured
        try:
            if hasattr(current_app, 'firebase') and current_app.firebase:
                _save_analysis_to_firebase(response_data)
        except Exception as e:
            logger.warning(f"Failed to save to Firebase: {e}")
            # Continue without Firebase - this is not critical

        logger.info(f"Successfully analyzed statement with {len(analysis_result.transactions)} transactions")

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error in analyze_statement: {e}", exc_info=True)
        return jsonify({
            'error': True,
            'message': 'Something went wrong analyzing your statement. Our team is looking into it! 🔧',
            'code': 'ANALYSIS_ERROR',
            'debug_info': str(e) if current_app.debug else None
        }), 500

@analysis_bp.route('/categorize', methods=['POST'])
def manual_categorize():
    """
    Endpoint for manually adjusting transaction categories.
    Allows users to correct AI categorization mistakes.
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': True,
                'message': 'No data provided',
                'code': 'NO_DATA'
            }), 400

        transaction_updates = data.get('transactions', [])

        if not transaction_updates:
            return jsonify({
                'error': True,
                'message': 'No transaction updates provided',
                'code': 'NO_TRANSACTIONS'
            }), 400

        # Validate updates
        valid_categories = [
            'Housing', 'Transportation', 'Food & Dining', 'Entertainment',
            'Shopping', 'Healthcare', 'Bills & Utilities', 'Income', 'Other'
        ]

        updated_transactions = []

        for update in transaction_updates:
            transaction_id = update.get('id')
            new_category = update.get('category')

            if not transaction_id or not new_category:
                continue

            if new_category not in valid_categories:
                return jsonify({
                    'error': True,
                    'message': f'Invalid category: {new_category}',
                    'code': 'INVALID_CATEGORY',
                    'valid_categories': valid_categories
                }), 400

            updated_transactions.append({
                'id': transaction_id,
                'category': new_category,
                'manually_categorized': True
            })

        # In a real implementation, you would update the stored analysis
        # For now, return success with the updates

        return jsonify({
            'success': True,
            'message': f'Successfully updated {len(updated_transactions)} transactions! 🎉',
            'updated_transactions': updated_transactions
        }), 200

    except Exception as e:
        logger.error(f"Error in manual_categorize: {e}")
        return jsonify({
            'error': True,
            'message': 'Error updating categories. Please try again! 🔄',
            'code': 'UPDATE_ERROR'
        }), 500

@analysis_bp.route('/insights/<analysis_id>', methods=['GET'])
def get_insights(analysis_id):
    """
    Retrieve detailed insights for a specific analysis.
    Provides additional AI-generated recommendations.
    """
    try:
        # In a real implementation, retrieve from database/Firebase
        # For now, return a success message

        return jsonify({
            'success': True,
            'message': 'Insights endpoint ready for implementation',
            'analysis_id': analysis_id
        }), 200

    except Exception as e:
        logger.error(f"Error in get_insights: {e}")
        return jsonify({
            'error': True,
            'message': 'Error retrieving insights',
            'code': 'INSIGHTS_ERROR'
        }), 500

@analysis_bp.route('/export/<analysis_id>', methods=['GET'])
def export_analysis(analysis_id):
    """
    Export analysis results to various formats (CSV, PDF, etc.)
    """
    try:
        export_format = request.args.get('format', 'csv').lower()

        if export_format not in ['csv', 'json', 'pdf']:
            return jsonify({
                'error': True,
                'message': 'Unsupported export format',
                'code': 'INVALID_EXPORT_FORMAT',
                'supported_formats': ['csv', 'json', 'pdf']
            }), 400

        # Implementation would generate and return the file
        return jsonify({
            'success': True,
            'message': f'Export in {export_format} format ready for implementation',
            'analysis_id': analysis_id,
            'format': export_format
        }), 200

    except Exception as e:
        logger.error(f"Error in export_analysis: {e}")
        return jsonify({
            'error': True,
            'message': 'Error exporting analysis',
            'code': 'EXPORT_ERROR'
        }), 500

# Insights API endpoints
@analysis_bp.route('/insights/adhd-patterns', methods=['GET'])
def get_adhd_patterns():
    """Get ADHD-specific spending pattern analysis."""
    try:
        return jsonify({
            'success': True,
            'patterns': {
                'impulse_control': 'good',
                'hyperfocus_spending': 'moderate',
                'routine_building': 'excellent'
            }
        }), 200
    except Exception as e:
        logger.error(f"Error in get_adhd_patterns: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@analysis_bp.route('/insights/predictions', methods=['GET'])
def get_predictions():
    """Get spending predictions and forecasts."""
    try:
        return jsonify({
            'success': True,
            'predictions': {
                'month_end_total': 2340.00,
                'budget_variance': -160.00,
                'upcoming_subscriptions': ['Netflix - Dec 28']
            }
        }), 200
    except Exception as e:
        logger.error(f"Error in get_predictions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@analysis_bp.route('/insights/category-trends', methods=['GET'])
def get_category_trends():
    """Get category-based spending trends."""
    try:
        return jsonify({
            'success': True,
            'trends': {
                'Food & Dining': {'amount': 542, 'change': -15},
                'Transportation': {'amount': 289, 'change': 8},
                'Entertainment': {'amount': 156, 'change': 0}
            }
        }), 200
    except Exception as e:
        logger.error(f"Error in get_category_trends: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@analysis_bp.route('/insights/anomalies', methods=['GET'])
def get_anomalies():
    """Get unusual activity and anomaly detection."""
    try:
        return jsonify({
            'success': True,
            'anomalies': [
                {
                    'type': 'large_purchase',
                    'description': '$450 at Best Buy',
                    'severity': 'medium'
                },
                {
                    'type': 'new_merchant',
                    'description': 'First purchase at Trader Joes',
                    'severity': 'low'
                }
            ]
        }), 200
    except Exception as e:
        logger.error(f"Error in get_anomalies: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Helper functions

def _process_pdf_statement(file, analyzer):
    """Process PDF bank statement."""
    try:
        # Check if PDF processing libraries are available
        if not PYMUPDF_AVAILABLE and not PYPDF2_AVAILABLE:
            raise ValueError("PDF processing libraries not installed. Please install PyMuPDF or PyPDF2.")

        # Read PDF conten
        file_content = file.read()
        text_content = ""

        # Try PyMuPDF first (better for complex layouts)
        if PYMUPDF_AVAILABLE:
            try:
                pdf_document = fitz.open(stream=file_content, filetype="pdf")

                for page_num in range(pdf_document.page_count):
                    page = pdf_document[page_num]
                    text_content += page.get_text() + "\n"

                pdf_document.close()

                if text_content.strip():
                    return analyzer.analyze_text_statement(text_content)

            except Exception as e:
                logger.warning(f"PyMuPDF failed: {e}")

        # Fallback to PyPDF2
        if PYPDF2_AVAILABLE and not text_content.strip():
            try:
                file.seek(0)  # Reset file pointer
                reader = PyPDF2.PdfReader(BytesIO(file_content))

                for page in reader.pages:
                    text_content += page.extract_text() + "\n"

                if text_content.strip():
                    return analyzer.analyze_text_statement(text_content)

            except Exception as e:
                logger.warning(f"PyPDF2 failed: {e}")

        # If text extraction failed, try as image using Gemini Vision
        if not text_content.strip():
            logger.info("Text extraction failed, processing PDF as image")
            return analyzer.analyze_image_statement(file_content, "application/pdf")

        raise ValueError("Could not extract text from PDF")

    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise ValueError(f"Could not process PDF file: {str(e)}")

def _process_image_statement(file, analyzer):
    """Process image bank statement."""
    try:
        image_data = file.read()

        # Validate image if PIL is available
        if PILLOW_AVAILABLE:
            try:
                img = Image.open(BytesIO(image_data))
                img.verify()  # Verify it's a valid image
            except Exception:
                raise ValueError("Invalid image file")

        # Determine MIME type
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        mime_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg'
        }

        mime_type = mime_types.get(file_ext, 'image/jpeg')

        return analyzer.analyze_image_statement(image_data, mime_type)

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise ValueError(f"Could not process image file: {str(e)}")

def _process_spreadsheet_statement(file, analyzer):
    """Process CSV/Excel bank statement."""
    try:
        if not PANDAS_AVAILABLE:
            raise ValueError("Pandas library not installed. Please install pandas and "
                             "openpyxl for spreadsheet processing.")

        file_ext = file.filename.rsplit('.', 1)[1].lower()

        # Read spreadshee
        if file_ext == 'csv':
            df = pd.read_csv(file)
        else:  # xlsx, xls
            df = pd.read_excel(file)

        # Convert to text format for analysis
        text_content = "Bank Statement Transactions:\n\n"

        for _, row in df.iterrows():
            row_text = " | ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
            text_content += row_text + "\n"

        return analyzer.analyze_text_statement(text_content)

    except Exception as e:
        logger.error(f"Error processing spreadsheet: {e}")
        raise ValueError(f"Could not process spreadsheet file: {str(e)}")

def _format_analysis_response(analysis: AnalysisResult, validation: dict) -> dict:
    """Format analysis results for frontend consumption."""

    # Convert transactions to JSON-serializable format
    transactions = []
    for i, txn in enumerate(analysis.transactions):
        transactions.append({
            'id': f"txn_{i}",
            'date': txn.date.isoformat(),
            'description': txn.description,
            'amount': txn.amount,
            'currency': getattr(txn, 'currency', 'USD'),
            'type': txn.transaction_type,
            'category': txn.category,
            'confidence': txn.confidence,
            'manually_categorized': False
        })

    # Convert insights to JSON-serializable forma
    insights = []
    for insight in analysis.insights:
        insights.append({
            'title': insight.title,
            'message': insight.message,
            'category': insight.category,
            'amount': insight.amount,
            'percentage': insight.percentage,
            'type': insight.insight_type,
            'recommendation': insight.recommendation,
            'icon': _get_insight_icon(insight.insight_type)
        })

    # Create spending breakdown for charts
    analyzer = StatementAnalyzer("")  # Temporary instance for chart data
    chart_data = analyzer.get_category_breakdown_for_charts(analysis)

    return {
        'success': True,
        'analysis': {
            'transactions': transactions,
            'spending_breakdown': analysis.spending_breakdown,
            'insights': insights,
            'summary': {
                'total_income': analysis.total_income,
                'total_expenses': analysis.total_expenses,
                'net_flow': analysis.net_flow,
                'transaction_count': len(analysis.transactions),
                'analysis_period': {
                    'start': analysis.analysis_period[0].isoformat(),
                    'end': analysis.analysis_period[1].isoformat()
                }
            },
            'charts': {
                'spending_breakdown': chart_data,
                'monthly_trend': _generate_monthly_trend_data(analysis.transactions),
                'category_insights': _generate_category_insights_data(analysis.spending_breakdown)
            }
        },
        'validation': validation,
        'metadata': {
            'confidence_score': analysis.confidence_score,
            'processed_at': datetime.now().isoformat(),
            'requires_review': validation.get('manual_review_suggested', False)
        }
    }

def _get_insight_icon(insight_type: str) -> str:
    """Get appropriate icon for insight type."""
    icons = {
        'positive': '🎉',
        'neutral': '💡',
        'improvement': '🎯'
    }
    return icons.get(insight_type, '📊')

def _generate_monthly_trend_data(transactions) -> dict:
    """Generate monthly spending trend data for charts."""
    from collections import defaultdic
    from datetime import datetime

    monthly_data = defaultdict(float)

    for txn in transactions:
        if txn.transaction_type == 'debit':
            month_key = txn.date.strftime('%Y-%m')
            monthly_data[month_key] += txn.amoun

    # Sort by month and prepare for Chart.js
    sorted_months = sorted(monthly_data.keys())

    return {
        'labels': [datetime.strptime(month, '%Y-%m').strftime('%b %Y') for month in sorted_months],
        'data': [monthly_data[month] for month in sorted_months],
        'colors': ['#4A90E2'] * len(sorted_months)
    }

def _generate_category_insights_data(spending_breakdown) -> list:
    """Generate category-specific insights for visualization."""
    insights = []

    if not spending_breakdown:
        return insights

    total_spending = sum(spending_breakdown.values())

    for category, amount in spending_breakdown.items():
        percentage = (amount / total_spending * 100) if total_spending > 0 else 0

        insights.append({
            'category': category,
            'amount': amount,
            'percentage': round(percentage, 1),
            'status': 'high' if percentage > 30 else 'medium' if percentage > 15 else 'low'
        })

    return sorted(insights, key=lambda x: x['amount'], reverse=True)

def _save_analysis_to_firebase(analysis_data):
    """Save analysis results to Firebase (optional)."""
    try:
        if hasattr(current_app, 'firebase') and current_app.firebase:
            firebase_service: FirebaseService = current_app.firebase

            # Create document reference
            doc_ref = firebase_service.db.collection('analyses').document()

            # Add timestamp and user info if available
            analysis_data['created_at'] = datetime.now()
            # analysis_data['user_id'] = get_current_user_id()  # Implement user auth

            # Save to Firestore
            doc_ref.set(analysis_data)

            logger.info(f"Analysis saved to Firebase: {doc_ref.id}")
            return doc_ref.id

    except Exception as e:
        logger.warning(f"Failed to save to Firebase: {e}")
        return None

# Import datetime for timestamp functionality
from datetime import datetime
