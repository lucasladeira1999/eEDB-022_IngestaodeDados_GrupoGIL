-- Garante que não existem bancos duplicados na tabela final delivery
SELECT
    COALESCE(NULLIF(cnpj_norm, ''), nome_norm) AS chave,
    COUNT(*) AS total
FROM {{ ref('bancos_indicadores') }}
GROUP BY 1
HAVING COUNT(*) > 1
