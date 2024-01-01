import inspect
import os
from datetime import datetime, timedelta

from plexapi.server import PlexServer
from plexapi.video import Movie


def main():
    horror_movies()


def horror_movies():
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
    # Print unwatched horror movies and calculate their total size
    for movie in horror_movie_results:
        # exclude movies added in the last 90 days
        if movie.addedAt < ninety_days_ago:
            print(
                f"Movie: {movie.title}, File path: {sanitize_file_path(movie.media[0].parts[0].file)}, "
                "Rating Key: {movie.ratingKey}")
            size += movie.media[0].parts[0].size  # Increment size with the size of the movie
            store_movie(movie=movie, search_key=inspect.currentframe().f_code.co_name)
    size_gb = size / (1024 ** 3)  # convert size to gigabytes
    print(f"Total size of horror movies: {size_gb}GB")


def store_movie(*, movie: Movie, search_key: str):
    movie_dict = {"title": movie.title, "file_path": sanitize_file_path(movie.media[0].parts[0].file),
                  "id": movie.ratingKey, "size_bytes": movie.media[0].parts[0].size, "search_key": search_key}
    eligible_movies.append(movie_dict)


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
    eligible_movies = []
    main()
