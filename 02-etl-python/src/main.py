import os

from to_raw.job import ToRawJob
from utils import load_config, setup_logger

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

logger = setup_logger()


def main():
    config = load_config(CONFIG_PATH)

    logger.info(f"Loaded config: {config}")

    ToRawJob.run(**config)


if __name__ == "__main__":
    main()
