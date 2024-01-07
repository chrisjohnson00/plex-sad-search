# Plex Search And Destroy - Search

## Development

`pulsar-client` does not support Python > 3.10

```shell
docker run -it --rm -v ${PWD}:/app -w /app python:3.10-slim bash
apt update && apt install -y git
pip install --upgrade pip
pip install --upgrade plexapi pulsar-client pygogo 'sad_libraries@git+https://github.com/chrisjohnson00/plex-sad-libraries.git@v0.1.3'
pip freeze > requirements.txt
```

Run redis locally with

```shell
docker run --rm --name redis -p 6379:6379 -d redis
```

# Pulsar Messages

This application will process messages sent to the configured topic, it is expected that the message follows this JSON
format:

```json
[
  "value1",
  "value2"
]
```

Each value is the name of a method in this application to be called. If `all` is present in the list, all methods will
be called. Invalid values will be skipped.

# Execution modes

If you pass the `--refresh` argument, the application will connect to the Pulsar topic and send a `all` message. This is
intended to be used by a `cronjob` execution to periodically refresh the data.
