import inspect
import os
from datetime import datetime, timedelta
import logging

from plexapi.server import PlexServer
from plexapi.video import Movie
from redis_lib import save_to_cache


def main():
    search_keys = []
    results_to_store = {}
    search_keys, results_to_store = horror_movies(search_keys=search_keys, results_to_store=results_to_store)
    save_to_cache(key='sad_search_keys', data=search_keys)
    save_to_cache(key='sad_results', data=results_to_store)


def horror_movies(*, search_keys, results_to_store):
    """
    Get all movies with a genre of Horror which are unwatched, added to the library more than 90 days ago
    :return:
    """
    # Fetch movie library
    movies = get_movie_library()
    ninety_days_ago = datetime.now() - timedelta(days=90)
    # Filter movies for genre "Horror" and check if they're unwatched
    horror_movie_results = [
        movie
        for movie in movies.search(unwatched=True)
        if any(genre.tag.lower() == "horror" for genre in movie.genres)
    ]
    size = 0
    count = 0
    # Print unwatched horror movies and calculate their total size
    for movie in horror_movie_results:
        # exclude movies added in the last 90 days
        if movie.addedAt < ninety_days_ago:
            logger.debug(
                f"Movie: '{movie.title}', File path: '{sanitize_file_path(movie.media[0].parts[0].file)}', "
                f"Rating Key: '{movie.ratingKey}'")
            size += movie.media[0].parts[0].size  # Increment size with the size of the movie
            count += 1
            store_movie(movie=movie, search_key=inspect.currentframe().f_code.co_name,
                        results_to_store=results_to_store)
    size_gb = size / (1024 ** 3)  # convert size to gigabytes
    logger.info(f"Total size of {inspect.currentframe().f_code.co_name}: {size_gb}GB, {count} movies")
    search_keys.append(inspect.currentframe().f_code.co_name)
    return search_keys, results_to_store


def store_movie(*, movie: Movie, search_key: str, results_to_store: dict):
    movie_dict = {"title": movie.title, "file_path": sanitize_file_path(movie.media[0].parts[0].file),
                  "id": movie.ratingKey, "size_bytes": movie.media[0].parts[0].size}
    if search_key in results_to_store:
        results_to_store[search_key].append(movie_dict)
    else:
        results_to_store[search_key] = [movie_dict]
    return results_to_store


def sanitize_file_path(file_path):
    directory_to_strip = "/mnt/movies"
    relative_path = os.path.relpath(file_path, start=directory_to_strip)
    return relative_path


def get_movie_library():
    plex = get_plex_client()
    movies = plex.library.section('Movies')
    return movies


def get_plex_client():
    baseurl = os.getenv("PLEX_URL")
    token = os.getenv("PLEX_TOKEN")
    plex = PlexServer(baseurl, token)
    return plex


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    logger = logging.getLogger("sad")
    logger.setLevel(logging.DEBUG)
    logger.handlers = []
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    main()
