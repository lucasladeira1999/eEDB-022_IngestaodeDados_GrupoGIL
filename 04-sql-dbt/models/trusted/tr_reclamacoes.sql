{{ config(
    materialized='table',
    schema='trusted',
    post_hook="COPY {{ this }} TO 'data/trusted/reclamacoes.parquet' (FORMAT PARQUET)"
) }}

WITH raw_rec AS (
    SELECT
        ano,
        trimestre,
        categoria,
        tipo,
        TRIM(instituicao_financeira) AS instituicao_financeira,
        {{ normalize_text('instituicao_financeira') }} AS nome_norm,
        {{ normalize_cnpj('cnpj_if') }} AS cnpj_norm,
        TRY_CAST(TRIM(REPLACE(REPLACE(COALESCE(indice, ''), '.', ''), ',', '.')) AS DOUBLE) AS indice,
        TRY_CAST(REGEXP_REPLACE(COALESCE(qtd_reclamacoes_reguladas_procedentes, '0'), '[^0-9]', '', 'g') AS BIGINT) AS qtd_reclamacoes_reguladas_procedentes,
        TRY_CAST(REGEXP_REPLACE(COALESCE(qtd_reclamacoes_reguladas_outras, '0'), '[^0-9]', '', 'g') AS BIGINT) AS qtd_reclamacoes_reguladas_outras,
        TRY_CAST(REGEXP_REPLACE(COALESCE(qtd_reclamacoes_nao_reguladas, '0'), '[^0-9]', '', 'g') AS BIGINT) AS qtd_reclamacoes_nao_reguladas,
        TRY_CAST(REGEXP_REPLACE(COALESCE(qtd_total_reclamacoes, '0'), '[^0-9]', '', 'g') AS BIGINT) AS qtd_total_reclamacoes,
        TRY_CAST(REGEXP_REPLACE(COALESCE(qtd_total_clientes_ccs_scr, '0'), '[^0-9]', '', 'g') AS BIGINT) AS qtd_total_clientes_ccs_scr,
        TRY_CAST(REGEXP_REPLACE(COALESCE(qtd_clientes_ccs, '0'), '[^0-9]', '', 'g') AS BIGINT) AS qtd_clientes_ccs,
        TRY_CAST(REGEXP_REPLACE(COALESCE(qtd_clientes_scr, '0'), '[^0-9]', '', 'g') AS BIGINT) AS qtd_clientes_scr
    FROM {{ source('raw', 'reclamacoes') }}
    WHERE instituicao_financeira IS NOT NULL AND TRIM(instituicao_financeira) != ''
)

SELECT
    r.*,
    COALESCE(d.nome_canonico, r.nome_norm) AS nome_canonico
FROM raw_rec r
LEFT JOIN {{ ref('de_para_bancos') }} d
    ON r.nome_norm = d.sigla_origem
