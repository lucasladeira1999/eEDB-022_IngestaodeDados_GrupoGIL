import os

from to_raw.job import ToRawJob
from to_trusted.job import ToTrustedJob
from utils import load_config, setup_logger

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

logger = setup_logger()


def main():
    config = load_config(CONFIG_PATH)
    config["dados_path"] = os.path.join(PROJECT_ROOT, config["dados_path"])

    logger.info(f"Loaded config: {config}")

    # ToRawJob.run(**config)
    ToTrustedJob.run(**config)


if __name__ == "__main__":
    main()
