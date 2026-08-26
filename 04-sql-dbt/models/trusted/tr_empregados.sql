{{ config(
    materialized='table',
    schema='trusted',
    post_hook="COPY {{ this }} TO 'data/trusted/empregados.parquet' (FORMAT PARQUET)"
) }}

WITH raw_emp AS (
    SELECT
        TRIM(Nome) AS nome,
        {{ normalize_text('Nome') }} AS nome_norm,
        {{ normalize_cnpj('CNPJ') }} AS cnpj_norm,
        TRY_CAST(TRIM(REPLACE(REPLACE("Geral", ' ', ''), ',', '.')) AS DOUBLE) AS avaliacao_geral,
        TRY_CAST(TRIM(REPLACE(REPLACE("Cultura e valores", ' ', ''), ',', '.')) AS DOUBLE) AS avaliacao_cultura,
        TRY_CAST(TRIM(REPLACE(REPLACE("Diversidade e inclusão", ' ', ''), ',', '.')) AS DOUBLE) AS avaliacao_diversidade,
        TRY_CAST(TRIM(REPLACE(REPLACE("Qualidade de vida", ' ', ''), ',', '.')) AS DOUBLE) AS avaliacao_qualidade_vida,
        TRY_CAST(TRIM(REPLACE(REPLACE("Alta liderança", ' ', ''), ',', '.')) AS DOUBLE) AS avaliacao_lideranca,
        TRY_CAST(TRIM(REPLACE(REPLACE("Remuneração e benefícios", ' ', ''), ',', '.')) AS DOUBLE) AS avaliacao_remuneracao,
        TRY_CAST(TRIM(REPLACE(REPLACE("Oportunidades de carreira", ' ', ''), ',', '.')) AS DOUBLE) AS avaliacao_carreira,
        TRY_CAST(TRIM(REPLACE(REPLACE("Recomendam para outras pessoas(%)", ' ', ''), ',', '.')) AS DOUBLE) AS avaliacao_recomendam_pct,
        TRY_CAST(TRIM(REPLACE(REPLACE("Perspectiva positiva da empresa(%)", ' ', ''), ',', '.')) AS DOUBLE) AS avaliacao_perspectiva_pct
    FROM {{ source('raw', 'empregados') }}
    WHERE Nome IS NOT NULL AND TRIM(Nome) != ''
),

with_canonical AS (
    SELECT
        e.*,
        COALESCE(d.nome_canonico, e.nome_norm) AS nome_canonico
    FROM raw_emp e
    LEFT JOIN {{ ref('de_para_bancos') }} d
        ON e.nome_norm = d.sigla_origem
),

dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY nome_canonico
            ORDER BY 
                (CASE WHEN cnpj_norm != '' AND cnpj_norm IS NOT NULL THEN 1 ELSE 2 END),
                avaliacao_geral DESC NULLS LAST
        ) AS row_num
    FROM with_canonical
)

SELECT
    nome,
    nome_norm,
    cnpj_norm,
    nome_canonico,
    avaliacao_geral,
    avaliacao_cultura,
    avaliacao_diversidade,
    avaliacao_qualidade_vida,
    avaliacao_lideranca,
    avaliacao_remuneracao,
    avaliacao_carreira,
    avaliacao_recomendam_pct,
    avaliacao_perspectiva_pct
FROM dedup
WHERE row_num = 1
