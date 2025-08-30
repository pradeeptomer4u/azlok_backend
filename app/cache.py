import redis
import json
import os
from typing import Optional, Any
from functools import wraps
import asyncio
from datetime import timedelta

# Redis configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://red-d2hf7madbo4c73b07d80:6379')

# Initialize Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class RedisCache:
    def __init__(self):
        self.client = redis_client
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, expire: int = 300) -> bool:
        """Set value in Redis cache with expiration (default 5 minutes)"""
        try:
            serialized_value = json.dumps(value, default=str)
            return self.client.setex(key, expire, serialized_value)
        except Exception as e:
            print(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis cache"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Redis clear pattern error: {e}")
            return 0

# Global cache instance
cache = RedisCache()

def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_parts = []
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(str(hash(str(arg))))
    
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool, type(None))):
            key_parts.append(f"{k}:{v}")
        else:
            key_parts.append(f"{k}:{hash(str(v))}")
    
    return ":".join(key_parts)

def cached(expire: int = 300, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_str = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key_str)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key_str, result, expire)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_str = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key_str)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key_str, result, expire)
            return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Cache invalidation helpers
def invalidate_categories_cache():
    """Invalidate all category-related cache"""
    cache.clear_pattern("categories:*")

def invalidate_products_cache():
    """Invalidate all product-related cache"""
    cache.clear_pattern("products:*")

def invalidate_product_cache(product_id: int):
    """Invalidate specific product cache"""
    cache.clear_pattern(f"products:*:{product_id}:*")

def invalidate_category_cache(category_id: int):
    """Invalidate specific category cache"""
    cache.clear_pattern(f"categories:*:{category_id}:*")
