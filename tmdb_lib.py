import os
from redis_lib import get_from_cache, save_to_cache
import logging
import json
import requests
from urllib.parse import quote

logger = logging.getLogger("tmdb_lib")
logger.setLevel(os.environ.get("TMDB_LIB_LOG_LEVEL", "INFO"))
logger.handlers = []
console_handler = logging.StreamHandler()
console_handler.setLevel(os.environ.get("TMDB_LIB_LOG_LEVEL", "INFO"))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def search_movie_by_query_and_year(*, query: str, year: int):
    api_access_token = os.getenv("TMDB_API_ACCESS_TOKEN")
    headers = {
        "Authorization": f"Bearer {api_access_token}",
    }
    url = f"https://api.themoviedb.org/3/search/movie?include_adult=false&language=en-US&query={quote(query)}&year={year}"  # noqa: E501
    cached = get_from_cache(key=url)
    if cached:
        logger.debug(f"TMDB Cache hit for {query} ({year})")
        return json.loads(cached)
    logger.debug(f"TMDB Cache miss for {query} ({year}), requesting from TMDB")
    r = requests.get(url, headers=headers)
    response_json = json.loads(r.text)
    logger.debug(f"Response url: '{url}' json: {response_json}")
    save_to_cache(key=url, data=response_json, ttl=28800)
    return response_json


def get_config():
    api_access_token = os.getenv("TMDB_API_ACCESS_TOKEN")
    headers = {
        "Authorization": f"Bearer {api_access_token}",
    }
    url = "https://api.themoviedb.org/3/configuration"
    cached = get_from_cache(key=url)
    if cached:
        logger.debug("TMDB Cache hit for /configuration)")
        return json.loads(cached)
    logger.debug("TMDB Cache miss for /configuration, requesting from TMDB")
    r = requests.get(url, headers=headers)
    response_json = json.loads(r.text)
    logger.debug(f"Response json: {response_json}")
    save_to_cache(key=url, data=response_json, ttl=28800)
    return response_json
