# src/autoheader/config.py

from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Dict

# Use tomllib if available (3.11+), else fall back to tomli
try:
    import tomllib
except ImportError:
    import tomli as tomllib

from .constants import CONFIG_FILE_NAME

log = logging.getLogger(__name__)


def load_config(root: Path) -> Dict[str, Any]:
    """
    Loads autoheader.toml from the root and flattens it into an
    argparse-compatible dictionary.
    """
    config_path = root / CONFIG_FILE_NAME
    if not config_path.is_file():
        log.debug(f"No {CONFIG_FILE_NAME} found, using defaults.")
        return {}

    log.debug(f"Loading config from {config_path}")
    try:
        with config_path.open("rb") as f:
            toml_data = tomllib.load(f)
    except Exception as e:
        log.warning(f"Could not parse {CONFIG_FILE_NAME}: {e}. Using defaults.")
        return {}

    # Flatten the TOML structure to match argparse dest names
    flat_config = {}

    # [general] section
    if "general" in toml_data and isinstance(toml_data["general"], dict):
        general = toml_data["general"]
        for key in ["dry_run", "backup", "workers", "yes", "override", "remove"]:
            if key in general:
                flat_config[key] = general[key]

    # [detection] section
    if "detection" in toml_data and isinstance(toml_data["detection"], dict):
        detection = toml_data["detection"]
        if "depth" in detection:
            flat_config["depth"] = detection["depth"]
        if "markers" in detection:
            flat_config["markers"] = detection["markers"]

    # [exclude] section
    if "exclude" in toml_data and isinstance(toml_data["exclude"], dict):
        if "paths" in toml_data["exclude"]:
            flat_config["exclude"] = toml_data["exclude"]["paths"]

    # [header] section
    if "header" in toml_data and isinstance(toml_data["header"], dict):
        if "blank_lines_after" in toml_data["header"]:
            flat_config["blank_lines_after"] = toml_data["header"]["blank_lines_after"]

    log.debug(f"Loaded config: {flat_config}")
    return flat_config