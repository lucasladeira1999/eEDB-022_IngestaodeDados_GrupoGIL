# 07-streaming-cloud

Requisito: ingerir as reclamações em **streaming** na AWS — uma Lambda produtora lê o S3 e
publica numa fila SQS; uma Lambda consumidora lê a fila, consulta um **banco de dados SQL**
para enriquecer cada mensagem e grava o resultado de volta no S3.


## Arquitetura

```
dados/                                                    ┌──────────────┐
  │                                                       │ RDS Postgres │
  │ to_raw (local)                                        │   (bancos)   │
  ▼                                                       └──────┬───────┘
S3 raw ──► Lambda produtor ──► SQS ──► Lambda consumidor ◄───────┘
           (lê CSV,            │       (trata + enriquece)
            publica)           │              │
                               ▼              ├──► S3 trusted   (mensagem tratada)
                             DLQ              └──► S3 delivery  (mensagem enriquecida)
```

As camadas do repositório continuam valendo, só que registro a registro em vez de lote:

| Camada | Onde | O que é |
|---|---|---|
| raw | `S3 raw` | os CSV/TSV originais, fiéis à origem |
| trusted | `S3 trusted` | a reclamação com chave normalizada e tipos convertidos |
| delivery | `S3 delivery` | a reclamação tratada + segmento e nome do banco |

O cadastro de bancos vai para o **RDS** porque é ele que responde a consulta de
enriquecimento

## Estrutura

```
infra/            IaC (Terraform): buckets, fila, RDS e as duas Lambdas
  s3/ sqs/ rds/ lambda/
src/
  main.py         roda o que é local e dispara o streaming
  to_raw/job.py   dados/ → S3 raw
  to_rds/job.py   S3 raw → tabela bancos     (a fonte do enriquecimento)
  produtor/job.py    Lambda: S3 raw → SQS
  consumidor/job.py  Lambda: SQS → trusted → delivery
  to_trusted/job.py  trata a mensagem  → S3 trusted
  to_delivery/job.py enriquece no SQL  → S3 delivery
  sql_schema.py   schema da tabela bancos num lugar só
  acronyms.yaml   de-para de sigla → nome canônico
```

Infra separada de código pelo motivo de sempre: ciclos de vida, ferramentas e permissões
diferentes. `src/` como raiz da aplicação deixa o empacotamento das Lambdas previsível.

## Como usar

1. Instale as dependências:

```bash
pip install -r requirements.txt
```

2. Empacote as Lambdas (gera `build/*.zip`, que o Terraform publica):

```bash
./build.sh
```

Rode de novo sempre que mexer em `src/` — o Terraform compara o hash do zip e só atualiza a
função se o pacote mudou.

3. Suba a infra:

```bash
cd infra
terraform init
terraform apply
```

4. Copie `src/config.example.yaml` para `src/config.yaml` e preencha com as saídas do apply:

```bash
cp src/config.example.yaml src/config.yaml
cd infra && terraform output
```

O `db_host` é o `rds_host` do output (só o hostname, sem porta). `db_user`/`db_password`
precisam bater com `rds_admin_username`/`rds_admin_password` do `infra/terraform.tfvars`.

5. Rode o pipeline:

```bash
python src/main.py
```

O `main.py` executa, nesta ordem:

1. **`to_raw`** — sobe todos os arquivos de `dados_path` para o bucket raw, mantendo a
   estrutura de pastas. Igual ao da atividade 02.
2. **`to_rds`** — lê o cadastro de bancos do raw, normaliza as chaves e carrega a tabela
   `bancos` no RDS via `COPY` (uma viagem de rede em vez de 1.400 inserts).
3. **dispara o produtor** — invoca a Lambda produtora, que lê os CSV de reclamações do raw
   e publica uma mensagem por linha no SQS (`send_message_batch`, 10 por chamada).

A ordem importa: `to_rds` depende dos arquivos que o `to_raw` subiu, e a tabela `bancos`
precisa existir **antes** de a fila começar a encher — senão o consumidor consome mensagem
sem ter onde buscar o enriquecimento.

A partir daí é assíncrono: o SQS entrega lotes de até 10 mensagens para a Lambda
consumidora, que para **cada** mensagem roda o tratamento (trusted), consulta o RDS e grava
o resultado (delivery).

### Acompanhar a execução

```bash
aws logs tail /aws/lambda/eedb-022-grupo03-consumidor --follow
aws s3 ls s3://eedb-022-2026-grupo03-stream-delivery/reclamacoes_enriquecidas/ --recursive | wc -l
```

## Tratamentos

Os mesmos das atividades anteriores, agora aplicados por mensagem. O registro completo do
*porquê* de cada um está em [`01-etl-visual/local/TRANSFORMACOES.md`](../01-etl-visual/local/TRANSFORMACOES.md).

