
from pathlib import Path
from unittest.mock import patch, MagicMock
from autoheader.config import (
    fetch_remote_config_safe,
    load_config_data,
    load_language_configs,
    load_general_config,
    generate_default_config,
)

def test_fetch_remote_config_http_error():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 404
        mock_urlopen.return_value.__enter__.return_value = mock_response
        result = fetch_remote_config_safe("http://example.com/config.toml")
        assert result is None


def test_fetch_remote_config_unexpected_error():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = Exception("Unexpected error")
        result = fetch_remote_config_safe("http://example.com/config.toml")
        assert result is None

def test_fetch_remote_config_content_length_too_large():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers.get.return_value = "2000000"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        result = fetch_remote_config_safe("http://example.com/config.toml")
        assert result is None

def test_fetch_remote_config_toml_decode_error():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers.get.return_value = "100"
        mock_response.read.side_effect = [b"invalid toml", b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response
        result = fetch_remote_config_safe("http://example.com/config.toml")
        assert result is None

def test_load_config_data_file_not_found(tmp_path: Path):
    result, _ = load_config_data(tmp_path, None, 10)
    assert result == {}

def test_load_config_data_toml_decode_error(tmp_path: Path):
    config_path = tmp_path / "autoheader.toml"
    config_path.write_text("invalid toml")
    result, _ = load_config_data(tmp_path, None, 10)
    assert result == {}

def test_load_language_configs_missing_prefix():
    toml_data = {"language": {"python": {"file_globs": ["*.py"]}}}
    with patch("autoheader.config.log.warning") as mock_log:
        result = load_language_configs(toml_data, {})
        assert not result
        mock_log.assert_called_with("Config for [language.python] is missing required key: 'prefix'")


def test_load_language_configs_no_languages():
    result = load_language_configs({}, {})
    assert len(result) == 1
    assert result[0].name == "python"

def test_load_general_config_legacy_prefix():
    toml_data = {"header": {"prefix": "#"}}
    result = load_general_config(toml_data)
    assert result["_legacy_prefix"] == "#"


def test_load_general_config_all_sections():
    toml_data = {
        "general": {"backup": True, "workers": 4, "timeout": 30},
        "detection": {"depth": 5, "markers": [".git"]},
        "exclude": {"paths": ["docs/"]},
        "header": {"blank_lines_after": 2},
    }
    config = load_general_config(toml_data)
    assert config["backup"] is True
    assert config["workers"] == 4
    assert config["timeout"] == 30
    assert config["depth"] == 5
    assert config["markers"] == [".git"]
    assert config["exclude"] == ["docs/"]
    assert config["blank_lines_after"] == 2


def test_load_general_config_empty():
    toml_data = {}
    config = load_general_config(toml_data)
    assert config == {}


def test_load_language_configs_invalid_entry():
    toml_data = {"language": {"python": "invalid"}}
    result = load_language_configs(toml_data, {})
    assert not result


def test_generate_default_config():
    config_string = generate_default_config()
    assert "[general]" in config_string
    assert "[detection]" in config_string
    assert "[exclude]" in config_string
    assert "[language.python]" in config_string
