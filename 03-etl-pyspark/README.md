# 03-etl-pyspark

Requisito: ingerir as três bases em um banco relacional open source e gerar uma tabela final tratada e unida, com o tratamento feito em **PySpark**.

Pipeline: Postgres (raw) → Spark (trusted em Parquet local) → Spark (delivery em Parquet local), orquestrado por `src/main.py` em 3 etapas sequenciais (`to_raw` → `to_trusted` → `to_delivery`).

## Como rodar

Pré-requisito: Docker Desktop rodando.

```powershell
cd 03-etl-pyspark
Copy-Item .env.example .env
docker compose up -d postgres pgadmin
```

O Postgres sobe com o schema `raw` e o usuário `etl` já criados pelo `init.sh`.

Rodar o job (ele está no profile `job`, por isso não sobe junto com `up -d` normal):

```powershell
docker compose --profile job up --build spark-job
```

Isso builda a imagem e roda `to_raw` → `to_trusted` → `to_delivery` em sequência: grava a camada `raw` no Postgres e as camadas `trusted`/`delivery` como Parquet em `./src/data` (montado no container em `/src/data`, então os arquivos ficam acessíveis também no host).

✅ *Deu certo se:* o comando termina sem erro e aparecem pastas dentro de `src/data/trusted/` e `src/data/delivery/`.

## Testar o select na raw

A raw fica no Postgres, então dá pra consultar direto via `psql`:

```powershell
docker compose exec postgres psql -U postgres -d postgres -c "SELECT * FROM raw.bancos LIMIT 5;"
docker compose exec postgres psql -U postgres -d postgres -c "SELECT count(*) FROM raw.reclamacoes;"
docker compose exec postgres psql -U postgres -d postgres -c "SELECT count(*) FROM raw.empregados;"
```

Ou pelo pgAdmin em **http://localhost:5050** (credenciais no `.env`), conectando em host `postgres`.

## Testar trusted/delivery com Spark

Trusted e delivery não vão para o Postgres — ficam como Parquet, então a forma mais simples de inspecionar é abrindo um shell do PySpark dentro do mesmo container do job:

```powershell
docker compose run --rm --entrypoint pyspark spark-job
```

Dentro do shell (`spark` já vem pronto):

```python
bancos = spark.read.parquet("/src/data/trusted/bancos")
bancos.show(5)

banco_final = spark.read.parquet("/src/data/delivery/banco_final")
banco_final.select("nome_norm", "qtd_total_reclamacoes", "nota_geral").show(5)
```

## Comandos do dia a dia

```powershell
docker compose ps                          # o que está de pé
docker compose logs -f spark-job           # ver erro do job
docker compose down                        # remover containers (mantém dados)
docker compose down -v                     # apagar tudo, inclusive o Postgres
Remove-Item -Recurse -Force src\data       # apagar os Parquet locais (trusted/delivery)
```