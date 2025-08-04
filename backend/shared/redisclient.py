# redis_client.py
# as of now we are not using redis any purpose.
import redis
import logging

try:
    # Connect to Redis (adjust host/port/password for production)
    redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)
    # Test connection
    redis_client.ping()
except redis.ConnectionError as e:
    logging.error(f"Redis connection error: {e}")
    redis_client = None
except Exception as e:
    logging.error(f"Unexpected error while connecting to Redis: {e}")
    redis_client = None

