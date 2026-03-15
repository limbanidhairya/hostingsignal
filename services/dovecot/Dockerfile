FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates dovecot-core dovecot-imapd dovecot-pop3d && rm -rf /var/lib/apt/lists/*
COPY config/dovecot.conf /etc/dovecot/dovecot.conf
COPY config/users /etc/dovecot/users
CMD ["/bin/sh", "-lc", "dovecot -F"]
