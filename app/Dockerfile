FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg vim \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN echo "alias ll='ls -alF'" >> /etc/bash.bashrc

ENTRYPOINT ["python", "/app/app/main.py", "run", "--accounts", "/app/data/accounts.txt"]
