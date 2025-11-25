# tests/unit/test_cli.py

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from concurrent.futures import TimeoutError, Future
import importlib

from autoheader import cli, config
from autoheader.models import PlanItem


def test_init_creates_config_file(tmp_path: Path):
    """Test that --init creates a default config file."""
    with patch("autoheader.ui.console.print") as mock_print:
        result = cli.main(["--init", "--root", str(tmp_path)])
        assert result == 0
        config_path = tmp_path / config.CONFIG_FILE_NAME
        assert config_path.exists()
        mock_print.assert_called_with(f"[green]✅ Created default config at [bold]{config_path}[/bold].[/green]")


def test_init_does_not_overwrite_existing_config(tmp_path: Path):
    """Test that --init does not overwrite an existing config file."""
    config_path = tmp_path / config.CONFIG_FILE_NAME
    config_path.touch()
    with patch("autoheader.ui.console.print") as mock_print:
        result = cli.main(["--init", "--root", str(tmp_path)])
        assert result == 1
        mock_print.assert_called_with(f"[red]Error: [bold]{config.CONFIG_FILE_NAME}[/bold] already exists in this directory.[/red]")


def test_init_handles_creation_error(tmp_path: Path):
    """Test that --init handles errors during file creation."""
    with patch("pathlib.Path.write_text", side_effect=IOError("Disk full")), patch("autoheader.ui.console.print") as mock_print:
        result = cli.main(["--init", "--root", str(tmp_path)])
        assert result == 1
        mock_print.assert_called_with("[red]Failed to create config file: Disk full[/red]")


def test_main_handles_timeout_error(tmp_path: Path):
    """Test that main handles TimeoutError during file processing."""
    plan_item = PlanItem(action="add", path=tmp_path / "a.py", rel_posix="a.py", prefix="#", check_encoding=False, template="{prefix} {path}", analysis_mode="line")
    future = Future()
    future.set_exception(TimeoutError)
    with patch("autoheader.app.ensure_root_or_confirm", return_value=True), patch("autoheader.cli.plan_files", return_value=([plan_item], {})), patch("concurrent.futures.as_completed", return_value=[future]), patch("autoheader.ui.format_error") as mock_format_error, patch("autoheader.ui.console.print"):
        cli.main(["--no-dry-run", "--yes", "--root", str(tmp_path)])
        mock_format_error.assert_called_once()


def test_main_handles_generic_exception(tmp_path: Path):
    """Test that main handles generic exceptions during file processing."""
    plan_item = PlanItem(action="add", path=tmp_path / "a.py", rel_posix="a.py", prefix="#", check_encoding=False, template="{prefix} {path}", analysis_mode="line")
    future = Future()
    future.set_exception(Exception("Disk full"))
    with patch("autoheader.app.ensure_root_or_confirm", return_value=True), patch("autoheader.cli.plan_files", return_value=([plan_item], {})), patch("concurrent.futures.as_completed", return_value=[future]), patch("autoheader.ui.format_error") as mock_format_error, patch("autoheader.ui.console.print"):
        cli.main(["--no-dry-run", "--yes", "--root", str(tmp_path)])
        mock_format_error.assert_called_once()


def test_get_version_fallback():
    """Test that get_version returns a fallback version when metadata is not found."""
    with patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError):
        version = cli.get_version()
        assert version == "0.1.0-dev"


def test_main_install_precommit(tmp_path: Path):
    """Test that main calls install_precommit_config."""
    with patch("autoheader.precommit.install_precommit_config") as mock_install:
        result = cli.main(["--install-precommit", "--root", str(tmp_path)])
        assert result == 0
        mock_install.assert_called_once_with(tmp_path)


def test_main_install_precommit_importerror(tmp_path: Path):
    """Test that main handles ImportError during pre-commit installation."""
    with patch("autoheader.precommit", None):
        with patch("autoheader.ui.console.print") as mock_print:
            result = cli.main(["--install-precommit", "--root", str(tmp_path)])
            assert result == 1
            mock_print.assert_any_call("[red]Failed to install pre-commit hook: 'NoneType' object has no attribute 'install_precommit_config'[/red]")


def test_main_install_precommit_exception(tmp_path: Path):
    """Test that main handles exceptions during pre-commit installation."""
    with patch("autoheader.precommit.install_precommit_config", side_effect=Exception("Test error")), patch("autoheader.ui.console.print") as mock_print:
        result = cli.main(["--install-precommit", "--root", str(tmp_path)])
        assert result == 1
        mock_print.assert_called_with("[red]Failed to install pre-commit hook: Test error[/red]")

def test_check_mode_fail(tmp_path: Path):
    """Test that main exits with 1 when in check mode and there are changes."""
    plan_item = PlanItem(action="add", path=tmp_path / "a.py", rel_posix="a.py", prefix="#", check_encoding=False, template="{prefix} {path}", analysis_mode="line")
    with patch("autoheader.app.ensure_root_or_confirm", return_value=True), patch("autoheader.cli.plan_files", return_value=([plan_item], {})), patch("autoheader.ui.console.print"):
        result = cli.main(["--check", "--root", str(tmp_path)])
        assert result == 1
