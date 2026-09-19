# variante java17: traz Python 3.10. A tag "3.5.3-python3" vem com Python 3.8, onde
# anotação como dict[str, dict] quebra em runtime.
FROM apache/spark:3.5.3-java17-python3

USER root
WORKDIR /app

ARG SPARK_VERSION=3.5.3
ARG MAVEN=https://repo1.maven.org/maven2

# jars baixados no build em vez de --packages no spark-submit: sem download a cada
# execução e sem depender de rede pra subir o job
RUN curl -sSL -o /opt/spark/jars/postgresql.jar \
      https://jdbc.postgresql.org/download/postgresql-42.7.4.jar && \
    curl -sSL -o /opt/spark/jars/spark-sql-kafka.jar \
      ${MAVEN}/org/apache/spark/spark-sql-kafka-0-10_2.12/${SPARK_VERSION}/spark-sql-kafka-0-10_2.12-${SPARK_VERSION}.jar && \
    curl -sSL -o /opt/spark/jars/spark-token-provider-kafka.jar \
      ${MAVEN}/org/apache/spark/spark-token-provider-kafka-0-10_2.12/${SPARK_VERSION}/spark-token-provider-kafka-0-10_2.12-${SPARK_VERSION}.jar && \
    curl -sSL -o /opt/spark/jars/kafka-clients.jar \
      ${MAVEN}/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar && \
    curl -sSL -o /opt/spark/jars/commons-pool2.jar \
      ${MAVEN}/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar

# o Spark lê este arquivo sozinho de $SPARK_HOME/conf
COPY log4j2.properties /opt/spark/conf/log4j2.properties

COPY requirements-spark.txt /app/requirements-spark.txt
RUN pip install --no-cache-dir -r /app/requirements-spark.txt

COPY src/ /app/src/

ENV PYTHONPATH=/app/src
# a imagem não põe /opt/spark/bin no PATH
ENV PATH="${PATH}:/opt/spark/bin"

ENTRYPOINT ["/opt/spark/bin/spark-submit", "--master", "local[*]", "/app/src/consumidor/job.py"]
