FROM ubuntu:xenial
MAINTAINER Nick Bolten <nbolten@gmail.com>

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

#
# Install dependencies
#

RUN apt-get update && \
    apt-get install -y \
      gdal-bin \
      libgdal-dev \
      libspatialindex-dev \
      python3-dev \
      python3-pip \
      python3-gdal \
      unzip

#
# Update pip to make wheels a thing
#
RUN pip3 install --upgrade pip

#
# Install the cli tool
#

WORKDIR /sourcedata
# Install dependencies first so rebuilds go faster if code changes
COPY ./data_manager/requirements.txt /sourcedata/requirements.txt
# Install numpy first because other packages want it and pip is dumb
RUN pip3 install --ignore-installed `grep numpy requirements.txt`
RUN pip3 install --ignore-installed -r requirements.txt
# Install whole package
COPY ./data_manager /sourcedata/data_manager
RUN pip3 install /sourcedata/data_manager

#
# Set up entrypoint so that container acts like cli app
#

ENTRYPOINT ["data_manager"]
