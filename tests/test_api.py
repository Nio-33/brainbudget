"""
API Endpoint Tests
=================

Tests for all API endpoints including error handling and data validation.
"""

import pytest
import json
from unittest.mock import patch, Mock
import io


class TestHealthEndpoint:
    """Test application health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns proper status."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['app'] == 'BrainBudget'
        assert 'version' in data


class TestDashboardAPI:
    """Test dashboard API endpoints."""
    
    @patch('app.routes.dashboard.current_app')
    def test_dashboard_data_authenticated(self, mock_app, client, mock_firebase_service, auth_headers):
        """Test dashboard data retrieval with authentication."""
        mock_app.firebase = mock_firebase_service
        
        response = client.get('/api/dashboard', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data

    def test_dashboard_data_unauthenticated(self, client):
        """Test dashboard access without authentication."""
        response = client.get('/api/dashboard')
        assert response.status_code in [401, 302]  # Unauthorized or redirect

    @patch('app.routes.dashboard.current_app')
    def test_dashboard_stats(self, mock_app, client, mock_firebase_service, auth_headers):
        """Test dashboard statistics endpoint."""
        mock_app.firebase = mock_firebase_service
        mock_app.firebase.get_user_stats.return_value = {
            'total_transactions': 150,
            'total_spent': 2500.50,
            'categories_count': 8
        }
        
        response = client.get('/api/dashboard/stats', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'total_transactions' in data


class TestUploadAPI:
    """Test file upload API endpoints."""
    
    @patch('app.routes.upload.current_app')
    def test_upload_valid_pdf(self, mock_app, client, mock_firebase_service, auth_headers, sample_pdf_file):
        """Test uploading a valid PDF file."""
        mock_app.firebase = mock_firebase_service
        
        with open(sample_pdf_file, 'rb') as pdf_file:
            response = client.post('/api/upload',
                                 data={'file': (pdf_file, 'statement.pdf')},
                                 headers={'Authorization': auth_headers['Authorization']})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    @patch('app.routes.upload.current_app')
    def test_upload_invalid_file_type(self, mock_app, client, mock_firebase_service, auth_headers):
        """Test uploading invalid file type."""
        mock_app.firebase = mock_firebase_service
        
        # Create a text file (invalid type)
        data = {'file': (io.BytesIO(b'invalid content'), 'test.txt')}
        
        response = client.post('/api/upload',
                             data=data,
                             headers={'Authorization': auth_headers['Authorization']})
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False

    def test_upload_no_file(self, client, auth_headers):
        """Test upload endpoint without file."""
        response = client.post('/api/upload',
                             data={},
                             headers=auth_headers)
        
        assert response.status_code == 400

    @patch('app.routes.upload.current_app')
    def test_upload_file_too_large(self, mock_app, client, mock_firebase_service, auth_headers):
        """Test uploading file that exceeds size limit."""
        mock_app.firebase = mock_firebase_service
        
        # Create large file content (exceed app's MAX_CONTENT_LENGTH)
        large_content = b'x' * (20 * 1024 * 1024)  # 20MB
        data = {'file': (io.BytesIO(large_content), 'large.pdf')}
        
        response = client.post('/api/upload',
                             data=data,
                             headers={'Authorization': auth_headers['Authorization']})
        
        assert response.status_code == 413  # Request Entity Too Large


class TestAnalysisAPI:
    """Test analysis API endpoints."""
    
    @patch('app.routes.analysis.current_app')
    def test_analyze_statement(self, mock_app, client, mock_firebase_service, mock_gemini_service, auth_headers, sample_statement_data):
        """Test statement analysis endpoint."""
        mock_app.firebase = mock_firebase_service
        mock_app.gemini = mock_gemini_service
        
        response = client.post('/api/analysis/analyze',
                             json={'statement_data': sample_statement_data},
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'analysis' in data

    @patch('app.routes.analysis.current_app')
    def test_analysis_invalid_data(self, mock_app, client, mock_firebase_service, auth_headers):
        """Test analysis with invalid data."""
        mock_app.firebase = mock_firebase_service
        
        response = client.post('/api/analysis/analyze',
                             json={'invalid': 'data'},
                             headers=auth_headers)
        
        assert response.status_code == 400

    @patch('app.routes.analysis.current_app')
    def test_get_analysis_history(self, mock_app, client, mock_firebase_service, auth_headers):
        """Test retrieving analysis history."""
        mock_app.firebase = mock_firebase_service
        mock_app.firebase.get_user_analyses.return_value = [
            {'id': '1', 'date': '2024-01-01', 'total': 1500},
            {'id': '2', 'date': '2024-01-15', 'total': 1200}
        ]
        
        response = client.get('/api/analysis/history', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['analyses']) == 2


class TestErrorHandling:
    """Test API error handling."""
    
    def test_404_error_handling(self, client):
        """Test 404 error returns proper JSON response."""
        response = client.get('/api/nonexistent')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['error'] is True
        assert 'message' in data

    def test_405_method_not_allowed(self, client):
        """Test 405 error for wrong HTTP method."""
        response = client.post('/health')  # GET endpoint
        assert response.status_code == 405

    def test_500_internal_error_handling(self, client):
        """Test 500 error handling."""
        # This would require triggering an internal server error
        # Implementation depends on specific error scenarios
        pass

    def test_malformed_json(self, client, auth_headers):
        """Test handling of malformed JSON in request."""
        response = client.post('/api/auth/verify',
                             data='{"invalid": json}',
                             headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 400

    def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = client.options('/api/dashboard')
        
        # Check for CORS headers
        assert 'Access-Control-Allow-Origin' in response.headers


class TestInputValidation:
    """Test input validation across API endpoints."""
    
    def test_email_validation(self, client):
        """Test email validation in various endpoints."""
        invalid_emails = ['invalid', 'test@', '@example.com', 'test.example.com']
        
        for email in invalid_emails:
            response = client.post('/api/auth/verify',
                                 json={'email': email})
            assert response.status_code == 400

    def test_sql_injection_prevention(self, client, auth_headers):
        """Test SQL injection prevention."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR 1=1 --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        for malicious_input in malicious_inputs:
            response = client.post('/api/analysis/analyze',
                                 json={'query': malicious_input},
                                 headers=auth_headers)
            
            # Should reject malicious input safely
            assert response.status_code in [400, 422]

    def test_xss_prevention(self, client):
        """Test XSS attack prevention."""
        xss_payloads = [
            '<script>alert("xss")</script>',
            'javascript:alert("xss")',
            '<img src="x" onerror="alert(\'xss\')">'
        ]
        
        for payload in xss_payloads:
            response = client.post('/api/auth/verify',
                                 json={'token': payload})
            
            data = json.loads(response.data)
            # Ensure payload is not reflected in response
            assert payload not in json.dumps(data)


class TestRateLimiting:
    """Test API rate limiting."""
    
    def test_auth_rate_limiting(self, client):
        """Test rate limiting on authentication endpoints."""
        # Make multiple rapid requests
        responses = []
        for _ in range(20):
            response = client.post('/api/auth/verify',
                                 json={'token': 'test-token'})
            responses.append(response.status_code)
        
        # Should eventually hit rate limit
        assert 429 in responses[-5:]  # Too Many Requests

    def test_upload_rate_limiting(self, client, auth_headers):
        """Test rate limiting on upload endpoints."""
        # Make multiple upload attempts
        responses = []
        for _ in range(10):
            response = client.post('/api/upload',
                                 data={'file': (io.BytesIO(b'test'), 'test.pdf')},
                                 headers=auth_headers)
            responses.append(response.status_code)
        
        # Should implement rate limiting for uploads
        # Implementation depends on rate limiting strategy