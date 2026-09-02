# Atividade 05 — Orquestração, Qualidade e Metadados

Orquestra o pipeline da [Atividade 4](../04-sql-dbt/) (ingestão Python + transformação
dbt/DuckDB) com **Airflow**, adiciona checks de qualidade com **Soda Core** e publica
metadados/lineage no **OpenMetadata**.

```
ingest_raw → dbt_seed → dbt_run → dbt_test → dbt_docs_generate → soda_scan
                                                                        │
                                              openmetadata_create_service → openmetadata_ingest_dbt
```

Nenhum arquivo do projeto dbt é duplicado aqui: o Airflow monta `../04-sql-dbt` como
volume e roda os mesmos `models/`, `seeds/` e `scripts/ingest_raw.py` de lá. A única
coisa nova é a saída (`data/database.duckdb` e os parquets), que fica isolada dentro
desta pasta para não sujar o estado da atividade 4.

## Por que essas ferramentas

- **Airflow (LocalExecutor)**: mais simples que Celery/K8s para rodar local, e o
  suficiente para uma DAG sequencial.
- **Soda Core**, não Deequ: `soda-core-duckdb` é uma lib Python que conversa direto
  com o arquivo `.duckdb`; Deequ exigiria uma JVM com versão do Spark casada, e esta
  atividade usa a base da Atividade 4 (dbt/DuckDB), sem Spark. Os checks aqui são
  complementares aos `dbt test`: focam em volume e duplicidade, não em integridade
  estrutural (isso já é coberto pelos testes do dbt).
- **OpenMetadata**, não DataHub/Amundsen: tem um workflow de ingestão de dbt pronto
  (lê `manifest.json`/`catalog.json`/`run_results.json` e monta lineage + descrições +
  resultado dos testes) sem precisar escrever um conector do zero.

## Duas stacks de Docker Compose

São duas pilhas separadas, porque o OpenMetadata sozinho já é um stack completo
(Postgres + Elasticsearch + servidor):

| Arquivo | Contém | Porta principal |
|---|---|---|
| `docker-compose.yml` | Postgres do Airflow + webserver + scheduler | `8081` (UI do Airflow) |
| `openmetadata/docker-compose-openmetadata.yml` | Postgres + Elasticsearch + servidor do OpenMetadata | `8585` (UI do OpenMetadata) |

`openmetadata/docker-compose-openmetadata.yml` é o arquivo oficial do projeto
(`docker-compose-postgres.yml` da release do OpenMetadata), só com o Airflow interno
dele removido — aqui a orquestração já é feita pelo nosso próprio Airflow, então a
ingestão de metadados roda como uma task normal da DAG (`metadata ingest -c ...`), sem
precisar de um segundo Airflow.

## Como rodar

**Pré-requisito:** Docker Desktop rodando, com pelo menos 6-8 GB de RAM livres (o
Elasticsearch do OpenMetadata sozinho já pede ~1 GB de heap).

### 1. Subir o OpenMetadata

```powershell
cd 05-orquestracao
Copy-Item .env.example .env
docker compose -f openmetadata/docker-compose-openmetadata.yml up -d
```

Primeira subida demora alguns minutos (migração do banco). Confirme em
**http://localhost:8585** (login `admin@open-metadata.org` / `admin`).

### 2. Subir o Airflow

```powershell
docker compose up -d --build
```

A primeira subida builda a imagem custom (dbt + Soda + `openmetadata-ingestion`
instalados por cima do `apache/airflow`) e roda `airflow-init` uma vez. Confirme em
**http://localhost:8081** (login `admin` / `admin`).

### 3. Rodar a DAG

Na UI do Airflow, ative e dispare a DAG `atividade4_pipeline`. Ela roda uma vez do
início ao fim (sem agendamento automático — é um job batch, não uma atividade contínua).

### 4. Conferir

```powershell
docker compose exec airflow-scheduler bash -c "cd /opt/dbt_project && duckdb data/database.duckdb -c 'select count(*) from delivery.bancos_indicadores;'"
```

Ou pela UI do OpenMetadata: procure o serviço `duckdb_atividade4` e veja as tabelas
`trusted.tr_bancos`, `trusted.tr_reclamacoes`, `trusted.tr_empregados` e
`delivery.bancos_indicadores`, com lineage e o resultado dos testes do dbt.

## Pontos de atenção conhecidos

- **Permissão de escrita em `../04-sql-dbt` e `./data`**: esses diretórios são criados
  pelo usuário do host (fora do container), mas as tasks da DAG rodam como o usuário
  `airflow` (uid `50000`) dentro dos containers. Sem ajuste, escritas no DuckDB
  (`data/database.duckdb`) e nos parquets gerados pelo dbt (`data/trusted/`,
  `data/delivery/`) falham com `Permission denied`. Sempre que esses diretórios forem
  recriados do zero (clone novo, `docker volume prune`, `rm -rf data/` etc.), rode:

  ```bash
  chmod o+rwX ../04-sql-dbt
  chmod -R o+rwX ./data
  ```

- **`requirements-airflow.txt` instalado sem `--constraint`**: `dbt-duckdb`,
  `soda-core-duckdb` e `openmetadata-ingestion` têm pins próprios de `pydantic`/
  `sqlalchemy` que podem conflitar com as constraints do Airflow. Se o build da imagem
  falhar no `pip install`, é sinal de que uma dessas libs mudou uma versão major —
  ajuste os pins em `requirements-airflow.txt`.
- **`openmetadata/create_service.py`**: os módulos gerados do SDK Python do
  OpenMetadata (`metadata.generated.schema...`) mudam de caminho entre versões. Se essa
  task falhar por `ImportError`, confirme o caminho certo para a versão instalada com:
  `python -c "from metadata.generated.schema.entity.services.databaseService import DatabaseServiceType; print(list(DatabaseServiceType))"`
  dentro do container do Airflow.
- **DuckDB não tem conector nativo no OpenMetadata**: por isso o serviço é registrado
  como `CustomDatabase` (metadados de registro, sem conexão ao vivo) e todo o
  preenchimento de tabelas/colunas/lineage vem só dos artefatos do dbt
  (`ingest_dbt.yaml`). Isso é suficiente para o requisito da atividade (metadados do
  processo), mas não dá profiling de dados ao vivo — quem cobre isso é o Soda.

## Estrutura

```
05-orquestracao/
├── docker-compose.yml              stack do Airflow (LocalExecutor)
├── Dockerfile                      imagem do Airflow + dbt + Soda + openmetadata-ingestion
├── requirements-airflow.txt
├── .env.example
├── dags/
│   └── atividade4_pipeline.py      a DAG
├── soda/
│   ├── configuration.yml           conexao com o duckdb da atividade 4
│   └── checks.yml                  checks de volume/duplicidade
├── openmetadata/
│   ├── docker-compose-openmetadata.yml   stack oficial do OpenMetadata (sem o Airflow interno)
│   ├── create_service.py           garante o Database Service antes da ingestao
│   └── ingest_dbt.yaml             workflow de ingestao do dbt no OpenMetadata
└── data/                           saida do dbt desta atividade (duckdb + parquets)
```
