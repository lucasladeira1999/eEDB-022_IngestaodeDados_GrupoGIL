# Entrega offline — Postgres + Apache Hop

Tudo roda na sua máquina, sem nuvem e sem custo. Siga as etapas na ordem; cada uma tem um
"como saber que deu certo" no fim.

## Como as peças se encaixam

```
dados/ (CSV, TSV)  ──►  Apache Hop (GUI no navegador)  ──►  Postgres
                              ▲                                 ▲
                              │                                 │
                             ETL                  init.sh cria db/schemas/usuário
```

| Serviço | Porta | Papel |
|---|---|---|
| `postgres` | 5432 | Banco relacional open source — o destino |
| `hop` | 8080 | Apache Hop Web, a ferramenta visual de ETL |
| `pgadmin` | 5050 | Só para conferir as tabelas no fim |

**Divisão importante:** o [`init.sh`](init.sh) cria *database, schemas e usuário*. As
**tabelas são criadas pelo próprio Hop**, porque o enunciado exige que o tratamento e a
carga sejam feitos pela ferramenta de ETL.

---

## Etapa 0 — Pré-requisitos

Só o **Docker Desktop**, rodando. Nada mais precisa estar instalado na máquina.

```powershell
docker ps
```

## Etapa 1 — Subir o banco

Todos os comandos a partir daqui são rodados **dentro de `01-etl-visual/local/`**.

```powershell
cd 01-etl-visual/local
Copy-Item .env.example .env
docker compose up -d
```

O `.env` guarda as senhas e não vai para o Git. Na primeira vez o Docker baixa as imagens;
pode demorar alguns minutos.

```powershell
docker compose ps
```

✅ *Deu certo se:* `atividade1-postgres` aparece como `healthy`.

Na primeira vez que o banco sobe, o Postgres executa sozinho o [`init.sh`](init.sh), que cria:

- database `glassdoor`
- usuário `etl`, dono do banco
- schemas `raw` (dados brutos) e `trusted` (dados tratados)

```powershell
docker compose exec postgres psql -U postgres -d glassdoor -c "\dn"
```

✅ *Deu certo se:* `raw` e `trusted` aparecem na lista.

> O `init.sh` **só roda com o banco vazio**. Se editar o arquivo depois, recomece do zero
> com `docker compose down -v` e suba de novo.

---

## Etapa 2 — Abrir o Apache Hop

```powershell
docker compose up -d hop
```

Essa imagem é grande (~1 GB), a primeira vez demora. Depois abra:

**http://localhost:8080/ui**

No rodapé da tela há dois seletores: **Project** e **Environment**. Escolha o projeto
`atividade1` e o environment `dev` — os dois já estão configurados na pasta `hop/`.
Ele abre no projeto `default`, então essa troca é necessária toda vez.

Agora teste a conexão com o banco: no painel esquerdo, em *Metadata → Relational Database
Connection*, abra a conexão `glassdoor` e clique em **Test**.

✅ *Deu certo se:* aparece a mensagem de conexão bem-sucedida. Se falhar, confira que o
host está como `postgres` (nome do container, não `localhost` — de dentro do container o
`localhost` seria ele mesmo).

> ⚠️ A senha do usuário `etl` aparece em **dois** lugares e precisa ser a mesma nos dois:
> `ETL_PASSWORD` no `.env` (que o `init.sh` usa para criar o usuário) e `PG_PASSWORD` no
> `hop/dev-config.json` (que o Hop usa para conectar). Mudou uma, mude a outra — e recrie
> o banco com `docker compose down -v`.

Os arquivos de origem estão visíveis dentro do Hop em `/files`, somente leitura.

---

## Etapa 3 — Primeiro pipeline (`raw_bancos`)

Vamos fazer o mais simples inteiro, para você pegar o ritmo da ferramenta. Ele só copia o
arquivo para o banco, sem transformar nada.

*File → New → Pipeline*, e salve como `hop/pipelines/raw_bancos.hpl`.

**1. Transform de leitura.** Clique com o botão direito no canvas → *Add a transform* →
busque **CSV file input**. Configure:

| Campo | Valor |
|---|---|
| Filename | `${FILES_DIR}/Bancos/EnquadramentoInicia_v2.tsv` |
| Delimiter | um TAB (cole um tab de verdade, ou use `\t`) |
| Enclosure | `"` |
| Header row present | marcado |

Clique em **Get Fields** — ele lê o arquivo e preenche as três colunas
(`Segmento`, `CNPJ`, `Nome`). Depois em **Preview** para ver os dados na tela. Esse ciclo
*Get Fields → Preview* é o que você vai repetir em toda leitura.

**2. Transform de escrita.** Adicione um **Table output**:

| Campo | Valor |
|---|---|
| Connection | `glassdoor` |
| Target schema | `raw` |
| Target table | `bancos` |
| Truncate table | marcado |

**3. Ligue os dois.** Passe o mouse sobre o transform de leitura, aparece uma seta —
arraste dela até o Table output.

**4. Crie a tabela.** Ainda no Table output, clique em **SQL**. O Hop *gera o CREATE TABLE*
a partir dos campos que estão chegando. Clique em **Execute**. É assim que as tabelas
nascem — você não escreve DDL na mão.

**5. Rode.** Botão ▶ (Run) na barra superior.

✅ *Deu certo se:* a linha entre os transforms mostra a contagem de registros e ambos ficam
com o ✔ verde.

---

## Etapa 4 — Os outros dois `raw`

Mesmo padrão, com as particularidades de cada arquivo.

### `raw_empregados`

Dois arquivos, separados por `|`, em UTF-8:

- `glassdoor_consolidado_join_match_v2.csv` → tem a coluna `Segmento`
- `glassdoor_consolidado_join_match_less_v2.csv` → tem a coluna `CNPJ`

