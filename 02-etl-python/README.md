# 02-etl-python

Requisito: ingerir as três bases em um banco relacional open source e gerar uma tabela
final tratada e unida, com o tratamento feito **em Python** (sem SQL).

Pipeline: S3 (raw → trusted em Parquet → delivery) → Redshift, orquestrado por
`src/main.py` em 4 jobs sequenciais. Infra provisionada via Terraform (`infra/`).

## Setup AWS

O boto3 precisa de credenciais AWS configuradas na máquina. A forma mais simples é via AWS CLI:

```bash
aws configure
```

Informe `Access Key ID`, `Secret Access Key` e a região (ex: `us-east-1`).

Isso salva as credenciais em `~/.aws/credentials`, que o boto3 usa automaticamente.

## IaC (Terraform)

A infraestrutura AWS (buckets S3 de raw/trusted/delivery e o cluster Redshift) é criada via Terraform, na pasta `infra/`.

```bash
cd infra
terraform init
terraform plan
terraform apply
```

Preencha as variáveis obrigatórias em `infra/terraform.tfvars` (nomes dos buckets, identificador do cluster, usuário e senha admin do Redshift) antes de aplicar.

## Como usar

1. Instale as dependências:

```bash
pip install -r requirements.txt
```

1. Copie `src/config.example.yaml` para `src/config.yaml`:

```bash
cp src/config.example.yaml src/config.yaml
```

Edite o `src/config.yaml` com o endpoint do *seu* cluster Redshift. O `redshift_user` e `redshift_password` devem ser os mesmos valores definidos em `redshift_admin_username` e `redshift_admin_password` no `infra/terraform.tfvars`.

O `redshift_host` é obtido depois que o `terraform apply` criar o cluster (Terraform não expõe esse valor como output no momento, então é preciso consultar a AWS):

- **Console**: AWS Console → Redshift → Clusters → selecione o cluster (`eedb-022-grupo03`) → em "General information", copie o campo **Endpoint**.
- **AWS CLI**:

```bash
aws redshift describe-clusters \
  --cluster-identifier eedb-022-grupo03 \
  --query 'Clusters[0].Endpoint.Address' \
  --output text
```
> Exemplo de saída:
```
eedb-022-grupo03.ct3ja6yhrepn.us-east-1.redshift.amazonaws.com
```
Use apenas o hostname (sem `:porta/database` no final) em `redshift_host` — a porta e o database já são informados separadamente em `redshift_port` e `redshift_database`.

O `redshift_iam_role` é o ARN da `LabRole` da conta AWS Academy — o Terraform já anexa essa role ao cluster automaticamente (via `data "aws_iam_role" "lab"` em `infra/redshift/create-database.tf`), e o `to_redshift` job usa ela pra rodar `COPY` direto do S3 pro Redshift. Pra pegar o ARN depois do `terraform apply`:

```bash
cd infra
terraform output redshift_iam_role_arn
```

Cole o valor retornado no campo `redshift_iam_role` do `config.yaml`.

1. Execute o pipeline:

```bash
python src/main.py
```

O `main.py` roda, em sequência, os 4 jobs definidos em `src/`:

1. **`to_raw`**: envia todos os arquivos da pasta `dados_path` para o bucket `raw_bucket`, mantendo a mesma estrutura de pastas.
2. **`to_trusted`**: lê os arquivos do `raw_bucket`, limpa/padroniza os dados (normaliza nome/CNPJ, converte tipos) e grava um `.parquet` por fonte (`bancos`, `empregados`, `reclamacoes`) no `trusted_bucket`.
3. **`to_delivery`**: lê os 3 parquets do `trusted_bucket` e junta as fontes (`to_delivery/join.py`: agrega reclamações por banco, casa por CNPJ e, quando falta, por nome com fuzzy matching + resolução de siglas, remove duplicatas do cadastro priorizando `cnpj_norm` como chave) num único `bancos_indicadores.parquet` no `delivery_bucket` — a tabela final tratada e unida (OBT) que a atividade exige. Além dos campos originais, calcula indicadores derivados (`reclamacao_indice_calculado`: reclamações por cliente via CCS/SCR; `reclamacao_pct_procedentes`: % de reclamações procedentes) e traz as 9 avaliações do Glassdoor (`avaliacao_geral`, `avaliacao_cultura`, `avaliacao_diversidade`, `avaliacao_qualidade_vida`, `avaliacao_lideranca`, `avaliacao_remuneracao`, `avaliacao_carreira`, `avaliacao_recomendam_pct`, `avaliacao_perspectiva_pct`).
4. **`to_redshift`**: para cada `.parquet` do `delivery_bucket` (hoje só `bancos_indicadores.parquet`), cria a tabela correspondente no Redshift caso não exista (`CREATE TABLE IF NOT EXISTS`, com o schema inferido a partir do DataFrame) e carrega os registros via `COPY ... IAM_ROLE ... FORMAT AS PARQUET` (bulk load direto do S3, bem mais rápido que inserir linha a linha). O DDL é gerado por `src/sql_schema.py`, módulo compartilhado com o `to_delivery` (debug via Postgres) para manter os dois caminhos com o mesmo schema.

Para rodar apenas alguns jobs, comente as chamadas correspondentes em `src/main.py`.

### Debug local opcional: espelhar no Postgres da atividade 01

Se `postgres_uri` estiver definido no `config.yaml`, o `to_delivery` também grava o
`bancos_indicadores` num Postgres local (o mesmo `docker-compose` da
[`01-etl-visual`](../01-etl-visual/)), pra comparar lado a lado com o resultado do Apache
Hop. É opcional — não faz parte da entrega desta atividade (que é S3 → Redshift) e não roda
se a chave não existir no config.

### Legado: `src/s3_trusted/`

Os arquivos `.parquet` em `src/s3_trusted/` são resultado de um teste local antigo (execução
do `to_trusted` sem S3) e não são lidos por nenhum job do pipeline atual — o `to_delivery`
sempre baixa os parquets direto do `trusted_bucket` no S3. Mantidos por ora só como histórico;
candidatos a remoção numa limpeza futura.
