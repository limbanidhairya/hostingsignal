FROM python:3.12-slim

WORKDIR /opt/hostingsignal-license

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Create log directory
RUN mkdir -p /opt/hostingsignal-license/logs

# Non-root user
RUN useradd -r -s /bin/false hslic && chown -R hslic:hslic /opt/hostingsignal-license
USER hslic

EXPOSE 8443

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8443/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8443", "--workers", "4"]
