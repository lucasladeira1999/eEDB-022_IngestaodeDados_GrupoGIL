from abc import ABC, abstractmethod

import boto3
import pandas as pd

from utils import setup_logger

logger = setup_logger()


class BaseETL(ABC):
    name: str
    prefix: str
    extension: str
    sep: str
    encoding: str = "iso-8859-1"
    dtype: dict | type | None = None

    def __init__(self) -> None:
        logger.info(f"Initializing ETL job for {self.name}")
        logger.info(
            f'ELT CONFIG:\nPrefix: "{self.prefix}" \n Extension: "{self.extension}"\n Separator: "{self.sep}"\n Encoding: "{self.encoding}"'
        )

    def list_files(self, bucket: str, extension: str) -> list[str]:
        s3_client = boto3.client("s3")
        paginator = s3_client.get_paginator("list_objects_v2")

        keys = []
        for page in paginator.paginate(Bucket=bucket, Prefix=self.prefix):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith(extension):
                    keys.append(obj["Key"])

        return sorted(keys)

    def get_data(self, raw_bucket: str) -> pd.DataFrame:
        logger.info(f"Loading data for {self.name} from bucket {raw_bucket}")
        keys = self.list_files(raw_bucket, self.extension)

        dfs = []
        for key in keys:
            try:
                dfs.append(
                    pd.read_csv(
                        f"s3://{raw_bucket}/{key}",
                        sep=self.sep,
                        encoding=self.encoding,
                        dtype=self.dtype,
                        low_memory=False,
                    )
                )
            except pd.errors.EmptyDataError:
                logger.warning(f"Skipping empty file: {key}")

        df = pd.concat(dfs, ignore_index=True)
        logger.info(f"Data loaded for {self.name} with {len(df)} records")
        return df

    @abstractmethod
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError

    def save_to_bucket(self, trusted_bucket: str, df: pd.DataFrame) -> None:
        logger.info(
            f"Saving data for {self.name} s3://{trusted_bucket}/{self.name}.parquet"
        )
        df.to_parquet(f"s3://{trusted_bucket}/{self.name}.parquet", index=False)

    def run(self, raw_bucket: str, trusted_bucket: str) -> None:
        df = self.get_data(raw_bucket)
        df = self.clean_data(df)
        self.save_to_bucket(trusted_bucket, df)
