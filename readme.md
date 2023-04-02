# Readme

## Create virtual environment

Create a virtual environment, activate it and install dependent modules by using the followings script:

```shell
python3 -m virtualenv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run app for debugging

Use Flask directive after indicating the file exposing the `app` instance:

```shell
export FLASK_APP=src/launch.py
export FLASK_DEBUG=1

flask run 
# flask run --no-debugger --no-reload
```

## Run using docker / gunicorn

```shell
docker build -t IMAGE_NAME .
docker run -p 8080:80 IMAGE_NAME
# docker run -p 8080:80 -v $(pwd)/DATA_PATH:/app/instance IMAGE_NAME
```

## For Docker Hub

Build using:

```shell
docker buildx build \
    --push \
    --platform linux/arm64/v8,linux/arm/v7,linux/amd64 \
    --tag muxelmann/billing \
    .
```

Run using:

```shell
docker run \
    -v $(pwd)/<HOST_DATA_PATH>:/app/instance:rw \
    -e FLASK_SECRET=<SOME_SECRET> \
    -p 8080:80 \
    muxelmann/billing
```