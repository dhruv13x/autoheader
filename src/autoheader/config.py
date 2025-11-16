# src/autoheader/config.py

from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
import urllib.request
import socket
import time

# Use tomllib if available (3.11+), else fall back to tomli
try:
    import tomllib
except ImportError:
    import tomli as tomllib

# --- MODIFIED ---
from .constants import CONFIG_FILE_NAME, HEADER_PREFIX, DEFAULT_EXCLUDES, ROOT_MARKERS
from .models import LanguageConfig

log = logging.getLogger(__name__)


def fetch_remote_config_safe(
    url: str, timeout: float = 10.0, max_size: int = 1_048_576
) -> dict | None:
    """Safely fetches and parses a remote TOML config file with retries."""
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                if response.status != 200:
                    log.warning(f"Failed to fetch remote config (HTTP {response.status}).")
                    return None

                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > max_size:
                    log.warning(f"Remote config exceeds size limit of {max_size} bytes.")
                    return None

                # Read in chunks to prevent memory exhaustion
                content = b""
                while True:
                    chunk = response.read(65536)  # 64KB chunks
                    if not chunk:
                        break
                    content += chunk
                    if len(content) > max_size:
                        log.warning(f"Remote config download exceeded size limit of {max_size} bytes.")
                        return None

                toml_content = content.decode("utf-8")
                return tomllib.loads(toml_content)

        except (urllib.error.URLError, ConnectionResetError, socket.timeout) as e:
            log.warning(f"Network error fetching remote config (attempt {attempt + 1}/3): {e}")
            time.sleep(1)  # backoff
        except tomllib.TOMLDecodeError as e:
            log.warning(f"Failed to parse remote TOML config: {e}")
            return None
        except Exception as e:
            log.warning(f"An unexpected error occurred while fetching remote config: {e}")
            return None

    log.error("Failed to fetch remote config after 3 attempts.")
    return None

def load_config_data(root: Path, config_url: str | None, timeout: float) -> Tuple[Dict[str, Any], Path | None]:
    """Helper to load the TOML data from a URL or local file."""
    if config_url:
        log.debug(f"Loading remote config from {config_url}")
        toml_data = fetch_remote_config_safe(config_url, timeout=timeout)
        return (toml_data or {}, None)

    config_path = root / CONFIG_FILE_NAME
    if not config_path.is_file():
        log.debug(f"No {CONFIG_FILE_NAME} found, using defaults.")
        return ({}, None)

    log.debug(f"Loading config from {config_path}")
    try:
        with config_path.open("rb") as f:
            toml_data = tomllib.load(f)
        return (toml_data, config_path)
    except Exception as e:
        log.warning(f"Could not parse {CONFIG_FILE_NAME}: {e}. Using defaults.")
        return ({}, None)


def load_general_config(toml_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Loads general settings (non-language) from the TOML data
    and flattens it.
    """
    flat_config = {}

    # [general] section
    if "general" in toml_data and isinstance(toml_data["general"], dict):
        general = toml_data["general"]
        # --- MODIFIED: Added 'timeout' to the list of keys ---
        for key in ["backup", "workers", "yes", "override", "remove", "timeout"]:
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

    # --- THIS SECTION IS NOW OBSOLETE, but we keep it for backward compat ---
    if "header" in toml_data and isinstance(toml_data["header"], dict):
        header = toml_data["header"]
        if "blank_lines_after" in header:
            flat_config["blank_lines_after"] = header["blank_lines_after"]
        # For old [header].prefix
        if "prefix" in header:
            flat_config["_legacy_prefix"] = header["prefix"]

    return flat_config


def load_language_configs(
    toml_data: Dict[str, Any],
    general_config: Dict[str, Any]
) -> List[LanguageConfig]:
    """
    Parses all [language.*] sections from the TOML data.
    """
    languages: List[LanguageConfig] = []
    
    if "language" in toml_data and isinstance(toml_data["language"], dict):
        for lang_name, lang_data in toml_data["language"].items():
            if not isinstance(lang_data, dict):
                continue
            
            try:
                # --- THIS IS THE FIX ---
                # 1. Get the prefix first
                prefix = lang_data['prefix']
                # 2. Create the default template string *without* a nested f-string
                #    We want the literal string "{path}"
                default_template = f"{prefix}{'{path}'}"
                # 3. Use the clean default string in the .get()
                template = lang_data.get("template", default_template)
                # --- END FIX ---
                
                lang = LanguageConfig(
                    name=lang_name,
                    file_globs=lang_data["file_globs"],
                    prefix=prefix, # Use the variable
                    check_encoding=lang_data.get("check_encoding", False),
                    template=template,
                    analysis_mode=lang_data.get("analysis_mode", "line"),
                )
                languages.append(lang)
            except KeyError as e:
                log.warning(f"Config for [language.{lang_name}] is missing required key: {e}")

    # --- DEFAULT / BACKWARD COMPATIBILITY ---
    if not languages:
        log.debug("No [language.*] sections found, using default Python config.")
        
        # Use legacy prefix if it exists
        legacy_prefix = general_config.get("_legacy_prefix", HEADER_PREFIX)
        
        languages.append(
            LanguageConfig(
                name="python",
                file_globs=["*.py", "*.pyi"],
                prefix=legacy_prefix,
                check_encoding=True,
                # --- FIX APPLIED HERE TOO ---
                template=f"{legacy_prefix}{'{path}'}",
            )
        )

    log.debug(f"Loaded {len(languages)} language configurations.")
    return languages


# --- ADD THIS FUNCTION ---
def generate_default_config() -> str:
    """Generates the full, default autoheader.toml content as a string."""

    # Format the default lists as TOML arrays
    markers_toml = "\n".join([f'    "{m}",' for m in sorted(list(ROOT_MARKERS))])
    excludes_toml = "\n".join([f'    "{p}",' for p in sorted(list(DEFAULT_EXCLUDES))])

    # Note: Using {{path}} to escape the f-string brace
    # This correctly writes the literal string `template = "# {path}"` to the file.
    return f"""# autoheader configuration file
# Generated by `autoheader --init`
# For more info, see: https://github.com/dhruv13x/autoheader

[general]
# Create .bak files before modifying. (Default: false)
backup = false

# Number of parallel workers. (Default: 8)
workers = 8

# Timeout in seconds for processing a single file. (Default: 60.0)
# timeout = 60.0

# auto-confirm all prompts (e.g., for CI). (Default: false)
# yes = false

[detection]
# Max directory depth to scan. (Default: no limit)
# depth = 10

# Files that mark the project root.
markers = [
{markers_toml}
]

[exclude]
# Extra paths/globs to exclude.
# The built-in defaults are included below for convenience.
paths = [
{excludes_toml}
]

# This legacy section is used for the global `blank_lines_after` setting.
[header]
blank_lines_after = 1


# --- Language-Specific Configuration ---
# autoheader v2.0+ uses language blocks.
# The default config for Python is shown below.
# You can add more, e.g., [language.javascript], [language.go], etc.

[language.python]
# Globs to identify files for this language
file_globs = [
    "*.py",
    "*.pyi",
]

# The comment prefix to use
prefix = "# "

# The template for the header line. {{path}} is the placeholder.
template = "# {{path}}"

# Whether to check for shebangs/encoding (Python-specific)
check_encoding = true
"""
# --- END ADDED FUNCTION ---
