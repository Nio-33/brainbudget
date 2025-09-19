"""
Application monitoring and metrics utilities.
Provides performance monitoring, error tracking, and health checks.
"""
import time
import logging
import functools
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from flask import request, g, current_app
import json

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor application performance and metrics."""
    
    def __init__(self):
        self.metrics = {}
        self.enabled = True
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a metric value."""
        if not self.enabled:
            return
            
        try:
            timestamp = datetime.utcnow().isoformat()
            metric_data = {
                'name': name,
                'value': value,
                'timestamp': timestamp,
                'tags': tags or {}
            }
            
            # Store in memory (in production, send to monitoring service)
            if name not in self.metrics:
                self.metrics[name] = []
            
            self.metrics[name].append(metric_data)
            
            # Keep only last 1000 entries per metric
            if len(self.metrics[name]) > 1000:
                self.metrics[name] = self.metrics[name][-1000:]
            
            # Log critical metrics
            if 'error' in name.lower() or 'failure' in name.lower():
                logger.warning(f"Performance metric: {name} = {value} {tags}")
            elif value > 5000:  # Log slow operations (> 5 seconds)
                logger.warning(f"Slow operation: {name} = {value}ms {tags}")
                
        except Exception as e:
            logger.error(f"Failed to record metric {name}: {e}")
    
    def get_metrics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get recorded metrics."""
        if name:
            return self.metrics.get(name, [])
        return self.metrics
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        summary = {}
        
        for name, values in self.metrics.items():
            if not values:
                continue
                
            metric_values = [v['value'] for v in values]
            summary[name] = {
                'count': len(metric_values),
                'avg': sum(metric_values) / len(metric_values),
                'min': min(metric_values),
                'max': max(metric_values),
                'last': values[-1]['value'] if values else 0
            }
        
        return summary


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def monitor_performance(metric_name: Optional[str] = None):
    """Decorator to monitor function performance."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            metric = metric_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                
                # Record success metric
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record_metric(
                    f"{metric}.duration",
                    duration_ms,
                    {'status': 'success'}
                )
                
                return result
                
            except Exception as e:
                # Record error metric
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record_metric(
                    f"{metric}.duration",
                    duration_ms,
                    {'status': 'error', 'error_type': type(e).__name__}
                )
                
                performance_monitor.record_metric(
                    f"{metric}.error",
                    1,
                    {'error_type': type(e).__name__, 'error_message': str(e)}
                )
                
                raise
        
        return wrapper
    return decorator


def track_request_metrics():
    """Track HTTP request metrics."""
    def before_request():
        g.start_time = time.time()
        g.request_id = request.headers.get('X-Request-ID', 'unknown')
    
    def after_request(response):
        try:
            if hasattr(g, 'start_time'):
                duration_ms = (time.time() - g.start_time) * 1000
                
                # Record request metrics
                tags = {
                    'method': request.method,
                    'endpoint': request.endpoint or 'unknown',
                    'status_code': str(response.status_code),
                    'user_agent': request.headers.get('User-Agent', '')[:50]
                }
                
                performance_monitor.record_metric(
                    'http_request_duration',
                    duration_ms,
                    tags
                )
                
                performance_monitor.record_metric(
                    'http_request_count',
                    1,
                    tags
                )
                
                # Log slow requests
                if duration_ms > 5000:
                    logger.warning(f"Slow request: {request.method} {request.path} - {duration_ms:.2f}ms")
                
                # Log errors
                if response.status_code >= 400:
                    logger.error(f"HTTP Error: {response.status_code} {request.method} {request.path}")
                    
        except Exception as e:
            logger.error(f"Failed to track request metrics: {e}")
        
        return response
    
    return before_request, after_request


