FROM python:3.8.5-buster
MAINTAINER Nick Bolten <nbolten@gmail.com>

RUN apt-get update && \
    apt-get install -y \
      fiona \
      libsqlite3-mod-spatialite \
      libspatialindex-dev \
      gdal-bin \
      osmosis

RUN pip3 install --upgrade pip

RUN pip3 install poetry

RUN mkdir -p /work
WORKDIR /work

COPY ./pyproject.toml /work
COPY ./poetry.lock /work

RUN poetry install
