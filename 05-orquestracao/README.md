# Atividade 05 - Orquestração, Qualidade e Metadados

Orquestra o pipeline da [Atividade 4](../04-sql-dbt/) (ingestão Python + transformação dbt/DuckDB) com **Airflow**, adiciona checks de qualidade com **Soda Core** e publica metadados/lineage no **OpenMetadata**.

ingest_raw → dbt_seed → dbt_run → dbt_test → dbt_docs_generate → soda_scan
│
openmetadata_create_service → openmetadata_ingest_dbt


Nenhum arquivo do projeto dbt é duplicado aqui: o Airflow monta `../04-sql-dbt` como volume e roda os mesmos `models/`, `seeds/` e `scripts/ingest_raw.py` de lá. A única coisa nova é a saída (`data/database.duckdb` e os parquets), que fica isolada dentro desta pasta para não sujar o estado da atividade 4.

## Por que essas ferramentas

- **Airflow (LocalExecutor)**: mais simples que Celery/K8s para rodar local, e suficiente para uma DAG sequencial.
- **Soda Core**, não Deequ: `soda-core-duckdb` é uma lib Python que conversa direto com o arquivo `.duckdb`. Deequ exigiria uma JVM com versão do Spark casada, e esta atividade usa a base da Atividade 4 (dbt/DuckDB), sem Spark. Os checks aqui são complementares aos `dbt test`: focam em volume e duplicidade, não em integridade estrutural (isso já é coberto pelos testes do dbt).
- **OpenMetadata**, não DataHub/Amundsen: tem um workflow de ingestão de dbt pronto (lê `manifest.json`/`catalog.json`/`run_results.json` e monta lineage, descrições e resultado dos testes) sem precisar escrever um conector do zero.

## Venvs isolados por ferramenta

O `Dockerfile` cria um virtualenv separado para cada ferramenta (`.venv-dbt`, `.venv-soda`, `.venv-openmetadata`), cada um instalado a partir do seu próprio arquivo de requirements (`requirements-dbt.txt`, `requirements-soda.txt`, `requirements-openmetadata.txt`). O motivo é que `dbt-duckdb`, `soda-core-duckdb` e `openmetadata-ingestion` têm pins próprios de `pydantic` e `sqlalchemy` que conflitam entre si e com as constraints do Airflow se instalados no mesmo ambiente. A DAG (`dags/atividade4_pipeline.py`) chama o binário certo de cada venv em cada task, então não existe um `requirements-airflow.txt` único.

## Duas stacks de Docker Compose

São duas pilhas separadas, porque o OpenMetadata sozinho já é um stack completo (Postgres + Elasticsearch + servidor):

| Arquivo | Contém | Porta principal |
|---|---|---|
| `docker-compose.yml` | Postgres do Airflow + webserver + scheduler | `8081` (UI do Airflow) |
| `openmetadata/docker-compose-openmetadata.yml` | Postgres + Elasticsearch + servidor do OpenMetadata | `8585` (UI do OpenMetadata) |

`openmetadata/docker-compose-openmetadata.yml` é o arquivo oficial do projeto (`docker-compose-postgres.yml` da release do OpenMetadata), só com o Airflow interno dele removido. Aqui a orquestração já é feita pelo nosso próprio Airflow, então a ingestão de metadados roda como uma task normal da DAG (`metadata ingest -c ...`), sem precisar de um segundo Airflow.

## Como rodar

**Pré-requisito:** Docker Desktop rodando, com pelo menos 6-8 GB de RAM livres (o Elasticsearch do OpenMetadata sozinho já pede ~1 GB de heap).

### 1. Subir o OpenMetadata

```powershell
cd 05-orquestracao
Copy-Item .env.example .env
docker compose -f openmetadata/docker-compose-openmetadata.yml up -d
```

Primeira subida demora alguns minutos (migração do banco). Confirme em **http://localhost:8585** (login `admin@open-metadata.org` / `admin`).

### 2. Subir o Airflow

```powershell
docker compose up -d --build
```

A primeira subida builda a imagem custom (dbt, Soda e openmetadata-ingestion instalados cada um no seu venv, por cima do `apache/airflow`) e roda `airflow-init` uma vez. Confirme em **http://localhost:8081** (login `admin` / `admin`).

### 3. Rodar a DAG

Na UI do Airflow, ative e dispare a DAG `atividade4_pipeline`. Ela roda uma vez do início ao fim (sem agendamento automático, é um job batch, não uma atividade contínua).

### 4. Conferir

```powershell
docker compose exec airflow-scheduler bash -c "cd /opt/dbt_project && duckdb data/database.duckdb -c 'select count(*) from delivery.bancos_indicadores;'"
```

Ou pela UI do OpenMetadata: procure o serviço `duckdb_atividade4` e veja as tabelas `trusted.tr_bancos`, `trusted.tr_reclamacoes`, `trusted.tr_empregados` e `delivery.bancos_indicadores`, com lineage e o resultado dos testes do dbt.

## Pontos de atenção conhecidos

- **Permissão de escrita em `../04-sql-dbt` e `./data`**: esses diretórios são criados pelo usuário do host (fora do container), mas as tasks da DAG rodam como o usuário `airflow` (uid `50000`) dentro dos containers. Sem ajuste, escritas no DuckDB (`data/database.duckdb`) e nos parquets gerados pelo dbt (`data/trusted/`, `data/delivery/`) falham com `Permission denied`. Sempre que esses diretórios forem recriados do zero (clone novo, `docker volume prune`, `rm -rf data/` etc.), rode:

```bash
  chmod o+rwX ../04-sql-dbt
  chmod -R o+rwX ./data
```

- **Pins de dependência por venv**: se o build da imagem falhar no `pip install` de algum dos três venvs, é sinal de que `dbt-duckdb`, `soda-core-duckdb` ou `openmetadata-ingestion` mudou uma versão major. Ajuste o pin no `requirements-*.txt` correspondente, não no `Dockerfile` como um todo.
- **`openmetadata/create_service.py`**: os módulos gerados do SDK Python do OpenMetadata (`metadata.generated.schema...`) mudam de caminho entre versões. Se essa task falhar por `ImportError`, confirme o caminho certo para a versão instalada com: `python -c "from metadata.generated.schema.entity.services.databaseService import DatabaseServiceType; print(list(DatabaseServiceType))"` dentro do container do Airflow.
- **DuckDB não tem conector nativo no OpenMetadata**: por isso o serviço é registrado como `CustomDatabase` (metadados de registro, sem conexão ao vivo) e todo o preenchimento de tabelas/colunas/lineage vem só dos artefatos do dbt (`ingest_dbt.yaml`). Isso é suficiente para o requisito da atividade (metadados do processo), mas não dá profiling de dados ao vivo, quem cobre isso é o Soda.

## Estrutura
