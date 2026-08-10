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
from utils import setup_logger

logger = setup_logger()

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS banco_final (
    nome VARCHAR(500),
    nome_norm VARCHAR(255),
    cnpj_norm VARCHAR(20),
    segmento VARCHAR(10),
    total_reclamacoes BIGINT,
    media_indice DOUBLE PRECISION,
    trimestres INTEGER,
    geral DOUBLE PRECISION,
    cultura_e_valores DOUBLE PRECISION
)
"""


def save_to_postgres(df: pd.DataFrame, postgres_uri: str) -> None:
    conn = psycopg2.connect(postgres_uri)
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_SQL)
    cursor.execute("TRUNCATE TABLE banco_final")
    cols = list(df.columns)
    placeholders = ", ".join(["%s"] * len(cols))
    quoted_cols = ", ".join(f'"{c}"' for c in cols)
    insert_sql = f"INSERT INTO banco_final ({quoted_cols}) VALUES ({placeholders})"
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
    logger.info(f"Inserted {len(df)} rows into banco_final (Postgres)")
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
            "Geral": "geral",
            "Cultura e valores": "cultura_e_valores",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        output_cols = [
            "nome",
            "nome_norm",
            "cnpj_norm",
            "segmento",
            "total_reclamacoes",
            "media_indice",
            "trimestres",
            "geral",
            "cultura_e_valores",
        ]
        output_cols = [c for c in output_cols if c in df.columns]
        df = df[output_cols]

        output_key = "banco_final.parquet"
        local_output = f"/tmp/{output_key}"
        df.to_parquet(local_output, index=False)
        s3_client.upload_file(local_output, delivery_bucket, output_key)
        logger.info(f"Saved banco_final.parquet to s3://{delivery_bucket}/{output_key}")

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
