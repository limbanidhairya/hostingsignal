FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates pure-ftpd && rm -rf /var/lib/apt/lists/*
COPY config/ChrootEveryone /etc/pure-ftpd/conf/ChrootEveryone
CMD ["/bin/sh", "-lc", "/usr/sbin/pure-ftpd -A -B -j -E -H"]
