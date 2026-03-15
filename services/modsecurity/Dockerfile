FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates libapache2-mod-security2 modsecurity-crs apache2 && rm -rf /var/lib/apt/lists/*
CMD ["/bin/sh", "-lc", "apachectl -D FOREGROUND"]
