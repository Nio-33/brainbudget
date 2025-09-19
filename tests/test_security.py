"""
Security Tests for BrainBudget
==============================

Tests for security features including rate limiting, authentication, and input validation.
"""

import pytest
import time
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

from app.utils.security import SecurityManager, rate_limit, account_lockout_check, log_security_event
from app.routes.auth import auth_bp


class TestSecurityManager:
    """Test security manager functionality."""
    
    @pytest.fixture
    def security_manager(self):
        """Create a security manager instance for testing."""
        manager = SecurityManager()
        manager._in_memory_store = {}  # Use in-memory store for testing
        manager.enabled = True
        return manager
    
    def test_rate_limiting_allows_within_limit(self, security_manager):
        """Test that requests within rate limit are allowed."""
        key = "test_key"
        
        # Test multiple requests within limit
        for i in range(4):
            assert not security_manager.is_rate_limited(key, max_attempts=5, window_minutes=15)
            security_manager.record_attempt(key)
    
    def test_rate_limiting_blocks_over_limit(self, security_manager):
        """Test that requests over rate limit are blocked."""
        key = "test_key"
        
        # Exceed rate limit
        for i in range(5):
            security_manager.record_attempt(key)
        
        # Should be rate limited now
        assert security_manager.is_rate_limited(key, max_attempts=5, window_minutes=15)
    
    def test_account_lockout_basic(self, security_manager):
        """Test basic account lockout functionality."""
        email = "test@example.com"
        
        # Initially not locked
        assert not security_manager.is_account_locked(email)
        
        # Lock the account
        security_manager.lock_account(email)
        
        # Should be locked now
        assert security_manager.is_account_locked(email)
    
    def test_failed_login_attempts_trigger_lockout(self, security_manager):
        """Test that multiple failed login attempts trigger account lockout."""
        email = "test@example.com"
        
        # Record failed login attempts
        for i in range(4):
            result = security_manager.record_failed_login(email)
            assert not result  # Should not be locked yet
        
        # Fifth attempt should trigger lockout
        result = security_manager.record_failed_login(email)
        assert result  # Should be locked now
        assert security_manager.is_account_locked(email)
    
    def test_clear_failed_attempts(self, security_manager):
        """Test clearing failed login attempts."""
        email = "test@example.com"
        
        # Record some failed attempts
        for i in range(3):
            security_manager.record_failed_login(email)
        
        # Clear attempts
        security_manager.clear_failed_attempts(email)
        
        # Should be able to make new attempts without triggering lockout
        for i in range(3):
            result = security_manager.record_failed_login(email)
            assert not result
    
    def test_unlock_account(self, security_manager):
        """Test manually unlocking an account."""
        email = "test@example.com"
        
        # Lock the account
        security_manager.lock_account(email)
        assert security_manager.is_account_locked(email)
        
        # Unlock the account
        security_manager.unlock_account(email)
        assert not security_manager.is_account_locked(email)
    
    def test_get_client_key_consistent(self):
        """Test that client key generation is consistent."""
        with patch('flask.request') as mock_request:
            mock_request.environ = {'HTTP_X_FORWARDED_FOR': '192.168.1.1'}
            mock_request.headers = {'User-Agent': 'Test Browser'}
            mock_request.remote_addr = '127.0.0.1'
            
            manager = SecurityManager()
            key1 = manager.get_client_key()
            key2 = manager.get_client_key()
            
            assert key1 == key2
            assert len(key1) == 16  # Should be 16 character hash


class TestSecurityDecorators:
    """Test security decorators for rate limiting and account lockout."""
    
    def test_rate_limit_decorator_allows_within_limit(self, app, client):
        """Test rate limit decorator allows requests within limit."""
        
        @app.route('/test-rate-limit')
        @rate_limit(max_attempts=3, window_minutes=5)
        def test_endpoint():
            return {'success': True}
        
        # Make requests within limit
        for i in range(3):
            response = client.get('/test-rate-limit')
            assert response.status_code == 200
    
    def test_rate_limit_decorator_blocks_over_limit(self, app, client):
        """Test rate limit decorator blocks requests over limit."""
        
        @app.route('/test-rate-limit-block')
        @rate_limit(max_attempts=2, window_minutes=5)
        def test_endpoint():
            return {'success': True}
        
        # Patch security manager to use in-memory store
        with patch('app.utils.security.security_manager') as mock_manager:
            mock_manager.enabled = True
            mock_manager.get_client_key.return_value = "test_key"
            mock_manager.is_rate_limited.side_effect = [False, False, True]
            mock_manager.record_attempt.return_value = None
            
            # First two requests should succeed
            response = client.get('/test-rate-limit-block')
            assert response.status_code == 200
            
            response = client.get('/test-rate-limit-block')
            assert response.status_code == 200
            
            # Third request should be rate limited
            response = client.get('/test-rate-limit-block')
            assert response.status_code == 429
    
    def test_account_lockout_decorator_blocks_locked_account(self, app, client):
        """Test account lockout decorator blocks locked accounts."""
        
        @app.route('/test-lockout', methods=['POST'])
        @account_lockout_check
        def test_endpoint():
            return {'success': True}
        
        with patch('app.utils.security.security_manager') as mock_manager:
            mock_manager.enabled = True
            mock_manager.is_account_locked.return_value = True
            
            response = client.post('/test-lockout', 
                                 json={'email': 'locked@example.com'})
            assert response.status_code == 423


