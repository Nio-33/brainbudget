"""
Security utilities for BrainBudget application.
Handles rate limiting, account lockout, and security monitoring.
"""
import logging
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from flask import request, current_app
from functools import wraps
import redis
import hashlib

logger = logging.getLogger(__name__)


class SecurityManager:
    """Manages security features including rate limiting and account lockout."""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = True
        
    def initialize(self, redis_url: Optional[str] = None):
        """Initialize Redis connection for security tracking."""
        try:
            if redis_url:
                import redis
                self.redis_client = redis.from_url(redis_url)
                logger.info("Redis security manager initialized")
            else:
                # Fallback to in-memory tracking for development
                self._in_memory_store = {}
                logger.warning("Using in-memory security tracking (not for production)")
        except Exception as e:
            logger.error(f"Failed to initialize security manager: {e}")
            self.enabled = False

    def get_client_key(self) -> str:
        """Generate a unique key for the client (IP + User Agent hash)."""
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        key_data = f"{ip_address}:{user_agent}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def is_rate_limited(self, key: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
        """Check if a key is rate limited."""
        if not self.enabled:
            return False
            
        try:
            if self.redis_client:
                # Redis-based rate limiting
                current_time = int(time.time())
                window_start = current_time - (window_minutes * 60)
                
                # Remove old entries
                self.redis_client.zremrangebyscore(f"rate_limit:{key}", 0, window_start)
                
                # Count current attempts
                current_attempts = self.redis_client.zcard(f"rate_limit:{key}")
                
                if current_attempts >= max_attempts:
                    logger.warning(f"Rate limit exceeded for key: {key}")
                    return True
                    
                return False
            else:
                # In-memory fallback
                current_time = datetime.utcnow()
                if key not in self._in_memory_store:
                    self._in_memory_store[key] = []
                
                # Remove old attempts
                self._in_memory_store[key] = [
                    attempt_time for attempt_time in self._in_memory_store[key]
                    if current_time - attempt_time < timedelta(minutes=window_minutes)
                ]
                
                return len(self._in_memory_store[key]) >= max_attempts
                
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return False

    def record_attempt(self, key: str):
        """Record an attempt for rate limiting."""
        if not self.enabled:
            return
            
        try:
            if self.redis_client:
                current_time = int(time.time())
                self.redis_client.zadd(f"rate_limit:{key}", {current_time: current_time})
                # Set expiry for cleanup
                self.redis_client.expire(f"rate_limit:{key}", 3600)  # 1 hour
            else:
                # In-memory fallback
                current_time = datetime.utcnow()
                if key not in self._in_memory_store:
                    self._in_memory_store[key] = []
                self._in_memory_store[key].append(current_time)
                
        except Exception as e:
            logger.error(f"Error recording attempt: {e}")

    def is_account_locked(self, email: str) -> bool:
        """Check if an account is locked due to failed login attempts."""
        if not self.enabled:
            return False
            
        try:
            lockout_key = f"lockout:{email}"
            
            if self.redis_client:
                lockout_data = self.redis_client.get(lockout_key)
                if lockout_data:
                    lockout_time = float(lockout_data.decode())
                    if time.time() - lockout_time < 1800:  # 30 minutes
                        return True
                return False
            else:
                # In-memory fallback
                if lockout_key in self._in_memory_store:
                    lockout_time = self._in_memory_store[lockout_key]
                    if datetime.utcnow() - lockout_time < timedelta(minutes=30):
                        return True
                return False
                
        except Exception as e:
            logger.error(f"Error checking account lockout: {e}")
            return False

    def lock_account(self, email: str):
        """Lock an account due to failed login attempts."""
        if not self.enabled:
            return
            
        try:
            lockout_key = f"lockout:{email}"
            
            if self.redis_client:
                self.redis_client.set(lockout_key, time.time(), ex=1800)  # 30 minutes
            else:
                # In-memory fallback
                self._in_memory_store[lockout_key] = datetime.utcnow()
                
            logger.warning(f"Account locked: {email}")
            
        except Exception as e:
            logger.error(f"Error locking account: {e}")

    def unlock_account(self, email: str):
        """Manually unlock an account."""
        if not self.enabled:
            return
            
        try:
            lockout_key = f"lockout:{email}"
            
            if self.redis_client:
                self.redis_client.delete(lockout_key)
            else:
                # In-memory fallback
                self._in_memory_store.pop(lockout_key, None)
                
            logger.info(f"Account unlocked: {email}")
            
        except Exception as e:
            logger.error(f"Error unlocking account: {e}")

    def record_failed_login(self, email: str) -> bool:
        """Record a failed login attempt and check if account should be locked."""
        if not self.enabled:
            return False
            
        try:
            failed_key = f"failed_login:{email}"
            
            if self.redis_client:
                # Increment failed attempts
                current_attempts = self.redis_client.incr(failed_key)
                self.redis_client.expire(failed_key, 1800)  # 30 minutes
                
                if current_attempts >= 5:  # Lock after 5 failed attempts
                    self.lock_account(email)
                    return True
                    
            else:
                # In-memory fallback
                current_time = datetime.utcnow()
                if failed_key not in self._in_memory_store:
                    self._in_memory_store[failed_key] = []
                
                # Remove old attempts (older than 30 minutes)
                self._in_memory_store[failed_key] = [
                    attempt_time for attempt_time in self._in_memory_store[failed_key]
                    if current_time - attempt_time < timedelta(minutes=30)
                ]
                
                # Add new attempt
                self._in_memory_store[failed_key].append(current_time)
                
                if len(self._in_memory_store[failed_key]) >= 5:
                    self.lock_account(email)
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error recording failed login: {e}")
            return False

    def clear_failed_attempts(self, email: str):
        """Clear failed login attempts for successful login."""
        if not self.enabled:
            return
            
        try:
            failed_key = f"failed_login:{email}"
            
            if self.redis_client:
                self.redis_client.delete(failed_key)
            else:
                # In-memory fallback
                self._in_memory_store.pop(failed_key, None)
                
        except Exception as e:
            logger.error(f"Error clearing failed attempts: {e}")


