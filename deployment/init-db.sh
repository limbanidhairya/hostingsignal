#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE hostingsignal_licenses'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hostingsignal_licenses')\gexec

    SELECT 'CREATE DATABASE hostingsignal_devpanel'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hostingsignal_devpanel')\gexec
EOSQL
