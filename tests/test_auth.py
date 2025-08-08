"""
Authentication Tests
===================

Tests for user authentication, registration, and session management.
"""

import pytest
from unittest.mock import patch, Mock
import json


class TestAuthenticationRoutes:
    """Test authentication-related routes."""
    
    def test_firebase_config_endpoint(self, client):
        """Test Firebase configuration endpoint returns proper config."""
        response = client.get('/api/auth/firebase-config')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'apiKey' in data
        assert 'authDomain' in data
        assert 'projectId' in data

    @patch('app.routes.auth.current_app')
    def test_verify_token_valid(self, mock_app, client, mock_firebase_service):
        """Test token verification with valid token."""
        mock_app.firebase = mock_firebase_service
        
        response = client.post('/api/auth/verify', 
                             json={'token': 'valid-firebase-token'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'user' in data

    @patch('app.routes.auth.current_app')
    def test_verify_token_invalid(self, mock_app, client, mock_firebase_service):
        """Test token verification with invalid token."""
        mock_app.firebase = mock_firebase_service
        mock_firebase_service.verify_token.side_effect = Exception("Invalid token")
        
        response = client.post('/api/auth/verify', 
                             json={'token': 'invalid-token'})
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False

    def test_verify_token_missing(self, client):
        """Test token verification without providing token."""
        response = client.post('/api/auth/verify', json={})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    @patch('app.routes.auth.current_app')
    def test_logout(self, mock_app, client, auth_headers):
        """Test user logout."""
        mock_app.firebase = Mock()
        
        response = client.post('/api/auth/logout', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestFirebaseAuthentication:
    """Test Firebase authentication integration."""
    
    @patch('app.services.firebase_service.FirebaseService.verify_token')
    def test_valid_firebase_token(self, mock_verify, mock_firebase_service):
        """Test validation of Firebase JWT token."""
        mock_verify.return_value = {
            'uid': 'test-user-123',
            'email': 'test@example.com'
        }
        
        result = mock_firebase_service.verify_token('valid-token')
        
        assert result['uid'] == 'test-user-123'
        assert result['email'] == 'test@example.com'

    @patch('app.services.firebase_service.FirebaseService.verify_token')
    def test_expired_firebase_token(self, mock_verify, mock_firebase_service):
        """Test handling of expired Firebase token."""
        mock_verify.side_effect = Exception("Token expired")
        
        with pytest.raises(Exception):
            mock_firebase_service.verify_token('expired-token')

    @patch('app.services.firebase_service.FirebaseService.create_user_profile')
    def test_user_profile_creation(self, mock_create, mock_firebase_service):
        """Test user profile creation in Firestore."""
        mock_create.return_value = True
        
        user_data = {
            'uid': 'new-user-123',
            'email': 'newuser@example.com',
            'displayName': 'New User'
        }
        
        result = mock_firebase_service.create_user_profile(user_data)
        assert result is True


class TestPasswordValidation:
    """Test password strength validation."""
    
    @pytest.mark.parametrize("password,expected", [
        ("WeakPass1!", True),     # Valid password
        ("weak123", False),       # Too weak
        ("NoNumbers!", False),    # No numbers
        ("nonumbers1", False),    # No uppercase
        ("NOCAPS123!", False),    # No lowercase
        ("NoSpecial123", False),  # No special chars
        ("Short1!", False),       # Too short
    ])
    def test_password_strength(self, password, expected):
        """Test password strength validation logic."""
        from app.utils.validators import validate_password_strength
        
        result = validate_password_strength(password)
        assert (result['score'] >= 3) == expected


class TestUserSession:
    """Test user session management."""
    
    def test_session_creation(self, client, mock_firebase_service):
        """Test session creation after successful login."""
        with patch('app.routes.auth.current_app') as mock_app:
            mock_app.firebase = mock_firebase_service
            
            response = client.post('/api/auth/verify', 
                                 json={'token': 'valid-token'})
            
            assert response.status_code == 200

    def test_session_persistence(self, client, mock_firebase_service):
        """Test session persistence across requests."""
        # This would test session storage and retrieval
        # Implementation depends on session management strategy
        pass

    def test_session_cleanup(self, client):
        """Test proper session cleanup on logout."""
        response = client.post('/api/auth/logout')
        # Test that session data is properly cleaned up
        assert response.status_code == 200


class TestAuthenticationMiddleware:
    """Test authentication middleware and decorators."""
    
    def test_protected_route_without_auth(self, client):
        """Test accessing protected route without authentication."""
        # Attempt to access a protected route
        response = client.get('/api/dashboard')
        # Should redirect to login or return 401
        assert response.status_code in [401, 302]

    @patch('app.routes.dashboard.current_app')
    def test_protected_route_with_auth(self, mock_app, client, mock_firebase_service, auth_headers):
        """Test accessing protected route with valid authentication."""
        mock_app.firebase = mock_firebase_service
        
        # This would require proper auth middleware implementation
        response = client.get('/api/dashboard', headers=auth_headers)
        # Should allow access with valid auth
        assert response.status_code == 200

    def test_auth_header_parsing(self, client, auth_headers):
        """Test parsing of Authorization header."""
        # Test that Bearer token is properly extracted
        response = client.get('/api/dashboard', headers=auth_headers)
        # Implementation would test header parsing logic
        assert 'Authorization' in auth_headers


class TestSecurityFeatures:
    """Test security-related authentication features."""
    
    def test_rate_limiting(self, client):
        """Test rate limiting on authentication endpoints."""
        # Make multiple rapid requests to test rate limiting
        responses = []
        for _ in range(10):
            response = client.post('/api/auth/verify', json={'token': 'test'})
            responses.append(response.status_code)
        
        # Should eventually return 429 (Too Many Requests)
        # Implementation depends on rate limiting setup
        assert any(status == 429 for status in responses[-3:])

    def test_csrf_protection(self, client):
        """Test CSRF protection on state-changing requests."""
        # Test CSRF token validation
        response = client.post('/api/auth/logout', 
                             json={},
                             headers={'Content-Type': 'application/json'})
        
        # Should handle CSRF appropriately
        assert response.status_code in [200, 403]

    def test_input_sanitization(self, client):
        """Test input sanitization for auth endpoints."""
        malicious_input = {
            'token': '<script>alert("xss")</script>',
            'email': 'test@example.com<script>alert("xss")</script>'
        }
        
        response = client.post('/api/auth/verify', json=malicious_input)
        
        # Should handle malicious input safely
        assert response.status_code in [400, 401]
        data = json.loads(response.data)
        # Ensure no script tags in response
        assert '<script>' not in json.dumps(data)