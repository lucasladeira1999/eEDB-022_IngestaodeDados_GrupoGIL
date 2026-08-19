FROM apache/spark:3.5.3-python3

USER root
WORKDIR /app

# driver JDBC do Postgres, para o Spark conseguir ler/gravar via .jdbc()
RUN curl -sSL -o /opt/spark/jars/postgresql-42.7.4.jar https://jdbc.postgresql.org/download/postgresql-42.7.4.jar

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src/ /app/src/

ENV PYTHONPATH=/app/src

ENTRYPOINT ["spark-submit", "--master", "local[*]", "--jars", "/opt/spark/jars/postgresql-42.7.4.jar", "/app/src/main.py"]