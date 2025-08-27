"""
File upload routes for BrainBudget.
Handles bank statement upload and AI analysis.
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge
from werkzeug.utils import secure_filename
import os

from app.routes.auth import require_auth
from app.services.firebase_service import FirebaseService
from app.services.gemini_ai import GeminiAIService
from app.utils.validators import validate_file_type, validate_file_size


logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/statement', methods=['POST'])
@require_auth
def upload_statement():
    """
    Upload and analyze bank statement.

    Expected form data:
    - file: Bank statement file (PDF, PNG, JPG, JPEG)

    Returns:
        Analysis results
    """
    try:
        uid = request.user['uid']

        # Check if file is in reques
        if 'file' not in request.files:
            raise BadRequest("No file provided. Please select a bank statement to upload! 📄")

        file = request.files['file']

        # Check if file was selected
        if file.filename == '':
            raise BadRequest("No file selected. Please choose your bank statement! 📁")

        # Validate file
        if not validate_file_type(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
            raise BadRequest("File type not supported. Please upload a PDF, PNG, JPG, or JPEG file! 📋")

        # Read file conten
        file.seek(0)  # Reset file pointer
        file_content = file.read()

        # Validate file size
        if not validate_file_size(len(file_content), current_app.config['MAX_CONTENT_LENGTH']):
            raise RequestEntityTooLarge("File is too large. Please keep it under 16MB! 📏")

        # Get secure filename
        filename = secure_filename(file.filename)
        file_type = file.content_type

        logger.info(f"Processing file upload: {filename} ({file_type}) for user {uid}")

        # Upload file to Firebase Storage
        firebase_service: FirebaseService = current_app.firebase
        if not firebase_service:
            return jsonify({
                'success': False,
                'error': "File storage is not configured yet. Please set up Firebase! 🔥",
                'details': "Contact the administrator to configure Firebase environment variables."
            }), 503

        file_url = firebase_service.upload_file(file_content, filename, uid)

        if not file_url:
            return jsonify({
                'success': False,
                'error': "Couldn't save your file right now. Please try again! 💾"
            }), 500

        # Analyze file with Gemini AI
        gemini_api_key = current_app.config.get('GEMINI_API_KEY')
        if not gemini_api_key:
            return jsonify({
                'success': False,
                'error': "AI analysis is not configured yet. Please set up your Gemini API key! 🔑",
                'details': "Contact the administrator to configure the GEMINI_API_KEY environment variable."
            }), 503

        gemini_service = GeminiAIService(gemini_api_key)
        analysis_result = gemini_service.analyze_bank_statement(file_content, file_type, filename)

        if not analysis_result['success']:
            # Clean up uploaded file if analysis fails
            firebase_service.delete_file(file_url)

            return jsonify({
                'success': False,
                'error': f"Couldn't analyze your statement: {analysis_result.get('error', 'Unknown error')} 🤔",
                'details': "Don't worry! Try uploading again, or make sure the image is clear and readable."
            }), 400

        # Save analysis result to database
        analysis_data = {
            'filename': filename,
            'file_url': file_url,
            'file_type': file_type,
            'analysis_result': analysis_result,
            'status': 'completed'
        }

        doc_id = firebase_service.save_analysis_result(uid, analysis_data)

        if not doc_id:
            logger.warning(f"Failed to save analysis result for user {uid}")

        logger.info(f"Statement analysis completed for user {uid}: {doc_id}")

        return jsonify({
            'success': True,
            'analysis_id': doc_id,
            'file_url': file_url,
            'result': analysis_result,
            'message': f"Great! Found {analysis_result['transaction_count']} transactions in your statement! 🎉"
        })

    except BadRequest as e:
        raise e
    except RequestEntityTooLarge as e:
        raise e
    except Exception as e:
        logger.error(f"Error processing file upload: {e}")
        return jsonify({
            'success': False,
            'error': "Something went wrong processing your statement. Let's try again! 🔄"
        }), 500


@upload_bp.route('/analysis/<analysis_id>', methods=['GET'])
@require_auth
def get_analysis(analysis_id):
    """
    Get specific analysis result by ID.

    Args:
        analysis_id: Analysis document ID

    Returns:
        Analysis result data
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase

        # Get analysis documen
        doc = firebase_service.db.collection('analyses').document(analysis_id).get()

        if not doc.exists:
            return jsonify({
                'success': False,
                'error': "Analysis not found. Maybe it's hiding? 🔍"
            }), 404

        analysis_data = doc.to_dict()

        # Verify ownership
        if analysis_data.get('user_id') != uid:
            return jsonify({
                'success': False,
                'error': "This analysis doesn't belong to you! 🚫"
            }), 403

        logger.info(f"Analysis retrieved: {analysis_id} for user {uid}")

        return jsonify({
            'success': True,
            'analysis': analysis_data,
            'message': "Here's your analysis! Hope it's helpful! 📊"
        })

    except Exception as e:
        logger.error(f"Error retrieving analysis {analysis_id}: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't load that analysis right now. Try again in a moment! 🔄"
        }), 500


