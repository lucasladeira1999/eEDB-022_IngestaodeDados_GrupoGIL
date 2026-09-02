# eEDB-022 — Ingestão de Dados · Grupo GIL

Atividades da disciplina, uma pasta por semana. Todas partem das mesmas três bases
(`dados/`): cadastro de bancos, avaliações do Glassdoor e reclamações do Banco Central.

| # | Tema | Ferramentas | Status |
|---|---|---|---|
| [01](01-etl-visual/) | ETL visual | Apache Hop + Postgres | ✅ feito |
| [02](02-etl-python/) | ETL com Python | Pandas + AWS S3 + Redshift (Terraform) | ✅ feito |
| [03](03-etl-pyspark/) | ETL com PySpark | Spark + Python | ✅ feito |
| [04](04-sql-dbt/) | Transformações SQL | dbt + DuckDB | ✅ feito |
| [05](05-orquestracao/) | Orquestração, qualidade e metadados | Airflow · Great Expectations · DataHub | ✅ feito |
| [06](06-aws/) | Implementação na cloud | AWS — reimplementa a 02, 03 ou 04 | ⬜ |
| [07](07-streaming-cloud/) | Pipeline cloud streaming | Lambda + S3 + SQS (local: RabbitMQ + Docker) | ⬜ |
| [08](08-streaming-kafka/) | Streaming local | Kafka + PySpark Structured Streaming | ⬜ |

## Os dados

| Base | Pasta | Formato |
|---|---|---|
| Bancos | `dados/Bancos/` | TSV, UTF-8 |
| Empregados (Glassdoor) | `dados/Empregados/` | CSV separado por `\|`, UTF-8 |
| Reclamações (BACEN) | `dados/Reclamacoes/` | CSV separado por `;`, **ISO-8859-1** |

As atividades referenciam a pasta central `dados/` — a base é versionada uma vez só.

## Saída comum

Todas as atividades de ETL resolvem o mesmo problema: unir as três bases numa tabela final, uma linha por banco, cruzando segmento, indicadores de reclamação e notas do Glassdoor.

A atividade 03 implementa esse fluxo em três etapas com PySpark: carrega os arquivos na camada `raw` do Postgres, transforma os dados na camada `trusted` e gera a tabela final na camada `delivery`. Os detalhes de execução estão no [README da atividade 03](03-etl-pyspark/).
