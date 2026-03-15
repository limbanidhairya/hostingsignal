FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates cron && rm -rf /var/lib/apt/lists/*
COPY config/crontab /etc/cron.d/hostingsignal
CMD ["/bin/sh", "-lc", "chmod 0644 /etc/cron.d/hostingsignal && crontab /etc/cron.d/hostingsignal && cron -f"]
