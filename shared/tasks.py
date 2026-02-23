import redis
import json
import os

# Get Redis connection details from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Parse Redis URL and create client with explicit parameters
try:
    from urllib.parse import urlparse
    parsed = urlparse(REDIS_URL)
    
    redis_client = redis.Redis(
        host=parsed.hostname or 'redis',
        port=parsed.port or 6379,
        db=0,
        decode_responses=True,
        socket_connect_timeout=10,
        socket_timeout=10,
        retry_on_timeout=True,
        health_check_interval=30
    )
    
    # Test connection on import
    redis_client.ping()
    print(f"✓ Connected to Redis at {REDIS_URL}", flush=True)
    
except redis.exceptions.ConnectionError as e:
    print(f"✗ Failed to connect to Redis at {REDIS_URL}: {e}", flush=True)
    print(f"  Redis host: {parsed.hostname or 'redis'}", flush=True)
    print(f"  Redis port: {parsed.port or 6379}", flush=True)
    raise
except Exception as e:
    print(f"✗ Unexpected Redis error: {e}", flush=True)
    raise

def enqueue_task(queue_name: str, task_data: dict):
    """Add task to queue."""
    redis_client.rpush(queue_name, json.dumps(task_data))
    print(f"✓ Enqueued task to {queue_name}: {task_data.get('id', 'unknown')}", flush=True)

def dequeue_task(queue_name: str, timeout: int = 0):
    """Get task from queue (blocking)."""
    result = redis_client.blpop(queue_name, timeout=timeout)
    if result:
        _, task_json = result
        return json.loads(task_json)
    return None

def get_queue_length(queue_name: str) -> int:
    """Get number of pending tasks."""
    return redis_client.llen(queue_name)