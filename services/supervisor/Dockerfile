FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates supervisor && rm -rf /var/lib/apt/lists/*
COPY config/supervisord.conf /etc/supervisor/supervisord.conf
CMD ["/bin/sh", "-lc", "/usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf"]
