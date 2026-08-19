# 03 - ETL com PySpark

Implementação do requisito de ingerir as três bases em um banco relacional open source e gerar uma tabela final tratada e unida, com o processamento feito em **PySpark**.

## Pipeline

O `src/main.py` executa três etapas sequenciais:

| Etapa | Entrada | Saída |
|---|---|---|
| `to_raw` | Arquivos em `../dados` | Tabelas no schema `raw` do Postgres |
| `to_trusted` | Tabelas `raw` | Parquets em `data/trusted/` |
| `to_delivery` | Parquets `trusted` | Parquet em `data/delivery/` e tabela final no schema `delivery` do Postgres |

Na entrega, os bancos e empregados são deduplicados priorizando `cnpj_norm`. Quando o CNPJ não está disponível, o nome normalizado é usado. As reclamações são agregadas por CNPJ e por nome, com fuzzy match como fallback. Os limiares desse fuzzy match podem ser ajustados pelo `.env`.

## Como rodar

Pré-requisito: Docker Desktop em execução.

No PowerShell:

```powershell
cd 03-etl-pyspark
Copy-Item .env.example .env
```

O `.env.example` já inclui `ETL_PASSWORD=etl`; altere esse valor se necessário. Depois, suba o Postgres e o pgAdmin:

```powershell
docker compose up -d postgres pgadmin
```

O `init.sh` cria o usuário `etl` e os schemas `raw`, `trusted` e `delivery` na primeira inicialização do volume do Postgres. Os nomes podem ser alterados pelas variáveis correspondentes no `.env`.

Execute o job, que está no profile `job`:

```powershell
docker compose --profile job up --build spark-job
```

Os Parquets ficam disponíveis no host em `data/trusted/` e `data/delivery/`. O diretório é montado no container em `/app/data`.

Após a execução, confirme se os diretórios `data/trusted/` e `data/delivery/` foram criados e se o job terminou sem erro.

## Configuração

| Variável | Padrão | Uso |
|---|---|---|
| `RAW_SCHEMA` | `raw` | Schema PostgreSQL da camada bruta |
| `TRUSTED_SCHEMA` | `trusted` | Nome da pasta da camada trusted |
| `DELIVERY_SCHEMA` | `delivery` | Schema PostgreSQL e nome da pasta da camada delivery |
| `DELIVERY_TABLE` | `bancos_indicadores` | Nome do dataset Parquet e da tabela final |
| `FUZZY_SCORE_CUTOFF_RECLAMACOES` | `80` | Score mínimo para casar reclamações por nome |
| `FUZZY_SCORE_CUTOFF_EMPREGADOS` | `90` | Score mínimo para casar avaliações por nome |

As demais variáveis de conexão, pgAdmin e senha do usuário `etl` também ficam no `.env`.

## Consultar a camada raw

Com os valores padrão do `.env.example`, as tabelas da camada bruta podem ser consultadas diretamente no Postgres:

```powershell
docker compose exec postgres psql -U postgres -d postgres -c "SELECT * FROM raw.bancos LIMIT 5;"
docker compose exec postgres psql -U postgres -d postgres -c "SELECT count(*) FROM raw.reclamacoes;"
docker compose exec postgres psql -U postgres -d postgres -c "SELECT count(*) FROM raw.empregados;"
```

Se `POSTGRES_USER`, `POSTGRES_DB` ou `RAW_SCHEMA` forem alterados, substitua esses valores nos comandos.

Também é possível usar o pgAdmin em **http://localhost:5050**, com as credenciais do `.env` e o host `postgres`.

## Inspecionar trusted e delivery

Como essas camadas são Parquet, abra um shell do PySpark no container do job:

```powershell
docker compose run --rm --entrypoint pyspark spark-job
```

Dentro do shell (`spark` já vem disponível):

```python
bancos = spark.read.parquet("/app/data/trusted/bancos")
bancos.show(5)

banco_final = spark.read.parquet("/app/data/delivery/bancos_indicadores")
banco_final.select("nome_norm", "qtd_total_reclamacoes", "nota_geral").show(5)
```

Os exemplos usam os valores padrão `trusted`, `delivery` e `bancos_indicadores`. Se esses nomes forem alterados no `.env`, use os diretórios correspondentes.

## Comandos do dia a dia

```powershell
docker compose ps                          # serviços em execução
docker compose logs -f spark-job           # logs do job
docker compose down                        # remove containers e mantém os dados
docker compose down -v                     # remove containers e o volume do Postgres
Remove-Item -Recurse -Force data           # remove os Parquets locais
```

Além do Parquet local, o job persiste a tabela final em `${DELIVERY_SCHEMA}.${DELIVERY_TABLE}` no Postgres.
