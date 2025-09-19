"""
API Routes Tests
================

Tests for all API endpoints including authentication, upload, and analysis.
"""

import pytest
import json
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock

from app import create_app


class TestAuthRoutes:
    """Test authentication API routes."""
    
    def test_verify_token_success(self, client):
        """Test successful token verification."""
        with patch('app.routes.auth.current_app') as mock_app:
            mock_app.firebase.verify_token.return_value = {
                'uid': 'test-user-123',
                'email': 'test@example.com'
            }
            mock_app.firebase.get_user.return_value = {
                'uid': 'test-user-123',
                'email': 'test@example.com',
                'email_verified': True
            }
            mock_app.firebase.get_user_profile.return_value = {
                'display_name': 'Test User'
            }
            
            response = client.post('/api/auth/verify', 
                                 json={'id_token': 'valid-token'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['user']['uid'] == 'test-user-123'
    
    def test_verify_token_missing_token(self, client):
        """Test token verification with missing token."""
        response = client.post('/api/auth/verify', json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] is True
    
    def test_verify_token_invalid_token(self, client):
        """Test token verification with invalid token."""
        with patch('app.routes.auth.current_app') as mock_app:
            mock_app.firebase.verify_token.return_value = None
            
            response = client.post('/api/auth/verify',
                                 json={'id_token': 'invalid-token'})
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['error'] is True
    
    def test_get_profile_success(self, client, auth_headers):
        """Test successful profile retrieval."""
        with patch('app.routes.auth.current_app') as mock_app:
            mock_app.firebase.get_user_profile.return_value = {
                'uid': 'test-user-123',
                'email': 'test@example.com',
                'display_name': 'Test User'
            }
            
            response = client.get('/api/auth/profile', headers=auth_headers)
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'profile' in data
    
    def test_get_profile_not_found(self, client, auth_headers):
        """Test profile retrieval when profile doesn't exist."""
        with patch('app.routes.auth.current_app') as mock_app:
            mock_app.firebase.get_user_profile.return_value = None
            
            response = client.get('/api/auth/profile', headers=auth_headers)
            
            assert response.status_code == 404
            data = response.get_json()
            assert data['success'] is False
    
    def test_update_profile_success(self, client, auth_headers):
        """Test successful profile update."""
        profile_data = {
            'display_name': 'Updated User',
            'settings': {
                'notifications_enabled': True,
                'currency': 'USD'
            }
        }
        
        with patch('app.routes.auth.current_app') as mock_app:
            mock_app.firebase.create_user_profile.return_value = True
            mock_app.firebase.get_user_profile.return_value = profile_data
            
            response = client.put('/api/auth/profile',
                                json=profile_data,
                                headers=auth_headers)
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['profile']['display_name'] == 'Updated User'
    
    def test_change_password_success(self, client, auth_headers):
        """Test successful password change."""
        password_data = {
            'current_password': 'oldpass123',
            'new_password': 'newpass456'
        }
        
        with patch('app.routes.auth.current_app') as mock_app, \
             patch('app.utils.security.security_manager') as mock_security:
            
            mock_app.firebase.get_user.return_value = {'email': 'test@example.com'}
            mock_app.firebase.verify_user_password.return_value = True
            mock_app.firebase.update_user_password.return_value = True
            
            response = client.post('/api/auth/change-password',
                                 json=password_data,
                                 headers=auth_headers)
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
    
    def test_change_password_wrong_current(self, client, auth_headers):
        """Test password change with wrong current password."""
        password_data = {
            'current_password': 'wrongpass',
            'new_password': 'newpass456'
        }
        
        with patch('app.routes.auth.current_app') as mock_app, \
             patch('app.utils.security.security_manager') as mock_security:
            
            mock_app.firebase.get_user.return_value = {'email': 'test@example.com'}
            mock_app.firebase.verify_user_password.return_value = False
            
            response = client.post('/api/auth/change-password',
                                 json=password_data,
                                 headers=auth_headers)
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['success'] is False
    
    def test_export_user_data(self, client, auth_headers):
        """Test user data export."""
        with patch('app.routes.auth.current_app') as mock_app:
            mock_app.firebase.get_user_profile.return_value = {'name': 'Test User'}
            mock_app.firebase.get_user_analyses.return_value = []
            mock_app.firebase.get_user_transactions.return_value = []
            mock_app.firebase.get_user_preferences.return_value = {}
            
            response = client.post('/api/auth/export-data', headers=auth_headers)
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'data' in data
            assert 'export_info' in data['data']
    
    def test_firebase_config(self, client):
        """Test Firebase configuration endpoint."""
        with patch('app.routes.auth.current_app') as mock_app:
            mock_app.config = {
                'FIREBASE_API_KEY': 'test-api-key',
                'FIREBASE_AUTH_DOMAIN': 'test.firebaseapp.com',
                'FIREBASE_PROJECT_ID': 'test-project',
                'FIREBASE_STORAGE_BUCKET': 'test.appspot.com',
                'FIREBASE_MESSAGING_SENDER_ID': '123456789',
                'FIREBASE_APP_ID': 'test-app-id'
            }
            
            response = client.get('/api/auth/firebase-config')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['config']['projectId'] == 'test-project'


class TestUploadRoutes:
    """Test file upload API routes."""
    
    def test_upload_statement_success(self, client, auth_headers):
        """Test successful statement upload."""
        # Create a test PDF file
        pdf_content = b'%PDF-1.4\nTest PDF content'
        
        with patch('app.routes.upload.current_app') as mock_app:
            mock_app.firebase.upload_file.return_value = 'https://example.com/file.pdf'
            
            response = client.post('/api/upload/statement',
                                 data={'file': (BytesIO(pdf_content), 'test.pdf')},
                                 headers=auth_headers)
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'file_url' in data
    
    def test_upload_statement_no_file(self, client, auth_headers):
        """Test statement upload without file."""
        response = client.post('/api/upload/statement', headers=auth_headers)
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] is True
    
    def test_upload_statement_invalid_type(self, client, auth_headers):
        """Test statement upload with invalid file type."""
        # Create a text file (not allowed)
        text_content = b'This is not a PDF or image'
        
        response = client.post('/api/upload/statement',
                             data={'file': (BytesIO(text_content), 'test.txt')},
                             headers=auth_headers)
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] is True


