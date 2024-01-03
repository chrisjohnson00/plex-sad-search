

```shell
docker run -it --rm -v ${PWD}:/app -w /app python:3.12-slim bash
apt update && apt install -y git
pip install --upgrade pip
pip install --upgrade plexapi 'sad_libraries@git+https://github.com/chrisjohnson00/plex-sad-libraries.git@initial-version'
pip freeze > requirements.txt
```

Run redis locally with

```shell
docker run --rm --name redis -p 6379:6379 -d redis
```
