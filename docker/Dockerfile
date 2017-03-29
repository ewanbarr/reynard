FROM ubuntu:16.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    git \
    gcc \
    openssl \
    ca-certificates \
    python2.7 \
    python2.7-dev \
    python-setuptools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists && \

# Python packages
    easy_install pip && \
    pip install \
    psutil \
    lxml \
    jinja2 \
    cmd2 && \
    pip install -e git://github.com/docker/docker-py.git@2.2.0-release#egg=docker-py && \

# KATCP-v0.6.1
    mkdir soft && \
    cd soft && \
    git clone https://github.com/ska-sa/katcp-python.git && \
    cd katcp-python && \
    git checkout tags/v0.6.1 && \
    python setup.py install

ENV ARSE 22

# Reynard-dev
RUN cd soft && \
    git clone https://github.com/ewanbarr/reynard.git && \
    cd reynard && \
    git checkout json_effcam && \
    python setup.py install

ENV PATH ${PATH}:/usr/local/bin
