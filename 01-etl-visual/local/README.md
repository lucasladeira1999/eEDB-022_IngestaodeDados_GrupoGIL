# Atividade 01 — ETL visual com Apache Hop

Ingestão das três bases (bancos, avaliações do Glassdoor e reclamações do BACEN) para
Postgres, com todo o tratamento feito por transforms do Apache Hop. Roda offline, em
Docker, sem custo.

## Arquitetura

```
dados/ (CSV, TSV)  ──►  Apache Hop  ──►  Postgres
                                          raw ──► trusted ──► delivery
```

| Serviço | Porta | Papel |
|---|---|---|
| `postgres` | 5432 | banco de destino |
| `hop` | 8080 | Apache Hop Web, a ferramenta visual de ETL |
| `pgadmin` | 5050 | inspeção das tabelas |

| Camada | Conteúdo | Linhas |
|---|---|---|
| `raw` | fiel ao arquivo, tudo texto | 1474 · 39 · 918 |
| `trusted` | limpo e tipado, uma tabela por fonte | 1474 · 39 · 918 |
| `delivery` | `banco_final`, o join das três | 1470 |

O [`init.sh`](init.sh) cria database, usuário e schemas; as tabelas e a carga ficam por
conta do Hop, em dois workflows — `cria_tabelas` e `carga_completa`. O enunciado exige que
o tratamento e a carga sejam feitos pela ferramenta de ETL, então não há SQL de
transformação em lugar nenhum: tudo é transform.

📄 **[TRANSFORMACOES.md](TRANSFORMACOES.md)** — o que cada pipeline faz com o dado, as
decisões de tratamento e por quê, cobertura da junção e limitações conhecidas.

---

## Como rodar

**Pré-requisito:** Docker Desktop rodando. Nada mais precisa estar instalado.

### 1. Subir o ambiente

```powershell
cd 01-etl-visual/local
Copy-Item .env.example .env
docker compose up -d
```

O `.env` guarda as senhas e não vai para o Git. Na primeira vez o Docker baixa as imagens
(a do Hop tem ~1 GB) e o Postgres executa o `init.sh`, criando o banco `glassdoor`, o
usuário `etl` e os schemas `raw`, `trusted` e `delivery`.

✅ *Deu certo se:* `docker compose ps` mostra `atividade1-postgres` como `healthy`.

### 2. Abrir o Hop e selecionar o projeto

**http://localhost:8080/ui**

No rodapé, escolha o projeto `atividade1` e o environment `dev`. Ele abre no projeto
`default`, então essa troca é necessária toda vez.

Teste a conexão em *Metadata → Relational Database Connection → `glassdoor` → Test*.

### 3. Criar as tabelas

Abra [`workflows/cria_tabelas.hwf`](hop/workflows/cria_tabelas.hwf) e clique em ▶. Leva
1 segundo e cria as 7 tabelas.

Só é necessário em ambiente novo. O script é idempotente (`CREATE TABLE IF NOT EXISTS`),
então rodar de novo não faz nada e não apaga dado.

> O DDL desse workflow foi **gerado pelo próprio Hop**, pelo botão SQL de cada Table
> output, e depois consolidado num script único para não repetir sete cliques. Se você
> mudar os campos de um pipeline, clique em SQL no Table output dele e o Hop gera o
> `ALTER TABLE` da diferença; para atualizar o retrato, veja o cabeçalho do
> [`ddl/schema.sql`](ddl/schema.sql).

### 4. Rodar a carga

Abra [`workflows/carga_completa.hwf`](hop/workflows/carga_completa.hwf) e clique em ▶.
Ele encadeia os sete pipelines:

```
Start → raw_bancos → raw_empregados → raw_reclamacoes
      → trusted_bancos → trusted_empregados → trusted_reclamacoes
      → delivery_banco_final
```

As ligações são **condicionais**: cada etapa só dispara se a anterior terminou com sucesso.
Se a ingestão falhar, o workflow para ali em vez de gerar uma camada `trusted` a partir de
dado incompleto — que falharia silenciosamente, com número errado em vez de erro.

Leva cerca de 10 segundos.

### 5. Conferir

```powershell
docker compose exec postgres psql -U postgres -d glassdoor -c "SELECT count(*) FROM delivery.banco_final;"
```

Ou pelo pgAdmin em **http://localhost:5050** (credenciais no `.env`), conectando em host
`postgres` — não `localhost`, porque o pgAdmin roda dentro de um container.

---

## Resultado

`delivery.banco_final`: uma linha por banco do cadastro, com indicadores de reclamação
agregados e as notas do Glassdoor.

| | |
|---|---|
| Bancos | 1470 |
| Com dados de reclamação | 119 |
| Com notas do Glassdoor | 33 |
| Com as duas fontes | 25 |

```sql
SELECT nome_norm, segmento, qtd_total_reclamacoes, round(indice_medio::numeric,1), nota_geral
FROM delivery.banco_final
WHERE nota_geral IS NOT NULL AND qtd_total_reclamacoes IS NOT NULL
ORDER BY qtd_total_reclamacoes DESC;
```

```
CAIXA ECONOMICA FEDERAL  S1   74106   21.5   4.40
BRADESCO                 S1   60835   25.9   4.20
SANTANDER                S1   45423   27.3   3.90
ITAU                     S1   43280   15.3   4.50
```

A cobertura parcial é esperada: as reclamações incluem instituições de pagamento que não
constam do cadastro de bancos prudenciais, e o Glassdoor cobre só 39 empresas. Os números
e o motivo de cada ausência estão em [TRANSFORMACOES.md](TRANSFORMACOES.md).

---

## Estrutura

```
local/
├── docker-compose.yml          postgres + hop + pgadmin
├── init.sh                     cria database, usuário e schemas
├── .env.example                modelo de senhas (copie para .env)
├── ddl/schema.sql              retrato das tabelas criadas pelo Hop (referência)
├── TRANSFORMACOES.md           decisões de tratamento
└── hop/
    ├── project-config.json     projeto atividade1
    ├── dev-config.json         variáveis do environment dev
    ├── metadata/rdbms/         conexão glassdoor
    ├── pipelines/              os 7 pipelines
    └── workflows/              cria_tabelas.hwf + carga_completa.hwf
```

## Comandos do dia a dia

```powershell
docker compose ps            # o que está de pé
docker compose logs -f hop   # ver erro do Hop
docker compose stop          # pausar (mantém os dados)
docker compose down          # remover containers (mantém os dados no volume)
docker compose down -v       # apagar TUDO, inclusive o banco
```

> ⚠️ A senha do usuário `etl` aparece em **dois** lugares e precisa ser a mesma nos dois:
> `ETL_PASSWORD` no `.env` (que o `init.sh` usa para criar o usuário) e `PG_PASSWORD` no
> `hop/dev-config.json` (que o Hop usa para conectar).

> **Janela "Apache Hop is handling a long running task" travada?** Acontece no Hop Web em
> operações de banco. O trabalho normalmente já foi concluído — confira o resultado direto
> no Postgres antes de cancelar e refazer.

## Referência das fontes

| Fonte | Caminho no Hop | Separador | Encoding |
|---|---|---|---|
| Bancos | `${FILES_DIR}/Bancos/EnquadramentoInicia_v2.tsv` | TAB | UTF-8 |
| Empregados | `${FILES_DIR}/Empregados/glassdoor_*.csv` | `\|` | UTF-8 |
| Reclamações | `${FILES_DIR}/Reclamacoes/*.csv` | `;` | ISO-8859-1 |

Os arquivos ficam visíveis dentro do Hop em `/files`, somente leitura.
