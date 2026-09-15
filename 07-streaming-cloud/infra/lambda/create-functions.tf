# No AWS Academy nao da pra criar IAM role, entao as Lambdas usam a LabRole
# que ja vem pronta na conta (mesmo padrao usado com o Redshift na atividade 02).
data "aws_iam_role" "lab" {
  name = "LabRole"
}

resource "aws_lambda_function" "produtor" {
  function_name    = var.produtor_function_name
  role             = data.aws_iam_role.lab.arn
  handler          = "produtor.job.lambda_handler"
  runtime          = var.runtime
  filename         = var.produtor_zip
  source_code_hash = filebase64sha256(var.produtor_zip)
  timeout          = 300
  memory_size      = 512

  environment {
    variables = {
      RAW_BUCKET = var.raw_bucket
      RAW_PREFIX = var.raw_prefix
      QUEUE_URL  = var.queue_url
    }
  }
}

resource "aws_lambda_function" "consumidor" {
  function_name    = var.consumidor_function_name
  role             = data.aws_iam_role.lab.arn
  handler          = "consumidor.job.lambda_handler"
  runtime          = var.runtime
  filename         = var.consumidor_zip
  source_code_hash = filebase64sha256(var.consumidor_zip)
  timeout          = var.consumidor_timeout
  memory_size      = 512

  environment {
    variables = {
      TRUSTED_BUCKET  = var.trusted_bucket
      DELIVERY_BUCKET = var.delivery_bucket
      DB_HOST         = var.db_host
      DB_PORT         = var.db_port
      DB_NAME         = var.db_name
      DB_USER         = var.db_user
      DB_PASSWORD     = var.db_password
    }
  }
}

# é isso que liga a fila no consumidor: o proprio Lambda faz o polling do SQS.
# ReportBatchItemFailures faz com que só a mensagem que falhou volte pra fila,
# em vez do lote inteiro.
resource "aws_lambda_event_source_mapping" "sqs_para_consumidor" {
  event_source_arn        = var.queue_arn
  function_name           = aws_lambda_function.consumidor.arn
  batch_size              = 10
  function_response_types = ["ReportBatchItemFailures"]
}

output "produtor_function_name" {
  value = aws_lambda_function.produtor.function_name
}

output "consumidor_function_name" {
  value = aws_lambda_function.consumidor.function_name
}
