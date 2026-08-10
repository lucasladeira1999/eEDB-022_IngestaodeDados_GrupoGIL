import boto3
from utils import setup_logger

logger = setup_logger()


class ToDeliveryJob:
    def run(**config) -> None:
        logger.info(f"Running ToDeliveryJob with config: {config}")
        s3_client = boto3.client("s3")
        trusted_bucket = config["trusted_bucket"]
        delivery_bucket = config["delivery_bucket"]

        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=trusted_bucket):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                logger.info(
                    f"Copying {key} from {trusted_bucket} to {delivery_bucket}"
                )
                s3_client.copy_object(
                    Bucket=delivery_bucket,
                    Key=key,
                    CopySource={"Bucket": trusted_bucket, "Key": key},
                )
