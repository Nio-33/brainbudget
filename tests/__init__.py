"""
BrainBudget Test Suite
=====================

Comprehensive testing framework for BrainBudget application.

Test Structure:
- test_auth.py: Authentication and user management tests  
- test_upload.py: File upload and processing tests
- test_analysis.py: Transaction analysis and AI features tests
- test_api.py: API endpoint tests
- test_firebase.py: Firebase service integration tests
- conftest.py: Shared test fixtures and configuration

Usage:
    pytest                           # Run all tests
    pytest tests/test_auth.py        # Run specific test file
    pytest -v                       # Verbose output
    pytest --cov=app                # With coverage report
"""