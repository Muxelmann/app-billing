# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11.2-slim

WORKDIR /app

EXPOSE 80

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN \
    apt-get -y update && \
    apt-get -y upgrade && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install pip requirements
COPY requirements.txt .
RUN \
    python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

COPY ./src /app

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["gunicorn", "--conf", "gunicorn_conf.py", "--bind", "0.0.0.0:80", "launch:app"]
