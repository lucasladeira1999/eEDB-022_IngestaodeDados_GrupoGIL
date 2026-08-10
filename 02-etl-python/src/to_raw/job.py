import os

import boto3

from utils import setup_logger

logger = setup_logger()


class ToRawJob:
    def run(**config) -> None:
        logger.info(f"Running ToRawJob with config: {config}")
        s3_client = boto3.client("s3")
        dados_folder = config["dados_path"]
        logger.info(f"Files found in {dados_folder}: {os.listdir(dados_folder)}")
        for root, _, files in os.walk(dados_folder):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(file_path, dados_folder)
                key = relative_path.replace(os.sep, "/")

                with open(file_path, "rb") as file_data:
                    logger.info(f"Putting object {key} in to {config['raw_bucket']}")
                    s3_client.put_object(
                        Bucket=config["raw_bucket"], Key=key, Body=file_data
                    )
