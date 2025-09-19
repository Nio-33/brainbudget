"""
Caching utilities for BrainBudget application.
Provides Redis-based caching with fallback to in-memory cache.
"""
import json
import logging
import hashlib
import pickle
from typing import Any, Optional, Union, Dict
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching with Redis primary and in-memory fallback."""
    
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}
        self.enabled = True
        self.default_ttl = 3600  # 1 hour default TTL
        
    def initialize(self, redis_url: Optional[str] = None):
        """Initialize cache with Redis connection."""
        try:
            if redis_url:
                import redis
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
            else:
                logger.warning("No Redis URL provided, using in-memory cache only")
                
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            logger.warning("Falling back to in-memory cache")
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for storage."""
        try:
            if isinstance(value, (str, int, float, bool)):
                return json.dumps(value)
            else:
                # Use pickle for complex objects, then base64 encode
                import base64
                pickled = pickle.dumps(value)
                return base64.b64encode(pickled).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to serialize cache value: {e}")
            raise
    
    def _deserialize_value(self, value: str) -> Any:
        """Deserialize value from storage."""
        try:
            # Try JSON first
            return json.loads(value)
        except json.JSONDecodeError:
            try:
                # Try pickle with base64
                import base64
                pickled = base64.b64decode(value.encode('utf-8'))
                return pickle.loads(pickled)
            except Exception as e:
                logger.error(f"Failed to deserialize cache value: {e}")
                return None
    
    def _generate_key(self, key: str, prefix: str = "bb") -> str:
        """Generate cache key with prefix."""
        return f"{prefix}:{key}"
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        if not self.enabled:
            return default
            
        cache_key = self._generate_key(key)
        
        try:
            # Try Redis first
            if self.redis_client:
                value = self.redis_client.get(cache_key)
                if value is not None:
                    return self._deserialize_value(value)
            
            # Fallback to memory cache
            cache_entry = self.memory_cache.get(cache_key)
            if cache_entry:
                # Check if expired
                if cache_entry['expires_at'] > datetime.utcnow():
                    return cache_entry['value']
                else:
                    # Remove expired entry
                    del self.memory_cache[cache_key]
            
            return default
            
        except Exception as e:
            logger.error(f"Failed to get cache value for key {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL."""
        if not self.enabled:
            return False
            
        cache_key = self._generate_key(key)
        ttl = ttl or self.default_ttl
        
        try:
            serialized_value = self._serialize_value(value)
            
            # Try Redis first
            if self.redis_client:
                success = self.redis_client.setex(cache_key, ttl, serialized_value)
                if success:
                    return True
            
            # Fallback to memory cache
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            self.memory_cache[cache_key] = {
                'value': value,
                'expires_at': expires_at
            }
            
            # Clean up expired entries periodically
            self._cleanup_memory_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache value for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.enabled:
            return False
            
        cache_key = self._generate_key(key)
        
        try:
            # Delete from Redis
            if self.redis_client:
                self.redis_client.delete(cache_key)
            
            # Delete from memory cache
            self.memory_cache.pop(cache_key, None)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    def clear(self, pattern: Optional[str] = None) -> bool:
        """Clear cache entries matching pattern."""
        if not self.enabled:
            return False
            
        try:
            if pattern:
                # Clear specific pattern
                if self.redis_client:
                    keys = self.redis_client.keys(f"bb:{pattern}*")
                    if keys:
                        self.redis_client.delete(*keys)
                
                # Clear from memory cache
                keys_to_delete = [k for k in self.memory_cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self.memory_cache[key]
            else:
                # Clear all
                if self.redis_client:
                    keys = self.redis_client.keys("bb:*")
                    if keys:
                        self.redis_client.delete(*keys)
                
                self.memory_cache.clear()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    def _cleanup_memory_cache(self):
        """Clean up expired entries from memory cache."""
        try:
            current_time = datetime.utcnow()
            expired_keys = [
                key for key, entry in self.memory_cache.items()
                if entry['expires_at'] <= current_time
            ]
            
            for key in expired_keys:
                del self.memory_cache[key]
                
            # Keep memory cache size reasonable (max 1000 entries)
            if len(self.memory_cache) > 1000:
                # Remove oldest entries
                sorted_entries = sorted(
                    self.memory_cache.items(),
                    key=lambda x: x[1]['expires_at']
                )
                
                for key, _ in sorted_entries[:len(self.memory_cache) - 1000]:
                    del self.memory_cache[key]
                    
        except Exception as e:
            logger.error(f"Failed to cleanup memory cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            'enabled': self.enabled,
            'redis_connected': self.redis_client is not None,
            'memory_cache_size': len(self.memory_cache),
            'default_ttl': self.default_ttl
        }
        
        try:
            if self.redis_client:
                info = self.redis_client.info()
                stats['redis_info'] = {
                    'used_memory': info.get('used_memory_human'),
                    'connected_clients': info.get('connected_clients'),
                    'keyspace_hits': info.get('keyspace_hits'),
                    'keyspace_misses': info.get('keyspace_misses')
                }
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
        
        return stats


# Global cache manager instance
cache_manager = CacheManager()


def cache_result(key_pattern: str, ttl: int = 3600):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            
            # Add positional arguments
            for arg in args:
                if isinstance(arg, (str, int, float, bool)):
                    key_parts.append(str(arg))
                else:
                    # Hash complex objects
                    arg_hash = hashlib.md5(str(arg).encode()).hexdigest()[:8]
                    key_parts.append(arg_hash)
            
            # Add keyword arguments
            for k, v in sorted(kwargs.items()):
                if isinstance(v, (str, int, float, bool)):
                    key_parts.append(f"{k}={v}")
                else:
                    arg_hash = hashlib.md5(str(v).encode()).hexdigest()[:8]
                    key_parts.append(f"{k}={arg_hash}")
            
            cache_key = key_pattern.format(key="_".join(key_parts))
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for key: {cache_key}")
            result = func(*args, **kwargs)
            
            # Only cache successful results
            if result is not None:
                cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str):
    """Invalidate cache entries matching pattern."""
    return cache_manager.clear(pattern)


def cache_user_data(user_id: str, data_type: str, ttl: int = 1800):
    """Cache user-specific data."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"user:{user_id}:{data_type}"
            
            # Check cache first
            cached_data = cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


class AnalysisCache:
    """Specialized cache for analysis results."""
    
    @staticmethod
    def get_analysis(user_id: str, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result."""
        cache_key = f"analysis:{user_id}:{file_hash}"
        return cache_manager.get(cache_key)
    
    @staticmethod
    def set_analysis(user_id: str, file_hash: str, analysis_result: Dict[str, Any], ttl: int = 86400):
        """Cache analysis result (24 hour default TTL)."""
        cache_key = f"analysis:{user_id}:{file_hash}"
        return cache_manager.set(cache_key, analysis_result, ttl)
    
    @staticmethod
    def invalidate_user_analyses(user_id: str):
        """Invalidate all cached analyses for a user."""
        return cache_manager.clear(f"analysis:{user_id}")


class UserProfileCache:
    """Specialized cache for user profiles."""
    
    @staticmethod
    def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user profile."""
        cache_key = f"profile:{user_id}"
        return cache_manager.get(cache_key)
    
    @staticmethod
    def set_profile(user_id: str, profile_data: Dict[str, Any], ttl: int = 3600):
        """Cache user profile (1 hour default TTL)."""
        cache_key = f"profile:{user_id}"
        return cache_manager.set(cache_key, profile_data, ttl)
    
    @staticmethod
    def invalidate_profile(user_id: str):
        """Invalidate cached user profile."""
        cache_key = f"profile:{user_id}"
        return cache_manager.delete(cache_key)


def warm_cache():
    """Warm up cache with frequently accessed data."""
    try:
        logger.info("Starting cache warm-up")
        
        # Example: Pre-load common currency rates, categories, etc.
        # This would be implemented based on specific application needs
        
        logger.info("Cache warm-up completed")
        
    except Exception as e:
        logger.error(f"Cache warm-up failed: {e}")


def initialize_cache(redis_url: Optional[str] = None):
    """Initialize the cache system."""
    try:
        cache_manager.initialize(redis_url)
        
        # Warm up cache if needed
        warm_cache()
        
        logger.info("Cache system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize cache system: {e}")
        raise