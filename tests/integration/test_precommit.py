# tests/integration/test_precommit.py

import pytest
import yaml
from pathlib import Path

# We need to import the module *after* pyfakefs is active
# so we import it inside the tests.

# 'fs' is the pyfakefs fixture

def test_install_precommit_new_file(fs):
    """
    Tests that a new .pre-commit-config.yaml is created if one doesn't exist.
    """
    from autoheader.precommit import install_precommit_config
    
    root = Path("/fake_project")
    fs.create_dir(root)
    
    config_path = root / ".pre-commit-config.yaml"
    assert not config_path.exists()
    
    install_precommit_config(root)
    
    assert config_path.exists()
    
    # Read the file and check its contents
    with config_path.open("r") as f:
        config = yaml.safe_load(f)
        
    assert "repos" in config
    assert config["repos"][0]["repo"] == "local"
    assert config["repos"][0]["hooks"][0]["id"] == "autoheader"
    assert config["repos"][0]["hooks"][0]["entry"] == "autoheader --check"

def test_install_precommit_existing_no_local(fs):
    """
    Tests that a new 'repo: local' is added if one doesn't exist.
    """
    from autoheader.precommit import install_precommit_config
    
    root = Path("/fake_project")
    fs.create_dir(root)
    config_path = root / ".pre-commit-config.yaml"
    
    # Create an existing config with a different repo
    existing_config = {
        "repos": [{"repo": "https://github.com/psf/black", "hooks": [{"id": "black"}]}]
    }
    fs.create_file(config_path, contents=yaml.safe_dump(existing_config))
    
    install_precommit_config(root)
    
    with config_path.open("r") as f:
        config = yaml.safe_load(f)
        
    assert len(config["repos"]) == 2
    assert config["repos"][0]["repo"] == "https://github.com/psf/black"
    assert config["repos"][1]["repo"] == "local"
    assert config["repos"][1]["hooks"][0]["id"] == "autoheader"

def test_install_precommit_existing_with_local(fs):
    """
    Tests that the hook is added to an *existing* 'repo: local'.
    """
    from autoheader.precommit import install_precommit_config
    
    root = Path("/fake_project")
    fs.create_dir(root)
    config_path = root / ".pre-commit-config.yaml"
    
    # Create an existing config with a 'local' repo
    existing_config = {
        "repos": [{"repo": "local", "hooks": [{"id": "my-local-script"}]}]
    }
    fs.create_file(config_path, contents=yaml.safe_dump(existing_config))
    
    install_precommit_config(root)
    
    with config_path.open("r") as f:
        config = yaml.safe_load(f)
    
    assert len(config["repos"]) == 1 # Still only one repo
    assert len(config["repos"][0]["hooks"]) == 2 # Now has two hooks
    assert config["repos"][0]["hooks"][0]["id"] == "my-local-script"
    assert config["repos"][0]["hooks"][1]["id"] == "autoheader"

def test_install_precommit_idempotent(fs):
    """
    Tests that the hook is not added twice.
    """
    from autoheader.precommit import install_precommit_config
    
    root = Path("/fake_project")
    fs.create_dir(root)
    config_path = root / ".pre-commit-config.yaml"
    
    # Create a config that *already has the hook*
    existing_config = {
        "repos": [{"repo": "local", "hooks": [{"id": "autoheader", "entry": "autoheader --check"}]}]
    }
    fs.create_file(config_path, contents=yaml.safe_dump(existing_config))
    
    install_precommit_config(root)
    
    with config_path.open("r") as f:
        config = yaml.safe_load(f)
        
    # Config should be unchanged
    assert len(config["repos"][0]["hooks"]) == 1
    assert config == existing_config