import argparse
import inspect
import json
import os
import traceback
from datetime import datetime, timedelta

import pulsar
import pygogo as gogo
import sad_libraries.redis as sad_redis
import sad_libraries.tmdb as sad_tmdb
from plexapi.library import MovieSection, ShowSection
from plexapi.server import PlexServer
from plexapi.video import Movie, Show


def main():
    logger.info("Starting SAD")
    client = pulsar.Client(f"pulsar://{os.environ['PULSAR_SERVER']}")
    consumer = client.subscribe(os.environ['PULSAR_TOPIC'], os.environ['PULSAR_SUBSCRIPTION'])

    while True:
        msg = consumer.receive()
        message_body = None  # set here to make my IDE happy
        try:
            # decode from bytes, encode with backslashes removed, decode back to a string, then load it as a
            # python native
            message_body = json.loads(msg.data().decode().encode('latin1', 'backslashreplace').decode('unicode-escape'))
            logger.info(f"Received message '{message_body}' id='{msg.message_id()}'")
            process_message(message_body)
            consumer.acknowledge(msg)
            logger.info(f"Message id='{msg.message_id()}' processed successfully")
        except Exception as e:  # noqa: E722
            # Message failed to be processed
            consumer.negative_acknowledge(msg)
            logger.error("A message could not be processed",
                         extra={'message_body': message_body, 'exception': e, 'stack_trace': traceback.format_exc()})


def process_message(message_body):
    # get the latest search keys and results from cache
    results_to_store, search_keys = refresh_from_cache()
    # message_body will be a list of search keys to execute, if a search key exists, that function will be
    # executed, if "all" is in the list, all will be executed.
    if "all" in message_body:
        logger.info("Searching for horror_movies")
        search_keys, results_to_store = horror_movies(search_keys=search_keys, results_to_store=results_to_store)
        logger.info("Searching for lowest_rated_movies")
        search_keys, results_to_store = lowest_rated_movies(search_keys=search_keys, results_to_store=results_to_store)
        logger.info("Searching for unwatched shows")
        search_keys, results_to_store = tv_never_watched(search_keys=search_keys, results_to_store=results_to_store)
        sad_redis.save_to_cache(key='sad_search_keys', data=search_keys)
        sad_redis.save_to_cache(key='sad_results', data=results_to_store)
    else:
        for search_key in message_body:
            search_keys, results_to_store = execute_search_function(search_key=search_key, search_keys=search_keys,
                                                                    results_to_store=results_to_store)
            sad_redis.save_to_cache(key='sad_search_keys', data=search_keys)
            sad_redis.save_to_cache(key='sad_results', data=results_to_store)


def execute_search_function(*, search_key, search_keys, results_to_store):
    search_functions = {
        "horror_movies": horror_movies,
        "lowest_rated_movies": lowest_rated_movies,
        "tv_never_watched": tv_never_watched
    }

    # Get the function corresponding to the search_key
    search_function = search_functions.get(search_key)

    if search_function:
        search_keys, results_to_store = search_function(search_keys=search_keys, results_to_store=results_to_store)
    else:
        logger.error(f"Could not find a function with the name '{search_key}'")

    return search_keys, results_to_store


def refresh_from_cache():
    cached_search_keys = sad_redis.get_from_cache(key='sad_search_keys')
    if cached_search_keys:
        logger.debug(f"Found cached search keys: {cached_search_keys}")
        search_keys = cached_search_keys
    else:
        search_keys = []
    cached_results = sad_redis.get_from_cache(key='sad_results')
    if cached_results:
        logger.debug(f"Found cached results: {cached_results}")
        results_to_store = cached_results
    else:
        results_to_store = {}
    return results_to_store, search_keys


def horror_movies(*, search_keys: list, results_to_store: dict):
    """
    Get all movies with a genre of Horror which are unwatched, added to the library more than 90 days ago
    :return:
    """
    search_key = inspect.currentframe().f_code.co_name
    # empty the results_to_store dict for this search key
    if search_key in results_to_store:
        results_to_store[search_key] = []
    # Fetch movie library
    movies = get_movie_library()
    ninety_days_ago: datetime = datetime.now() - timedelta(days=90)
    size = 0
    count = 0
    # Unwatched horror movies which were added more than 90 days ago and have an audience rating less than 8
    for movie in movies.search(
            filters={'unwatched': True, 'genre': 'horror', 'addedAt<<': ninety_days_ago.strftime("%Y-%m-%d"),
                     'audienceRating<<': 7.5}):
        logger.info(
            f"Movie: '{movie.title}', File path: '{sanitize_file_path(movie.media[0].parts[0].file)}', "
            f"AddedAt: '{movie.addedAt}', Audience Rating: '{movie.audienceRating}'")
        size += movie.media[0].parts[0].size  # Increment size with the size of the movie
        count += 1
        store_movie(movie=movie, search_key=search_key, results_to_store=results_to_store)
    size_gb = size / (1024 ** 3)  # convert size to gigabytes
    logger.info(f"Total size of {search_key}: {size_gb}GB, {count} movies")
    if not search_key_in_cache(search_key=search_key, search_keys=search_keys):
        search_keys.append({'type': 'movie', 'key': search_key})
    return search_keys, results_to_store


