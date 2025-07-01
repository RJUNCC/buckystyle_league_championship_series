# shared/config/config.py
from omegaconf import OmegaConf
import os

def load_config():
    """Loads configuration from YAML files using OmegaConf."""
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    conf_dir = os.path.join(current_dir, "conf")

    # Load main configuration
    cfg = OmegaConf.load(os.path.join(conf_dir, "main.yaml"))

    # Load environment variables configuration and merge
    env_cfg = OmegaConf.load(os.path.join(conf_dir, "env.yaml"))
    cfg = OmegaConf.merge(cfg, env_cfg)

    return cfg

# Load the configuration when this module is imported
config = load_config()