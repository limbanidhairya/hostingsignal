FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates firewalld dbus && rm -rf /var/lib/apt/lists/*
CMD ["/bin/sh", "-lc", "mkdir -p /run/dbus && dbus-daemon --system && /usr/sbin/firewalld --nofork --nopid"]
