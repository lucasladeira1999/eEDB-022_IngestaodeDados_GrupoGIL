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

A infraestrutura AWS (ex: buckets S3) é criada via Terraform, na pasta `infra/`.

```bash
cd infra
terraform init
terraform plan
terraform apply
```

## Como usar

1. Instale as dependências:

```bash
pip install -r requirements.txt
```

2. Configure os caminhos em `src/config.yaml`:

```yaml
dados_path: "/caminho/para/dados"
raw_bucket: "nome-do-bucket-s3"
```

3. Execute o job:

```bash
python src/main.py
```

Isso envia todos os arquivos da pasta `dados_path` para o bucket S3 configurado, mantendo a mesma estrutura de pastas.

