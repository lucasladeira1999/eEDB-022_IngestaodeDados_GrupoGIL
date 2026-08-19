#!/bin/bash
# Executado automaticamente pelo Postgres na primeira inicialização.
# Para rodar de novo depois de editar: docker compose down -v && docker compose up -d
set -e

# O Postgres já cria o banco $POSTGRES_DB sozinho a partir da env var,
# então só precisamos criar os schemas das camadas.
# raw = fiel ao arquivo, trusted = Parquet local, delivery = modelo final (tabela + Parquet)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE SCHEMA "${RAW_SCHEMA}";
	CREATE SCHEMA "${TRUSTED_SCHEMA}";
	CREATE SCHEMA "${DELIVERY_SCHEMA}";
EOSQL
