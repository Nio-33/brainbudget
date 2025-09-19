#!/usr/bin/env python3
"""
Smoke tests for BrainBudget deployment validation.
Validates critical functionality after deployment.
"""
import argparse
import requests
import time
import sys
import json
from typing import Dict, List, Any


class SmokeTestRunner:
    """Run smoke tests against deployed application."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BrainBudget-SmokeTest/1.0',
            'Accept': 'application/json'
        })
        
        self.results = []
    
    def run_test(self, name: str, test_func) -> bool:
        """Run a single test and record result."""
        print(f"Running test: {name}...")
        
        try:
            start_time = time.time()
            test_func()
            duration = time.time() - start_time
            
            self.results.append({
                'name': name,
                'status': 'PASS',
                'duration': duration,
                'error': None
            })
            
            print(f"✅ {name} - PASS ({duration:.2f}s)")
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            
            self.results.append({
                'name': name,
                'status': 'FAIL',
                'duration': duration,
                'error': str(e)
            })
            
            print(f"❌ {name} - FAIL ({duration:.2f}s): {e}")
            return False
    
    def test_health_check(self):
        """Test basic health check endpoint."""
        response = self.session.get(f"{self.base_url}/health", timeout=self.timeout)
        response.raise_for_status()
        
        data = response.json()
        assert data['status'] == 'healthy', f"Health check failed: {data}"
        assert data['app'] == 'BrainBudget', "Incorrect app name in health check"
    
    def test_detailed_health_check(self):
        """Test detailed health check endpoint."""
        response = self.session.get(f"{self.base_url}/health/detailed", timeout=self.timeout)
        response.raise_for_status()
        
        data = response.json()
        assert 'checks' in data, "Missing checks in detailed health"
        assert 'timestamp' in data, "Missing timestamp in detailed health"
        
        # Check that critical services are healthy
        if 'database' in data['checks']:
            db_check = data['checks']['database']
            assert db_check.get('healthy', False), f"Database health check failed: {db_check}"
    
    def test_static_assets(self):
        """Test that static assets are accessible."""
        static_files = [
            '/static/css/auth.css',
            '/static/js/core.js',
            '/static/manifest.json',
            '/static/favicon.ico'
        ]
        
        for static_file in static_files:
            response = self.session.get(f"{self.base_url}{static_file}", timeout=self.timeout)
            if response.status_code not in [200, 304]:
                # Not all static files may exist, so we'll just warn
                print(f"⚠️  Static file not accessible: {static_file}")
    
    def test_api_endpoints_accessibility(self):
        """Test that API endpoints are accessible (even if they return auth errors)."""
        api_endpoints = [
            '/api/auth/firebase-config',
            '/api/auth/verify',
            '/api/upload/statement',
            '/api/analysis/history'
        ]
        
        for endpoint in api_endpoints:
            response = self.session.get(f"{self.base_url}{endpoint}", timeout=self.timeout)
            # We expect 401 or 400 for most endpoints (auth required)
            # But we want to make sure they don't return 500 or are unreachable
            assert response.status_code < 500, f"Server error on {endpoint}: {response.status_code}"
    
    def test_firebase_config_endpoint(self):
        """Test Firebase configuration endpoint."""
        response = self.session.get(f"{self.base_url}/api/auth/firebase-config", timeout=self.timeout)
        response.raise_for_status()
        
        data = response.json()
        assert data['success'] is True, "Firebase config endpoint failed"
        assert 'config' in data, "Missing config in Firebase config response"
        
        config = data['config']
        required_fields = ['projectId', 'authDomain', 'apiKey']
        for field in required_fields:
            assert field in config, f"Missing {field} in Firebase config"
            assert config[field], f"Empty {field} in Firebase config"
    
    def test_security_headers(self):
        """Test that security headers are present."""
        response = self.session.get(f"{self.base_url}/", timeout=self.timeout)
        
        expected_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection'
        ]
        
        for header in expected_headers:
            assert header in response.headers, f"Missing security header: {header}"
    
    def test_cors_headers(self):
        """Test CORS configuration."""
        # Make an OPTIONS request to test CORS
        response = self.session.options(f"{self.base_url}/api/auth/verify", timeout=self.timeout)
        
        # Should have CORS headers or at least not return an error
        assert response.status_code < 500, "CORS preflight request failed"
    
    def test_rate_limiting(self):
        """Test that rate limiting is working (basic check)."""
        # Make multiple rapid requests to a rate-limited endpoint
        endpoint = f"{self.base_url}/api/auth/verify"
        
        responses = []
        for i in range(5):
            response = self.session.post(endpoint, json={'id_token': 'invalid'}, timeout=self.timeout)
            responses.append(response.status_code)
        
        # We should get some rate limiting or at least consistent responses
        # This is a basic check - in production you might want more sophisticated testing
        assert all(code < 500 for code in responses), "Server errors during rate limit test"
    
    def test_error_handling(self):
        """Test error handling for various scenarios."""
        # Test 404 handling
        response = self.session.get(f"{self.base_url}/nonexistent/endpoint", timeout=self.timeout)
        assert response.status_code == 404, "404 handling not working"
        
        # Test invalid JSON handling
        response = self.session.post(
            f"{self.base_url}/api/auth/verify",
            data='{"invalid": json}',
            headers={'Content-Type': 'application/json'},
            timeout=self.timeout
        )
        assert response.status_code == 400, "Invalid JSON handling not working"
    
    def run_all_tests(self) -> bool:
        """Run all smoke tests."""
        print(f"🚀 Starting smoke tests for {self.base_url}")
        print("=" * 60)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Detailed Health Check", self.test_detailed_health_check),
            ("Static Assets", self.test_static_assets),
            ("API Endpoints Accessibility", self.test_api_endpoints_accessibility),
            ("Firebase Config", self.test_firebase_config_endpoint),
            ("Security Headers", self.test_security_headers),
            ("CORS Headers", self.test_cors_headers),
            ("Rate Limiting", self.test_rate_limiting),
            ("Error Handling", self.test_error_handling)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            if self.run_test(test_name, test_func):
                passed += 1
            else:
                failed += 1
        
        print("=" * 60)
        print(f"📊 Test Results: {passed} passed, {failed} failed")
        
        if failed > 0:
            print("\n❌ Failed tests:")
            for result in self.results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['name']}: {result['error']}")
        
        return failed == 0
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a test report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['status'] == 'PASS')
        failed_tests = total_tests - passed_tests
        
        return {
            'timestamp': time.time(),
            'base_url': self.base_url,
            'summary': {
                'total': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'success_rate': (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            },
            'results': self.results
        }


def main():
    parser = argparse.ArgumentParser(description='Run BrainBudget smoke tests')
    parser.add_argument('--env', choices=['staging', 'production'], required=True,
                       help='Environment to test')
    parser.add_argument('--url', help='Custom base URL (overrides environment)')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Request timeout in seconds')
    parser.add_argument('--report', help='Save test report to file')
    
    args = parser.parse_args()
    
    # Determine base URL
    if args.url:
        base_url = args.url
    elif args.env == 'staging':
        base_url = 'https://brainbudget-staging.web.app'
    elif args.env == 'production':
        base_url = 'https://brainbudget.web.app'
    else:
        print("❌ Environment not supported")
        sys.exit(1)
    
    # Run tests
    runner = SmokeTestRunner(base_url, timeout=args.timeout)
    success = runner.run_all_tests()
    
    # Generate and save report if requested
    if args.report:
        report = runner.generate_report()
        with open(args.report, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Test report saved to {args.report}")
    
    # Exit with appropriate code
    if success:
        print("🎉 All smoke tests passed!")
        sys.exit(0)
    else:
        print("💥 Some smoke tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()