{{ config(
    materialized='table',
    schema='delivery',
    post_hook="COPY {{ this }} TO 'data/delivery/bancos_indicadores.parquet' (FORMAT PARQUET)"
) }}

WITH bancos_base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY b.nome_norm, b.cnpj_norm) AS banco_id,
        b.nome,
        b.nome_norm,
        b.cnpj_norm,
        b.segmento,
        COALESCE(d.nome_canonico, b.nome_norm) AS nome_canonico
    FROM {{ ref('tr_bancos') }} b
    LEFT JOIN {{ ref('de_para_bancos') }} d
        ON b.nome_norm = d.sigla_origem
),

rec_agg AS (
    SELECT * FROM {{ ref('del_reclamacoes_agg') }}
),

emp_base AS (
    SELECT * FROM {{ ref('tr_empregados') }}
),

-- =========================================================================
-- 1. Casamento com Reclamações (CNPJ -> Nome Canônico -> Fuzzy Matching)
-- =========================================================================
-- 1.1 Match exato por CNPJ
rec_cnpj_match AS (
    SELECT
        b.banco_id,
        r.*
    FROM bancos_base b
    INNER JOIN rec_agg r
        ON b.cnpj_norm = r.join_key
        AND r.join_type = 'cnpj'
        AND b.cnpj_norm IS NOT NULL
        AND b.cnpj_norm != ''
),

-- 1.2 Match exato por Nome Canônico (para quem não casou por CNPJ)
rec_nome_match AS (
    SELECT
        b.banco_id,
        r.*
    FROM bancos_base b
    INNER JOIN rec_agg r
        ON b.nome_canonico = r.join_key
        AND r.join_type = 'nome'
    WHERE b.banco_id NOT IN (SELECT banco_id FROM rec_cnpj_match)
),

-- 1.3 Match por Similaridade / Fuzzy (fallback com Jaro-Winkler >= 0.90)
rec_fuzzy_ranked AS (
    SELECT
        b.banco_id,
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY b.banco_id 
            ORDER BY jaro_winkler_similarity(b.nome_canonico, r.join_key) DESC
        ) AS rnk
    FROM bancos_base b
    CROSS JOIN (SELECT * FROM rec_agg WHERE join_type = 'nome') r
    WHERE b.banco_id NOT IN (SELECT banco_id FROM rec_cnpj_match)
      AND b.banco_id NOT IN (SELECT banco_id FROM rec_nome_match)
      AND jaro_winkler_similarity(b.nome_canonico, r.join_key) >= 0.90
),
rec_fuzzy_match AS (
    SELECT * EXCLUDE (rnk)
    FROM rec_fuzzy_ranked
    WHERE rnk = 1
),

-- Unificação das Reclamações casadas
rec_consolidado AS (
    SELECT * FROM rec_cnpj_match
    UNION ALL
    SELECT * FROM rec_nome_match
    UNION ALL
    SELECT * FROM rec_fuzzy_match
),

-- =========================================================================
-- 2. Casamento com Empregados / Glassdoor (CNPJ -> Nome Canônico -> Fuzzy)
-- =========================================================================
-- 2.1 Match exato por CNPJ
emp_cnpj_match AS (
    SELECT
        b.banco_id,
        e.*
    FROM bancos_base b
    INNER JOIN emp_base e
        ON b.cnpj_norm = e.cnpj_norm
        AND b.cnpj_norm IS NOT NULL
        AND b.cnpj_norm != ''
),

-- 2.2 Match exato por Nome Canônico (para quem não casou por CNPJ)
emp_nome_match AS (
    SELECT
        b.banco_id,
        e.*
    FROM bancos_base b
    INNER JOIN emp_base e
        ON b.nome_canonico = e.nome_canonico
    WHERE b.banco_id NOT IN (SELECT banco_id FROM emp_cnpj_match)
),

-- 2.3 Match por Similaridade / Fuzzy (fallback com Jaro-Winkler >= 0.92)
emp_fuzzy_ranked AS (
    SELECT
        b.banco_id,
        e.*,
        ROW_NUMBER() OVER (
            PARTITION BY b.banco_id 
            ORDER BY jaro_winkler_similarity(b.nome_canonico, e.nome_canonico) DESC
        ) AS rnk
    FROM bancos_base b
    CROSS JOIN emp_base e
    WHERE b.banco_id NOT IN (SELECT banco_id FROM emp_cnpj_match)
      AND b.banco_id NOT IN (SELECT banco_id FROM emp_nome_match)
      AND jaro_winkler_similarity(b.nome_canonico, e.nome_canonico) >= 0.92
),
emp_fuzzy_match AS (
    SELECT * EXCLUDE (rnk)
    FROM emp_fuzzy_ranked
    WHERE rnk = 1
),

-- Unificação dos Empregados casados
emp_consolidado AS (
    SELECT * FROM emp_cnpj_match
    UNION ALL
    SELECT * FROM emp_nome_match
    UNION ALL
    SELECT * FROM emp_fuzzy_match
)

-- =========================================================================
-- 3. Projeção da Tabela Final (OBT)
-- =========================================================================
SELECT
    b.nome,
    b.nome_norm,
    b.cnpj_norm,
    b.segmento,
    
    -- Métricas de Reclamações
    CAST(r.total_reclamacoes AS BIGINT) AS reclamacao_total,
    r.media_indice AS reclamacao_indice_bacen,
    CAST(r.trimestres AS BIGINT) AS reclamacao_trimestres,
    r.taxa_reclamacao_por_cliente AS reclamacao_indice_calculado,
    r.pct_reclamacoes_procedentes AS reclamacao_pct_procedentes,

    -- Métricas do Glassdoor (Avaliações)
    e.avaliacao_geral,
    e.avaliacao_cultura,
    e.avaliacao_diversidade,
    e.avaliacao_qualidade_vida,
    e.avaliacao_lideranca,
    e.avaliacao_remuneracao,
    e.avaliacao_carreira,
    e.avaliacao_recomendam_pct,
    e.avaliacao_perspectiva_pct

FROM bancos_base b
LEFT JOIN rec_consolidado r ON b.banco_id = r.banco_id
LEFT JOIN emp_consolidado e ON b.banco_id = e.banco_id
