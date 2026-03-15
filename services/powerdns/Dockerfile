FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates pdns-server pdns-backend-sqlite3 sqlite3 && rm -rf /var/lib/apt/lists/*
COPY config/pdns.conf /etc/powerdns/pdns.conf
CMD ["/bin/sh", "-lc", "mkdir -p /var/lib/powerdns && sqlite3 /var/lib/powerdns/pdns.sqlite3 'create table if not exists domains (id integer primary key, name varchar(255), master varchar(128), last_check integer, type varchar(6), notified_serial integer, account varchar(40), options varchar(65535), catalog varchar(255));' && pdns_server --daemon=no --guardian=no --control-console=no"]