**Na leitura (produtor).** As reclamações são **ISO-8859-1** — sem declarar, `Instituição`
vira `Institui��o`. O cabeçalho termina com `;` sobrando, o que cria uma 15ª coluna sempre
vazia: as colunas são renomeadas por posição e o excedente é ignorado. O arquivo
`2022_tri_02_nao_ha_dados.csv` é pulado pelo nome. Nada é convertido aqui: no raw tudo é
texto, porque converter CNPJ para número comeria o zero à esquerda.

**No tratamento (trusted).** `nome_norm` e `cnpj_norm` saem da mesma normalização da
atividade 02 (`to_trusted/etl/normalize.py`): maiúsculas → remove sufixo (`- PRUDENCIAL`,
`(conglomerado)`, `S.A.`, `LTDA`) → **translitera** acento (apagar faria `ECONÔMICA` virar
`ECONMICA` e não casar com `ECONOMICA`) → só alfanumérico → remove zero à esquerda do CNPJ
(`00360305` = `360305`). O índice vem em formato brasileiro (`14.015,05`) e vira decimal;
as quantidades viram inteiro; o trimestre `1º` vira `1`, que é o que entra na chave do S3.

**No enriquecimento (delivery).** **52% das reclamações não trazem CNPJ**, então a consulta
tenta três chaves, em ordem de confiança:

| # | Consulta | Cobertura |
|---|---|---|
| 1 | `cnpj_norm` | 35% |
| 2 | `nome_norm` (exato) | 30% |
| 3 | `nome_resolvido` (sigla resolvida) | 5% |
| — | sem correspondência | 30% |

O passo 3 é o de-para que o `TRANSFORMACOES.md` da atividade 01 já previa ("só uma tabela
de-para resolveria"): `BB` → `BANCO DO BRASIL`. Ele é aplicado **dos dois lados** — o
`to_rds` grava o cadastro já com `nome_resolvido`, e a reclamação é resolvida na hora da
consulta, então sigla compara com sigla.

Um detalhe que já custou caro na atividade 01: **CNPJ vazio não pode casar com CNPJ vazio**.
O Banco do Brasil tem CNPJ `0` no cadastro, que normaliza para vazio; sem a guarda, ele
casaria com todas as reclamações sem CNPJ. Por isso a consulta por CNPJ só roda quando o
campo tem conteúdo.

Os 30% restantes são ausências legítimas (instituições de pagamento que não constam do
cadastro prudencial) ou nomes que só *fuzzy matching* resolveria — que aqui ficaria fora do
banco, e a atividade pede que o enriquecimento seja uma consulta SQL.

## Decisões de infraestrutura

**Buckets criados pelo AWS CLI, não pelo `aws_s3_bucket`.** A service control policy do
Academy nega `s3:GetBucketObjectLockConfiguration`, e o provider faz essa chamada toda vez
que lê um bucket — logo depois de criar e em cada refresh. O resultado é que o bucket sobe
mas o `apply` quebra em seguida com `AccessDenied`, e o mesmo erro volta em todo
`plan`/`apply`/`destroy` seguinte. O módulo `infra/s3/` então cria os buckets via
`aws s3api create-bucket` dentro de um `terraform_data`, mantendo a mesma interface (entra
`bucket_name`, sai `bucket_name`) para o resto do Terraform não precisar saber disso. O
`provisioner` de destroy faz o papel do antigo `force_destroy`. Não é elegante, mas é o
preço de rodar num ambiente com policy restritiva — e fixar a versão do provider **não**
resolve: foi a primeira hipótese testada e o erro é idêntico na 6.58.0 e na 6.64.0.

**Lambda fora da VPC + RDS público.** Lambda dentro de VPC não alcança o S3 sem VPC
endpoint. Como as duas funções precisam do S3, elas ficam fora da VPC e falam com o RDS pelo
endpoint público. O security group libera 5432 para `0.0.0.0/0` — aceitável num lab, não em
produção, onde isso seria restrito à VPC.

**LabRole.** O AWS Academy não deixa criar IAM role, então as Lambdas usam a `LabRole` que
já vem na conta, buscada por `data "aws_iam_role"` — o mesmo padrão que a atividade 02 usa
no Redshift, e que mantém o Terraform portável entre as contas do grupo.

**DLQ + falha parcial.** A fila tem *dead-letter queue* com `maxReceiveCount = 3`: mensagem
que falha três vezes sai de circulação em vez de travar o processamento. O consumidor
responde `batchItemFailures`, então só a mensagem com erro volta para a fila — o resto do
lote de 10 segue.

**Conexão reaproveitada.** A conexão com o RDS fica no escopo do módulo, fora do handler:
abrir conexão por mensagem seria o gargalo do pipeline. O `visibility_timeout` da fila (180s)
é maior que o timeout da Lambda (60s), senão a mesma mensagem voltaria a ficar visível
enquanto ainda está sendo processada.

## Lembretes do AWS Academy

As credenciais são temporárias e a conta é destruída no fim da sessão — `terraform apply` do
zero a cada aula, e `src/config.yaml` precisa ser atualizado com o novo `rds_host` (o
endpoint muda). Rode `terraform destroy` **antes** de encerrar o lab: depois de "End Lab" as
credenciais são revogadas no meio do caminho.
