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

COPY ./datahelpers /work/datahelpers

RUN pip install /work/datahelpers
# RUN poetry install

RUN \
  sed -i '/import pandas._libs.testing as _testing/i np.bool = np.bool_' /usr/local/lib/python3.8/site-packages/pandas/util/testing.py && \
  sed -i '/import numpy as np/a np.object = np.object_' /usr/local/lib/python3.8/site-packages/pandas/core/internals/construction.py