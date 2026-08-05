# Tratamento dos dados — atividade 01

Registro de tudo que os pipelines fazem com o dado, e por quê. Todo o tratamento é
executado por transforms do Apache Hop; não há SQL de transformação em lugar nenhum.

## Camadas

```
arquivos            raw                  trusted                 delivery
(CSV/TSV)     fiel à origem        limpo e tipado,           modelo final
              tudo texto           uma tabela por fonte      (join das três)
```

| Camada | Tabela | Linhas |
|---|---|---|
| raw | `bancos`, `empregados`, `reclamacoes` | 1474 · 39 · 918 |
| trusted | idem | 1474 · 39 · 918 |
| delivery | `banco_final` | 1470 |

---

## Pipelines

| Arquivo | O que faz |
|---|---|
| `workflows/cria_tabelas.hwf` | cria as 7 tabelas; DDL gerado pelo botão SQL dos Table outputs e consolidado num script idempotente |
| `workflows/carga_completa.hwf` | encadeia os 7 pipelines na ordem; cada etapa só dispara se a anterior deu certo |
| `raw_bancos.hpl` | lê o TSV separado por TAB |
| `raw_empregados.hpl` | lê os 2 CSV separados por `\|` e os une num stream só |
| `raw_reclamacoes.hpl` | lê os 7 CSV trimestrais em ISO-8859-1 |
| `trusted_bancos.hpl` | normaliza chave |
| `trusted_empregados.hpl` | normaliza chave + converte notas para número |
| `trusted_reclamacoes.hpl` | normaliza chave + converte índice e quantidades |
| `delivery_banco_final.hpl` | agrega reclamações e junta as três fontes |

---

## Tratamentos na ingestão (`raw`)

**Encoding.** As reclamações são **ISO-8859-1**; declarado no Text file input. Sem isso
`Instituição` vira `Institui��o`. Bancos e Empregados são UTF-8 e usam o padrão.

**Separador TAB.** O arquivo de bancos usa TAB. O campo Delimiter não aceita `\t`
digitado — é preciso o botão *Insert TAB* do Text file input.

**Coluna fantasma.** Toda linha das reclamações termina com `;`, o que cria uma 15ª
coluna sempre vazia. Confirmado que tem 0 valores não-nulos em 918 linhas, e removida
na leitura: é artefato do delimitador, não dado.

**Arquivo vazio.** `2022_tri_02_nao_ha_dados.csv` tem 0 bytes e quebraria a leitura por
falta de cabeçalho. Excluído pela máscara `.*nao_ha_dados.*`.

**Colunas diferentes entre os dois arquivos do Glassdoor.** São 23 colunas em cada, e só
a 21ª difere: `Segmento` num, `CNPJ` no outro. Um *Add constants* cria a coluna que falta
em cada ramo (o Hop só une streams com os mesmos campos) e um *Select values* alinha a
ordem. O campo `origem` registra de qual arquivo veio a linha.

**Tudo entra como texto.** Nenhuma conversão de tipo no `raw`: CNPJ com zero à esquerda
viraria número e perderia o zero, e número com vírgula decimal falharia. Conversão é
assunto da `trusted`.

---

## Normalização da chave (`trusted`)

O problema central: as três fontes escrevem o mesmo banco de formas diferentes.

| Fonte | Como aparece |
|---|---|
| Bancos | `BRADESCO - PRUDENCIAL` |
| Reclamações | `CREDIT SUISSE (conglomerado)` |
| Empregados | `BANCO FIBRA S.A.` |

A mesma cadeia de 7 transforms roda nas três, produzindo `nome_norm` e `cnpj_norm`:

| # | Transform | O que faz |
|---|---|---|
| 1 | `maiusculas` | trim + UPPER |
| 2 | `tira_sufixos` | remove `- PRUDENCIAL`, `(conglomerado)`, `S.A.`, `LTDA`; deixa só dígitos no CNPJ |
| 3 | `tira_acentos` | `Á`→`A`, `Ç`→`C`, … |
| 4 | `so_alfanumerico` | remove o que sobrou fora de `A-Z0-9 ` |
| 5 | `espaco_unico` | colapsa espaços; remove zeros à esquerda do CNPJ |
| 6 | `trim_final` | limpa as bordas |
| 7 | `define_tamanhos` | fixa `nome_norm` em 255 e `cnpj_norm` em 20 |

Três desses passos existem por um motivo que só aparece testando:

