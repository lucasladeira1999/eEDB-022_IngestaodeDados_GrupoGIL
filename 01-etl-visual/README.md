# 01 — Ingestão e ETL com ferramenta visual

Requisito: ingerir as três bases em um banco relacional open source e gerar uma tabela
final tratada e unida, com o tratamento feito **pela ferramenta visual de ETL**.

| Pasta | O que é |
|---|---|
| [`local/`](local/) | **Entrega atual.** Apache Hop + Postgres em Docker, Terraform provisionando o banco. Roda offline, custo zero. |
| [`aws/`](aws/) | Versão alternativa com AWS Glue Studio + RDS. Não iniciada. |

Comece por [`local/README.md`](local/README.md) — passo a passo em 8 etapas.