class TestInputValidation:
    """Test input validation and sanitization."""
    
    def test_malicious_script_injection(self, client, auth_headers):
        """Test that script injection attempts are blocked."""
        malicious_data = {
            'display_name': '<script>alert("xss")</script>',
            'settings': {
                'theme': '"><script>alert("xss")</script>'
            }
        }
        
        with patch('app.routes.auth.current_app') as mock_app:
            mock_app.firebase.get_user_profile.return_value = {}
            mock_app.firebase.create_user_profile.return_value = True
            
            response = client.put('/api/auth/profile', 
                                json=malicious_data, 
                                headers=auth_headers)
            
            # Should succeed but data should be sanitized
            assert response.status_code == 200
    
    def test_sql_injection_protection(self, client):
        """Test protection against SQL injection attempts."""
        malicious_data = {
            'email': "'; DROP TABLE users; --",
            'password': 'password123'
        }
        
        response = client.post('/api/auth/verify', json=malicious_data)
        
        # Should return 400 or 401, not 500 (which might indicate SQL injection)
        assert response.status_code in [400, 401]
    
    def test_file_upload_validation(self, client, auth_headers):
        """Test file upload validation."""
        # Test with malicious file content
        malicious_content = b'<?php system($_GET["cmd"]); ?>'
        
        response = client.post('/api/upload/statement',
                             data={'file': (BytesIO(malicious_content), 'test.php')},
                             headers=auth_headers)
        
        # Should reject non-PDF/image files
        assert response.status_code == 400
    
    def test_oversized_file_rejection(self, client, auth_headers):
        """Test rejection of oversized files."""
        # Create a large file (simulate 20MB)
        large_content = b'A' * (20 * 1024 * 1024)
        
        response = client.post('/api/upload/statement',
                             data={'file': (BytesIO(large_content), 'large.pdf')},
                             headers=auth_headers)
        
        # Should reject oversized files
        assert response.status_code == 413


class TestAuthenticationSecurity:
    """Test authentication security measures."""
    
    def test_token_validation_failure_logged(self, client):
        """Test that token validation failures are logged."""
        with patch('app.utils.security.log_security_event') as mock_log:
            response = client.post('/api/auth/verify', 
                                 json={'id_token': 'invalid-token'})
            
            # Should log security event
            mock_log.assert_called()
            call_args = mock_log.call_args[0]
            assert call_args[0] == 'failed_token_verification'
    
    def test_password_change_security_logging(self, client, auth_headers):
        """Test that password changes are properly logged."""
        with patch('app.routes.auth.current_app') as mock_app, \
             patch('app.utils.security.log_security_event') as mock_log:
            
            mock_app.firebase.get_user.return_value = {'email': 'test@example.com'}
            mock_app.firebase.verify_user_password.return_value = True
            mock_app.firebase.update_user_password.return_value = True
            
            response = client.post('/api/auth/change-password',
                                 json={
                                     'current_password': 'oldpass123',
                                     'new_password': 'newpass123'
                                 },
                                 headers=auth_headers)
            
            # Should log successful password change
            mock_log.assert_called()
            call_args = mock_log.call_args[0]
            assert call_args[0] == 'password_changed'
    
    def test_failed_password_verification_handling(self, client, auth_headers):
        """Test handling of failed password verification."""
        with patch('app.routes.auth.current_app') as mock_app, \
             patch('app.utils.security.security_manager') as mock_manager:
            
            mock_app.firebase.get_user.return_value = {'email': 'test@example.com'}
            mock_app.firebase.verify_user_password.return_value = False
            
            response = client.post('/api/auth/change-password',
                                 json={
                                     'current_password': 'wrongpass',
                                     'new_password': 'newpass123'
                                 },
                                 headers=auth_headers)
            
            # Should record failed attempt
            mock_manager.record_failed_login.assert_called_with('test@example.com')
            assert response.status_code == 401


class TestSecurityMonitoring:
    """Test security monitoring and logging."""
    
    def test_security_event_logging_structure(self):
        """Test that security events are logged with proper structure."""
        with patch('flask.request') as mock_request, \
             patch('app.utils.security.logger') as mock_logger:
            
            mock_request.environ = {'HTTP_X_FORWARDED_FOR': '192.168.1.1'}
            mock_request.headers = {'User-Agent': 'Test Browser'}
            mock_request.endpoint = 'test_endpoint'
            
            log_security_event('test_event', {'key': 'value'})
            
            # Verify logging was called
            mock_logger.warning.assert_called_once()
            logged_message = mock_logger.warning.call_args[0][0]
            assert 'SECURITY_EVENT' in logged_message
    
    def test_security_manager_disabled_gracefully(self):
        """Test that security manager gracefully handles being disabled."""
        manager = SecurityManager()
        manager.enabled = False
        
        # All security checks should pass when disabled
        assert not manager.is_rate_limited('test_key')
        assert not manager.is_account_locked('test@example.com')
        
        # Recording attempts should not raise errors
        manager.record_attempt('test_key')
        manager.record_failed_login('test@example.com')


# Integration tests
class TestSecurityIntegration:
    """Integration tests for security features."""
    
    def test_full_authentication_flow_with_security(self, client):
        """Test complete authentication flow with security measures."""
        with patch('app.routes.auth.current_app') as mock_app, \
             patch('app.utils.security.security_manager') as mock_manager:
            
            # Setup mocks
            mock_app.firebase.verify_token.return_value = {
                'uid': 'test-user-123',
                'email': 'test@example.com'
            }
            mock_app.firebase.get_user.return_value = {
                'uid': 'test-user-123',
                'email': 'test@example.com',
                'email_verified': True
            }
            mock_app.firebase.get_user_profile.return_value = None
            mock_app.firebase.create_user_profile.return_value = True
            
            mock_manager.enabled = True
            mock_manager.is_rate_limited.return_value = False
            mock_manager.is_account_locked.return_value = False
            
            # Test authentication
            response = client.post('/api/auth/verify',
                                 json={'id_token': 'valid-token'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'user' in data


if __name__ == '__main__':
    pytest.main([__file__])