Como as colunas diferem, o mais limpo é **um CSV file input para cada**, ambos apontando
para o mesmo `Table output` em `raw.empregados` — deixe o Hop juntar o que for comum, ou
carregue em duas tabelas (`raw.empregados_cnpj` e `raw.empregados_segmento`) se preferir
não misturar. As notas usam **vírgula decimal**; deixe tudo como String no `raw`, a
conversão fica para a etapa 6.

### `raw_reclamacoes`

São 8 arquivos trimestrais e aqui moram as pegadinhas:

- encoding **ISO-8859-1** (não UTF-8 — se errar, aparece `Institui��o`)
- separador `;`
- cada linha **termina com `;`**, o que cria uma coluna vazia extra no fim
- `2022_tri_02_nao_ha_dados.csv` está **vazio** (0 bytes)

Em vez de 8 transforms, use dois em sequência:

1. **Get file names** — Directory: `${FILES_DIR}/Reclamações`, Wildcard (regex): `.*\.csv`
2. **Text file input** — na aba *File*, marque **"Accept filenames from previous step"** e
   escolha o Get file names como origem. Na aba *Content*: separador `;`,
   **Encoding `ISO-8859-1`**. Na aba *Fields*, use *Get Fields*.

Assim os 8 trimestres entram de uma vez e o arquivo vazio é ignorado sozinho. Ligue no
`Table output` → `raw.reclamacoes`.

✅ *Deu certo se:* o preview mostra acentuação correta ("Instituição", "Índice") e a
contagem bate com a soma das linhas dos arquivos.

---

## Etapa 5 — O pipeline de tratamento (`trusted_banco_final`)

Aqui é onde o "tratamento pela ferramenta de ETL" realmente acontece. O objetivo é uma
tabela única unindo as três fontes.

**O problema central:** as três bases identificam o mesmo banco de jeitos diferentes.

| Fonte | Como aparece |
|---|---|
| Bancos | `ITAU - PRUDENCIAL`, CNPJ `60872504` |
| Reclamações | `ITAÚ (conglomerado)`, CNPJ às vezes vazio |
| Empregados | `Itaú Unibanco`, CNPJ com pontuação |

Então a maior parte do trabalho é **normalizar a chave antes de juntar**:

1. **CNPJ** — *Replace in string* com regex `[^0-9]` → `""` (tira ponto, barra, traço).
   Depois *Select values* convertendo para Integer e voltando a String, para eliminar
   zeros à esquerda inconsistentes.
2. **Nome** — *String operations* (Trim: both, Upper case) e um *Replace in string*
   removendo ` - PRUDENCIAL`, ` (conglomerado)`, ` S.A.`, ` S/A`.
3. **Números** — *Replace in string* trocando `,` por `.` nos índices e notas, depois
   *Select values* → aba *Meta-data* convertendo para Number. Descarte aqui a coluna vazia
   das reclamações.
4. **Agregar reclamações** — há várias linhas por banco (uma por trimestre). Use
   *Sort rows* pela chave e depois *Group by*: soma das quantidades, média do índice.
   ⚠️ O *Group by* do Hop **exige entrada ordenada** — sem o Sort antes, o resultado sai
   errado silenciosamente.
5. **Juntar** — *Merge join* tipo LEFT, partindo de `bancos` (a lista oficial) e trazendo
   reclamações e empregados. Merge join também **exige as duas entradas ordenadas** pela
   chave. Se a junção por nome ficar ruim, o *Fuzzy match* é uma alternativa — mas
   documente o critério que usou.
6. **Gravar** — *Table output* → schema `trusted`, tabela **`banco_final`**, botão SQL para
   criar, e rode.

✅ *Deu certo se:* `trusted.banco_final` tem uma linha por banco e os campos de reclamação
e Glassdoor estão preenchidos para a maioria. Nem todos vão casar — bancos sem reclamação
ou sem página no Glassdoor ficam nulos, e isso é esperado.

---

## Etapa 6 — Amarrar tudo num Workflow

*File → New → Workflow*, salve como `hop/workflows/main.hwf`. Adicione um **Start**, depois
quatro ações **Pipeline** apontando para os `.hpl`, ligadas em sequência:

```
Start → raw_bancos → raw_empregados → raw_reclamacoes → trusted_banco_final
```

É o que você executa para reprocessar tudo do zero, e rende um bom print para a entrega.

---

## Etapa 7 — Conferir o resultado

Abra o pgAdmin em **http://localhost:5050** (login do `.env`) e conecte em host `postgres`,
usuário `postgres`. Ou direto pelo terminal:

```powershell
docker compose exec postgres psql -U postgres -d glassdoor -c "SELECT count(*) FROM trusted.banco_final;"
docker compose exec postgres psql -U postgres -d glassdoor -c "SELECT * FROM trusted.banco_final LIMIT 10;"
```

---

## Comandos do dia a dia

```powershell
docker compose ps            # o que está de pé
docker compose logs -f hop   # ver erro do Hop
docker compose stop          # pausar (mantém os dados)
docker compose down          # remover containers (mantém os dados no volume)
docker compose down -v       # apagar TUDO, inclusive o banco
```

## Referência das fontes

| Fonte | Caminho no Hop | Separador | Encoding |
|---|---|---|---|
| Bancos | `${FILES_DIR}/Bancos/EnquadramentoInicia_v2.tsv` | TAB | UTF-8 |
| Empregados | `${FILES_DIR}/Empregados/glassdoor_*.csv` | `\|` | UTF-8 |
| Reclamações | `${FILES_DIR}/Reclamações/*.csv` | `;` | ISO-8859-1 |
