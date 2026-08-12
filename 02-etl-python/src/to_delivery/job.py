import os

import boto3
import pandas as pd
import psycopg2

from to_delivery.join import (
    aggregate_reclamacoes,
    deduplicate,
    join_bancos_reclamacoes,
    join_empregados,
)
from sql_schema import create_table_sql
from utils import setup_logger

logger = setup_logger()

TABLE_NAME = "bancos_indicadores"


def save_to_postgres(df: pd.DataFrame, postgres_uri: str) -> None:
    conn = psycopg2.connect(postgres_uri)
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(create_table_sql(TABLE_NAME, df))
    cursor.execute(f"TRUNCATE TABLE {TABLE_NAME}")
    cols = list(df.columns)
    placeholders = ", ".join(["%s"] * len(cols))
    quoted_cols = ", ".join(f'"{c}"' for c in cols)
    insert_sql = f"INSERT INTO {TABLE_NAME} ({quoted_cols}) VALUES ({placeholders})"
    for _, row in df.iterrows():
        values = tuple(
            None
            if pd.isna(v)
            else int(v)
            if isinstance(v, float) and v.is_integer()
            else v
            for v in row
        )
        cursor.execute(insert_sql, values)
    logger.info(f"Inserted {len(df)} rows into {TABLE_NAME} (Postgres)")
    cursor.close()
    conn.close()


class ToDeliveryJob:
    def run(**config) -> None:
        logger.info(f"Running ToDeliveryJob with config: {config}")
        s3_client = boto3.client("s3")
        trusted_bucket = config["trusted_bucket"]
        delivery_bucket = config["delivery_bucket"]

        trusted = {}
        for name in ["bancos", "empregados", "reclamacoes"]:
            key = f"{name}.parquet"
            local_path = f"/tmp/{name}.parquet"
            s3_client.download_file(trusted_bucket, key, local_path)
            trusted[name] = pd.read_parquet(local_path)
            logger.info(f"Loaded {name}: {len(trusted[name])} rows")

        df_bancos = trusted["bancos"]
        df_empregados = trusted["empregados"]
        df_reclamacoes = trusted["reclamacoes"]

        df_reclamacoes_agg = aggregate_reclamacoes(df_reclamacoes)
        df = join_bancos_reclamacoes(df_bancos, df_reclamacoes_agg)
        df = deduplicate(df)
        df = join_empregados(df, df_empregados)

        rename_map = {
            "Segmento": "segmento",
            "Nome": "nome",
            "total_reclamacoes": "reclamacao_total",
            "media_indice": "reclamacao_indice_bacen",
            "trimestres": "reclamacao_trimestres",
            "taxa_reclamacao_por_cliente": "reclamacao_indice_calculado",
            "pct_reclamacoes_procedentes": "reclamacao_pct_procedentes",
            "Geral": "avaliacao_geral",
            "Cultura e valores": "avaliacao_cultura",
            "Diversidade e inclusão": "avaliacao_diversidade",
            "Qualidade de vida": "avaliacao_qualidade_vida",
            "Alta liderança": "avaliacao_lideranca",
            "Remuneração e benefícios": "avaliacao_remuneracao",
            "Oportunidades de carreira": "avaliacao_carreira",
            "Recomendam para outras pessoas(%)": "avaliacao_recomendam_pct",
            "Perspectiva positiva da empresa(%)": "avaliacao_perspectiva_pct",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        output_cols = [
            "nome",
            "nome_norm",
            "cnpj_norm",
            "segmento",
            "reclamacao_total",
            "reclamacao_indice_bacen",
            "reclamacao_trimestres",
            "reclamacao_indice_calculado",
            "reclamacao_pct_procedentes",
            "avaliacao_geral",
            "avaliacao_cultura",
            "avaliacao_diversidade",
            "avaliacao_qualidade_vida",
            "avaliacao_lideranca",
            "avaliacao_remuneracao",
            "avaliacao_carreira",
            "avaliacao_recomendam_pct",
            "avaliacao_perspectiva_pct",
        ]
        output_cols = [c for c in output_cols if c in df.columns]
        df = df[output_cols]

        for int_col in ["reclamacao_total", "reclamacao_trimestres"]:
            if int_col in df.columns:
                df[int_col] = df[int_col].astype("Int64")

        output_key = "bancos_indicadores.parquet"
        local_output = f"/tmp/{output_key}"
        df.to_parquet(local_output, index=False)
        s3_client.upload_file(local_output, delivery_bucket, output_key)
        logger.info(f"Saved bancos_indicadores.parquet to s3://{delivery_bucket}/{output_key}")

        if "postgres_uri" in config:
            save_to_postgres(df, config["postgres_uri"])

        for local_file in [
            "/tmp/bancos.parquet",
            "/tmp/empregados.parquet",
            "/tmp/reclamacoes.parquet",
            local_output,
        ]:
            if os.path.exists(local_file):
                os.remove(local_file)
