#!/bin/bash
# Executado automaticamente pelo Postgres na primeira inicialização.
# Para rodar de novo depois de editar: docker compose down -v && docker compose up -d
set -e

# Usuário usado pelo Apache Hop (não usamos o superusuário no pipeline).
# A senha vem do .env, via ETL_PASSWORD.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
	CREATE USER etl WITH PASSWORD '${ETL_PASSWORD}';
	CREATE DATABASE glassdoor OWNER etl;
EOSQL

# Camadas: raw = fiel ao arquivo, trusted = limpo e tipado por fonte,
# delivery = modelo final entregue (join das três fontes)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname glassdoor <<-EOSQL
	CREATE SCHEMA raw      AUTHORIZATION etl;
	CREATE SCHEMA trusted  AUTHORIZATION etl;
	CREATE SCHEMA delivery AUTHORIZATION etl;
EOSQL