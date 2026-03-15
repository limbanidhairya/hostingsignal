FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates postfix && rm -rf /var/lib/apt/lists/*
COPY config/main.cf /etc/postfix/main.cf
CMD ["/bin/sh", "-lc", "postfix start-fg"]
