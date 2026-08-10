# 02-etl-python

TODO: ADICIONAR CONTEXTO

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

2. Copie `src/config.example.yaml` para `src/config.yaml` (esse último é local, ignorado pelo Git, então cada dev mantém o seu sem conflitar com o dos colegas):

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

O `redshift_iam_role` é o ARN da `LabRole` da *sua* conta AWS Academy — o Terraform já anexa essa role ao cluster automaticamente (via `data "aws_iam_role" "lab"` em `infra/redshift/create-database.tf`), e o `to_redshift` job usa ela pra rodar `COPY` direto do S3 pro Redshift. Pra pegar o ARN depois do `terraform apply`:

```bash
cd infra
terraform output redshift_iam_role_arn
```

Cole o valor retornado no campo `redshift_iam_role` do `config.yaml`.

3. Execute o pipeline:

```bash
python src/main.py
```

O `main.py` roda, em sequência, os 4 jobs definidos em `src/`:

1. **`to_raw`**: envia todos os arquivos da pasta `dados_path` para o bucket `raw_bucket`, mantendo a mesma estrutura de pastas.
2. **`to_trusted`**: lê os arquivos do `raw_bucket`, limpa/padroniza os dados e grava um `.parquet` por fonte no `trusted_bucket`.
3. **`to_delivery`**: copia todos os objetos do `trusted_bucket` para o `delivery_bucket`.
4. **`to_redshift`**: para cada `.parquet` do `delivery_bucket`, cria a tabela correspondente no Redshift caso não exista (`CREATE TABLE IF NOT EXISTS`, com o schema inferido a partir do DataFrame) e carrega os registros via `COPY ... IAM_ROLE ... FORMAT AS PARQUET` (bulk load direto do S3, bem mais rápido que inserir linha a linha).

Para rodar apenas alguns jobs, comente as chamadas correspondentes em `src/main.py`.
