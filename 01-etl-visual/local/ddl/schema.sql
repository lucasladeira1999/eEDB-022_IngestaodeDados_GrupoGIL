-- Estrutura das tabelas dos schemas raw / trusted / delivery.
-- GERADO, nao editar a mao: as tabelas sao criadas pelo botao SQL do Apache Hop,
-- dentro de cada Table output. Este arquivo e so um retrato para referencia.
--
-- Regerar:
--   docker compose exec postgres pg_dump -U postgres -d glassdoor --schema-only \
--     --no-owner --no-privileges -n raw -n trusted -n delivery > ddl/schema.sql


CREATE SCHEMA delivery;

CREATE SCHEMA raw;

CREATE SCHEMA trusted;

CREATE TABLE delivery.banco_final (
    segmento text,
    cnpj text,
    nome text,
    cnpj_norm character varying(20),
    nome_norm character varying(255),
    qtd_total_reclamacoes double precision,
    qtd_procedentes double precision,
    indice_medio double precision,
    trimestres_com_reclamacao double precision,
    nota_geral numeric(13,2),
    nota_cultura numeric(13,2),
    nota_diversidade numeric(13,2),
    nota_qualidade_vida numeric(13,2),
    nota_lideranca numeric(13,2),
    nota_remuneracao numeric(13,2),
    nota_carreira numeric(13,2),
    pct_recomendam numeric(13,2),
    pct_perspectiva numeric(13,2)
);

CREATE TABLE raw.bancos (
    segmento text,
    cnpj text,
    nome text
);

CREATE TABLE raw.empregados (
    employer_name text,
    reviews_count text,
    culture_count text,
    salaries_count text,
    benefits_count text,
    employer_website text,
    employer_headquarters text,
    employer_founded text,
    employer_industry text,
    employer_revenue text,
    url text,
    geral text,
    cultura_e_valores text,
    "diversidade_e_inclusão" text,
    qualidade_de_vida text,
    "alta_liderança" text,
    "remuneração_e_benefícios" text,
    oportunidades_de_carreira text,
    "Recomendam_para_outras_pessoas(%)" text,
    "Perspectiva_positiva_da_empresa(%)" text,
    segmento text,
    nome text,
    match_percent text,
    cnpj text,
    origem text
);

CREATE TABLE raw.reclamacoes (
    ano text,
    trimestre text,
    categoria text,
    tipo text,
    cnpj_if text,
    instituicao_financeira text,
    indice text,
    qtd_reclamacoes_reguladas_procedentes text,
    qtd_reclamacoes_reguladas_outras text,
    qtd_reclamacoes_nao_reguladas text,
    qtd_total_reclamacoes text,
    qtd_total_clientes_ccs_e_scr text,
    qtd_clientes_ccs text,
    qtd_clientes_scr text,
    origem_arquivo character varying(100)
);

CREATE TABLE trusted.bancos (
    segmento text,
    cnpj text,
    nome text,
    nome_norm character varying(255),
    cnpj_norm character varying(20)
);

CREATE TABLE trusted.empregados (
    employer_name text,
    nome text,
    cnpj text,
    segmento text,
    origem text,
    geral numeric(11,2),
    cultura_e_valores numeric(11,2),
    diversidade_e_inclusao numeric(11,2),
    qualidade_de_vida numeric(11,2),
    alta_lideranca numeric(11,2),
    remuneracao_e_beneficios numeric(11,2),
    oportunidades_de_carreira numeric(11,2),
    recomendam_pct numeric(11,2),
    perspectiva_pct numeric(11,2),
    nome_norm character varying(255),
    cnpj_norm character varying(20)
);

CREATE TABLE trusted.reclamacoes (
    ano text,
    trimestre text,
    categoria text,
    tipo text,
    cnpj_if text,
    instituicao_financeira text,
    indice numeric(11,2),
    qtd_reclamacoes_reguladas_procedentes bigint,
    qtd_reclamacoes_reguladas_outras bigint,
    qtd_reclamacoes_nao_reguladas bigint,
    qtd_total_reclamacoes bigint,
    qtd_total_clientes_ccs_e_scr bigint,
    qtd_clientes_ccs bigint,
    qtd_clientes_scr bigint,
    origem_arquivo character varying(100),
    nome_norm character varying(255),
    cnpj_norm character varying(20)
);

