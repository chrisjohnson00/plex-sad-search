

```shell
docker run -it --rm -v ${PWD}:/app -w /app python:3.12-slim bash
pip install --upgrade pip
pip install --upgrade plexapi redis
pip freeze > requirements.txt
```

Run redis locally with

```shell
docker run --rm --name redis -p 6379:6379 -d redis
```
