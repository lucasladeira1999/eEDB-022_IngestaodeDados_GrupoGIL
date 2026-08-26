{{ config(
    materialized='table',
    schema='trusted',
    post_hook="COPY {{ this }} TO 'data/trusted/bancos.parquet' (FORMAT PARQUET)"
) }}

WITH raw_data AS (
    SELECT
        TRIM(Nome) AS nome,
        {{ normalize_text('Nome') }} AS nome_norm,
        {{ normalize_cnpj('CNPJ') }} AS cnpj_norm,
        TRIM(Segmento) AS segmento
    FROM {{ source('raw', 'bancos') }}
    WHERE Nome IS NOT NULL AND TRIM(Nome) != ''
),

ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY (CASE WHEN cnpj_norm != '' AND cnpj_norm IS NOT NULL THEN cnpj_norm ELSE nome_norm END)
            ORDER BY
                (CASE WHEN segmento IS NOT NULL AND segmento != '' THEN 1 ELSE 2 END),
                nome
        ) AS row_num
    FROM raw_data
)

SELECT
    nome,
    nome_norm,
    cnpj_norm,
    segmento
FROM ranked
WHERE row_num = 1
