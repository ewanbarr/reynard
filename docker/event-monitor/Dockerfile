FROM ubuntu:16.04

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends docker.io && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

CMD ["docker","events"]
