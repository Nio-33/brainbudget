"""
Machine Learning Analytics Service for BrainBudge
Provides ADHD-aware spending pattern analysis with privacy-first design
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import hashlib
import json
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

from app.services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)


@dataclass
class TransactionPattern:
    """Represents a detected spending pattern."""
    pattern_id: str
    pattern_type: str  # recurring, anomaly, seasonal, etc.
    confidence_score: float
    description: str
    frequency: Optional[str] = None
    amount_range: Optional[Tuple[float, float]] = None
    categories: Optional[List[str]] = None
    merchants: Optional[List[str]] = None
    adhd_insight: Optional[str] = None
    recommendations: Optional[List[str]] = None


@dataclass
class SpendingInsight:
    """ADHD-friendly spending insight."""
    insight_id: str
    title: str
    description: str
    insight_type: str  # positive, warning, neutral, celebration
    confidence: float
    adhd_relevance: str
    actionable_tips: List[str]
    affected_amount: Optional[float] = None
    time_period: Optional[str] = None
    supporting_data: Optional[Dict[str, Any]] = None


@dataclass
class PredictionResult:
    """Spending prediction result."""
    prediction_id: str
    predicted_amount: float
    confidence_interval: Tuple[float, float]
    time_period: str
    category: Optional[str] = None
    factors: List[str] = None
    accuracy_score: Optional[float] = None


class MLAnalyticsService:
    """
    ADHD-aware machine learning analytics for spending patterns.

    Features:
    - Privacy-preserving transaction analysis
    - ADHD-specific pattern recognition
    - Predictive spending modeling
    - Emotional trigger detection
    - Real-time anomaly detection
    """

    def __init__(self, firebase_service: FirebaseService = None):
        """Initialize ML analytics service."""
        self.firebase_service = firebase_service or FirebaseService()
        self.db = self.firebase_service.db

        # Initialize ML models
        self.models = {
            'anomaly_detector': IsolationForest(
                contamination=0.1,
                random_state=42,
                n_estimators=100
            ),
            'spending_predictor': RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                max_depth=10
            ),
            'pattern_clusterer': KMeans(
                n_clusters=5,
                random_state=42,
                n_init=10
            ),
            'subscription_detector': DBSCAN(
                eps=0.5,
                min_samples=3
            )
        }

        # Feature scalers
        self.scalers = {
            'transaction': StandardScaler(),
            'temporal': StandardScaler(),
            'categorical': LabelEncoder()
        }

        # ADHD-specific pattern definitions
        self.adhd_patterns = {
            'impulse_spending': {
                'time_threshold': 300,  # seconds
                'amount_multiplier': 2.0,
                'categories': ['shopping', 'entertainment', 'dining'],
                'keywords': ['instant', 'sale', 'limited', 'now']
            },
            'hyperfocus_periods': {
                'transaction_density': 5,  # transactions per hour
                'category_concentration': 0.8,  # % in single category
                'duration_threshold': 3600  # seconds
            },
            'forgotten_subscriptions': {
                'usage_gap_days': 30,
                'amount_consistency': 0.95,
                'frequency_pattern': 'monthly'
            },
            'stress_spending': {
                'deviation_threshold': 2.0,  # standard deviations
                'time_patterns': ['late_night', 'weekend'],
                'categories': ['food', 'shopping', 'entertainment']
            }
        }

        # Privacy settings
        self.privacy_config = {
            'hash_merchants': True,
            'anonymize_amounts': True,
            'aggregate_only': False,
            'retention_days': 365,
            'min_analysis_transactions': 50
        }

    async def analyze_user_patterns(
        self,
        user_id: str,
        analysis_types: List[str] = None,
        time_period_days: int = 90
    ) -> Dict[str, Any]:
        """
        Comprehensive spending pattern analysis for a user.

        Args:
            user_id: User identifier
            analysis_types: Specific analyses to run (default: all)
            time_period_days: Days of history to analyze

        Returns:
            Analysis results with insights and recommendations
        """
        try:
            # Get user consent for ML processing
            if not await self._check_ml_consent(user_id):
                return {
                    'status': 'consent_required',
                    'message': 'ML analysis requires user consent for data processing'
                }

            # Load and preprocess transactions
            transactions_df = await self._load_user_transactions(user_id, time_period_days)

            if len(transactions_df) < self.privacy_config['min_analysis_transactions']:
                return {
                    'status': 'insufficient_data',
                    'message': f'Need at least {self.privacy_config["min_analysis_transactions"]} transactions for analysis'
                }

            # Preprocess data with privacy protection
            processed_df = await self._preprocess_transactions(transactions_df)

            # Run requested analyses
            if analysis_types is None:
                analysis_types = [
                    'recurring_patterns',
                    'anomaly_detection',
                    'spending_predictions',
                    'adhd_insights',
                    'category_trends'
                ]

            results = {
                'user_id_hash': self._hash_user_id(user_id),
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'time_period_days': time_period_days,
                'total_transactions': len(processed_df),
                'analyses': {}
            }

            # Execute analyses
            for analysis_type in analysis_types:
                try:
                    if analysis_type == 'recurring_patterns':
                        results['analyses']['recurring_patterns'] = await self._detect_recurring_patterns(processed_df)
                    elif analysis_type == 'anomaly_detection':
                        results['analyses']['anomaly_detection'] = await self._detect_spending_anomalies(processed_df)
                    elif analysis_type == 'spending_predictions':
                        results['analyses']['spending_predictions'] = await self._predict_future_spending(processed_df)
                    elif analysis_type == 'adhd_insights':
                        results['analyses']['adhd_insights'] = await self._analyze_adhd_patterns(processed_df)
                    elif analysis_type == 'category_trends':
                        results['analyses']['category_trends'] = await self._analyze_category_trends(processed_df)

                except Exception as e:
                    logger.error(f"Error in {analysis_type}: {str(e)}")
                    results['analyses'][analysis_type] = {
                        'status': 'error',
                        'message': f'Analysis failed: {str(e)}'
                    }

            # Generate ADHD-friendly insights
            insights = await self._generate_adhd_insights(results['analyses'], processed_df)
            results['insights'] = insights

            # Log analysis for improvemen
            await self._log_analysis_event(user_id, analysis_types, len(processed_df))

            logger.info(f"Completed ML analysis for user {user_id[:8]}... with {len(analysis_types)} analyses")
            return results

        except Exception as e:
            logger.error(f"Error in user pattern analysis: {str(e)}")
            return {
                'status': 'error',
                'message': 'Analysis temporarily unavailable',
                'error_code': 'ANALYSIS_ERROR'
            }

    async def score_new_transaction(
        self,
        user_id: str,
        transaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Real-time scoring of new transactions for anomalies and patterns.

        Args:
            user_id: User identifier
            transaction: New transaction data

        Returns:
            Scoring results with flags and recommendations
        """
        try:
            # Load user's historical patterns
            patterns = await self._load_user_patterns(user_id)

            # Score transaction
            scores = {
                'anomaly_score': await self._score_anomaly(transaction, patterns),
                'impulse_score': await self._score_impulse_likelihood(transaction, patterns),
                'recurring_score': await self._score_recurring_likelihood(transaction, patterns),
                'emotional_score': await self._score_emotional_trigger(transaction, patterns)
            }

            # Generate real-time insights
            insights = []

            if scores['anomaly_score'] > 0.7:
                insights.append({
                    'type': 'unusual_spending',
                    'message': '💡 This transaction is unusual for you',
                    'confidence': scores['anomaly_score'],
                    'adhd_note': 'Checking in on unusual spending can help with awareness'
                })

            if scores['impulse_score'] > 0.8:
                insights.append({
                    'type': 'possible_impulse',
                    'message': '🧠 This might be an impulse purchase',
                    'confidence': scores['impulse_score'],
                    'adhd_note': 'ADHD brains often make quick decisions - totally normal!'
                })

            if scores['recurring_score'] > 0.9:
                insights.append({
                    'type': 'recurring_transaction',
                    'message': '🔄 This looks like a regular expense',
                    'confidence': scores['recurring_score'],
                    'adhd_note': 'Recognizing patterns is great for budgeting'
                })

            return {
                'transaction_id': transaction.get('id'),
                'scores': scores,
                'insights': insights,
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error scoring transaction: {str(e)}")
            return {
                'transaction_id': transaction.get('id'),
                'scores': {},
                'insights': [],
                'error': 'Scoring unavailable'
            }

    # Private helper methods

    async def _load_user_transactions(
        self,
        user_id: str,
        days: int
    ) -> pd.DataFrame:
        """Load user transactions with privacy protection."""
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Query transactions from database
            transactions_ref = self.db.collection('transactions').where('user_id', '==', user_id).where('date', '>=', start_date).where('date', '<=', end_date)

            transactions = []
            for doc in transactions_ref.stream():
                transaction = doc.to_dict()
                transaction['id'] = doc.id
                transactions.append(transaction)

            if not transactions:
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(transactions)

            # Ensure required columns exis
            required_columns = ['amount', 'date', 'merchant', 'category', 'description']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = None

            return df

        except Exception as e:
            logger.error(f"Error loading transactions: {str(e)}")
            return pd.DataFrame()

    async def _preprocess_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess transactions with privacy-preserving techniques."""
        if df.empty:
            return df

        try:
            # Make a copy to avoid modifying original
            processed_df = df.copy()

            # Convert date column
            processed_df['date'] = pd.to_datetime(processed_df['date'])
            processed_df = processed_df.sort_values('date')

            # Privacy-preserving transformations
            if self.privacy_config['hash_merchants']:
                processed_df['merchant_hash'] = processed_df['merchant'].apply(
                    lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:16] if pd.notna(x) else 'unknown'
                )

            # Feature engineering
            processed_df['hour'] = processed_df['date'].dt.hour
            processed_df['day_of_week'] = processed_df['date'].dt.dayofweek
            processed_df['month'] = processed_df['date'].dt.month
            processed_df['is_weekend'] = processed_df['day_of_week'].isin([5, 6])
            processed_df['is_late_night'] = processed_df['hour'].between(22, 6)

            # Amount features
            processed_df['amount_abs'] = processed_df['amount'].abs()
            processed_df['amount_log'] = np.log1p(processed_df['amount_abs'])

            # Time-based features
            processed_df['time_since_last'] = processed_df['date'].diff().dt.total_seconds()
            processed_df['time_since_last'] = processed_df['time_since_last'].fillna(0)

            # Category encoding
            processed_df['category'] = processed_df['category'].fillna('other')
            processed_df['category_encoded'] = self.scalers['categorical'].fit_transform(
                processed_df['category'].astype(str)
            )

            # Clean up NaN values
            processed_df = processed_df.fillna({
                'amount': 0,
                'merchant': 'unknown',
                'description': '',
                'category': 'other'
            })

            return processed_df

        except Exception as e:
            logger.error(f"Error preprocessing transactions: {str(e)}")
            return df

    async def _detect_recurring_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect recurring transactions and subscriptions."""
        if df.empty:
            return {'patterns': [], 'subscriptions': []}

        try:
            patterns = []
            subscriptions = []

            # Group by merchant and amount for potential subscriptions
            for (merchant, amount), group in df.groupby(['merchant', 'amount_abs']):
                if len(group) < 3:  # Need at least 3 occurrences
                    continue

                # Calculate time differences
                dates = sorted(group['date'].tolist())
                intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]

                # Check for regular intervals
                if intervals:
                    avg_interval = np.mean(intervals)
                    interval_std = np.std(intervals)
                    consistency = 1 - (interval_std / avg_interval) if avg_interval > 0 else 0

                    if consistency > 0.8 and 25 <= avg_interval <= 35:  # Monthly-ish
                        subscription = {
                            'merchant': merchant,
                            'amount': float(amount),
                            'frequency': 'monthly',
                            'consistency_score': float(consistency),
                            'occurrences': len(group),
                            'avg_interval_days': float(avg_interval),
                            'next_expected_date': (max(dates) + timedelta(days=avg_interval)).isoformat(),
                            'adhd_insight': 'Regular subscription detected - great for budgeting predictability!'
                        }
                        subscriptions.append(subscription)

                    elif consistency > 0.7:  # Other recurring pattern
                        pattern = {
                            'merchant': merchant,
                            'amount': float(amount),
                            'pattern_type': 'recurring',
                            'consistency_score': float(consistency),
                            'occurrences': len(group),
                            'avg_interval_days': float(avg_interval)
                        }
                        patterns.append(pattern)

            return {
                'patterns': patterns,
                'subscriptions': subscriptions,
                'total_recurring_amount': sum(s['amount'] for s in subscriptions),
                'analysis_confidence': 0.9 if subscriptions else 0.7
            }

        except Exception as e:
            logger.error(f"Error detecting recurring patterns: {str(e)}")
            return {'patterns': [], 'subscriptions': []}

    async def _detect_spending_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect unusual spending patterns using isolation forest."""
        if len(df) < 10:
            return {'anomalies': [], 'anomaly_score_threshold': 0.0}

        try:
            # Prepare features for anomaly detection
            feature_columns = ['amount_abs', 'hour', 'day_of_week', 'category_encoded']
            features = df[feature_columns].copy()

            # Scale features
            features_scaled = self.scalers['transaction'].fit_transform(features)

            # Detect anomalies
            anomaly_scores = self.models['anomaly_detector'].fit_predict(features_scaled)
            anomaly_score_values = self.models['anomaly_detector'].score_samples(features_scaled)

            # Add anomaly scores to dataframe
            df_copy = df.copy()
            df_copy['anomaly_score'] = anomaly_score_values
            df_copy['is_anomaly'] = anomaly_scores == -1

            # Extract anomalous transactions
            anomalies = []
            anomalous_transactions = df_copy[df_copy['is_anomaly']].copy()

            for _, transaction in anomalous_transactions.iterrows():
                anomaly = {
                    'transaction_id': transaction.get('id', 'unknown'),
                    'date': transaction['date'].isoformat(),
                    'amount': float(transaction['amount']),
                    'merchant': transaction['merchant'],
                    'category': transaction['category'],
                    'anomaly_score': float(transaction['anomaly_score']),
                    'anomaly_reason': self._explain_anomaly(transaction, df),
                    'adhd_insight': 'Unusual spending detected - worth a quick check to see if this aligns with your goals'
                }
                anomalies.append(anomaly)

            return {
                'anomalies': sorted(anomalies, key=lambda x: x['anomaly_score']),
                'total_anomalies': len(anomalies),
                'anomaly_percentage': float(len(anomalies) / len(df) * 100),
                'anomaly_score_threshold': float(np.percentile(anomaly_score_values, 10))
            }

        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            return {'anomalies': [], 'anomaly_score_threshold': 0.0}

    async def _predict_future_spending(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Predict future spending using time series analysis."""
        if len(df) < 30:
            return {'predictions': [], 'accuracy': 0.0}

        try:
            # Aggregate spending by day
            daily_spending = df.groupby(df['date'].dt.date).agg({
                'amount_abs': 'sum',
                'id': 'count'
            }).rename(columns={'id': 'transaction_count'})

            # Create features for prediction
            daily_spending = daily_spending.reset_index()
            daily_spending['day_of_week'] = pd.to_datetime(daily_spending['date']).dt.dayofweek
            daily_spending['month'] = pd.to_datetime(daily_spending['date']).dt.month
            daily_spending['is_weekend'] = daily_spending['day_of_week'].isin([5, 6])

            # Prepare training data
            feature_cols = ['day_of_week', 'month', 'is_weekend', 'transaction_count']
            X = daily_spending[feature_cols].fillna(0)
            y = daily_spending['amount_abs']

            if len(X) < 15:
                return {'predictions': [], 'accuracy': 0.0}

            # Train model
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            self.models['spending_predictor'].fit(X_train, y_train)

            # Calculate accuracy
            y_pred = self.models['spending_predictor'].predict(X_test)
            accuracy = 1 - (mean_absolute_error(y_test, y_pred) / np.mean(y_test))
            accuracy = max(0, min(1, accuracy))  # Bound between 0 and 1

            # Generate predictions for next 30 days
            predictions = []
            today = datetime.now().date()

            for i in range(30):
                future_date = today + timedelta(days=i+1)
                day_of_week = future_date.weekday()
                month = future_date.month
                is_weekend = day_of_week in [5, 6]

                # Predict based on historical transaction count average
                avg_transaction_count = daily_spending['transaction_count'].mean()

                features = np.array([[day_of_week, month, is_weekend, avg_transaction_count]])
                predicted_amount = self.models['spending_predictor'].predict(features)[0]

                # Calculate confidence interval (simple approach)
                std_error = np.std(y_test - y_pred) if len(y_test) > 0 else predicted_amount * 0.2
                confidence_lower = max(0, predicted_amount - 1.96 * std_error)
                confidence_upper = predicted_amount + 1.96 * std_error

                prediction = {
                    'date': future_date.isoformat(),
                    'predicted_amount': float(predicted_amount),
                    'confidence_lower': float(confidence_lower),
                    'confidence_upper': float(confidence_upper),
                    'day_type': 'weekend' if is_weekend else 'weekday'
                }
                predictions.append(prediction)

            # Weekly and monthly aggregations
            weekly_pred = sum(p['predicted_amount'] for p in predictions[:7])
            monthly_pred = sum(p['predicted_amount'] for p in predictions[:30])

            return {
                'predictions': predictions,
                'weekly_prediction': float(weekly_pred),
                'monthly_prediction': float(monthly_pred),
                'accuracy_score': float(accuracy),
                'confidence_level': 'high' if accuracy > 0.8 else 'medium' if accuracy > 0.6 else 'low',
                'adhd_note': 'Predictions help with planning, but remember ADHD brains can be unpredictable - be kind to yourself!'
            }

        except Exception as e:
            logger.error(f"Error predicting future spending: {str(e)}")
            return {'predictions': [], 'accuracy': 0.0}

    async def _analyze_adhd_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze ADHD-specific spending patterns."""
        if df.empty:
            return {'patterns': []}

        try:
            patterns = []

            # 1. Impulse spending detection
            impulse_patterns = await self._detect_impulse_spending(df)
            if impulse_patterns:
                patterns.extend(impulse_patterns)

            # 2. Hyperfocus spending periods
            hyperfocus_patterns = await self._detect_hyperfocus_spending(df)
            if hyperfocus_patterns:
                patterns.extend(hyperfocus_patterns)

            # 3. Forgotten subscription analysis
            forgotten_subs = await self._detect_forgotten_subscriptions(df)
            if forgotten_subs:
                patterns.extend(forgotten_subs)

            # 4. Stress spending correlation
            stress_patterns = await self._detect_stress_spending(df)
            if stress_patterns:
                patterns.extend(stress_patterns)

            # 5. Late night spending (executive function fatigue)
            late_night_patterns = await self._detect_late_night_spending(df)
            if late_night_patterns:
                patterns.extend(late_night_patterns)

            return {
                'patterns': patterns,
                'total_adhd_patterns': len(patterns),
                'pattern_types': list(set(p['pattern_type'] for p in patterns))
            }

        except Exception as e:
            logger.error(f"Error analyzing ADHD patterns: {str(e)}")
            return {'patterns': []}

    async def _analyze_category_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze spending trends by category."""
        if df.empty:
            return {'trends': []}

        try:
            # Group by category and week
            df['week'] = df['date'].dt.to_period('W')
            weekly_category = df.groupby(['category', 'week'])['amount_abs'].sum().reset_index()

            trends = []
            for category in df['category'].unique():
                if pd.isna(category):
                    continue

                category_data = weekly_category[weekly_category['category'] == category]
                if len(category_data) < 3:
                    continue

                amounts = category_data['amount_abs'].values
                weeks = range(len(amounts))

                # Calculate trend
                if len(amounts) > 1:
                    trend_slope = np.polyfit(weeks, amounts, 1)[0]
                    trend_direction = 'increasing' if trend_slope > 0 else 'decreasing' if trend_slope < 0 else 'stable'

                    # Calculate variability
                    variability = np.std(amounts) / np.mean(amounts) if np.mean(amounts) > 0 else 0

                    trend = {
                        'category': category,
                        'trend_direction': trend_direction,
                        'trend_strength': float(abs(trend_slope)),
                        'variability': float(variability),
                        'average_weekly': float(np.mean(amounts)),
                        'total_amount': float(np.sum(amounts)),
                        'weeks_analyzed': len(amounts),
                        'adhd_insight': self._get_category_adhd_insight(category, trend_direction, variability)
                    }
                    trends.append(trend)

            # Sort by total amount descending
            trends = sorted(trends, key=lambda x: x['total_amount'], reverse=True)

            return {
                'trends': trends,
                'top_categories': [t['category'] for t in trends[:5]],
                'most_variable_category': max(trends, key=lambda x: x['variability'])['category'] if trends else None
            }

        except Exception as e:
            logger.error(f"Error analyzing category trends: {str(e)}")
            return {'trends': []}

    # ADHD-specific pattern detection methods

    async def _detect_impulse_spending(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect impulse spending patterns."""
        patterns = []

        # Look for rapid successive transactions
        df_sorted = df.sort_values('date')

        for i in range(len(df_sorted) - 1):
            current = df_sorted.iloc[i]
            next_trans = df_sorted.iloc[i + 1]

            time_diff = (next_trans['date'] - current['date']).total_seconds()

            # Check for impulse pattern
            if (time_diff < self.adhd_patterns['impulse_spending']['time_threshold'] and
                current['amount_abs'] > df['amount_abs'].mean() * self.adhd_patterns['impulse_spending']['amount_multiplier'] and
                current['category'] in self.adhd_patterns['impulse_spending']['categories']):

                patterns.append({
                    'pattern_type': 'impulse_spending',
                    'transaction_id': current.get('id'),
                    'date': current['date'].isoformat(),
                    'amount': float(current['amount_abs']),
                    'category': current['category'],
                    'confidence': 0.8,
                    'adhd_insight': 'Impulse spending is common with ADHD - this is normal brain behavior!'
                })

        return patterns[:10]  # Limit results

    async def _detect_hyperfocus_spending(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect hyperfocus spending periods."""
        patterns = []

        # Group transactions by hour windows
        df['hour_window'] = df['date'].dt.floor('H')
        hourly_groups = df.groupby(['hour_window', 'category']).size()

        for (hour, category), count in hourly_groups.items():
            if count >= self.adhd_patterns['hyperfocus_periods']['transaction_density']:
                period_transactions = df[
                    (df['hour_window'] == hour) & (df['category'] == category)
                ]

                total_amount = period_transactions['amount_abs'].sum()

                patterns.append({
                    'pattern_type': 'hyperfocus_spending',
                    'date': hour.isoformat(),
                    'category': category,
                    'transaction_count': int(count),
                    'total_amount': float(total_amount),
                    'confidence': 0.9,
                    'adhd_insight': 'Hyperfocus spending in one category - ADHD brains sometimes get very focused!'
                })

        return patterns[:5]  # Limit results

    async def _detect_forgotten_subscriptions(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect potentially forgotten subscriptions."""
        patterns = []

        # This would integrate with external data or user behavior
        # For now, identify regular charges with no recent complementary activity

        return patterns  # Placeholder

    async def _detect_stress_spending(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect stress-related spending patterns."""
        patterns = []

        # Look for spending spikes during typical stress times
        late_night_spending = df[df['is_late_night']]
        weekend_spending = df[df['is_weekend']]

        if not late_night_spending.empty:
            avg_late_night = late_night_spending['amount_abs'].mean()
            avg_normal = df[~df['is_late_night']]['amount_abs'].mean()

            if avg_late_night > avg_normal * self.adhd_patterns['stress_spending']['deviation_threshold']:
                patterns.append({
                    'pattern_type': 'stress_spending',
                    'trigger': 'late_night',
                    'average_amount': float(avg_late_night),
                    'comparison_amount': float(avg_normal),
                    'confidence': 0.7,
                    'adhd_insight': 'Late night spending can happen when executive function is tired - be gentle with yourself'
                })

        return patterns

    async def _detect_late_night_spending(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect late night spending patterns."""
        patterns = []

        late_night_transactions = df[df['is_late_night']]

        if not late_night_transactions.empty:
            total_late_night = len(late_night_transactions)
            total_transactions = len(df)
            late_night_percentage = (total_late_night / total_transactions) * 100

            if late_night_percentage > 15:  # More than 15% late night spending
                patterns.append({
                    'pattern_type': 'late_night_spending',
                    'percentage': float(late_night_percentage),
                    'transaction_count': int(total_late_night),
                    'average_amount': float(late_night_transactions['amount_abs'].mean()),
                    'confidence': 0.8,
                    'adhd_insight': 'Late night spending often happens when our executive function is tired - consider setting spending limits after 10pm'
                })

        return patterns

    # Helper methods

    def _explain_anomaly(self, transaction: pd.Series, df: pd.DataFrame) -> str:
        """Explain why a transaction is considered anomalous."""
        reasons = []

        avg_amount = df['amount_abs'].mean()
        if transaction['amount_abs'] > avg_amount * 3:
            reasons.append(f"Amount (${transaction['amount_abs']:.2f}) is much higher than usual")

        if transaction['is_late_night']:
            reasons.append("Transaction occurred late at night")

        category_avg = df[df['category'] == transaction['category']]['amount_abs'].mean()
        if pd.notna(category_avg) and transaction['amount_abs'] > category_avg * 2:
            reasons.append(f"Amount is unusually high for {transaction['category']} category")

        return "; ".join(reasons) if reasons else "Pattern differs from typical spending behavior"

    def _get_category_adhd_insight(self, category: str, trend: str, variability: float) -> str:
        """Get ADHD-specific insight for category trends."""
        insights = {
            'dining': f"Food spending is {trend} - ADHD brains often use food for comfort and executive function support",
            'shopping': f"Shopping is {trend} - this could be dopamine-seeking or hyperfocus periods",
            'entertainment': f"Entertainment spending is {trend} - good for you for investing in joy and stimulation!",
            'transportation': f"Transportation costs are {trend} - routine expenses like this help with predictability",
            'healthcare': f"Healthcare spending is {trend} - taking care of your health is always a win!"
        }

        base_insight = insights.get(category, f"{category} spending is {trend}")

        if variability > 0.5:
            base_insight += " with high variability - totally normal for ADHD brains!"

        return base_insight

    async def _generate_adhd_insights(
        self,
        analyses: Dict[str, Any],
        df: pd.DataFrame
    ) -> List[SpendingInsight]:
        """Generate ADHD-friendly insights from analyses."""
        insights = []
        insight_id = 0

        try:
            # Recurring patterns insights
            if 'recurring_patterns' in analyses:
                recurring = analyses['recurring_patterns']
                if recurring.get('subscriptions'):
                    insight_id += 1
                    insights.append(SpendingInsight(
                        insight_id=str(insight_id),
                        title="Subscription Detective Work! 🔍",
                        description=f"Found {len(recurring['subscriptions'])} regular subscriptions totaling ${recurring.get('total_recurring_amount', 0):.2f}/month",
                        insight_type='positive',
                        confidence=0.9,
                        adhd_relevance="Predictable expenses are great for ADHD budgeting!",
                        actionable_tips=[
                            "Review subscriptions to ensure they're still valuable",
                            "Set up calendar reminders to check them quarterly",
                            "Consider if any forgotten subscriptions can be cancelled"
                        ],
                        affected_amount=recurring.get('total_recurring_amount', 0)
                    ))

            # Anomaly insights
            if 'anomaly_detection' in analyses:
                anomalies = analyses['anomaly_detection']
                if anomalies.get('anomalies'):
                    insight_id += 1
                    unusual_count = len(anomalies['anomalies'])
                    insights.append(SpendingInsight(
                        insight_id=str(insight_id),
                        title="Unusual Spending Spotted 👀",
                        description=f"Detected {unusual_count} unusual transactions - worth a quick check!",
                        insight_type='neutral',
                        confidence=0.8,
                        adhd_relevance="ADHD brains sometimes make impulsive decisions - that's totally normal",
                        actionable_tips=[
                            "Review unusual transactions to see if they align with your goals",
                            "No shame if some were impulse purchases - we all do it!",
                            "Consider if any patterns could inform future budgeting"
                        ]
                    ))

            # ADHD pattern insights
            if 'adhd_insights' in analyses:
                adhd_patterns = analyses['adhd_insights']
                for pattern in adhd_patterns.get('patterns', []):
                    insight_id += 1

                    if pattern['pattern_type'] == 'impulse_spending':
                        insights.append(SpendingInsight(
                            insight_id=str(insight_id),
                            title="Impulse Purchase Alert 🛍️",
                            description="Noticed some quick spending decisions - totally normal for ADHD brains!",
                            insight_type='neutral',
                            confidence=pattern.get('confidence', 0.7),
                            adhd_relevance="Impulse purchases are common with ADHD due to dopamine-seeking",
                            actionable_tips=[
                                "Try the '24-hour rule' for non-essential purchases over $50",
                                "Keep a 'want list' to help with impulse control",
                                "Remember: occasional impulse purchases are human!"
                            ],
                            affected_amount=pattern.get('amount')
                        ))

                    elif pattern['pattern_type'] == 'hyperfocus_spending':
                        insights.append(SpendingInsight(
                            insight_id=str(insight_id),
                            title="Hyperfocus Shopping Session 🎯",
                            description=f"Detected focused spending in {pattern.get('category', 'a category')} - classic ADHD hyperfocus!",
                            insight_type='positive',
                            confidence=pattern.get('confidence', 0.8),
                            adhd_relevance="Hyperfocus can lead to concentrated spending - it's how ADHD brains work!",
                            actionable_tips=[
                                "Hyperfocus purchases can be strategic - assess if they align with goals",
                                "Set spending limits for hyperfocus sessions",
                                "Use hyperfocus productively for researching big purchases"
                            ]
                        ))

            # Spending predictions insigh
            if 'spending_predictions' in analyses:
                predictions = analyses['spending_predictions']
                if predictions.get('monthly_prediction'):
                    insight_id += 1
                    insights.append(SpendingInsight(
                        insight_id=str(insight_id),
                        title="Future Spending Forecast 🔮",
                        description=f"Based on your patterns, predicting ~${predictions['monthly_prediction']:.0f} for next month",
                        insight_type='positive',
                        confidence=predictions.get('accuracy_score', 0.7),
                        adhd_relevance="Predictions help ADHD brains plan ahead and reduce anxiety",
                        actionable_tips=[
                            "Use this forecast for monthly budgeting",
                            "Remember predictions are estimates - be flexible!",
                            "Plan for both the predicted amount and some buffer"
                        ],
                        affected_amount=predictions['monthly_prediction']
                    ))

            return insights[:5]  # Limit to top 5 insights

        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return []

    # Privacy and utility methods

    def _hash_user_id(self, user_id: str) -> str:
        """Create privacy-preserving hash of user ID."""
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

    async def _check_ml_consent(self, user_id: str) -> bool:
        """Check if user has consented to ML analysis."""
        try:
            user_ref = self.db.collection('user_preferences').document(user_id)
            user_doc = user_ref.get()

            if user_doc.exists:
                prefs = user_doc.to_dict()
                return prefs.get('ml_analytics_consent', False)

            return False

        except Exception as e:
            logger.error(f"Error checking ML consent: {str(e)}")
            return False

    async def _load_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """Load cached user patterns for real-time scoring."""
        try:
            patterns_ref = self.db.collection('ml_patterns').document(user_id)
            patterns_doc = patterns_ref.get()

            if patterns_doc.exists:
                return patterns_doc.to_dict()

            return {}

        except Exception as e:
            logger.error(f"Error loading user patterns: {str(e)}")
            return {}

    async def _score_anomaly(self, transaction: Dict[str, Any], patterns: Dict[str, Any]) -> float:
        """Score transaction for anomaly likelihood."""
        # Simplified scoring based on amount deviation
        try:
            amount = abs(float(transaction.get('amount', 0)))
            avg_amount = patterns.get('average_amount', amount)

            if avg_amount > 0:
                deviation = abs(amount - avg_amount) / avg_amount
                return min(1.0, deviation)

            return 0.0

        except Exception:
            return 0.0

    async def _score_impulse_likelihood(self, transaction: Dict[str, Any], patterns: Dict[str, Any]) -> float:
        """Score transaction for impulse likelihood."""
        score = 0.0

        # Check category
        category = transaction.get('category', '').lower()
        if category in ['shopping', 'entertainment', 'dining']:
            score += 0.3

        # Check time of day
        hour = datetime.fromisoformat(transaction.get('timestamp', datetime.now().isoformat())).hour
        if 20 <= hour <= 23:  # Evening hours
            score += 0.2

        # Check amount relative to typical
        amount = abs(float(transaction.get('amount', 0)))
        avg_amount = patterns.get('average_amount', amount)
        if amount > avg_amount * 1.5:
            score += 0.3

        return min(1.0, score)

    async def _score_recurring_likelihood(self, transaction: Dict[str, Any], patterns: Dict[str, Any]) -> float:
        """Score transaction for recurring likelihood."""
        merchant = transaction.get('merchant', '')
        amount = abs(float(transaction.get('amount', 0)))

        # Check against known recurring patterns
        recurring_patterns = patterns.get('recurring_transactions', [])

        for pattern in recurring_patterns:
            if (pattern.get('merchant') == merchant and
                abs(pattern.get('amount', 0) - amount) < 1.0):
                return 0.9

        return 0.1

    async def _score_emotional_trigger(self, transaction: Dict[str, Any], patterns: Dict[str, Any]) -> float:
        """Score transaction for emotional trigger likelihood."""
        score = 0.0

        # Check time patterns (late night, weekend)
        timestamp = datetime.fromisoformat(transaction.get('timestamp', datetime.now().isoformat()))

        if timestamp.hour >= 22 or timestamp.hour <= 6:
            score += 0.4

        if timestamp.weekday() >= 5:  # Weekend
            score += 0.2

        # Check category
        emotional_categories = ['food', 'shopping', 'entertainment']
        if transaction.get('category', '').lower() in emotional_categories:
            score += 0.3

        return min(1.0, score)

    async def _log_analysis_event(
        self,
        user_id: str,
        analysis_types: List[str],
        transaction_count: int
    ):
        """Log analysis event for monitoring and improvement."""
        try:
            event = {
                'user_id_hash': self._hash_user_id(user_id),
                'analysis_types': analysis_types,
                'transaction_count': transaction_count,
                'timestamp': datetime.utcnow(),
                'service': 'ml_analytics'
            }

            self.db.collection('ml_analytics_events').add(event)

        except Exception as e:
            logger.error(f"Error logging analysis event: {str(e)}")

    # Synchronous wrappers for Flask routes

    def analyze_user_patterns_sync(
        self,
        user_id: str,
        analysis_types: List[str] = None,
        time_period_days: int = 90
    ) -> Dict[str, Any]:
        """Synchronous wrapper for analyze_user_patterns."""
        import asyncio
        return asyncio.run(self.analyze_user_patterns(user_id, analysis_types, time_period_days))

    def score_new_transaction_sync(
        self,
        user_id: str,
        transaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synchronous wrapper for score_new_transaction."""
        import asyncio
        return asyncio.run(self.score_new_transaction(user_id, transaction))
