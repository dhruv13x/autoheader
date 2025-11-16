# tests/unit/test_cli_no_rich.py

from __future__ import annotations

from unittest.mock import patch
import sys
import importlib

def test_build_parser_no_rich():
    """Test that the parser is built without rich_argparse."""
    with patch.dict(sys.modules, {"rich_argparse": None}):
        from autoheader import cli
        importlib.reload(cli)
        parser = cli.build_parser()
        assert "RichHelpFormatter" not in str(parser.formatter_class)
