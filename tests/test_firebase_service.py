"""
Firebase Service Tests
======================

Tests for Firebase authentication, database, and storage operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from app.services.firebase_service import FirebaseService


class TestFirebaseService:
    """Test Firebase service functionality."""
    
    @pytest.fixture
    def firebase_service(self):
        """Create a Firebase service instance for testing."""
        service = FirebaseService()
        service._initialized = True
        service.web_api_key = "test-api-key"
        return service
    
    @pytest.fixture
    def mock_flask_app(self):
        """Create a mock Flask app for testing."""
        app = Mock()
        app.config = {
            'FIREBASE_PROJECT_ID': 'test-project',
            'FIREBASE_PRIVATE_KEY': 'test-private-key',
            'FIREBASE_CLIENT_EMAIL': 'test@test.com',
            'FIREBASE_API_KEY': 'test-api-key'
        }
        return app
    
    def test_initialization_with_valid_credentials(self, mock_flask_app):
        """Test Firebase initialization with valid credentials."""
        service = FirebaseService()
        
        with patch('firebase_admin.initialize_app') as mock_init, \
             patch('firebase_admin.credentials.Certificate') as mock_cert, \
             patch('firebase_admin.firestore.client') as mock_firestore, \
             patch('firebase_admin.storage.bucket') as mock_storage:
            
            service.initialize(mock_flask_app)
            
            assert service._initialized is True
            assert service.web_api_key == 'test-api-key'
            mock_init.assert_called_once()
    
    def test_initialization_with_placeholder_credentials(self, mock_flask_app):
        """Test Firebase initialization with placeholder credentials."""
        mock_flask_app.config['FIREBASE_PROJECT_ID'] = 'placeholder-project'
        
        service = FirebaseService()
        service.initialize(mock_flask_app)
        
        assert service._initialized is False
    
    def test_verify_token_success(self, firebase_service):
        """Test successful token verification."""
        with patch('firebase_admin.auth.verify_id_token') as mock_verify:
            mock_verify.return_value = {
                'uid': 'test-user-123',
                'email': 'test@example.com'
            }
            
            result = firebase_service.verify_token('valid-token')
            
            assert result is not None
            assert result['uid'] == 'test-user-123'
            assert result['email'] == 'test@example.com'
    
    def test_verify_token_failure(self, firebase_service):
        """Test token verification failure."""
        with patch('firebase_admin.auth.verify_id_token') as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")
            
            result = firebase_service.verify_token('invalid-token')
            
            assert result is None
    
    def test_get_user_success(self, firebase_service):
        """Test successful user retrieval."""
        with patch('firebase_admin.auth.get_user') as mock_get_user:
            mock_user = Mock()
            mock_user.uid = 'test-user-123'
            mock_user.email = 'test@example.com'
            mock_user.email_verified = True
            mock_user.display_name = 'Test User'
            mock_user.user_metadata.creation_timestamp = datetime.now()
            mock_user.user_metadata.last_sign_in_timestamp = datetime.now()
            
            mock_get_user.return_value = mock_user
            
            result = firebase_service.get_user('test-user-123')
            
            assert result is not None
            assert result['uid'] == 'test-user-123'
            assert result['email'] == 'test@example.com'
    
    def test_get_user_not_found(self, firebase_service):
        """Test user retrieval when user not found."""
        with patch('firebase_admin.auth.get_user') as mock_get_user:
            mock_get_user.side_effect = Exception("User not found")
            
            result = firebase_service.get_user('nonexistent-user')
            
            assert result is None
    
    def test_create_user_profile(self, firebase_service):
        """Test user profile creation."""
        firebase_service.db = Mock()
        
        profile_data = {
            'email': 'test@example.com',
            'display_name': 'Test User'
        }
        
        result = firebase_service.create_user_profile('test-user-123', profile_data)
        
        assert result is True
        firebase_service.db.collection.assert_called_with('users')
    
    def test_get_user_profile_exists(self, firebase_service):
        """Test retrieving existing user profile."""
        firebase_service.db = Mock()
        
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'email': 'test@example.com',
            'display_name': 'Test User'
        }
        
        firebase_service.db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = firebase_service.get_user_profile('test-user-123')
        
        assert result is not None
        assert result['email'] == 'test@example.com'
    
    def test_get_user_profile_not_exists(self, firebase_service):
        """Test retrieving non-existent user profile."""
        firebase_service.db = Mock()
        
        mock_doc = Mock()
        mock_doc.exists = False
        
        firebase_service.db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = firebase_service.get_user_profile('test-user-123')
        
        assert result is None
    
    def test_save_analysis_result(self, firebase_service):
        """Test saving analysis result."""
        firebase_service.db = Mock()
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = 'analysis-123'
        firebase_service.db.collection.return_value.add.return_value = (None, mock_doc_ref)
        
        analysis_data = {
            'transactions': [],
            'summary': {'total_spent': 100.0}
        }
        
        result = firebase_service.save_analysis_result('test-user-123', analysis_data)
        
        assert result == 'analysis-123'
        firebase_service.db.collection.assert_called_with('analyses')
    
    def test_get_user_analyses(self, firebase_service):
        """Test retrieving user analyses."""
        firebase_service.db = Mock()
        
        mock_query = Mock()
        mock_doc1 = Mock()
        mock_doc1.id = 'analysis-1'
        mock_doc1.to_dict.return_value = {'total_spent': 100.0}
        
        mock_doc2 = Mock()
        mock_doc2.id = 'analysis-2'
        mock_doc2.to_dict.return_value = {'total_spent': 200.0}
        
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        firebase_service.db.collection.return_value.where.return_value.order_by.return_value.limit.return_value = mock_query
        
        result = firebase_service.get_user_analyses('test-user-123', limit=10)
        
        assert len(result) == 2
        assert result[0]['id'] == 'analysis-1'
        assert result[1]['id'] == 'analysis-2'
    
    def test_upload_file_success(self, firebase_service):
        """Test successful file upload."""
        firebase_service.bucket = Mock()
        
        mock_blob = Mock()
        mock_blob.public_url = 'https://example.com/file.pdf'
        firebase_service.bucket.blob.return_value = mock_blob
        
        file_data = b'test file content'
        result = firebase_service.upload_file(file_data, 'test.pdf', 'test-user-123')
        
        assert result == 'https://example.com/file.pdf'
        mock_blob.upload_from_string.assert_called_with(file_data)
        mock_blob.make_public.assert_called_once()
    
    def test_upload_file_bucket_not_found(self, firebase_service):
        """Test file upload when bucket doesn't exist."""
        firebase_service.bucket = Mock()
        
        mock_blob = Mock()
        mock_blob.upload_from_string.side_effect = Exception("bucket does not exist")
        firebase_service.bucket.blob.return_value = mock_blob
        
        with patch.object(firebase_service, '_upload_file_locally') as mock_local:
            mock_local.return_value = '/local/file/path'
            
            file_data = b'test file content'
            result = firebase_service.upload_file(file_data, 'test.pdf', 'test-user-123')
            
            assert result == '/local/file/path'
            mock_local.assert_called_once()
    
    def test_verify_user_password_success(self, firebase_service):
        """Test successful password verification."""
        firebase_service.web_api_key = 'test-api-key'
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            result = firebase_service.verify_user_password('test@example.com', 'password123')
            
            assert result is True
            mock_post.assert_called_once()
    
    def test_verify_user_password_failure(self, firebase_service):
        """Test failed password verification."""
        firebase_service.web_api_key = 'test-api-key'
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_post.return_value = mock_response
            
            result = firebase_service.verify_user_password('test@example.com', 'wrongpassword')
            
            assert result is False
    
    def test_verify_user_password_network_error(self, firebase_service):
        """Test password verification with network error."""
        firebase_service.web_api_key = 'test-api-key'
        
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            result = firebase_service.verify_user_password('test@example.com', 'password123')
            
            assert result is False
    
    def test_update_user_password(self, firebase_service):
        """Test password update."""
        with patch('firebase_admin.auth.update_user') as mock_update:
            result = firebase_service.update_user_password('test-user-123', 'newpassword123')
            
            assert result is True
            mock_update.assert_called_with('test-user-123', password='newpassword123')
    
    def test_save_transaction_data(self, firebase_service):
        """Test saving transaction data."""
        firebase_service.db = Mock()
        
        mock_batch = Mock()
        firebase_service.db.batch.return_value = mock_batch
        
        transactions = [
            {'description': 'Coffee', 'amount': -5.00},
            {'description': 'Salary', 'amount': 3000.00}
        ]
        
        result = firebase_service.save_transaction_data('test-user-123', transactions)
        
        assert result is True
        mock_batch.commit.assert_called_once()
    
    def test_get_user_stats(self, firebase_service):
        """Test getting user statistics."""
        firebase_service.db = Mock()
        
        # Mock profile
        with patch.object(firebase_service, 'get_user_profile') as mock_profile:
            mock_profile.return_value = {
                'created_at': datetime.now(timezone.utc)
            }
            
            # Mock transactions
            with patch.object(firebase_service, 'get_user_transactions') as mock_transactions:
                mock_transactions.return_value = [
                    {'amount': 100.00},
                    {'amount': -50.00},
                    {'amount': 200.00}
                ]
                
                # Mock analyses
                with patch.object(firebase_service, 'get_user_analyses') as mock_analyses:
                    mock_analyses.return_value = [
                        {'id': 'analysis-1'},
                        {'id': 'analysis-2'}
                    ]
                    
                    result = firebase_service.get_user_stats('test-user-123')
                    
                    assert 'days_active' in result
                    assert 'goals_achieved' in result
                    assert 'user_score' in result
                    assert 'total_saved' in result
                    assert result['goals_achieved'] == 2
    
    def test_get_user_timeline(self, firebase_service):
        """Test getting user timeline."""
        with patch.object(firebase_service, 'get_user_profile') as mock_profile:
            mock_profile.return_value = {
                'created_at': datetime.now(timezone.utc)
            }
            
            with patch.object(firebase_service, 'get_user_analyses') as mock_analyses:
                mock_analyses.return_value = [
                    {'id': 'analysis-1', 'created_at': datetime.now(timezone.utc)}
                ]
                
                result = firebase_service.get_user_timeline('test-user-123')
                
                assert len(result) >= 2  # At least joined and analysis events
                assert any(event['title'] == 'Joined BrainBudget' for event in result)
    
    def test_schedule_account_deletion(self, firebase_service):
        """Test scheduling account deletion."""
        firebase_service.db = Mock()
        
        deletion_date = datetime.now(timezone.utc)
        result = firebase_service.schedule_account_deletion('test-user-123', deletion_date)
        
        assert result is True
        firebase_service.db.collection.assert_called_with('account_deletions')
    
    def test_cancel_account_deletion(self, firebase_service):
        """Test canceling account deletion."""
        firebase_service.db = Mock()
        
        result = firebase_service.cancel_account_deletion('test-user-123')
        
        assert result is True
        firebase_service.db.collection.assert_called_with('account_deletions')
    
    def test_get_user_achievements(self, firebase_service):
        """Test getting user achievements."""
        with patch.object(firebase_service, 'get_user_profile') as mock_profile:
            mock_profile.return_value = {
                'created_at': datetime.now(timezone.utc)
            }
            
            with patch.object(firebase_service, 'get_user_transactions') as mock_transactions:
                mock_transactions.return_value = [{'id': f'tx-{i}'} for i in range(60)]
                
                with patch.object(firebase_service, 'get_user_analyses') as mock_analyses:
                    mock_analyses.return_value = [{'id': f'analysis-{i}'} for i in range(6)]
                    
                    result = firebase_service.get_user_achievements('test-user-123')
                    
                    assert len(result) >= 4  # Should have multiple achievements
                    achievement_titles = [a['title'] for a in result]
                    assert 'First Steps' in achievement_titles
                    assert 'Budget Warrior' in achievement_titles  # 50+ transactions


