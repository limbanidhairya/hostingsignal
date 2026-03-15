FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates spamassassin && rm -rf /var/lib/apt/lists/*
CMD ["/bin/sh", "-lc", "spamd -d -c -m 5"]
