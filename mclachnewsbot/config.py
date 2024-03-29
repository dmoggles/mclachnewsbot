import yaml
import os


def parse_config():
    """
    Parse the yaml config file config.yaml
    """
    config_file = os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml")
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Config file not found: {config_file}")
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    return config
