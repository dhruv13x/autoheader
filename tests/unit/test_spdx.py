from __future__ import annotations
import pytest
from pathlib import Path
from autoheader.core import _analyze_single_file, write_with_header
from autoheader.models import LanguageConfig, RuntimeContext, PlanItem
from autoheader.config import load_language_configs
from autoheader.licenses import get_license_text, SPDX_LICENSES

@pytest.fixture
def base_context(tmp_path):
    return RuntimeContext(
        root=tmp_path,
        excludes=[],
        depth=None,
        override=False,
        remove=False,
        check_hash=False,
        timeout=10.0
    )

def test_spdx_license_generation_integration(tmp_path, base_context):
    """
    Test that configuring license_spdx generates the correct header.
    We test the full integration from config parsing (simulated) to header generation.
    """
    # 1. Setup the config data simulating autoheader.toml
    config_data = {
        "language": {
            "python": {
                "file_globs": ["*.py"],
                "prefix": "# ",
                "license_spdx": "MIT",
                "template": "# {path}\n#\n{license}"
            }
        }
    }

    # 2. Load the language config
    general_config = {}
    langs = load_language_configs(config_data, general_config)
    py_lang = langs[0]

    # Verify the config object has the license info
    assert hasattr(py_lang, 'license_spdx')
    assert py_lang.license_spdx == "MIT"

    # 3. Create a dummy file
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')\n")

    # 4. Plan the file
    plan_item, _ = _analyze_single_file((test_file, py_lang, base_context), {})

    # 5. Execute the plan
    write_with_header(
        plan_item,
        backup=False,
        dry_run=False,
        blank_lines_after=1
    )

    # 6. Verify content
    content = test_file.read_text()
    expected_license_snippet = "Permission is hereby granted, free of charge" # Part of MIT
    assert expected_license_snippet in content
    assert "MIT License" in content

def test_spdx_license_with_owner(tmp_path, base_context):
    config_data = {
        "language": {
            "python": {
                "file_globs": ["*.py"],
                "prefix": "# ",
                "license_spdx": "MIT",
                "license_owner": "Jane Doe",
                "template": "# {license}"
            }
        }
    }

    general_config = {}
    langs = load_language_configs(config_data, general_config)
    py_lang = langs[0]

    test_file = tmp_path / "test_owner.py"
    test_file.write_text("x = 1\n")

    plan_item, _ = _analyze_single_file((test_file, py_lang, base_context), {})
    write_with_header(plan_item, backup=False, dry_run=False, blank_lines_after=1)

    content = test_file.read_text()
    assert "Copyright (c)" in content
    assert "Jane Doe" in content

def test_unknown_spdx_license():
    config_data = {
        "language": {
            "python": {
                "file_globs": ["*.py"],
                "prefix": "# ",
                "license_spdx": "UNKNOWN_LICENSE_123",
            }
        }
    }

    with pytest.raises(ValueError, match="Unsupported or unknown SPDX license"):
        load_language_configs(config_data, {})

def test_get_license_text_found():
    assert get_license_text("MIT") == SPDX_LICENSES["MIT"]

def test_get_license_text_not_found():
    assert get_license_text("UNKNOWN") is None
