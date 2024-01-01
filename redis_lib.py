import json
import os
import redis
import logging

logger = logging.getLogger("redis_lib")


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
