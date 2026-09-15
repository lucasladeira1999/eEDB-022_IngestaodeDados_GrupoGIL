resource "aws_sqs_queue" "dlq" {
  name                      = "${var.queue_name}-dlq"
  message_retention_seconds = 1209600 # 14 dias
}

resource "aws_sqs_queue" "this" {
  name = var.queue_name

  # precisa ser maior que o timeout da Lambda consumidora, senao a mesma mensagem
  # volta a ficar visivel enquanto ainda esta sendo processada
  visibility_timeout_seconds = var.visibility_timeout_seconds

  # mensagem que falha 3 vezes sai da fila principal e vai pra DLQ, em vez de
  # ficar em loop infinito bloqueando o processamento
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

output "queue_url" {
  value = aws_sqs_queue.this.url
}

output "queue_arn" {
  value = aws_sqs_queue.this.arn
}

output "dlq_url" {
  value = aws_sqs_queue.dlq.url
}
