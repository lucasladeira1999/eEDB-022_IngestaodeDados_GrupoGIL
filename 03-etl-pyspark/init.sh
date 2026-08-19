#!/bin/bash
# Executado automaticamente pelo Postgres na primeira inicializacao.
# Para rodar de novo depois de editar: docker compose down -v && docker compose up -d
set -e

# Usuario usado pelo job Spark para ler e gravar as camadas do pipeline.
# Nao usamos o superusuario no pipeline. A senha vem do .env, via ETL_PASSWORD.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE USER etl WITH PASSWORD '${ETL_PASSWORD}';
	CREATE SCHEMA "${RAW_SCHEMA}" AUTHORIZATION etl;
	CREATE SCHEMA "${TRUSTED_SCHEMA}" AUTHORIZATION etl;
	CREATE SCHEMA "${DELIVERY_SCHEMA}" AUTHORIZATION etl;
EOSQL
