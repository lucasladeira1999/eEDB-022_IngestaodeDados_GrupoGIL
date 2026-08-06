import os
import boto3


class ToRawJob:
    def run(dados_path: str, raw_bucket: str) -> None:
        s3_client = boto3.client("s3")

        for root, _, files in os.walk(dados_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(file_path, dados_path)
                key = relative_path.replace(os.sep, "/")

                with open(file_path, "rb") as file_data:
                    s3_client.put_object(Bucket=raw_bucket, Key=key, Body=file_data)
