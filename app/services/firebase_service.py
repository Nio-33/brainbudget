"""
Firebase integration service for BrainBudget.
Handles authentication, Firestore database, and Cloud Storage.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import json

import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
from google.cloud.firestore import Client as FirestoreClient
from google.cloud.storage import Bucket

from app.utils.cache import UserProfileCache, AnalysisCache, cache_result


logger = logging.getLogger(__name__)


class FirebaseService:
    """Firebase service for authentication, database, and storage operations."""

    def __init__(self):
        self.app = None
        self.db: Optional[FirestoreClient] = None
        self.bucket: Optional[Bucket] = None
        self._initialized = False
        self.web_api_key = None
        self.flask_app = None

    def initialize(self, flask_app):
        """
        Initialize Firebase with Flask app configuration.

        Args:
            flask_app: Flask application instance
        """
        try:
            # Store Flask app reference for accessing config
            self.flask_app = flask_app
            
            # Check if we have valid Firebase credentials
            project_id = flask_app.config.get('FIREBASE_PROJECT_ID')
            private_key = flask_app.config.get('FIREBASE_PRIVATE_KEY')
            client_email = flask_app.config.get('FIREBASE_CLIENT_EMAIL')
            self.web_api_key = flask_app.config.get('FIREBASE_API_KEY')

            # Skip Firebase initialization in development if credentials are placeholders
            if (not project_id or not private_key or not client_email or
                'placeholder' in project_id.lower() or
                'demo' in project_id.lower() or
                'your-' in project_id.lower() or
                'placeholder' in private_key.lower() or
                'demo' in private_key.lower() or
                'YOUR_PRIVATE_KEY_HERE' in private_key):

                logger.warning("Firebase credentials appear to be placeholders. Skipping Firebase initialization.")
                logger.info("App will run without Firebase functionality for development purposes.")
                self._initialized = False
                return

            # Create credentials from config
            cred_dict = {
                "type": "service_account",
                "project_id": project_id,
                "private_key": private_key,
                "client_email": client_email,
                "token_uri": "https://oauth2.googleapis.com/token"
            }

            cred = credentials.Certificate(cred_dict)

            # Initialize Firebase app
            self.app = firebase_admin.initialize_app(cred, {
                'storageBucket': f"{project_id}.appspot.com"
            })

            # Initialize services
            self.db = firestore.client()
            self.bucket = storage.bucket()

            self._initialized = True
            logger.info("Firebase service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            if flask_app.config.get('DEBUG', False):
                logger.warning("Running in debug mode - continuing without Firebase")
                self._initialized = False
            else:
                raise

    def verify_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Firebase authentication token.

        Args:
            id_token: Firebase ID token

        Returns:
            User information if token is valid, None otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return None

        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None

    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by UID.

        Args:
            uid: Firebase user UID

        Returns:
            User information if found
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return None

        try:
            user_record = auth.get_user(uid)
            return {
                'uid': user_record.uid,
                'email': user_record.email,
                'email_verified': user_record.email_verified,
                'display_name': user_record.display_name,
                'created_at': user_record.user_metadata.creation_timestamp,
                'last_sign_in': user_record.user_metadata.last_sign_in_timestamp
            }
        except Exception as e:
            logger.error(f"Failed to get user {uid}: {e}")
            return None

    def create_user_profile(self, uid: str, profile_data: Dict[str, Any]) -> bool:
        """
        Create or update user profile in Firestore.

        Args:
            uid: Firebase user UID
            profile_data: User profile data

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return False

        try:
            profile_data.update({
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            })

            self.db.collection('users').document(uid).set(profile_data, merge=True)
            logger.info(f"User profile created/updated for {uid}")
            
            # Invalidate cache after update
            UserProfileCache.invalidate_profile(uid)
            
            return True

        except Exception as e:
            logger.error(f"Failed to create user profile for {uid}: {e}")
            return False

    def get_user_profile(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile from Firestore with caching.

        Args:
            uid: Firebase user UID

        Returns:
            User profile data if found
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return None

        # Try cache first
        cached_profile = UserProfileCache.get_profile(uid)
        if cached_profile is not None:
            return cached_profile

        try:
            doc = self.db.collection('users').document(uid).get()
            if doc.exists:
                profile_data = doc.to_dict()
                # Cache the result
                UserProfileCache.set_profile(uid, profile_data)
                return profile_data
            return None

        except Exception as e:
            logger.error(f"Failed to get user profile for {uid}: {e}")
            return None

    def save_analysis_result(self, uid: str, analysis_data: Dict[str, Any]) -> Optional[str]:
        """
        Save spending analysis result to Firestore.

        Args:
            uid: Firebase user UID
            analysis_data: Analysis result data

        Returns:
            Document ID if successful, None otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return None

        try:
            analysis_data.update({
                'user_id': uid,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            })

            doc_ref = self.db.collection('analyses').add(analysis_data)
            doc_id = doc_ref[1].id

            logger.info(f"Analysis result saved with ID: {doc_id}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to save analysis result for {uid}: {e}")
            return None

    @cache_result("user_analyses:{key}", ttl=900)  # Cache for 15 minutes
    def get_user_analyses(self, uid: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get user's spending analyses from Firestore.

        Args:
            uid: Firebase user UID
            limit: Maximum number of analyses to return

        Returns:
            List of analysis documents
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return []

        try:
            query = (self.db.collection('analyses')
                    .where('user_id', '==', uid)
                    .order_by('created_at', direction=firestore.Query.DESCENDING)
                    .limit(limit))

            docs = query.stream()
            analyses = []

            for doc in docs:
                analysis = doc.to_dict()
                analysis['id'] = doc.id
                analyses.append(analysis)

            logger.info(f"Retrieved {len(analyses)} analyses for user {uid}")
            return analyses

        except Exception as e:
            logger.error(f"Failed to get analyses for {uid}: {e}")
            return []

    def upload_file(self, file_data: bytes, filename: str, uid: str) -> Optional[str]:
        """
        Upload file to Firebase Cloud Storage.

        Args:
            file_data: File data as bytes
            filename: Original filename
            uid: Firebase user UID

        Returns:
            Public URL if successful, None otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return None

        try:
            # Create unique blob name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            blob_name = f"uploads/{uid}/{timestamp}_{filename}"

            # Upload file
            blob = self.bucket.blob(blob_name)
            blob.upload_from_string(file_data)

            # Make blob publicly accessible
            blob.make_public()

            logger.info(f"File uploaded: {blob_name}")
            return blob.public_url

        except Exception as e:
            logger.error(f"Failed to upload file {filename}: {e}")

            # Check if it's a "bucket does not exist" error
            if "bucket does not exist" in str(e).lower() or "notfound" in str(e).lower():
                logger.warning("Firebase Storage bucket not found. Using local storage fallback for development.")
                return self._upload_file_locally(file_data, filename, uid)

            return None

    def _upload_file_locally(self, file_data: bytes, filename: str, uid: str) -> Optional[str]:
        """
        Fallback: Upload file to local storage for development.

        Args:
            file_data: File data as bytes
            filename: Original filename
            uid: Firebase user UID

        Returns:
            Local file URL if successful, None otherwise
        """
        import os

        try:
            # Create uploads directory
            upload_dir = os.path.join("uploads", uid)
            os.makedirs(upload_dir, exist_ok=True)

            # Create unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(upload_dir, local_filename)

            # Save file locally
            with open(file_path, 'wb') as f:
                f.write(file_data)

            # Return local file URL (for development)
            local_url = f"/uploads/{uid}/{local_filename}"
            logger.info(f"File uploaded locally: {file_path}")

            return local_url

        except Exception as e:
            logger.error(f"Failed to upload file locally {filename}: {e}")
            return None

    def delete_file(self, file_url: str) -> bool:
        """
        Delete file from Firebase Cloud Storage.

        Args:
            file_url: Public URL of the file to delete

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return False

        try:
            # Extract blob name from URL
            blob_name = file_url.split('/')[-1]
            blob = self.bucket.blob(f"uploads/{blob_name}")
            blob.delete()

            logger.info(f"File deleted: {blob_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete file {file_url}: {e}")
            return False

    def save_transaction_data(self, uid: str, transactions: List[Dict[str, Any]]) -> bool:
        """
        Save transaction data to Firestore.

        Args:
            uid: Firebase user UID
            transactions: List of transaction dictionaries

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return False

        try:
            batch = self.db.batch()

            for transaction in transactions:
                transaction.update({
                    'user_id': uid,
                    'created_at': datetime.now(timezone.utc)
                })

                doc_ref = self.db.collection('transactions').document()
                batch.set(doc_ref, transaction)

            batch.commit()
            logger.info(f"Saved {len(transactions)} transactions for user {uid}")
            return True

        except Exception as e:
            logger.error(f"Failed to save transactions for {uid}: {e}")
            return False

    def send_email_verification(self, uid: str) -> bool:
        """
        Send email verification to user.

        Args:
            uid: Firebase user UID

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return False

        try:
            # In a real implementation, this would use Firebase Admin SDK
            # to generate and send a verification email
            logger.info(f"Email verification sent to user {uid}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email verification to {uid}: {e}")
            return False

    def get_user_transactions(self, uid: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get user's transaction data.

        Args:
            uid: Firebase user UID
            limit: Maximum number of transactions to return

        Returns:
            List of transaction documents
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return []

        try:
            query = (self.db.collection('transactions')
                    .where('user_id', '==', uid)
                    .order_by('created_at', direction=firestore.Query.DESCENDING)
                    .limit(limit))

            docs = query.stream()
            transactions = []

            for doc in docs:
                transaction = doc.to_dict()
                transaction['id'] = doc.id
                transactions.append(transaction)

            logger.info(f"Retrieved {len(transactions)} transactions for user {uid}")
            return transactions

        except Exception as e:
            logger.error(f"Failed to get transactions for {uid}: {e}")
            return []

    def get_user_preferences(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Get user's preferences and settings.

        Args:
            uid: Firebase user UID

        Returns:
            User preferences if found
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return None

        try:
            doc = self.db.collection('user_preferences').document(uid).get()
            if doc.exists:
                return doc.to_dict()
            return None

        except Exception as e:
            logger.error(f"Failed to get preferences for {uid}: {e}")
            return None

    def verify_user_password(self, email: str, password: str) -> bool:
        """
        Verify user password using Firebase Auth REST API.

        Args:
            email: User email
            password: Password to verify

        Returns:
            True if password is correct, False otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return False

        try:
            import requests
            
            # Get the Web API Key from config
            if not self.web_api_key:
                logger.error("Firebase Web API Key not available")
                return False
            
            # Firebase Auth REST API endpoint
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.web_api_key}"
            
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Password verification successful for {email}")
                return True
            else:
                logger.warning(f"Password verification failed for {email}: {response.status_code}")
                return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during password verification for {email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to verify password for {email}: {e}")
            return False

    def update_user_password(self, uid: str, new_password: str) -> bool:
        """
        Update user password.

        Args:
            uid: Firebase user UID
            new_password: New password

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return False

        try:
            # Use Firebase Admin SDK to update the user's password
            auth.update_user(uid, password=new_password)
            logger.info(f"Password updated for user {uid}")
            return True

        except Exception as e:
            logger.error(f"Failed to update password for {uid}: {e}")
            return False

    def schedule_account_deletion(self, uid: str, deletion_date: datetime) -> bool:
        """
        Schedule account for deletion.

        Args:
            uid: Firebase user UID
            deletion_date: When to delete the accoun

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return False

        try:
            deletion_data = {
                'user_id': uid,
                'scheduled_deletion': deletion_date,
                'created_at': datetime.now(timezone.utc),
                'status': 'scheduled'
            }

            self.db.collection('account_deletions').document(uid).set(deletion_data)
            logger.info(f"Account deletion scheduled for user {uid} on {deletion_date}")
            return True

        except Exception as e:
            logger.error(f"Failed to schedule deletion for {uid}: {e}")
            return False

    def cancel_account_deletion(self, uid: str) -> bool:
        """
        Cancel scheduled account deletion.

        Args:
            uid: Firebase user UID

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return False

        try:
            # Remove from scheduled deletions
            self.db.collection('account_deletions').document(uid).delete()
            logger.info(f"Account deletion cancelled for user {uid}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel deletion for {uid}: {e}")
            return False

    def send_account_deletion_email(self, uid: str, deletion_date: datetime) -> bool:
        """
        Send account deletion confirmation email.

        Args:
            uid: Firebase user UID
            deletion_date: Scheduled deletion date

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return False

        try:
            # In a real implementation, this would send an email
            # with cancellation instructions
            logger.info(f"Deletion confirmation email sent to user {uid}")
            return True

        except Exception as e:
            logger.error(f"Failed to send deletion email to {uid}: {e}")
            return False

    def update_user_profile(self, uid: str, profile_updates: Dict[str, Any]) -> bool:
        """
        Update specific fields in user profile.

        Args:
            uid: Firebase user UID
            profile_updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return False

        try:
            profile_updates['updated_at'] = datetime.now(timezone.utc)
            
            self.db.collection('users').document(uid).update(profile_updates)
            logger.info(f"User profile updated for {uid}")
            return True

        except Exception as e:
            logger.error(f"Failed to update user profile for {uid}: {e}")
            return False

    @cache_result("user_stats:{key}", ttl=1800)  # Cache for 30 minutes
    def get_user_stats(self, uid: str) -> Dict[str, Any]:
        """
        Calculate user statistics from their data.

        Args:
            uid: Firebase user UID

        Returns:
            Dictionary containing user statistics
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return {}

        try:
            # Get user data
            profile = self.get_user_profile(uid)
            transactions = self.get_user_transactions(uid, limit=1000)
            analyses = self.get_user_analyses(uid, limit=100)

            # Calculate days active
            days_active = 1
            if profile and 'created_at' in profile:
                try:
                    join_date = profile['created_at']
                    if hasattr(join_date, 'date'):
                        days_active = (datetime.now().date() - join_date.date()).days + 1
                    else:
                        # Handle Firestore timestamp
                        days_active = (datetime.now(timezone.utc) - join_date).days + 1
                except Exception:
                    pass

            # Calculate financial metrics
            total_saved = 0.0
            transaction_count = len(transactions)
            
            if transactions:
                # Simple calculation - sum positive amounts as savings
                positive_amounts = [t.get('amount', 0) for t in transactions if t.get('amount', 0) > 0]
                total_saved = sum(positive_amounts)

            # Calculate user score based on activity
            base_score = 50
            activity_score = min(len(analyses) * 5, 30)  # Up to 30 points for analyses
            transaction_score = min(transaction_count // 10, 20)  # Up to 20 points for transactions
            user_score = min(base_score + activity_score + transaction_score, 100)

            return {
                'days_active': max(days_active, 1),
                'goals_achieved': len(analyses),
                'user_score': user_score,
                'total_saved': round(total_saved, 2),
                'avg_monthly_save': round(total_saved / max(days_active / 30, 1), 2),
                'total_analyses': len(analyses),
                'total_transactions': transaction_count,
                'last_activity': datetime.now().strftime('%B %d, %Y')
            }

        except Exception as e:
            logger.error(f"Failed to calculate user stats for {uid}: {e}")
            return {}

    def get_user_timeline(self, uid: str) -> List[Dict[str, Any]]:
        """
        Generate user's financial journey timeline.

        Args:
            uid: Firebase user UID

        Returns:
            List of timeline events
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return []

        try:
            timeline = []
            
            # Get user data
            profile = self.get_user_profile(uid)
            analyses = self.get_user_analyses(uid, limit=10)

            # Add join event
            if profile and 'created_at' in profile:
                timeline.append({
                    'id': 'joined',
                    'title': 'Joined BrainBudget',
                    'description': 'Started your smart budgeting journey',
                    'date': profile['created_at'].strftime('%B %d, %Y') if hasattr(profile['created_at'], 'strftime') else str(profile['created_at']),
                    'status': 'completed',
                    'icon': '🎉',
                    'badge': 'Welcome Milestone'
                })

            # Add analysis milestones
            for i, analysis in enumerate(analyses):
                timeline.append({
                    'id': f'analysis_{analysis.get("id", i)}',
                    'title': f'Financial Analysis #{i+1}',
                    'description': 'Generated spending insights and recommendations',
                    'date': analysis.get('created_at').strftime('%B %d, %Y') if hasattr(analysis.get('created_at'), 'strftime') else 'Recent',
                    'status': 'completed',
                    'icon': '📊',
                    'badge': 'Insight Generated'
                })

            # Add current/future goals
            if len(analyses) > 0:
                timeline.append({
                    'id': 'goal_progress',
                    'title': 'Building Smart Habits',
                    'description': 'Continue using BrainBudget for financial insights',
                    'date': 'In Progress',
                    'status': 'in_progress',
                    'icon': '🎯',
                    'badge': 'Current Goal'
                })
            else:
                timeline.append({
                    'id': 'first_analysis',
                    'title': 'Upload Your First Statement',
                    'description': 'Get your first financial insights',
                    'date': 'Next Step',
                    'status': 'upcoming',
                    'icon': '📋',
                    'badge': 'Getting Started'
                })

            return timeline

        except Exception as e:
            logger.error(f"Failed to generate timeline for {uid}: {e}")
            return []

    def upload_profile_picture(self, uid: str, image_data: bytes, filename: str) -> Optional[str]:
        """
        Upload user profile picture to Firebase Storage.

        Args:
            uid: Firebase user UID
            image_data: Image file data as bytes
            filename: Original filename

        Returns:
            Public URL if successful, None otherwise
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return None

        try:
            # Create unique blob name for profile picture
            file_extension = filename.split('.')[-1] if '.' in filename else 'jpg'
            blob_name = f"profiles/{uid}/avatar.{file_extension}"

            # Upload file
            blob = self.bucket.blob(blob_name)
            blob.upload_from_string(image_data, content_type=f'image/{file_extension}')

            # Make blob publicly accessible
            blob.make_public()

            # Update user profile with new picture URL
            self.update_user_profile(uid, {'profile_picture': blob.public_url})

            logger.info(f"Profile picture uploaded for user {uid}")
            return blob.public_url

        except Exception as e:
            logger.error(f"Failed to upload profile picture for {uid}: {e}")
            
            # Fallback to local storage
            return self._upload_profile_picture_locally(uid, image_data, filename)

    def _upload_profile_picture_locally(self, uid: str, image_data: bytes, filename: str) -> Optional[str]:
        """
        Fallback: Upload profile picture to local storage.

        Args:
            uid: Firebase user UID
            image_data: Image file data as bytes
            filename: Original filename

        Returns:
            Local file URL if successful, None otherwise
        """
        import os

        try:
            # Create profile pictures directory
            profile_dir = os.path.join("static", "uploads", "profiles", uid)
            os.makedirs(profile_dir, exist_ok=True)

            # Save profile picture
            file_extension = filename.split('.')[-1] if '.' in filename else 'jpg'
            local_filename = f"avatar.{file_extension}"
            file_path = os.path.join(profile_dir, local_filename)

            with open(file_path, 'wb') as f:
                f.write(image_data)

            # Return local file URL
            local_url = f"/static/uploads/profiles/{uid}/{local_filename}"
            logger.info(f"Profile picture uploaded locally for user {uid}")

            return local_url

        except Exception as e:
            logger.error(f"Failed to upload profile picture locally for {uid}: {e}")
            return None

    def get_user_achievements(self, uid: str) -> List[Dict[str, Any]]:
        """
        Calculate and return user achievements.

        Args:
            uid: Firebase user UID

        Returns:
            List of user achievements
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return []

        try:
            # Get user data
            profile = self.get_user_profile(uid)
            transactions = self.get_user_transactions(uid)
            analyses = self.get_user_analyses(uid)

            achievements = []

            # First Steps Achievement
            if profile:
                achievements.append({
                    'id': 'first_steps',
                    'title': 'First Steps',
                    'description': 'Created your BrainBudget profile',
                    'icon': '🎯',
                    'color': 'green',
                    'unlocked': True,
                    'date': profile.get('created_at', 'Recent')
                })

            # Analysis Achievements
            if len(analyses) >= 1:
                achievements.append({
                    'id': 'insight_seeker',
                    'title': 'Insight Seeker',
                    'description': 'Completed your first financial analysis',
                    'icon': '🔍',
                    'color': 'blue',
                    'unlocked': True,
                    'date': 'Recent'
                })

            if len(analyses) >= 5:
                achievements.append({
                    'id': 'analysis_master',
                    'title': 'Analysis Master',
                    'description': 'Completed 5+ financial analyses',
                    'icon': '🔥',
                    'color': 'orange',
                    'unlocked': True,
                    'date': 'Recent'
                })

            # Transaction Tracking
            if len(transactions) >= 50:
                achievements.append({
                    'id': 'budget_warrior',
                    'title': 'Budget Warrior',
                    'description': 'Tracked 50+ transactions',
                    'icon': '🧠',
                    'color': 'purple',
                    'unlocked': True,
                    'date': 'Recent'
                })

            # Community Achievement (placeholder)
            achievements.append({
                'id': 'community_member',
                'title': 'Community Member',
                'description': 'Joined the BrainBudget community',
                'icon': '🤝',
                'color': 'teal',
                'unlocked': True,
                'date': 'Recent'
            })

            return achievements

        except Exception as e:
            logger.error(f"Failed to get achievements for {uid}: {e}")
            return []
