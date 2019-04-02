FROM python:3.6-stretch
MAINTAINER Nick Bolten <nbolten@gmail.com>

RUN apt-get update && \
    apt-get install -y \
      fiona \
      libsqlite3-mod-spatialite \
      libspatialindex-dev \
      gdal-bin \
      osmosis

RUN pip3 install --upgrade pip

RUN mkdir -p /work
WORKDIR /work

COPY ./requirements.txt /work

RUN pip3 install -r requirements.txt