class HealthChecker:
    """Application health check utilities."""
    
    def __init__(self):
        self.checks = {}
    
    def register_check(self, name: str, check_func: Callable[[], Dict[str, Any]]):
        """Register a health check function."""
        self.checks[name] = check_func
    
    def run_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        overall_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                check_result = check_func()
                results['checks'][name] = check_result
                
                if not check_result.get('healthy', False):
                    overall_healthy = False
                    
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results['checks'][name] = {
                    'healthy': False,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
                overall_healthy = False
        
        results['status'] = 'healthy' if overall_healthy else 'unhealthy'
        return results


# Global health checker instance
health_checker = HealthChecker()


def check_database_health() -> Dict[str, Any]:
    """Check Firebase/database connectivity."""
    try:
        from flask import current_app
        
        if hasattr(current_app, 'firebase') and current_app.firebase._initialized:
            # Simple check - try to access Firestore
            db = current_app.firebase.db
            if db:
                # Perform a lightweight query
                test_doc = db.collection('health_check').limit(1).get()
                return {
                    'healthy': True,
                    'message': 'Database connection successful',
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        return {
            'healthy': False,
            'message': 'Database not initialized',
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'message': f'Database check failed: {str(e)}',
            'timestamp': datetime.utcnow().isoformat()
        }


def check_external_services() -> Dict[str, Any]:
    """Check external service connectivity."""
    try:
        import requests
        
        services = {
            'gemini_api': 'https://generativelanguage.googleapis.com',
            'plaid_api': 'https://production.plaid.com'
        }
        
        results = {}
        all_healthy = True
        
        for service, url in services.items():
            try:
                response = requests.get(f"{url}/health", timeout=5)
                healthy = response.status_code < 500
                results[service] = {
                    'healthy': healthy,
                    'status_code': response.status_code,
                    'response_time_ms': response.elapsed.total_seconds() * 1000
                }
                if not healthy:
                    all_healthy = False
            except Exception as e:
                results[service] = {
                    'healthy': False,
                    'error': str(e)
                }
                all_healthy = False
        
        return {
            'healthy': all_healthy,
            'services': results,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'message': f'External services check failed: {str(e)}',
            'timestamp': datetime.utcnow().isoformat()
        }


def check_system_resources() -> Dict[str, Any]:
    """Check system resource usage."""
    try:
        import psutil
        
        # Get CPU and memory usage
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Define thresholds
        cpu_threshold = 80
        memory_threshold = 85
        disk_threshold = 90
        
        healthy = (
            cpu_percent < cpu_threshold and
            memory.percent < memory_threshold and
            disk.percent < disk_threshold
        )
        
        return {
            'healthy': healthy,
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent,
            'thresholds': {
                'cpu': cpu_threshold,
                'memory': memory_threshold,
                'disk': disk_threshold
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except ImportError:
        return {
            'healthy': True,
            'message': 'psutil not available, skipping system resource check',
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            'healthy': False,
            'message': f'System resource check failed: {str(e)}',
            'timestamp': datetime.utcnow().isoformat()
        }


def initialize_monitoring(app):
    """Initialize monitoring for the Flask app."""
    try:
        # Register health checks
        health_checker.register_check('database', check_database_health)
        health_checker.register_check('external_services', check_external_services)
        health_checker.register_check('system_resources', check_system_resources)
        
        # Register request tracking
        before_request, after_request = track_request_metrics()
        app.before_request(before_request)
        app.after_request(after_request)
        
        # Add monitoring endpoints
        @app.route('/health/detailed')
        def detailed_health_check():
            return health_checker.run_checks()
        
        @app.route('/metrics')
        def get_metrics():
            return {
                'metrics': performance_monitor.get_summary(),
                'timestamp': datetime.utcnow().isoformat()
            }
        
        logger.info("Monitoring initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize monitoring: {e}")


class StructuredLogger:
    """Structured logging utility for consistent log formatting."""
    
    @staticmethod
    def log_event(level: str, event_type: str, message: str, **kwargs):
        """Log a structured event."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'message': message,
            **kwargs
        }
        
        logger_func = getattr(logger, level.lower(), logger.info)
        logger_func(json.dumps(log_data))
    
    @staticmethod
    def log_security_event(event_type: str, message: str, **kwargs):
        """Log a security-related event."""
        StructuredLogger.log_event(
            'warning', 
            f'security.{event_type}', 
            message,
            **kwargs
        )
    
    @staticmethod
    def log_performance_event(event_type: str, duration_ms: float, **kwargs):
        """Log a performance-related event."""
        StructuredLogger.log_event(
            'info',
            f'performance.{event_type}',
            f'Operation completed in {duration_ms:.2f}ms',
            duration_ms=duration_ms,
            **kwargs
        )
    
    @staticmethod
    def log_business_event(event_type: str, message: str, **kwargs):
        """Log a business logic event."""
        StructuredLogger.log_event(
            'info',
            f'business.{event_type}',
            message,
            **kwargs
        )


# Global structured logger instance
structured_logger = StructuredLogger()