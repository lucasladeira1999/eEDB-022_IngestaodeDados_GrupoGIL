# 08-streaming-kafka

Requisito: o mesmo pipeline da [atividade 07](../07-streaming-cloud/), agora **em máquina
local** — produtor em Python puro lendo arquivos do disco, fila no Apache Kafka, e um
consumidor PySpark **Structured Streaming** que, a cada janela, consulta um banco SQL para
enriquecer as mensagens e grava o resultado em arquivo local.

## Arquitetura

```
dados/                                        ┌──────────────────┐
  │  to_raw (local)                           │ Postgres         │
  ▼                                           │ cadastro.bancos  │
data/raw/ ──► produtor (Python) ──► Kafka ──► └────────┬─────────┘
                                       │               │ 1 consulta por janela
                                       ▼               │
                          consumidor (Structured Streaming)
                                       │
                          ├──► data/trusted/reclamacoes/              (Parquet)
                          └──► data/delivery/reclamacoes_enriquecidas/ (Parquet)
```

| Camada | Onde | O que é |
|---|---|---|
| raw | `data/raw/` | cópia fiel dos CSV/TSV de origem |
| trusted | `data/trusted/` | reclamação com chave normalizada e tipos convertidos |
| delivery | `data/delivery/` | reclamação tratada + segmento e nome do banco |

O cadastro de bancos vai para o **Postgres**, não para uma camada de arquivo: é ele que
responde a consulta de enriquecimento.

## A diferença para a atividade 07

Lá o enunciado pedia uma consulta ao banco **por mensagem** — cada Lambda recebia uma
reclamação e fazia um `SELECT` pontual. Aqui ele pede "ao receber uma **janela** de
informações", então o consumidor acumula o micro-batch e faz **uma consulta por janela**,
seguida de um `JOIN` do lote inteiro contra o cadastro.

Na prática é a diferença entre *lookup* e *join* — e é o padrão que um pipeline de produção
usaria, porque troca N idas ao banco por uma.

## Estrutura

```
docker-compose.yml   kafka (KRaft) + kafka-init + postgres + pgadmin + kafka-ui + consumidor
Dockerfile           spark (java17/python3.10) + jars do conector Kafka e do JDBC do Postgres
log4j2.properties    silencia avisos conhecidos do log do Spark
src/
  main.py             roda as etapas locais, na ordem
  to_raw/job.py       dados/ -> data/raw/
  to_postgres/job.py  cadastro de bancos -> tabela no Postgres
  produtor/job.py     data/raw/ -> Kafka          (Python puro, sem Spark)
  consumidor/job.py   Kafka -> trusted + delivery (PySpark Structured Streaming)
  consolida/job.py    achata as janelas em um .parquet e um .csv por camada
  utils.py            conversores (normalize_text, normalize_cnpj, resolve_acronym)
  schemas.yaml        colunas de cada etapa, num lugar só
  acronyms.yaml       de-para de sigla -> nome canônico
```

## Como usar

1. Dependências locais (só o produtor e as cargas; o Spark roda no container):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

2. Suba a infra — `kafka-init` cria o tópico e encerra, o resto fica de pé:

```bash
docker compose up -d
docker compose ps
```

3. Suba o consumidor — ele fica rodando, esperando mensagem:

```bash
docker compose --profile job up --build consumidor
```

4. Em outro terminal, rode as etapas locais:

```bash
python src/main.py
```

O `main.py` executa, nesta ordem:

1. **`to_raw`** — copia `dados/Reclamacoes` e `dados/Bancos` para `data/raw/`, sem tocar no
   conteúdo.
2. **`to_postgres`** — lê o cadastro do raw, normaliza as chaves, deduplica e carrega a
   tabela `cadastro.bancos` via `COPY`.
3. **`produtor`** — lê os CSV de reclamações e publica uma mensagem por linha no Kafka.

A ordem importa: a tabela `bancos` precisa existir antes das mensagens chegarem, senão o
consumidor abre a janela e não tem o que consultar.

Para publicar só algumas mensagens por arquivo durante um teste:

```bash
python src/main.py --limite 20
```

5. Depois que a janela fechar (o log do consumidor mostra `janela N: ... mensagens
   tratadas e enriquecidas`), achate o resultado num arquivo por camada:

```bash
python src/main.py --consolidar
```

Gera `data/trusted/reclamacoes.parquet`, `data/delivery/reclamacoes_enriquecidas.parquet`
e `data/delivery/reclamacoes_enriquecidas.csv`.

### Conferir o resultado

```bash
ls data/trusted/reclamacoes data/delivery/reclamacoes_enriquecidas
docker compose exec postgres psql -U postgres -c "SELECT count(*) FROM cadastro.bancos"
```

### Acompanhar visualmente

| Endereço | O que mostra |
|---|---|
| `localhost:8080` | Kafka UI: tópico, partições e o JSON de cada mensagem publicada |
| `localhost:4040` | Spark UI: aba *Structured Streaming*, com cada janela e quantas linhas entraram |
| `localhost:5050` | pgAdmin (credenciais no `.env`) |

O Spark UI só existe enquanto o consumidor está rodando — ele morre junto com o job.

E uma surpresa do Kafka UI: o consumidor **não aparece** na aba *Consumers*. O Structured
Streaming não usa consumer group do Kafka — ele guarda os offsets no próprio
`checkpointLocation` e não faz commit de volta pro broker. É o que garante o controle de
reprocessamento dele, mas significa que ferramenta de monitoramento de Kafka não enxerga o
lag do job. Para ver o progresso do consumidor, use o Spark UI.

## Tratamentos

