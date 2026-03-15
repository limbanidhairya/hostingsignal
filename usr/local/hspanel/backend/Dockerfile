FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies:
#  - mariadb-client     → mysql CLI for DatabaseManager to talk to MariaDB
#  - certbot            → SSL certificate management
#  - pure-ftpd          → FTP user management (pure-pw binary)
#  - useradd (shadow)   → create the hspanel system user for FTP
RUN apt-get update && apt-get install -y --no-install-recommends \
        mariadb-client \
        certbot \
        pure-ftpd \
        passwd \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --no-create-home --shell /usr/sbin/nologin hspanel \
    && mkdir -p /etc/modsecurity /etc/pure-ftpd /var/hspanel/queue /var/hspanel/users \
    && echo 'SecRuleEngine DetectionOnly' > /etc/modsecurity/modsecurity.conf

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 2083

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "2083"]
