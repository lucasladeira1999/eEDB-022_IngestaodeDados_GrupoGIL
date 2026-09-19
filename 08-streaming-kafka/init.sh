#!/bin/bash
# Executado pelo Postgres na primeira inicialização.
# Para rodar de novo: docker compose down -v && docker compose up -d
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE USER etl WITH PASSWORD '${ETL_PASSWORD}';
	CREATE SCHEMA "${CADASTRO_SCHEMA}" AUTHORIZATION etl;
EOSQL