# Global security manager instance
security_manager = SecurityManager()


def rate_limit(max_attempts: int = 5, window_minutes: int = 15):
    """Decorator for rate limiting endpoints."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not security_manager.enabled:
                return f(*args, **kwargs)
                
            client_key = security_manager.get_client_key()
            
            if security_manager.is_rate_limited(client_key, max_attempts, window_minutes):
                logger.warning(f"Rate limit exceeded for endpoint {request.endpoint}")
                return {
                    'error': True,
                    'message': 'Too many requests. Please try again later! ⏰',
                    'status_code': 429
                }, 429
            
            # Record the attempt
            security_manager.record_attempt(client_key)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def account_lockout_check(f):
    """Decorator to check for account lockout before authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not security_manager.enabled:
            return f(*args, **kwargs)
            
        # Extract email from request data
        data = request.get_json() or {}
        email = data.get('email')
        
        if email and security_manager.is_account_locked(email):
            logger.warning(f"Blocked login attempt for locked account: {email}")
            return {
                'error': True,
                'message': 'Account temporarily locked due to multiple failed attempts. Please try again later! 🔒',
                'status_code': 423
            }, 423
        
        return f(*args, **kwargs)
    return decorated_function


def log_security_event(event_type: str, details: Dict):
    """Log security events for monitoring."""
    try:
        security_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
            'user_agent': request.headers.get('User-Agent', ''),
            'endpoint': request.endpoint,
            'details': details
        }
        
        logger.warning(f"SECURITY_EVENT: {security_log}")
        
        # In a production environment, you might want to send this to a
        # security monitoring service like Datadog, Splunk, or custom SIEM
        
    except Exception as e:
        logger.error(f"Failed to log security event: {e}")