@upload_bp.route('/analyses', methods=['GET'])
@require_auth
def get_user_analyses():
    """
    Get all analyses for current user.

    Query parameters:
    - limit: Maximum number of analyses to return (default: 10)
    - offset: Number of analyses to skip (for pagination)

    Returns:
        List of user's analyses
    """
    try:
        uid = request.user['uid']
        limit = min(int(request.args.get('limit', 10)), 50)  # Max 50 per reques

        firebase_service: FirebaseService = current_app.firebase
        analyses = firebase_service.get_user_analyses(uid, limit)

        logger.info(f"Retrieved {len(analyses)} analyses for user {uid}")

        return jsonify({
            'success': True,
            'analyses': analyses,
            'count': len(analyses),
            'message': f"Found {len(analyses)} of your analyses! Nice work! 📈"
        })

    except Exception as e:
        logger.error(f"Error retrieving analyses for user {request.user['uid']}: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't load your analyses right now. They're still safe! 💾"
        }), 500


@upload_bp.route('/analysis/<analysis_id>', methods=['DELETE'])
@require_auth
def delete_analysis(analysis_id):
    """
    Delete specific analysis and associated file.

    Args:
        analysis_id: Analysis document ID

    Returns:
        Deletion confirmation
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase

        # Get analysis documen
        doc = firebase_service.db.collection('analyses').document(analysis_id).get()

        if not doc.exists:
            return jsonify({
                'success': False,
                'error': "Analysis not found. Maybe it's already gone? 🔍"
            }), 404

        analysis_data = doc.to_dict()

        # Verify ownership
        if analysis_data.get('user_id') != uid:
            return jsonify({
                'success': False,
                'error': "This analysis doesn't belong to you! 🚫"
            }), 403

        # Delete associated file from storage
        file_url = analysis_data.get('file_url')
        if file_url:
            firebase_service.delete_file(file_url)

        # Delete analysis documen
        firebase_service.db.collection('analyses').document(analysis_id).delete()

        logger.info(f"Analysis deleted: {analysis_id} for user {uid}")

        return jsonify({
            'success': True,
            'message': "Analysis deleted successfully! All cleaned up! 🗑️"
        })

    except Exception as e:
        logger.error(f"Error deleting analysis {analysis_id}: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't delete that analysis right now. Try again in a moment! 🔄"
        }), 500


@upload_bp.route('/reanalyze/<analysis_id>', methods=['POST'])
@require_auth
def reanalyze_statement(analysis_id):
    """
    Re-analyze an existing statement with updated AI.

    Args:
        analysis_id: Existing analysis document ID

    Returns:
        Updated analysis results
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase

        # Get existing analysis
        doc = firebase_service.db.collection('analyses').document(analysis_id).get()

        if not doc.exists:
            return jsonify({
                'success': False,
                'error': "Original analysis not found! 🔍"
            }), 404

        analysis_data = doc.to_dict()

        # Verify ownership
        if analysis_data.get('user_id') != uid:
            return jsonify({
                'success': False,
                'error': "This analysis doesn't belong to you! 🚫"
            }), 403

        # Get original file
        file_url = analysis_data.get('file_url')
        if not file_url:
            return jsonify({
                'success': False,
                'error': "Original file not found for re-analysis! 📄"
            }), 400

        # TODO: Download file from Firebase Storage and re-analyze
        # For now, return a message about this feature being in developmen

        logger.info(f"Re-analysis requested for: {analysis_id} by user {uid}")

        return jsonify({
            'success': False,
            'error': "Re-analysis feature is coming soon! For now, try uploading the file again. 🔄",
            'message': "We're working on making this even better for you! 🚀"
        }), 501

    except Exception as e:
        logger.error(f"Error re-analyzing {analysis_id}: {e}")
        return jsonify({
            'success': False,
            'error': "Something went wrong with re-analysis. Try uploading again! 🔄"
        }), 500


@upload_bp.route('/supported-formats', methods=['GET'])
def get_supported_formats():
    """
    Get list of supported file formats.

    Returns:
        Supported file formats and size limits
    """
    try:
        return jsonify({
            'success': True,
            'supported_formats': list(current_app.config['ALLOWED_EXTENSIONS']),
            'max_file_size_mb': current_app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024),
            'message': "Upload your PDF or image bank statements! We support most formats! 📋"
        })

    except Exception as e:
        logger.error(f"Error getting supported formats: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't load format info right now, but PDFs and images work great! 📄"
        }), 500