**Acento é transliterado, não apagado.** Bancos escreve `CAIXA ECONOMICA FEDERAL` sem
acento; reclamações escreve `CAIXA ECONÔMICA FEDERAL`. Apagando o `Ô` daria `ECONMICA` de
um lado e `ECONOMICA` do outro — não casariam. Transliterando, os dois viram `ECONOMICA`.

**Zeros à esquerda do CNPJ.** Bancos grava `360305`, reclamações grava `00360305`. Sem
remover os zeros, o mesmo CNPJ não casa. Essa correção sozinha levou o casamento por CNPJ
de 39 para 75 bancos.

**Tamanho explícito de campo.** O Hop cria campo texto novo com 100 caracteres por padrão,
e há nome de banco com 200. Sem o passo 7, a gravação falha com
`value too long for character varying(100)`.

### Conversão de tipos

| Campo | Origem | Tratamento |
|---|---|---|
| notas do Glassdoor | `3.8` | já com ponto decimal → `Number(9,2)` |
| `indice` | `15,52` e `14.015,05` | remove espaço, remove ponto de milhar, vírgula → ponto → `Number(9,2)` |
| quantidades | `5538591` | → `Integer(12)` |

O índice vem como `' '` (um espaço) quando não há valor; o espaço é removido antes da
conversão, e o campo vazio vira nulo.

---

## Junção (`delivery`)

O CNPJ é a chave confiável, mas **52% das reclamações não têm CNPJ**. Então cada banco é
procurado duas vezes:

```
trusted.bancos ──┬─→ busca_por_cnpj  (contra reclamações agregadas por CNPJ)
                 └─→ busca_por_nome  (contra reclamações agregadas por nome)
                              ↓
                     NVL(cnpj, nome) → usa o resultado do CNPJ; se nulo, o do nome
```

Usei *Stream lookup* em vez de *Merge join* porque não exige entrada ordenada e não
descarta linha sem correspondência — banco sem reclamação entra na tabela com campos nulos.

**Agregação.** As reclamações vêm por banco × trimestre; o *Group by* soma as quantidades,
tira a média do índice e conta os trimestres. O Group by do Hop exige entrada ordenada
pelo campo de agrupamento, garantido pelo `ORDER BY` na leitura.

**Duplicatas do cadastro.** 4 bancos aparecem duas vezes no arquivo de origem — a visão do
conglomerado e a instituição individual (`BANCO DO BRASIL - PRUDENCIAL` e
`BANCO DO BRASIL S/A`). Um *Unique rows* mantém uma linha por banco: 1474 → 1470.

**CNPJ vazio não casa com CNPJ vazio.** O Banco do Brasil tem CNPJ `0` no cadastro, que
após a limpeza vira vazio — e casava com todas as reclamações sem CNPJ, acumulando 44
conglomerados numa linha só (428 mil reclamações, 200 trimestres). A leitura do ramo por
CNPJ agora filtra registros sem CNPJ.

---

## Cobertura da junção

| | |
|---|---|
| Bancos no cadastro | 1470 |
| Com dados de reclamação | 119 |
| Com notas do Glassdoor | 33 |
| Com as duas fontes | 25 |

Dos 217 bancos distintos nas reclamações, 125 casam com o cadastro. Os 92 restantes são
ausências legítimas: instituições de pagamento (Ame Digital, Acesso Soluções, PicPay) que
não constam do cadastro de bancos prudenciais, e registros agregados por conglomerado sem
CNPJ.

---

## Limitações conhecidas

**Acentuação destruída na origem.** `EnquadramentoInicia_v2.tsv` chega com 3109 ocorrências
de `U+FFFD` (`�`) no lugar de acentos — `AF PARAN�` deveria ser `AF PARANÁ`. A mesma
corrupção está no `_original.zip`, então é anterior a este repositório. Não é recuperável:
todos os acentos viraram o mesmo caractere, sem como distinguir `Á` de `Ã`. Verificável com
`python scripts/check_encoding.py dados/Bancos/EnquadramentoInicia_v2.tsv`.

Isso não afeta a junção, porque o `�` é removido junto com a pontuação. Afeta a
apresentação do nome na tabela final.

**Abreviações não casam.** Nas reclamações o Banco do Brasil aparece como
`BB (conglomerado)`. `BB` não casa com `BANCO DO BRASIL` por nenhuma regra de
normalização — só uma tabela de-para resolveria. É o principal banco fora da junção.

**Nome de pasta corrompido no unzip.** A pasta das reclamações vinha como `ReclamaçΣes` no
Windows (o zip não guarda o encoding dos nomes). Renomeada para `Reclamacoes`, sem acento,
para não depender do sistema operacional de quem clonar.
