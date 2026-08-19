from to_delivery import job as ToDeliveryJob
from to_raw import job as ToRawJob
from to_trusted import job as ToTrustedJob
from utils import get_spark_session, setup_logger

logger = setup_logger()


def main() -> None:
    spark = get_spark_session("glassdoor-etl")

    logger.info("Running to_raw")
    ToRawJob.run(spark)

    logger.info("Running to_trusted")
    ToTrustedJob.run(spark)

    logger.info("Running to_delivery")
    ToDeliveryJob.run(spark)

    spark.stop()


if __name__ == "__main__":
    main()