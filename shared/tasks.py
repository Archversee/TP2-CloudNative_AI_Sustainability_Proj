import redis
import json
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL)

def enqueue_task(queue_name: str, task_data: dict):
    """Add task to queue."""
    redis_client.rpush(queue_name, json.dumps(task_data))
    print(f"✓ Enqueued task to {queue_name}: {task_data.get('id', 'unknown')}")

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