import os

import yaml
from to_raw.job import ToRawJob

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def main():
    with open(CONFIG_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)

    ToRawJob.run(config["dados_path"], config["raw_bucket"])


if __name__ == "__main__":
    main()