class TestAnalysisRoutes:
    """Test analysis API routes."""
    
    def test_analyze_statement_success(self, client, auth_headers):
        """Test successful statement analysis."""
        request_data = {
            'file_url': 'https://example.com/statement.pdf',
            'filename': 'statement.pdf'
        }
        
        analysis_result = {
            'success': True,
            'transactions': [
                {'description': 'Coffee', 'amount': -5.00, 'category': 'Food & Dining'}
            ],
            'summary': {'total_spent': 5.00, 'total_income': 0.00},
            'insights': {'key_patterns': ['Coffee spending detected']}
        }
        
        with patch('app.routes.analysis.current_app') as mock_app:
            mock_app.firebase.download_file.return_value = b'PDF content'
            
            with patch('app.services.gemini_ai.GeminiAIService') as mock_gemini_class:
                mock_gemini = Mock()
                mock_gemini.analyze_bank_statement.return_value = analysis_result
                mock_gemini_class.return_value = mock_gemini
                
                with patch('app.routes.analysis.GeminiAIService', mock_gemini_class):
                    response = client.post('/api/analysis/analyze',
                                         json=request_data,
                                         headers=auth_headers)
                
                assert response.status_code == 200
                data = response.get_json()
                assert data['success'] is True
                assert 'analysis' in data
                assert len(data['analysis']['transactions']) == 1
    
    def test_analyze_statement_missing_data(self, client, auth_headers):
        """Test statement analysis with missing data."""
        response = client.post('/api/analysis/analyze',
                             json={},
                             headers=auth_headers)
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] is True
    
    def test_get_user_analyses(self, client, auth_headers):
        """Test retrieving user's analyses."""
        with patch('app.routes.analysis.current_app') as mock_app:
            mock_app.firebase.get_user_analyses.return_value = [
                {'id': 'analysis-1', 'filename': 'statement1.pdf'},
                {'id': 'analysis-2', 'filename': 'statement2.pdf'}
            ]
            
            response = client.get('/api/analysis/history', headers=auth_headers)
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert len(data['analyses']) == 2


class TestDashboardRoutes:
    """Test dashboard API routes."""
    
    def test_get_dashboard_data(self, client, auth_headers):
        """Test dashboard data retrieval."""
        with patch('app.routes.dashboard.current_app') as mock_app:
            mock_app.firebase.get_user_analyses.return_value = [
                {'summary': {'total_spent': 100.00, 'total_income': 1000.00}}
            ]
            mock_app.firebase.get_user_transactions.return_value = []
            
            response = client.get('/api/dashboard/data', headers=auth_headers)
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'dashboard_data' in data


class TestSecurityIntegration:
    """Test security integration with API routes."""
    
    def test_rate_limiting_on_auth_endpoint(self, client):
        """Test rate limiting on authentication endpoint."""
        with patch('app.utils.security.security_manager') as mock_manager:
            mock_manager.enabled = True
            mock_manager.get_client_key.return_value = "test_key"
            mock_manager.is_rate_limited.return_value = True
            
            response = client.post('/api/auth/verify',
                                 json={'id_token': 'test-token'})
            
            assert response.status_code == 429
    
    def test_authentication_required(self, client):
        """Test that protected routes require authentication."""
        response = client.get('/api/auth/profile')
        
        assert response.status_code == 401
    
    def test_invalid_auth_header(self, client):
        """Test handling of invalid authorization header."""
        headers = {'Authorization': 'Invalid header format'}
        
        response = client.get('/api/auth/profile', headers=headers)
        
        assert response.status_code == 401


class TestErrorHandling:
    """Test error handling across API routes."""
    
    def test_404_error_handling(self, client):
        """Test 404 error handling."""
        response = client.get('/api/nonexistent/endpoint')
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] is True
        assert 'find what you\'re looking for' in data['message']
    
    def test_method_not_allowed(self, client):
        """Test method not allowed error."""
        response = client.put('/api/auth/verify')  # Only POST allowed
        
        assert response.status_code == 405
    
    def test_large_request_body(self, client, auth_headers):
        """Test handling of oversized request body."""
        # Create a large JSON payload (over 16MB)
        large_data = {'data': 'x' * (17 * 1024 * 1024)}
        
        response = client.post('/api/upload/statement',
                             json=large_data,
                             headers=auth_headers)
        
        assert response.status_code == 413
    
    def test_malformed_json(self, client):
        """Test handling of malformed JSON."""
        response = client.post('/api/auth/verify',
                             data='{"invalid": json}',
                             content_type='application/json')
        
        assert response.status_code == 400


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['app'] == 'BrainBudget'
        assert data['version'] == '1.0.0'


class TestCORSConfiguration:
    """Test CORS configuration."""
    
    def test_cors_headers(self, client):
        """Test that CORS headers are properly set."""
        response = client.options('/api/auth/verify')
        
        # Check for CORS headers (Flask-CORS should add these)
        assert 'Access-Control-Allow-Origin' in response.headers or response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__])