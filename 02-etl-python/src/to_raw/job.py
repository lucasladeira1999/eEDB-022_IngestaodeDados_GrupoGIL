import os
import boto3
import logging


logger = logging.getLogger()


class ToRawJob:
    def run(**config) -> None:
        s3_client = boto3.client("s3")

        for root, _, files in os.walk(config["dados_path"]):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(file_path, config["dados_path"])
                key = relative_path.replace(os.sep, "/")

                with open(file_path, "rb") as file_data:
                    logger.info(f"Putting object {key} in to {config['raw_bucket']}")
                    s3_client.put_object(
                        Bucket=config["raw_bucket"], Key=key, Body=file_data
                    )