Os mesmos das atividades anteriores. O registro do *porquê* de cada um está em
[`01-etl-visual/local/TRANSFORMACOES.md`](../01-etl-visual/local/TRANSFORMACOES.md).

**Na leitura (produtor).** As reclamações são **ISO-8859-1** — sem declarar, `Instituição`
vira `Institui��o`. O cabeçalho termina com `;` sobrando, o que criaria uma 15ª coluna
vazia: as colunas são renomeadas por posição. O arquivo `2022_tri_02_nao_ha_dados.csv` é
pulado pelo nome. Nada é convertido aqui — converter CNPJ para número comeria o zero à
esquerda.

**No tratamento (trusted).** `nome_norm` e `cnpj_norm` saem da mesma normalização da
atividade 02: maiúsculas → remove sufixo (`- PRUDENCIAL`, `(conglomerado)`, `S.A.`, `LTDA`)
→ **translitera** acento (apagar faria `ECONÔMICA` virar `ECONMICA` e não casar com
`ECONOMICA`) → só alfanumérico → remove zero à esquerda do CNPJ. O índice vem em formato
brasileiro (`14.015,05`) e vira decimal, as quantidades viram inteiro, e o trimestre `1º`
vira `1`.

**No enriquecimento (delivery).** 52% das reclamações não trazem CNPJ, então o join tenta
quatro chaves, em ordem de confiança:

| # | Chave | O que é |
|---|---|---|
| 1 | `cnpj_norm` | chave real, quando existe |
| 2 | `nome_norm` | nome normalizado, igual dos dois lados |
| 3 | `nome_resolvido` | sigla resolvida pelo de-para (`BB` → `BANCO DO BRASIL`) |
| 4 | fuzzy | similaridade de nome (rapidfuzz), último recurso |

**CNPJ vazio não pode casar com CNPJ vazio.** O Banco do Brasil tem CNPJ `0` no cadastro,
que normaliza para vazio; o tratamento transforma vazio em nulo, e nulo não casa em `JOIN`.
Sem isso ele casaria com todas as reclamações sem CNPJ.

**O fuzzy foi adaptado, não copiado.** Na atividade 03 cada banco só podia casar uma vez
(o código removia o candidato da lista a cada acerto), porque lá havia uma linha por banco.
Aqui várias reclamações — uma por trimestre — apontam para o **mesmo** banco, então o
candidato permanece disponível e o mapa é montado sobre nomes distintos.

## Decisões de infraestrutura

**Kafka em KRaft, sem Zookeeper.** O Kafka 3.x acumula broker e controller no mesmo
processo, então é um container só.

**Dois listeners no broker.** O produtor roda na sua máquina e o consumidor dentro de um
container — endereços diferentes para o mesmo broker. `PLAINTEXT_HOST` responde em
`localhost:9092` e `PLAINTEXT` em `kafka:19092`. O `advertised.listeners` é o endereço que
o broker devolve ao cliente depois da primeira conexão; errar isso dá um erro confuso, em
que o cliente conecta e depois trava.

**`kafka-init` cria o tópico e sai.** Desligamos `KAFKA_AUTO_CREATE_TOPICS_ENABLE`: o
conector Kafka do Spark usa o `AdminClient` para listar partições, e esse caminho não
dispara criação automática — sem o tópico já existir, o consumidor falha com
`UnknownTopicOrPartitionException`. O `kafka-init` roda `kafka-topics.sh --create` uma vez
e o consumidor só sobe depois dele terminar (`service_completed_successfully`).

**Imagem do Spark com Java 17.** A tag `apache/spark:3.5.3-python3` vem com Python 3.8, e
o projeto usa sintaxe que só existe a partir do 3.10. A variante `java17` traz Python 3.10
de brinde. Nenhuma das duas põe `/opt/spark/bin` no `PATH`, então o `ENTRYPOINT` usa o
caminho absoluto do `spark-submit`.

**Jars baixados no build.** O conector Kafka do Spark exige quatro jars
(`spark-sql-kafka`, `spark-token-provider-kafka`, `kafka-clients`, `commons-pool2`). Ficam
no `Dockerfile` em vez de `--packages` no `spark-submit`, para não depender de rede a cada
execução.

**Checkpoint obrigatório.** Structured Streaming exige `checkpointLocation` — é onde ele
guarda os offsets já processados. Fica em `data/checkpoint/`. Apagar essa pasta faz o job
reprocessar o tópico do começo — necessário depois de qualquer mudança em configuração de
sessão Spark, porque o checkpoint também guarda essa configuração e a restaura no restart.

**`persist()` na janela.** O micro-batch é usado duas vezes (grava trusted, depois
enriquece). Sem `persist`, o Spark recalcularia a leitura e o tratamento na segunda vez.

**Idempotência: overwrite dinâmico por partição.** `foreachBatch` garante
*at-least-once* — se o job cair entre gravar e confirmar o offset, a janela é
reprocessada. Com `mode("append")` isso duplicaria; com `spark.sql.sources.partitionOverwriteMode = dynamic`, o `overwrite` substitui só as partições `ano`/`trimestre`
presentes no lote, não o diretório inteiro. Isso também absorve o outro cenário óbvio de
duplicação — rodar `python src/main.py` de novo, republicando as mesmas 918 mensagens —
porque cada rerun sobrescreve por completo as partições que toca.

A ressalva: isso só é seguro porque cada execução republica o conteúdo inteiro de cada
trimestre. Se um dia o produtor publicasse só uma fatia de um trimestre já gravado, o
overwrite apagaria o resto daquela partição. Para streaming de verdade, com dado chegando
aos poucos para o mesmo período ao longo do tempo, essa proteção não seria suficiente.
