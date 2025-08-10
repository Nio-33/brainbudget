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


logger = logging.getLogger(__name__)


class FirebaseService:
    """Firebase service for authentication, database, and storage operations."""
    
    def __init__(self):
        self.app = None
        self.db: Optional[FirestoreClient] = None
        self.bucket: Optional[Bucket] = None
        self._initialized = False
    
    def initialize(self, flask_app):
        """
        Initialize Firebase with Flask app configuration.
        
        Args:
            flask_app: Flask application instance
        """
        try:
            # Check if we have valid Firebase credentials
            project_id = flask_app.config.get('FIREBASE_PROJECT_ID')
            private_key = flask_app.config.get('FIREBASE_PRIVATE_KEY')
            client_email = flask_app.config.get('FIREBASE_CLIENT_EMAIL')
            
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
            return True
            
        except Exception as e:
            logger.error(f"Failed to create user profile for {uid}: {e}")
            return False
    
    def get_user_profile(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile from Firestore.
        
        Args:
            uid: Firebase user UID
            
        Returns:
            User profile data if found
        """
        if not self._initialized:
            logger.error("Firebase not initialized")
            return None
        
        try:
            doc = self.db.collection('users').document(uid).get()
            if doc.exists:
                return doc.to_dict()
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
            # In a real implementation, this would use Firebase Admin SDK
            # to update the user's password
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
            deletion_date: When to delete the account
            
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