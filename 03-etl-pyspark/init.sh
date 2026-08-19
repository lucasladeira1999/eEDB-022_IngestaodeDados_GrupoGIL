#!/bin/bash
# Executado automaticamente pelo Postgres na primeira inicializacao.
# Para rodar de novo depois de editar: docker compose down -v && docker compose up -d
set -e

# Usuario usado pelo job Spark para ler e gravar a camada raw.
# Nao usamos o superusuario no pipeline. A senha vem do .env, via ETL_PASSWORD.
# So a camada raw fica no Postgres; trusted e delivery ficam em Parquet.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE USER etl WITH PASSWORD '${ETL_PASSWORD}';
	CREATE SCHEMA raw AUTHORIZATION etl;
EOSQL