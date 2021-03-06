FROM python:alpine3.8

ENV PYTHONUNBUFFERED=1

RUN apk --update add make vim

RUN apk --update add gcc musl-dev gmp-dev tmux

RUN mkdir -p /usr/src/HoneyBadgerMPC
WORKDIR /usr/src/HoneyBadgerMPC

RUN pip install --upgrade pip

COPY . /usr/src/HoneyBadgerMPC

RUN pip install --no-cache-dir -e .[dev]
