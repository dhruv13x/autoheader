
import importlib
from pathlib import Path
from unittest.mock import patch

import pytest
from autoheader.precommit import install_precommit_config


def test_install_precommit_config_no_existing_file(fs):
    install_precommit_config(Path(fs.cwd))
    config_path = Path(fs.cwd) / ".pre-commit-config.yaml"
    assert config_path.exists()
    assert "autoheader" in config_path.read_text()


def test_install_precommit_config_write_error(fs):
    with patch("pathlib.Path.open", side_effect=IOError("Permission denied")):
        install_precommit_config(Path(fs.cwd))
    config_path = Path(fs.cwd) / ".pre-commit-config.yaml"
    assert not config_path.exists()


def test_install_precommit_config_parse_error(fs):
    config_path = Path(fs.cwd) / ".pre-commit-config.yaml"
    fs.create_file(config_path, contents=":")  # Invalid YAML
    install_precommit_config(Path(fs.cwd))
    # Should not raise, just log an error


def test_install_precommit_config_empty_yaml(fs):
    config_path = Path(fs.cwd) / ".pre-commit-config.yaml"
    fs.create_file(config_path, contents="")
    install_precommit_config(Path(fs.cwd))
    assert "autoheader" in config_path.read_text()


def test_install_precommit_config_existing_local_repo(fs):
    config_path = Path(fs.cwd) / ".pre-commit-config.yaml"
    fs.create_file(
        config_path,
        contents="repos:\n- repo: local\n  hooks:\n  - id: my-hook",
    )
    install_precommit_config(Path(fs.cwd))
    content = config_path.read_text()
    assert "my-hook" in content
    assert "autoheader" in content


def test_install_precommit_config_existing_hook(fs):
    config_path = Path(fs.cwd) / ".pre-commit-config.yaml"
    initial_content = "repos:\n- repo: local\n  hooks:\n  - id: autoheader"
    fs.create_file(config_path, contents=initial_content)
    install_precommit_config(Path(fs.cwd))
    assert config_path.read_text() == initial_content


def test_install_precommit_config_no_local_repo(fs):
    config_path = Path(fs.cwd) / ".pre-commit-config.yaml"
    fs.create_file(config_path, contents="repos:\n- repo: other")
    install_precommit_config(Path(fs.cwd))
    content = config_path.read_text()
    assert "other" in content
    assert "autoheader" in content


def test_install_precommit_config_yaml_not_found():
    # We need to reload the module to trigger the top-level import error
    with patch.dict("sys.modules", {"yaml": None}):
        from autoheader import precommit

        with pytest.raises(ImportError):
            importlib.reload(precommit)
