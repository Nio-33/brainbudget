"""
Machine Learning Analytics API Routes for BrainBudge
Provides ADHD-aware spending pattern analysis endpoints
"""
from flask import Blueprint, request, jsonify, current_app
from firebase_admin import auth
import logging
from datetime import datetime, timedelta
from app.services.ml_analytics_service import MLAnalyticsService
from app.services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)

# Create blueprin
ml_analytics_bp = Blueprint('ml_analytics', __name__, url_prefix='/api/analytics')

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


@ml_analytics_bp.route('/patterns', methods=['POST'])
@require_auth
def analyze_spending_patterns():
    """Analyze user's spending patterns with ML."""
    try:
        data = request.get_json() or {}

        # Parse request parameters
        analysis_types = data.get('analysis_types', [
            'recurring_patterns',
            'anomaly_detection',
            'spending_predictions',
            'adhd_insights',
            'category_trends'
        ])

        time_period_days = min(data.get('time_period_days', 90), 365)  # Cap at 1 year

        # Validate analysis types
        valid_types = [
            'recurring_patterns', 'anomaly_detection', 'spending_predictions',
            'adhd_insights', 'category_trends'
        ]

        invalid_types = [t for t in analysis_types if t not in valid_types]
        if invalid_types:
            return jsonify({
                'error': True,
                'message': f'Invalid analysis types: {", ".join(invalid_types)}',
                'valid_types': valid_types
            }), 400

        # Run analysis
        ml_service = MLAnalyticsService()
        results = ml_service.analyze_user_patterns_sync(
            request.user_id,
            analysis_types,
            time_period_days
        )

        # Handle different result types
        if results.get('status') == 'consent_required':
            return jsonify({
                'error': True,
                'message': '🔒 ML analysis requires your consent for data processing',
                'consent_required': True,
                'next_steps': 'Enable ML analytics in your privacy settings'
            }), 403

        elif results.get('status') == 'insufficient_data':
            return jsonify({
                'error': False,
                'message': f"📊 We need more transaction data to provide meaningful insights. Keep using BrainBudget and check back soon!",
                'insufficient_data': True,
                'current_transactions': results.get('total_transactions', 0),
                'needed_transactions': 50
            }), 200

        elif results.get('status') == 'error':
            return jsonify({
                'error': True,
                'message': '🔧 Our analysis engine is having a moment. Please try again shortly!',
                'temporary_error': True
            }), 500

        # Successful analysis
        return jsonify({
            'success': True,
            'message': '🎉 Your spending analysis is ready!',
            'analysis': results,
            'generated_at': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error in spending pattern analysis: {str(e)}")
        return jsonify({
            'error': True,
            'message': '🔧 Something went wrong with your analysis. Our team is looking into it!'
        }), 500


@ml_analytics_bp.route('/insights', methods=['GET'])
@require_auth
def get_spending_insights():
    """Get digestible, ADHD-friendly spending insights."""
    try:
        # Get query parameters
        limit = min(int(request.args.get('limit', 5)), 20)
        insight_types = request.args.getlist('types') or ['all']
        time_period = int(request.args.get('days', 30))

        # Run focused analysis for insights
        ml_service = MLAnalyticsService()
        results = ml_service.analyze_user_patterns_sync(
            request.user_id,
            ['adhd_insights', 'anomaly_detection', 'recurring_patterns'],
            time_period
        )

        if results.get('status') in ['consent_required', 'insufficient_data', 'error']:
            return jsonify({
                'insights': [],
                'message': 'Insights will be available once we have enough data and consent',
                'status': results.get('status')
            })

        # Extract insights
        insights = results.get('insights', [])

        # Filter by type if specified
        if 'all' not in insight_types:
            insights = [i for i in insights if i.get('insight_type') in insight_types]

        # Limit results
        insights = insights[:limit]

        # Add user-friendly formatting
        formatted_insights = []
        for insight in insights:
            formatted = {
                'id': insight.get('insight_id'),
                'title': insight.get('title'),
                'message': insight.get('description'),
                'type': insight.get('insight_type'),
                'confidence': insight.get('confidence'),
                'adhd_note': insight.get('adhd_relevance'),
                'tips': insight.get('actionable_tips', []),
                'amount': insight.get('affected_amount'),
                'period': insight.get('time_period')
            }
            formatted_insights.append(formatted)

        return jsonify({
            'success': True,
            'insights': formatted_insights,
            'total_insights': len(insights),
            'analysis_period_days': time_period,
            'message': f"💡 Found {len(insights)} insights about your spending patterns!"
        })

    except Exception as e:
        logger.error(f"Error getting spending insights: {str(e)}")
        return jsonify({
            'error': True,
            'insights': [],
            'message': '🔧 Having trouble loading insights right now'
        }), 500


@ml_analytics_bp.route('/score-transaction', methods=['POST'])
@require_auth
def score_transaction():
    """Score a single transaction for patterns and anomalies."""
    try:
        transaction_data = request.get_json()

        if not transaction_data:
            return jsonify({
                'error': True,
                'message': 'Transaction data is required for scoring'
            }), 400

        # Validate required fields
        required_fields = ['amount', 'merchant', 'category']
        missing_fields = [f for f in required_fields if f not in transaction_data]

        if missing_fields:
            return jsonify({
                'error': True,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Add timestamp if not provided
        if 'timestamp' not in transaction_data:
            transaction_data['timestamp'] = datetime.utcnow().isoformat()

        # Score transaction
        ml_service = MLAnalyticsService()
        score_result = ml_service.score_new_transaction_sync(
            request.user_id,
            transaction_data
        )

        return jsonify({
            'success': True,
            'scoring': score_result,
            'message': '📊 Transaction scored successfully!'
        })

    except Exception as e:
        logger.error(f"Error scoring transaction: {str(e)}")
        return jsonify({
            'error': True,
            'message': '🔧 Unable to score transaction right now'
        }), 500


@ml_analytics_bp.route('/subscriptions', methods=['GET'])
@require_auth
def get_detected_subscriptions():
    """Get detected recurring subscriptions."""
    try:
        time_period = int(request.args.get('days', 180))  # 6 months defaul

        # Run recurring pattern analysis
        ml_service = MLAnalyticsService()
        results = ml_service.analyze_user_patterns_sync(
            request.user_id,
            ['recurring_patterns'],
            time_period
        )

        if results.get('status') in ['consent_required', 'insufficient_data', 'error']:
            return jsonify({
                'subscriptions': [],
                'message': 'Subscription detection will be available with more data',
                'status': results.get('status')
            })

        # Extract subscription data
        recurring_data = results.get('analyses', {}).get('recurring_patterns', {})
        subscriptions = recurring_data.get('subscriptions', [])

        # Format for frontend
        formatted_subs = []
        for sub in subscriptions:
            formatted = {
                'merchant': sub.get('merchant'),
                'amount': sub.get('amount'),
                'frequency': sub.get('frequency'),
                'confidence': sub.get('consistency_score'),
                'next_payment_date': sub.get('next_expected_date'),
                'total_occurrences': sub.get('occurrences'),
                'adhd_insight': sub.get('adhd_insight')
            }
            formatted_subs.append(formatted)

        # Sort by amount descending
        formatted_subs.sort(key=lambda x: x['amount'], reverse=True)

        total_monthly = sum(s['amount'] for s in formatted_subs if s['frequency'] == 'monthly')

        return jsonify({
            'success': True,
            'subscriptions': formatted_subs,
            'summary': {
                'total_subscriptions': len(formatted_subs),
                'estimated_monthly_total': total_monthly,
                'analysis_period_days': time_period
            },
            'message': f"🔍 Found {len(formatted_subs)} recurring subscriptions totaling ~${total_monthly:.2f}/month"
        })

    except Exception as e:
        logger.error(f"Error getting subscriptions: {str(e)}")
        return jsonify({
            'error': True,
            'subscriptions': [],
            'message': '🔧 Subscription detection is temporarily unavailable'
        }), 500


@ml_analytics_bp.route('/predictions', methods=['GET'])
@require_auth
def get_spending_predictions():
    """Get spending predictions for future periods."""
    try:
        period = request.args.get('period', 'monthly')  # daily, weekly, monthly
        days_ahead = int(request.args.get('days', 30))

        if period not in ['daily', 'weekly', 'monthly']:
            return jsonify({
                'error': True,
                'message': 'Period must be one of: daily, weekly, monthly'
            }), 400

        # Run prediction analysis
        ml_service = MLAnalyticsService()
        results = ml_service.analyze_user_patterns_sync(
            request.user_id,
            ['spending_predictions'],
            90  # Use 90 days for prediction training
        )

        if results.get('status') in ['consent_required', 'insufficient_data', 'error']:
            return jsonify({
                'predictions': {},
                'message': 'Predictions will be available with more transaction history',
                'status': results.get('status')
            })

        # Extract prediction data
        pred_data = results.get('analyses', {}).get('spending_predictions', {})

        if not pred_data.get('predictions'):
            return jsonify({
                'predictions': {},
                'message': 'Not enough data for reliable predictions yet',
                'status': 'insufficient_data'
            })

        # Format predictions based on requested period
        if period == 'weekly':
            prediction_value = pred_data.get('weekly_prediction', 0)
            period_label = 'next week'
        elif period == 'monthly':
            prediction_value = pred_data.get('monthly_prediction', 0)
            period_label = 'next month'
        else:  # daily
            daily_preds = pred_data.get('predictions', [])[:days_ahead]
            prediction_value = sum(p['predicted_amount'] for p in daily_preds)
            period_label = f'next {days_ahead} days'

        accuracy_level = pred_data.get('confidence_level', 'medium')
        accuracy_score = pred_data.get('accuracy_score', 0.7)

        return jsonify({
            'success': True,
            'predictions': {
                'period': period,
                'predicted_amount': prediction_value,
                'confidence_level': accuracy_level,
                'accuracy_score': accuracy_score,
                'period_label': period_label,
                'daily_breakdown': pred_data.get('predictions', [])[:7] if period == 'weekly' else []
            },
            'adhd_note': pred_data.get('adhd_note', ''),
            'message': f"🔮 Predicting ~${prediction_value:.0f} for {period_label} (confidence: {accuracy_level})"
        })

    except Exception as e:
        logger.error(f"Error getting predictions: {str(e)}")
        return jsonify({
            'error': True,
            'predictions': {},
            'message': '🔧 Prediction service is temporarily unavailable'
        }), 500


@ml_analytics_bp.route('/anomalies', methods=['GET'])
@require_auth
def get_spending_anomalies():
    """Get detected spending anomalies."""
    try:
        days = int(request.args.get('days', 30))
        limit = min(int(request.args.get('limit', 10)), 50)

        # Run anomaly detection
        ml_service = MLAnalyticsService()
        results = ml_service.analyze_user_patterns_sync(
            request.user_id,
            ['anomaly_detection'],
            days
        )

        if results.get('status') in ['consent_required', 'insufficient_data', 'error']:
            return jsonify({
                'anomalies': [],
                'message': 'Anomaly detection will be available with more data',
                'status': results.get('status')
            })

        # Extract anomaly data
        anomaly_data = results.get('analyses', {}).get('anomaly_detection', {})
        anomalies = anomaly_data.get('anomalies', [])[:limit]

        # Format for frontend
        formatted_anomalies = []
        for anomaly in anomalies:
            formatted = {
                'date': anomaly.get('date'),
                'amount': anomaly.get('amount'),
                'merchant': anomaly.get('merchant'),
                'category': anomaly.get('category'),
                'anomaly_score': anomaly.get('anomaly_score'),
                'reason': anomaly.get('anomaly_reason'),
                'adhd_insight': anomaly.get('adhd_insight')
            }
            formatted_anomalies.append(formatted)

        return jsonify({
            'success': True,
            'anomalies': formatted_anomalies,
            'summary': {
                'total_anomalies': anomaly_data.get('total_anomalies', 0),
                'anomaly_percentage': anomaly_data.get('anomaly_percentage', 0),
                'analysis_period_days': days
            },
            'message': f"🔍 Found {len(formatted_anomalies)} unusual transactions in the last {days} days"
        })

    except Exception as e:
        logger.error(f"Error getting anomalies: {str(e)}")
        return jsonify({
            'error': True,
            'anomalies': [],
            'message': '🔧 Anomaly detection is temporarily unavailable'
        }), 500


@ml_analytics_bp.route('/consent', methods=['POST'])
@require_auth
def update_ml_consent():
    """Update user's ML analytics consent."""
    try:
        data = request.get_json()

        if 'consent' not in data:
            return jsonify({
                'error': True,
                'message': 'Consent value (true/false) is required'
            }), 400

        consent = bool(data['consent'])

        # Update user preferences
        firebase_service = FirebaseService()
        user_ref = firebase_service.db.collection('user_preferences').document(request.user_id)

        user_ref.set({
            'ml_analytics_consent': consent,
            'ml_consent_updated_at': datetime.utcnow(),
            'ml_consent_version': '1.0'
        }, merge=True)

        if consent:
            message = '✅ ML analytics enabled! Your insights will be available shortly.'
        else:
            message = '🔒 ML analytics disabled. Your privacy settings have been updated.'

        return jsonify({
            'success': True,
            'consent': consent,
            'message': message
        })

    except Exception as e:
        logger.error(f"Error updating ML consent: {str(e)}")
        return jsonify({
            'error': True,
            'message': '🔧 Unable to update consent settings right now'
        }), 500


@ml_analytics_bp.route('/consent', methods=['GET'])
@require_auth
def get_ml_consent():
    """Get user's current ML analytics consent status."""
    try:
        firebase_service = FirebaseService()
        user_ref = firebase_service.db.collection('user_preferences').document(request.user_id)
        user_doc = user_ref.get()

        if user_doc.exists:
            prefs = user_doc.to_dict()
            consent = prefs.get('ml_analytics_consent', False)
            consent_date = prefs.get('ml_consent_updated_at')
        else:
            consent = False
            consent_date = None

        return jsonify({
            'success': True,
            'consent': consent,
            'consent_date': consent_date.isoformat() if consent_date else None,
            'privacy_info': {
                'data_anonymized': True,
                'data_encrypted': True,
                'retention_days': 365,
                'third_party_sharing': False
            }
        })

    except Exception as e:
        logger.error(f"Error getting ML consent: {str(e)}")
        return jsonify({
            'error': True,
            'consent': False,
            'message': '🔧 Unable to load consent settings'
        }), 500


@ml_analytics_bp.route('/category-trends', methods=['GET'])
@require_auth
def get_category_trends():
    """Get spending trends by category."""
    try:
        days = int(request.args.get('days', 90))
        limit = min(int(request.args.get('limit', 10)), 20)

        # Run category trend analysis
        ml_service = MLAnalyticsService()
        results = ml_service.analyze_user_patterns_sync(
            request.user_id,
            ['category_trends'],
            days
        )

        if results.get('status') in ['consent_required', 'insufficient_data', 'error']:
            return jsonify({
                'trends': [],
                'message': 'Category trends will be available with more data',
                'status': results.get('status')
            })

        # Extract trend data
        trend_data = results.get('analyses', {}).get('category_trends', {})
        trends = trend_data.get('trends', [])[:limit]

        return jsonify({
            'success': True,
            'trends': trends,
            'summary': {
                'top_categories': trend_data.get('top_categories', []),
                'most_variable': trend_data.get('most_variable_category'),
                'analysis_period_days': days
            },
            'message': f"📈 Analyzed spending trends across {len(trends)} categories"
        })

    except Exception as e:
        logger.error(f"Error getting category trends: {str(e)}")
        return jsonify({
            'error': True,
            'trends': [],
            'message': '🔧 Category trend analysis is temporarily unavailable'
        }), 500


# Health check for ML analytics system
@ml_analytics_bp.route('/health', methods=['GET'])
def ml_health():
    """Health check for ML analytics system."""
    try:
        # Test basic service initialization
        ml_service = MLAnalyticsService()

        # Check ML libraries availability
        ml_libraries_ok = True
        try:
            import pandas, numpy, sklearn
        except ImportError:
            ml_libraries_ok = False

        return jsonify({
            'status': 'healthy',
            'component': 'ml_analytics',
            'timestamp': datetime.utcnow().isoformat(),
            'ml_libraries_available': ml_libraries_ok,
            'privacy_config_loaded': bool(ml_service.privacy_config),
            'adhd_patterns_loaded': bool(ml_service.adhd_patterns)
        }), 200

    except Exception as e:
        logger.error(f"ML analytics health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'component': 'ml_analytics',
            'error': str(e)
        }), 503


# Error handlers specific to ML analytics
@ml_analytics_bp.errorhandler(400)
def ml_bad_request(error):
    """Handle 400 errors with ADHD-friendly messaging."""
    return jsonify({
        'error': True,
        'message': "Something wasn't quite right with your request. Let's try again - no worries! 🤗",
        'status_code': 400
    }), 400


@ml_analytics_bp.errorhandler(403)
def ml_forbidden(error):
    """Handle 403 errors (consent required)."""
    return jsonify({
        'error': True,
        'message': "ML analytics requires your consent for data processing. You can enable this in your privacy settings! 🔒",
        'consent_required': True,
        'status_code': 403
    }), 403


@ml_analytics_bp.errorhandler(429)
def ml_rate_limit(error):
    """Handle rate limiting with ADHD-friendly messaging."""
    return jsonify({
        'error': True,
        'message': "Our analysis engine needs a quick breather! Please try again in a moment. 😊",
        'status_code': 429
    }), 429


@ml_analytics_bp.errorhandler(500)
def ml_server_error(error):
    """Handle 500 errors with supportive messaging."""
    return jsonify({
        'error': True,
        'message': "Our ML analysis is having a moment, but your data is safe! Please try again shortly. 🔧",
        'status_code': 500
    }), 500
