FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates opendkim opendkim-tools && rm -rf /var/lib/apt/lists/*
CMD ["/bin/sh", "-lc", "opendkim -f"]
