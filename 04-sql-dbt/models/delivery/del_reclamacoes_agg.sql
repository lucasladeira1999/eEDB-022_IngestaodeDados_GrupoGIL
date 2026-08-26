{{ config(
    materialized='view',
    schema='delivery'
) }}

WITH rec AS (
    SELECT * FROM {{ ref('tr_reclamacoes') }}
),

by_cnpj AS (
    SELECT
        cnpj_norm AS join_key,
        'cnpj' AS join_type,
        SUM(qtd_total_reclamacoes) AS total_reclamacoes,
        AVG(indice) AS media_indice,
        COUNT(DISTINCT trimestre) AS trimestres,
        SUM(qtd_total_clientes_ccs_scr) AS total_clientes,
        SUM(qtd_reclamacoes_reguladas_procedentes) AS total_procedentes
    FROM rec
    WHERE cnpj_norm IS NOT NULL AND cnpj_norm != ''
    GROUP BY cnpj_norm
),

by_nome AS (
    SELECT
        nome_canonico AS join_key,
        'nome' AS join_type,
        SUM(qtd_total_reclamacoes) AS total_reclamacoes,
        AVG(indice) AS media_indice,
        COUNT(DISTINCT trimestre) AS trimestres,
        SUM(qtd_total_clientes_ccs_scr) AS total_clientes,
        SUM(qtd_reclamacoes_reguladas_procedentes) AS total_procedentes
    FROM rec
    WHERE cnpj_norm IS NULL OR cnpj_norm = ''
    GROUP BY nome_canonico
),

unioned AS (
    SELECT * FROM by_cnpj
    UNION ALL
    SELECT * FROM by_nome
)

SELECT
    join_key,
    join_type,
    total_reclamacoes,
    media_indice,
    trimestres,
    total_clientes,
    total_procedentes,
    CASE 
        WHEN total_clientes > 0 THEN CAST(total_reclamacoes AS DOUBLE) / total_clientes 
        ELSE NULL 
    END AS taxa_reclamacao_por_cliente,
    CASE 
        WHEN total_reclamacoes > 0 THEN CAST(total_procedentes AS DOUBLE) / total_reclamacoes 
        ELSE NULL 
    END AS pct_reclamacoes_procedentes
FROM unioned
