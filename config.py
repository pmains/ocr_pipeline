
import yaml
from pathlib import Path

def load_config(config_path="config.yaml"):
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"No config file found at {config_path}")
    with config_file.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)
