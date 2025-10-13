import redis
import json
import os
import logging
from typing import Optional, Any
from functools import wraps
import asyncio
from datetime import timedelta

# Configure logging
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = "redis://default:neXvrqBYXo5Hwdcbm3JBRCTYyuriDgSU@redis-11813.c323.us-east-1-2.ec2.redns.redis-cloud.com:11813"

# Initialize Redis client with fault tolerance
try:
    # Configure Redis with SSL support for rediss:// URLs
    ssl_enabled = REDIS_URL.startswith('rediss://')
    redis_client = redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5.0,
        # ssl=ssl_enabled
    )
    # Test connection
    redis_client.ping()
    logger.info("Redis connection established successfully")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Caching will be disabled.")
    redis_client = None

class RedisCache:
    def __init__(self):
        self.client = redis_client
        self.enabled = self.client is not None
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self.enabled:
            return None
            
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, expire: int = 300) -> bool:
        """Set value in Redis cache with expiration (default 5 minutes)"""
        if not self.enabled:
            return False
            
        try:
            serialized_value = json.dumps(value, default=str)
            return self.client.setex(key, expire, serialized_value)
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis cache"""
        if not self.enabled:
            return False
            
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.enabled:
            return 0
            
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Redis clear pattern error: {e}")
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
    try:
        cache.clear_pattern("categories:*")
    except Exception as e:
        logger.warning(f"Failed to invalidate categories cache: {e}")

def invalidate_products_cache():
    """Invalidate all product-related cache"""
    try:
        cache.clear_pattern("products:*")
    except Exception as e:
        logger.warning(f"Failed to invalidate products cache: {e}")

def invalidate_product_cache(product_id: int):
    """Invalidate specific product cache"""
    try:
        cache.clear_pattern(f"products:*:{product_id}:*")
    except Exception as e:
        logger.warning(f"Failed to invalidate product cache for ID {product_id}: {e}")

def invalidate_category_cache(category_id: int):
    """Invalidate specific category cache"""
    try:
        cache.clear_pattern(f"categories:*:{category_id}:*")
    except Exception as e:
        logger.warning(f"Failed to invalidate category cache for ID {category_id}: {e}")


def invalidate_blog_cache():
    """Invalidate all category-related cache"""
    try:
        cache.clear_pattern("blogs:*")
    except Exception as e:
        logger.warning(f"Failed to invalidate blogs cache: {e}")