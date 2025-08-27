"""
BrainBudget Notification Service
ADHD-friendly intelligent notification system using Firebase Cloud Messaging
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import firebase_admin
from firebase_admin import messaging, firestore
from app.services.firebase_service import FirebaseService
import pytz

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications supported by BrainBudget."""
    SPENDING_ALERT = "spending_alert"
    UNUSUAL_PATTERN = "unusual_pattern"
    GOAL_ACHIEVEMENT = "goal_achievement"
    WEEKLY_SUMMARY = "weekly_summary"
    BILL_REMINDER = "bill_reminder"
    ENCOURAGEMENT = "encouragement"
    MILESTONE = "milestone"


class NotificationPriority(Enum):
    """Priority levels for notifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationService:
    """
    Intelligent notification service with ADHD-friendly design principles.

    Features:
    - Rate limiting to prevent notification fatigue
    - Quiet hours respec
    - Personalized messaging with gentle, encouraging language
    - User preference managemen
    - Analytics tracking for effectiveness
    """

    def __init__(self, firebase_service: FirebaseService = None):
        """Initialize the notification service."""
        self.firebase_service = firebase_service or FirebaseService()
        self.db = self.firebase_service.db

        # ADHD-friendly notification templates
        self.templates = {
            NotificationType.SPENDING_ALERT: {
                'gentle': {
                    'title': '💫 Hey, just a friendly heads up!',
                    'body': "You're at {percentage}% of your {category} budget. Still time to adjust if needed! 💙",
                    'action': 'View spending details'
                },
                'approaching': {
                    'title': '🌟 Almost there!',
                    'body': "You've used {percentage}% of your {category} budget. You're doing great managing your money! 🎯",
                    'action': 'See remaining budget'
                },
                'exceeded': {
                    'title': '🤗 No worries, it happens!',
                    'body': "You went a bit over your {category} budget. Let's look at some gentle adjustments together. 🌱",
                    'action': 'Adjust budget'
                }
            },
            NotificationType.UNUSUAL_PATTERN: {
                'spending_spike': {
                    'title': '🔍 Something different today',
                    'body': "I noticed you spent more than usual on {category} today. Everything okay? I'm here to help if needed! 💜",
                    'action': 'Review transactions'
                },
                'new_merchant': {
                    'title': '👋 New place detected!',
                    'body': "I see you tried somewhere new: {merchant}. How was it? Want to set a budget for this category? 🗺️",
                    'action': 'Categorize spending'
                }
            },
            NotificationType.GOAL_ACHIEVEMENT: {
                'milestone': {
                    'title': '🎉 Incredible achievement!',
                    'body': "You reached your {goal_name} goal! That takes real dedication. You should be proud! 🌟",
                    'action': 'Celebrate & set new goal'
                },
                'streak': {
                    'title': '🔥 Amazing streak!',
                    'body': "Day {days} of staying under budget! Your brain is building fantastic money habits. Keep it up! 🧠✨",
                    'action': 'View progress'
                }
            },
            NotificationType.WEEKLY_SUMMARY: {
                'positive': {
                    'title': '📊 Your week in money',
                    'body': "This week you stayed within budget {success_rate}% of the time! That's fantastic progress. 🎯💚",
                    'action': 'View full summary'
                },
                'encouraging': {
                    'title': '🌱 Growing your skills',
                    'body': "This week had some ups and downs with spending, and that's completely normal! Let's see what you learned. 📈",
                    'action': 'View insights'
                }
            },
            NotificationType.BILL_REMINDER: {
                'upcoming': {
                    'title': '📅 Gentle reminder',
                    'body': "Your {bill_name} bill ({amount}) is due in {days} days. Want me to help you prepare? 🤝",
                    'action': 'Plan payment'
                },
                'overdue': {
                    'title': '💙 No judgment here',
                    'body': "Your {bill_name} bill was due {days_ago} days ago. ADHD brains sometimes miss these - let's handle it gently. 🌸",
                    'action': 'Handle bill'
                }
            },
            NotificationType.ENCOURAGEMENT: {
                'daily': {
                    'title': '🌅 Good morning, financial warrior!',
                    'body': "You're taking control of your money one day at a time. That takes courage. I believe in you! 💪💜",
                    'action': 'Start your day'
                },
                'tough_day': {
                    'title': '🫂 It\'s okay to have tough days',
                    'body': "Money management is hard, especially for ADHD brains. Be gentle with yourself. Tomorrow is a fresh start. 🌅",
                    'action': 'Self-care tips'
                }
            }
        }

    async def send_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        template_key: str,
        data: Dict[str, Any] = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        schedule_time: datetime = None
    ) -> bool:
        """
        Send an ADHD-friendly notification to a user.

        Args:
            user_id: Firebase user ID
            notification_type: Type of notification
            template_key: Specific template variant to use
            data: Template data for personalization
            priority: Notification priority level
            schedule_time: When to send (None for immediate)

        Returns:
            bool: Success status
        """
        try:
            # Check user preferences and rate limits
            if not await self._can_send_notification(user_id, notification_type, priority):
                logger.info(f"Notification blocked by user preferences or rate limiting: {user_id}")
                return False

            # Get user's FCM tokens
            tokens = await self._get_user_fcm_tokens(user_id)
            if not tokens:
                logger.warning(f"No FCM tokens found for user: {user_id}")
                return False

            # Build notification conten
            notification_content = await self._build_notification_content(
                notification_type, template_key, data or {}, user_id
            )

            # Send notification
            success = await self._send_fcm_notification(
                tokens, notification_content, notification_type, priority
            )

            # Log notification for analytics
            await self._log_notification(
                user_id, notification_type, template_key, success, data
            )

            # Update rate limiting counters
            await self._update_rate_limits(user_id, notification_type)

            return success

        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return False

    async def _can_send_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        priority: NotificationPriority
    ) -> bool:
        """Check if we can send a notification based on user preferences and rate limits."""
        try:
            # Get user preferences
            prefs = await self._get_user_notification_preferences(user_id)

            # Check if notifications are enabled globally
            if not prefs.get('enabled', True):
                return False

            # Check if this specific type is enabled
            type_key = notification_type.value
            if not prefs.get('types', {}).get(type_key, {}).get('enabled', True):
                return False

            # Check quiet hours (unless urgent)
            if priority != NotificationPriority.URGENT:
                if await self._is_quiet_hours(user_id):
                    return False

            # Check rate limits
            if await self._is_rate_limited(user_id, notification_type):
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking notification permissions: {str(e)}")
            return False

    async def _is_quiet_hours(self, user_id: str) -> bool:
        """Check if current time is within user's quiet hours."""
        try:
            prefs = await self._get_user_notification_preferences(user_id)
            quiet_hours = prefs.get('quiet_hours', {})

            if not quiet_hours.get('enabled', False):
                return False

            # Get user's timezone, default to UTC
            user_timezone = prefs.get('timezone', 'UTC')
            tz = pytz.timezone(user_timezone)
            current_time = datetime.now(tz)
            current_hour = current_time.hour

            start_hour = quiet_hours.get('start', 22)  # 10 PM defaul
            end_hour = quiet_hours.get('end', 8)  # 8 AM defaul

            # Handle quiet hours that span midnigh
            if start_hour > end_hour:
                return current_hour >= start_hour or current_hour < end_hour
            else:
                return start_hour <= current_hour < end_hour

        except Exception as e:
            logger.error(f"Error checking quiet hours: {str(e)}")
            return False

    async def _is_rate_limited(self, user_id: str, notification_type: NotificationType) -> bool:
        """Check if user has hit rate limits for notifications."""
        try:
            today = datetime.utcnow().date().isoformat()

            # Check daily total limi
            daily_ref = self.db.collection('notification_limits').document(f"{user_id}_{today}")
            daily_doc = daily_ref.get()

            if daily_doc.exists:
                daily_count = daily_doc.to_dict().get('total_count', 0)
                if daily_count >= 10:  # Max 10 notifications per day
                    return True

            # Check per-type limits
            type_count = daily_doc.to_dict().get('type_counts', {}).get(notification_type.value, 0) if daily_doc.exists else 0
            type_limits = {
                NotificationType.SPENDING_ALERT.value: 5,
                NotificationType.UNUSUAL_PATTERN.value: 3,
                NotificationType.GOAL_ACHIEVEMENT.value: 10,
                NotificationType.WEEKLY_SUMMARY.value: 1,
                NotificationType.BILL_REMINDER.value: 3,
                NotificationType.ENCOURAGEMENT.value: 2
            }

            limit = type_limits.get(notification_type.value, 5)
            return type_count >= limi

        except Exception as e:
            logger.error(f"Error checking rate limits: {str(e)}")
            return False

    async def _get_user_fcm_tokens(self, user_id: str) -> List[str]:
        """Get all FCM tokens for a user."""
        try:
            tokens_ref = self.db.collection('user_fcm_tokens').document(user_id)
            tokens_doc = tokens_ref.get()

            if not tokens_doc.exists:
                return []

            tokens_data = tokens_doc.to_dict()
            # Filter out expired tokens and return active ones
            active_tokens = []
            for token, data in tokens_data.get('tokens', {}).items():
                if data.get('active', True):
                    active_tokens.append(token)

            return active_tokens

        except Exception as e:
            logger.error(f"Error getting FCM tokens: {str(e)}")
            return []

    async def _build_notification_content(
        self,
        notification_type: NotificationType,
        template_key: str,
        data: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Build personalized notification content from templates."""
        try:
            template = self.templates[notification_type][template_key]

            # Get user's name for personalization
            user_data = await self._get_user_data(user_id)
            user_name = user_data.get('display_name', 'there')

            # Format template with user data
            title = template['title'].format(**data) if data else template['title']
            body = template['body'].format(**data) if data else template['body']
            action = template['action'].format(**data) if data else template['action']

            # Add gentle personalization
            if '{user_name}' in body:
                body = body.replace('{user_name}', user_name)

            return {
                'title': title,
                'body': body,
                'action': action,
                'type': notification_type.value,
                'template_key': template_key,
                'icon': '/static/icons/brainbudget-icon-192.png',
                'badge': '/static/icons/brainbudget-badge.png'
            }

        except Exception as e:
            logger.error(f"Error building notification content: {str(e)}")
            return {
                'title': '🧠💰 BrainBudget',
                'body': 'You have a new update in your BrainBudget app!',
                'action': 'View app'
            }

    async def _send_fcm_notification(
        self,
        tokens: List[str],
        content: Dict[str, Any],
        notification_type: NotificationType,
        priority: NotificationPriority
    ) -> bool:
        """Send FCM notification to device tokens."""
        try:
            # Build FCM message
            fcm_priority = self._get_fcm_priority(priority)

            # Create notification payload
            notification = messaging.Notification(
                title=content['title'],
                body=content['body'],
                image=None  # Could add contextual images later
            )

            # Create data payload for handling in app
            data_payload = {
                'type': content['type'],
                'template_key': content['template_key'],
                'action': content['action'],
                'timestamp': datetime.utcnow().isoformat()
            }

            # Web-specific config for PWA
            web_config = messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=content['title'],
                    body=content['body'],
                    icon=content['icon'],
                    badge=content['badge'],
                    tag=f"brainbudget_{notification_type.value}",
                    renotify=True,
                    require_interaction=(priority == NotificationPriority.HIGH),
                    actions=[
                        messaging.WebpushNotificationAction(
                            action='view',
                            title=content['action']
                        ),
                        messaging.WebpushNotificationAction(
                            action='dismiss',
                            title='Not now'
                        )
                    ]
                ),
                fcm_options=messaging.WebpushFCMOptions(
                    link='/dashboard'  # Deep link to relevant page
                )
            )

            # Android-specific config
            android_config = messaging.AndroidConfig(
                priority=fcm_priority,
                notification=messaging.AndroidNotification(
                    icon='brainbudget_icon',
                    color='#4A90E2',  # Brand blue
                    sound='default',
                    tag=f"brainbudget_{notification_type.value}",
                    click_action='FLUTTER_NOTIFICATION_CLICK'
                )
            )

            # iOS-specific config
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=content['title'],
                            body=content['body']
                        ),
                        badge=1,
                        sound='default',
                        category='BRAINBUDGET_NOTIFICATION'
                    )
                )
            )

            # Send to each token
            successful_tokens = 0
            failed_tokens = []

            for token in tokens:
                try:
                    message = messaging.Message(
                        notification=notification,
                        data=data_payload,
                        token=token,
                        webpush=web_config,
                        android=android_config,
                        apns=apns_config
                    )

                    response = messaging.send(message)
                    successful_tokens += 1
                    logger.info(f"Successfully sent notification: {response}")

                except messaging.UnregisteredError:
                    # Token is invalid, remove i
                    failed_tokens.append(token)
                    logger.warning(f"Invalid FCM token removed: {token[:20]}...")

                except Exception as e:
                    logger.error(f"Error sending to token {token[:20]}...: {str(e)}")
                    failed_tokens.append(token)

            # Clean up invalid tokens
            if failed_tokens:
                await self._remove_invalid_tokens(tokens, failed_tokens)

            return successful_tokens > 0

        except Exception as e:
            logger.error(f"Error in FCM send: {str(e)}")
            return False

    def _get_fcm_priority(self, priority: NotificationPriority) -> str:
        """Convert our priority to FCM priority."""
        mapping = {
            NotificationPriority.LOW: 'normal',
            NotificationPriority.MEDIUM: 'normal',
            NotificationPriority.HIGH: 'high',
            NotificationPriority.URGENT: 'high'
        }
        return mapping.get(priority, 'normal')

    async def _log_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        template_key: str,
        success: bool,
        data: Dict[str, Any]
    ) -> None:
        """Log notification for analytics and debugging."""
        try:
            log_entry = {
                'user_id': user_id,
                'type': notification_type.value,
                'template_key': template_key,
                'success': success,
                'timestamp': datetime.utcnow(),
                'data': data or {},
                'platform': 'web'  # Could detect platform
            }

            self.db.collection('notification_logs').add(log_entry)

        except Exception as e:
            logger.error(f"Error logging notification: {str(e)}")

    async def _update_rate_limits(self, user_id: str, notification_type: NotificationType) -> None:
        """Update rate limiting counters."""
        try:
            today = datetime.utcnow().date().isoformat()
            limit_ref = self.db.collection('notification_limits').document(f"{user_id}_{today}")

            # Use transaction to update counters atomically
            @firestore.transactional
            def update_limits(transaction, ref):
                doc = ref.get(transaction=transaction)

                if doc.exists:
                    data = doc.to_dict()
                    total_count = data.get('total_count', 0) + 1
                    type_counts = data.get('type_counts', {})
                    type_counts[notification_type.value] = type_counts.get(notification_type.value, 0) + 1
                else:
                    total_count = 1
                    type_counts = {notification_type.value: 1}

                transaction.set(ref, {
                    'total_count': total_count,
                    'type_counts': type_counts,
                    'date': today,
                    'updated_at': datetime.utcnow()
                })

            transaction = self.db.transaction()
            update_limits(transaction, limit_ref)

        except Exception as e:
            logger.error(f"Error updating rate limits: {str(e)}")

    async def _get_user_notification_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's notification preferences."""
        try:
            prefs_ref = self.db.collection('user_preferences').document(user_id)
            prefs_doc = prefs_ref.get()

            if not prefs_doc.exists:
                # Return ADHD-friendly defaults
                return {
                    'enabled': True,
                    'types': {
                        'spending_alert': {'enabled': True, 'threshold': 80},
                        'unusual_pattern': {'enabled': True},
                        'goal_achievement': {'enabled': True},
                        'weekly_summary': {'enabled': True, 'day': 'sunday'},
                        'bill_reminder': {'enabled': False},  # Opt-in for bills
                        'encouragement': {'enabled': True}
                    },
                    'quiet_hours': {'enabled': True, 'start': 22, 'end': 8},
                    'timezone': 'UTC',
                    'tone': 'gentle',  # gentle, encouraging, direc
                    'frequency': 'moderate'  # minimal, moderate, frequen
                }

            return prefs_doc.to_dict().get('notifications', {})

        except Exception as e:
            logger.error(f"Error getting user preferences: {str(e)}")
            return {'enabled': False}  # Fail safe

    async def _get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get user profile data for personalization."""
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()

            if user_doc.exists:
                return user_doc.to_dict()

            return {}

        except Exception as e:
            logger.error(f"Error getting user data: {str(e)}")
            return {}

    async def _remove_invalid_tokens(self, all_tokens: List[str], invalid_tokens: List[str]) -> None:
        """Remove invalid FCM tokens from user's token list."""
        try:
            # This would be implemented to clean up invalid tokens from Firestore
            logger.info(f"Would remove {len(invalid_tokens)} invalid tokens")

        except Exception as e:
            logger.error(f"Error removing invalid tokens: {str(e)}")

    # Public methods for notification triggers

    async def send_spending_alert(
        self,
        user_id: str,
        category: str,
        percentage: int,
        amount_spent: float,
        budget_limit: float
    ) -> bool:
        """Send a spending alert notification."""
        if percentage >= 100:
            template_key = 'exceeded'
        elif percentage >= 80:
            template_key = 'approaching'
        else:
            template_key = 'gentle'

        data = {
            'category': category,
            'percentage': percentage,
            'amount_spent': f"${amount_spent:.2f}",
            'budget_limit': f"${budget_limit:.2f}"
        }

        priority = NotificationPriority.HIGH if percentage >= 100 else NotificationPriority.MEDIUM

        return await self.send_notification(
            user_id, NotificationType.SPENDING_ALERT, template_key, data, priority
        )

    async def send_goal_achievement(
        self,
        user_id: str,
        goal_name: str,
        achievement_type: str = 'milestone',
        days: int = None
    ) -> bool:
        """Send a goal achievement celebration."""
        data = {'goal_name': goal_name}
        if days:
            data['days'] = days

        return await self.send_notification(
            user_id, NotificationType.GOAL_ACHIEVEMENT, achievement_type, data, NotificationPriority.HIGH
        )

    async def send_weekly_summary(
        self,
        user_id: str,
        success_rate: int,
        total_spent: float,
        categories_summary: Dict[str, float]
    ) -> bool:
        """Send weekly spending summary."""
        template_key = 'positive' if success_rate >= 70 else 'encouraging'

        data = {
            'success_rate': success_rate,
            'total_spent': f"${total_spent:.2f}",
            'top_category': max(categories_summary, key=categories_summary.get) if categories_summary else 'dining'
        }

        return await self.send_notification(
            user_id, NotificationType.WEEKLY_SUMMARY, template_key, data, NotificationPriority.LOW
        )

    async def send_unusual_pattern_alert(
        self,
        user_id: str,
        pattern_type: str,
        category: str = None,
        merchant: str = None,
        amount: float = None
    ) -> bool:
        """Send unusual spending pattern alert."""
        data = {}
        if category:
            data['category'] = category
        if merchant:
            data['merchant'] = merchan
        if amount:
            data['amount'] = f"${amount:.2f}"

        return await self.send_notification(
            user_id, NotificationType.UNUSUAL_PATTERN, pattern_type, data, NotificationPriority.MEDIUM
        )

    async def send_encouragement(
        self,
        user_id: str,
        message_type: str = 'daily',
        context: Dict[str, Any] = None
    ) -> bool:
        """Send an encouraging message."""
        return await self.send_notification(
            user_id, NotificationType.ENCOURAGEMENT, message_type, context or {}, NotificationPriority.LOW
        )


# Utility functions for ML pattern analysis

class SpendingPatternAnalyzer:
    """Analyze spending patterns to detect unusual activity."""

    def __init__(self, firebase_service: FirebaseService):
        self.firebase_service = firebase_service
        self.db = firebase_service.db

    async def analyze_user_spending(self, user_id: str) -> List[Dict[str, Any]]:
        """Analyze user spending for unusual patterns."""
        try:
            # Get last 30 days of transactions
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)

            transactions = await self._get_user_transactions(user_id, start_date, end_date)

            if len(transactions) < 10:  # Need minimum data
                return []

            patterns = []

            # Check for spending spikes
            daily_spending = self._group_by_day(transactions)
            spike_alerts = self._detect_spending_spikes(daily_spending)
            patterns.extend(spike_alerts)

            # Check for new merchants
            new_merchants = self._detect_new_merchants(transactions, user_id)
            patterns.extend(new_merchants)

            # Check for category changes
            category_changes = self._detect_category_changes(transactions)
            patterns.extend(category_changes)

            return patterns

        except Exception as e:
            logger.error(f"Error analyzing spending patterns: {str(e)}")
            return []

    def _group_by_day(self, transactions: List[Dict]) -> Dict[str, float]:
        """Group transactions by day."""
        daily_totals = {}
        for transaction in transactions:
            date = transaction['date']
            amount = transaction['amount']
            daily_totals[date] = daily_totals.get(date, 0) + amoun
        return daily_totals

    def _detect_spending_spikes(self, daily_spending: Dict[str, float]) -> List[Dict]:
        """Detect days with unusually high spending."""
        if len(daily_spending) < 7:
            return []

        amounts = list(daily_spending.values())
        avg_spending = sum(amounts) / len(amounts)
        std_dev = (sum((x - avg_spending) ** 2 for x in amounts) / len(amounts)) ** 0.5

        threshold = avg_spending + (2 * std_dev)  # 2 standard deviations

        spikes = []
        for date, amount in daily_spending.items():
            if amount > threshold and amount > avg_spending * 1.5:
                spikes.append({
                    'type': 'spending_spike',
                    'date': date,
                    'amount': amount,
                    'avg_amount': avg_spending,
                    'severity': 'medium' if amount < avg_spending * 2 else 'high'
                })

        return spikes[-3:]  # Return only recent spikes

    def _detect_new_merchants(self, transactions: List[Dict]) -> List[Dict]:
        """Detect transactions with new merchants."""
        # This would typically compare against historical merchant data
        # For now, just return empty - would need historical data analysis
        return []

    def _detect_category_changes(self, transactions: List[Dict]) -> List[Dict]:
        """Detect significant changes in category spending."""
        # Group by category and compare to historical averages
        category_totals = {}
        for transaction in transactions:
            category = transaction.get('category', 'Other')
            amount = transaction.get('amount', 0)
            category_totals[category] = category_totals.get(category, 0) + amoun

        # This would compare against historical category averages
        # Implementation would require historical data analysis
        return []

    async def _get_user_transactions(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Get user transactions for analysis."""
        try:
            transactions_ref = self.db.collection('user_transactions').where('user_id', '==', user_id)
            transactions_ref = transactions_ref.where('date', '>=', start_date.date().isoformat())
            transactions_ref = transactions_ref.where('date', '<=', end_date.date().isoformat())

            docs = transactions_ref.stream()
            transactions = []

            for doc in docs:
                transaction_data = doc.to_dict()
                transactions.append(transaction_data)

            return transactions

        except Exception as e:
            logger.error(f"Error getting user transactions: {str(e)}")
            return []