class TestFirebaseServiceErrorHandling:
    """Test error handling in Firebase service."""
    
    def test_service_not_initialized(self):
        """Test operations when service is not initialized."""
        service = FirebaseService()
        service._initialized = False
        
        assert service.verify_token('token') is None
        assert service.get_user('uid') is None
        assert service.create_user_profile('uid', {}) is False
        assert service.upload_file(b'data', 'file.txt', 'uid') is None
    
    def test_database_connection_error(self, firebase_service):
        """Test handling of database connection errors."""
        firebase_service.db = Mock()
        firebase_service.db.collection.side_effect = Exception("Connection error")
        
        result = firebase_service.get_user_profile('test-user-123')
        assert result is None
        
        result = firebase_service.create_user_profile('test-user-123', {})
        assert result is False
    
    def test_storage_upload_error(self, firebase_service):
        """Test handling of storage upload errors."""
        firebase_service.bucket = Mock()
        
        mock_blob = Mock()
        mock_blob.upload_from_string.side_effect = Exception("Upload failed")
        firebase_service.bucket.blob.return_value = mock_blob
        
        with patch.object(firebase_service, '_upload_file_locally') as mock_local:
            mock_local.return_value = None  # Local upload also fails
            
            result = firebase_service.upload_file(b'data', 'file.txt', 'test-user-123')
            assert result is None


if __name__ == '__main__':
    pytest.main([__file__])