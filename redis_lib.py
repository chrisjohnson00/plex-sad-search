import json
import os
import redis
import logging

logger = logging.getLogger("redis_lib")
logger.setLevel(os.environ.get("REDIS_LIB_LOG_LEVEL", "INFO"))
logger.handlers = []
console_handler = logging.StreamHandler()
console_handler.setLevel(os.environ.get("REDIS_LIB_LOG_LEVEL", "INFO"))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def get_from_cache(*, key):
    r = get_redis_connection()
    value = r.get(key)
    logger.debug("Fetched '{}':'{}' from cache".format(key, value))
    return value


def get_redis_connection():
    redis_host = os.getenv("REDIS_HOST")
    redis_port = os.getenv('REDIS_PORT', 6379)
    r = redis.Redis(host=redis_host, port=redis_port, db=0)
    return r


def save_to_cache(*, key, data, ttl=0):
    r = get_redis_connection()
    logger.debug("Saving '{}':'{}' to cache".format(key, data))
    if ttl > 0:
        return r.set(key, json.dumps(data), ex=ttl)
    else:
        return r.set(key, json.dumps(data))
