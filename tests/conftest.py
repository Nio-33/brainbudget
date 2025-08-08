"""
Test Configuration and Shared Fixtures
=====================================

Provides common test fixtures and configuration for BrainBudget tests.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from app import create_app
from app.services.firebase_service import FirebaseService


@pytest.fixture
def app():
    """Create test Flask application."""
    # Create temporary database file
    db_fd, temp_db = tempfile.mkstemp()
    
    # Test configuration
    test_config = {
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'FIREBASE_PROJECT_ID': 'test-project',
        'FIREBASE_PRIVATE_KEY': 'test-private-key',
        'FIREBASE_CLIENT_EMAIL': 'test@test.com',
        'GEMINI_API_KEY': 'test-gemini-key',
        'PLAID_CLIENT_ID': 'test-plaid-id',
        'PLAID_SECRET': 'test-plaid-secret',
        'PLAID_ENV': 'sandbox'
    }
    
    # Mock environment variables
    with patch.dict(os.environ, test_config):
        app = create_app('testing')
        
        # Override config for testing
        for key, value in test_config.items():
            app.config[key] = value
    
    yield app
    
    # Cleanup
    os.close(db_fd)
    os.unlink(temp_db)


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def mock_firebase_service():
    """Mock Firebase service for testing."""
    mock_service = Mock(spec=FirebaseService)
    mock_service.auth = Mock()
    mock_service.db = Mock()
    mock_service.storage = Mock()
    
    # Mock common Firebase operations
    mock_service.verify_token.return_value = {
        'uid': 'test-user-123',
        'email': 'test@example.com'
    }
    
    mock_service.create_user_profile.return_value = True
    mock_service.get_user_profile.return_value = {
        'uid': 'test-user-123',
        'email': 'test@example.com',
        'displayName': 'Test User',
        'preferences': {
            'currency': 'USD',
            'theme': 'light'
        }
    }
    
    return mock_service


@pytest.fixture
def mock_gemini_service():
    """Mock Gemini AI service for testing."""
    mock_service = Mock()
    
    # Mock analysis response
    mock_service.analyze_statement.return_value = {
        'success': True,
        'analysis': {
            'total_transactions': 25,
            'total_amount': 1250.50,
            'categories': {
                'food': 450.00,
                'transport': 200.00,
                'entertainment': 150.00,
                'utilities': 300.00,
                'other': 150.50
            },
            'insights': [
                'High spending on food category',
                'Regular utility payments detected'
            ]
        }
    }
    
    return mock_service


@pytest.fixture
def sample_statement_data():
    """Sample bank statement data for testing."""
    return {
        'transactions': [
            {
                'date': '2024-01-15',
                'description': 'GROCERY STORE',
                'amount': -125.50,
                'category': 'food'
            },
            {
                'date': '2024-01-14',
                'description': 'SALARY DEPOSIT',
                'amount': 3000.00,
                'category': 'income'
            },
            {
                'date': '2024-01-13',
                'description': 'UBER RIDE',
                'amount': -25.00,
                'category': 'transport'
            }
        ],
        'balance': 2849.50,
        'period': 'January 2024'
    }


@pytest.fixture
def auth_headers():
    """Sample authentication headers for API tests."""
    return {
        'Authorization': 'Bearer mock-firebase-token',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for upload testing."""
    # Create a minimal PDF-like file
    pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\nxref\n0 3\ntrailer\n<<\n/Size 3\n/Root 1 0 R\n>>\nstartxref\n%%EOF'
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_file.write(pdf_content)
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


# Test data fixtures
@pytest.fixture
def valid_user_data():
    """Valid user registration data."""
    return {
        'email': 'test@example.com',
        'password': 'SecurePass123!',
        'name': 'Test User'
    }


@pytest.fixture
def invalid_user_data():
    """Invalid user registration data for testing validation."""
    return {
        'email': 'invalid-email',
        'password': '123',  # Too weak
        'name': ''  # Empty name
    }


# Parameterized fixtures for testing multiple scenarios
@pytest.fixture(params=[
    'application/pdf',
    'image/png', 
    'image/jpeg',
    'text/plain'
])
def file_types(request):
    """Different file types for upload testing."""
    return request.param


@pytest.fixture(params=[
    {'amount': 100, 'currency': 'USD'},
    {'amount': 85.50, 'currency': 'EUR'},
    {'amount': 1000, 'currency': 'GBP'}
])
def currency_test_data(request):
    """Different currency scenarios for testing."""
    return request.param