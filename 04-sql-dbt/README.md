# 04 - Ingestão e ETL com SQL (DBT + DuckDB)

Implementação da **Atividade 4** do curso de Engenharia de Dados: pipeline de ingestão e transformação de dados utilizando **Python** para ingestão e **DBT (Data Build Tool)** com engine **DuckDB** para modelagem e transformação em SQL relacional.

---

## 1. Arquitetura do Pipeline

```
dados/ (origem)
   ├── Bancos/ (TSV)
   ├── Empregados/ (2 CSVs pipe)
   └── Reclamacoes/ (8 CSVs ponto-e-vírgula)
            │
            ▼ [Python: scripts/ingest_raw.py]
Camada RAW
   ├── DuckDB: schema `raw` (tabelas `bancos`, `empregados`, `reclamacoes`)
   └── Disco: `data/raw/` (arquivos CSV brutos)
            │
            ▼ [DBT + DuckDB: dbt seed / dbt run]
Camada Trusted (Parquet)
   ├── `data/trusted/bancos.parquet` (dados limpos, normalizados e deduplicados)
   ├── `data/trusted/empregados.parquet` (avaliações Glassdoor com tipos numéricos)
   └── `data/trusted/reclamacoes.parquet` (reclamações BACEN tipadas e normalizadas)
            │
            ▼ [DBT + DuckDB: dbt run]
Camada Delivery (Parquet + Tabela Relacional)
   ├── DuckDB: `delivery.bancos_indicadores` (tabela relacional final no `data/database.duckdb`)
   └── Disco: `data/delivery/bancos_indicadores.parquet` (dataset colunar consolidado)
```

---

## 2. Destaques da Implementação

- **Ingestão Python (`scripts/ingest_raw.py`)**:
  - Trata encodings diferentes (`ISO-8859-1` para Reclamações, `UTF-8` para Bancos e Empregados).
  - Trata separadores diversos (`\t`, `|`, `;`).
  - Descarta colunas fantasmas e arquivos vazios (`2022_tri_02_nao_ha_dados.csv`).
  - Persiste a camada RAW tanto em disco (`data/raw/`) quanto no schema `raw` do DuckDB.
- **Seeds e Resolução de Acrônimos (`seeds/de_para_bancos.csv`)**:
  - Mapeia siglas e acrônimos conhecidos (`BB` → `BANCO DO BRASIL`, `C6` → `C6 BANK`, `ITAU` → `ITAU UNIBANCO`, `SAFRA` → `BANCO SAFRA`, etc.) para garantir alto percentual de casamento nos joins.
- **Macros SQL Modulares (`macros/`)**:
  - `normalize_text.sql`: Remoção de acentos (`STRIP_ACCENTS`), pontuação, sufixos corporativos (`- PRUDENCIAL`, `(CONGLOMERADO)`, `S.A.`, `LTDA`, `S/A`) e colapso de espaços em SQL puro.
  - `normalize_cnpj.sql`: Remoção de pontuação e zeros à esquerda.
- **Camada Trusted (`models/trusted/`)**:
  - Limpeza, tipagem e deduplicação de bancos por chave normalizada (`cnpj_norm` / `nome_norm`).
  - Exportação direta para arquivos `.parquet` em `data/trusted/`.
- **Camada Delivery (`models/delivery/`)**:
  - `del_reclamacoes_agg.sql`: Agrupamento e cálculo de taxas derivadas (`reclamacao_indice_calculado`, `reclamacao_pct_procedentes`).
  - `bancos_indicadores.sql`: Tabela consolidada (One Big Table - OBT) com matching hierárquico (CNPJ com fallback para Nome Canônico).
  - Tabela relacional criada no DuckDB (`delivery.bancos_indicadores`) e exportada para Parquet em `data/delivery/bancos_indicadores.parquet`.
- **Testes Automatizados (`tests/` e YAMLs)**:
  - 13 testes cobrindo unicidade, campos obrigatórios e regras de negócio.

---

## 3. Como Executar com Docker Compose (Recomendado)

O projeto está totalmente containerizado:

```bash
# Na pasta 04-sql-dbt
docker compose up --build
```

O container executa automaticamente:
1. Ingestão RAW em Python (`ingest_raw.py`)
2. Carga das seeds do DBT (`dbt seed`)
3. Execução dos modelos SQL (`dbt run`)
4. Execução dos testes automatizados (`dbt test`)
5. Exibição do resumo final com contagens e métricas

Os dados processados ficam salvos na pasta `./data` da sua máquina host:
- `data/raw/`: Arquivos brutos
- `data/trusted/`: Parquets da camada trusted
- `data/delivery/`: Parquet da camada delivery (`bancos_indicadores.parquet`)
- `data/database.duckdb`: Banco de dados relacional DuckDB com todas as camadas (`raw`, `trusted`, `delivery`)

---

## 4. Execução Local (Opcional)

Se preferir rodar localmente com o ambiente virtual Python:

```bash
# Ativar venv
source .venv/bin/activate

# Executar o pipeline completo
python scripts/run_pipeline.py
```

---

## 5. Como Inspecionar os Resultados

### Consultar a tabela final no DuckDB

```bash
python3 -c "
import duckdb
con = duckdb.connect('data/database.duckdb')

print('--- Contagens e Médias da Tabela Final (delivery.bancos_indicadores) ---')
print(con.execute('''
    SELECT 
        COUNT(*) as total_bancos,
        COUNT(reclamacao_total) as com_reclamacoes,
        COUNT(avaliacao_geral) as com_glassdoor,
        SUM(reclamacao_total) as total_reclamacoes,
        AVG(avaliacao_geral) as media_avaliacao_geral
    FROM delivery.bancos_indicadores
''').df())

print('\n--- Amostra dos Principais Bancos ---')
print(con.execute('''
    SELECT 
        nome, 
        cnpj_norm, 
        segmento, 
        reclamacao_total, 
        reclamacao_indice_bacen, 
        avaliacao_geral 
    FROM delivery.bancos_indicadores 
    WHERE nome_norm IN ('BANCO DO BRASIL', 'ITAU', 'BRADESCO', 'SANTANDER', 'CAIXA ECONOMICA FEDERAL', 'BTG PACTUAL')
''').df())
"
```

### Inspecionar os arquivos Parquet

```bash
python3 -c "
import pandas as pd
df_del = pd.read_parquet('data/delivery/bancos_indicadores.parquet')
print(f'Delivery Parquet: {len(df_del)} linhas, {len(df_del.columns)} colunas')
print(df_del[['nome', 'cnpj_norm', 'reclamacao_total', 'avaliacao_geral']].dropna().head())
"
```