def lowest_rated_movies(*, search_keys: list, results_to_store: dict):
    """
    Get all movies with a genre of Horror which are unwatched, added to the library more than 90 days ago
    :return:
    """
    search_key = inspect.currentframe().f_code.co_name
    # empty the results_to_store dict for this search key
    if search_key in results_to_store:
        results_to_store[search_key] = []
    # Fetch movie library
    movies = get_movie_library()
    size = 0
    count = 0
    # Lowest rating movies, under 3.5
    for movie in movies.search(limit=100, sort='audienceRating:asc', filters={'audienceRating<<': 3.5}):
        logger.info(f"Movie: '{movie.title}', File path: '{sanitize_file_path(movie.media[0].parts[0].file)}', "
                    f"AddedAt: '{movie.addedAt}', Audience Rating: '{movie.audienceRating}'")
        size += movie.media[0].parts[0].size  # Increment size with the size of the movie
        count += 1
        store_movie(movie=movie, search_key=search_key, results_to_store=results_to_store)
    size_gb = size / (1024 ** 3)  # convert size to gigabytes
    logger.info(f"Total size of {search_key}: {size_gb}GB, {count} movies")
    if not search_key_in_cache(search_key=search_key, search_keys=search_keys):
        search_keys.append({'type': 'movie', 'key': search_key})
    return search_keys, results_to_store


def tv_never_watched(*, search_keys: list, results_to_store: dict):
    """
    Get all movies with a genre of Horror which are unwatched, added to the library more than 90 days ago
    :return:
    """
    search_key = inspect.currentframe().f_code.co_name
    # empty the results_to_store dict for this search key
    if search_key in results_to_store:
        results_to_store[search_key] = []
    # Fetch movie library
    tv = get_tv_library()
    show: Show
    for show in tv.search(filters={'viewCount': 0, 'unviewedLeafCount>>': 1}):
        logger.info(
            f"Show title: {show.title}, view count: {show.viewCount}, season count: {show.childCount}, "
            f"episode count: {show.leafCount}, viewed episode count: {show.viewedLeafCount}")
        store_show(show=show, search_key=search_key, results_to_store=results_to_store)
    if not search_key_in_cache(search_key=search_key, search_keys=search_keys):
        search_keys.append({'type': 'show', 'key': search_key})
    return search_keys, results_to_store


def store_movie(*, movie: Movie, search_key: str, results_to_store: dict):
    tmdb_results = sad_tmdb.search_movie_by_query_and_year(query=movie.title, year=movie.year)
    # tmdb_results comes back with a dict of this format:
    # {'page': 1, 'results': [], 'total_pages': 1, 'total_results': 0}
    if tmdb_results['total_results'] > 0:
        movie_dict = {"file_path": sanitize_file_path(movie.media[0].parts[0].file), "id": movie.ratingKey,
                      "size_bytes": movie.media[0].parts[0].size, "tmdb_results": tmdb_results['results'][0],
                      "audience_rating": movie.audienceRating, "roles": [str(role) for role in movie.roles]}
        if search_key in results_to_store:
            results_to_store[search_key].append(movie_dict)
        else:
            results_to_store[search_key] = [movie_dict]
    else:
        logger.error(
            f"TMDB API did not return any results for '{movie.title} ({movie.year})' with a file name "
            f"of '{sanitize_file_path(movie.media[0].parts[0].file)}'")
    return results_to_store


def store_show(*, show: Show, search_key: str, results_to_store: dict):
    show_dict = {'id': show.ratingKey, 'title': show.title, 'view_count': show.viewCount,
                 'season_count': show.childCount,
                 'episode_count': show.leafCount, 'description': show.summary}
    if search_key in results_to_store:
        results_to_store[search_key].append(show_dict)
    else:
        results_to_store[search_key] = [show_dict]
    return results_to_store


def search_key_in_cache(*, search_key: str, search_keys: list):
    for key in search_keys:
        if key['key'] == search_key:
            return True
    return False


def sanitize_file_path(file_path):
    directory_to_strip = "/mnt/movies"
    relative_path = os.path.relpath(file_path, start=directory_to_strip)
    return relative_path


def get_movie_library() -> MovieSection:
    plex = get_plex_client()
    movies = plex.library.section('Movies')
    return movies


def get_tv_library() -> ShowSection:
    plex = get_plex_client()
    tv = plex.library.section('TV Shows')
    return tv


def get_plex_client():
    baseurl = os.getenv("PLEX_URL")
    token = os.getenv("PLEX_TOKEN")
    plex = PlexServer(baseurl, token)
    return plex


def send_all_refresh():
    # Create a Pulsar client
    client = pulsar.Client(f'pulsar://{os.environ["PULSAR_SERVER"]}')

    # Create a producer on the topic 'plex-search'
    producer = client.create_producer(os.environ['PULSAR_TOPIC'])

    # Create a message
    message = ['all']
    message_json = json.dumps(message).encode('utf-8')

    # Send the message
    producer.send(message_json)

    # Close the producer and client to free up resources
    producer.close()
    client.close()


if __name__ == '__main__':
    # Argument parser setup
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true', help='Call send_all_refresh instead of main')
    args = parser.parse_args()

    # Logging setup
    kwargs = {}
    formatter = gogo.formatters.structured_formatter
    logger = gogo.Gogo('sad.search', low_formatter=formatter, low_level=os.getenv("SAD_LOG_LEVEL", "INFO")).get_logger(
        **kwargs)

    # Call main or send_all_refresh based on --refresh argument
    if args.refresh:
        send_all_refresh()
    else:
        main()
