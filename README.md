# eEDB-022 — Ingestão de Dados · Grupo GIL

Atividades da disciplina, uma pasta por semana. Todas partem das mesmas três bases
(`dados/`): cadastro de bancos, avaliações do Glassdoor e reclamações do Banco Central.

| # | Tema | Ferramentas | Status |
|---|---|---|---|
| [01](01-etl-visual/) | ETL visual | Apache Hop + Postgres + Terraform | 🚧 em andamento |
| [02](02-etl-python/) | ETL com Python | Pandas + Postgres | ⬜ |
| [03](03-etl-pyspark/) | ETL com PySpark | Spark + Python | ⬜ |
| [04](04-sql-dbt/) | Transformações SQL | dbt + DuckDB | ⬜ |
| [05](05-orquestracao/) | Orquestração, qualidade e metadados | Airflow · Great Expectations · DataHub | ⬜ |
| [06](06-aws/) | Implementação na cloud | AWS — reimplementa a 02, 03 ou 04 | ⬜ |
| [07](07-streaming-cloud/) | Pipeline cloud streaming | Lambda + S3 + SQS (local: RabbitMQ + Docker) | ⬜ |
| [08](08-streaming-kafka/) | Streaming local | Kafka + PySpark Structured Streaming | ⬜ |

## Os dados

| Base | Pasta | Formato |
|---|---|---|
| Bancos | `dados/Bancos/` | TSV, UTF-8 |
| Empregados (Glassdoor) | `dados/Empregados/` | CSV separado por `\|`, UTF-8 |
| Reclamações (BACEN) | `dados/Reclamações/` | CSV separado por `;`, **ISO-8859-1** |

Cada atividade referencia `../../dados` — a base é versionada uma vez só.

## Saída comum

Todas as atividades de ETL produzem a mesma tabela final, **`trusted.banco_final`**: uma
linha por banco, unindo segmento, indicadores de reclamação e notas do Glassdoor. Manter o
mesmo schema entre as semanas permite comparar as ferramentas resolvendo o problema
idêntico — e é o que torna a atividade 06 uma reimplementação real, não um recomeço.

O desafio recorrente é o mesmo em todas: as três bases escrevem o nome do mesmo banco de
formas diferentes (`ITAU - PRUDENCIAL` / `ITAÚ (conglomerado)` / `Itaú Unibanco`), então
normalizar a chave antes de juntar é o cerne do tratamento.
