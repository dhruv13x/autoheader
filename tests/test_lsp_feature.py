import pytest
import sys
from unittest.mock import MagicMock, patch

try:
    import pygls.lsp.server
    from lsprotocol import types as lsp_types
    from autoheader.lsp import AutoHeaderServer
    HAS_PYGLS = True
except ImportError:
    HAS_PYGLS = False

@pytest.mark.skipif(not HAS_PYGLS, reason="pygls not installed")
def test_lsp_server_initialization():
    """Test that AutoHeaderServer can be instantiated."""
    server = AutoHeaderServer()
    assert isinstance(server, pygls.lsp.server.LanguageServer)

@pytest.mark.skipif(not HAS_PYGLS, reason="pygls not installed")
@patch("autoheader.lsp.plan_files")
@patch("autoheader.lsp.RuntimeContext")
def test_lsp_diagnostics(mock_context_cls, mock_plan_files, tmp_path):
    """Test that check_document generates diagnostics."""
    server = AutoHeaderServer()

    # Mock context
    mock_context = MagicMock()
    mock_context_cls.return_value = mock_context

    # Mock plan item to simulate a file needing a header
    from autoheader.models import PlanItem

    # Case 1: Header needs to be added
    mock_item = MagicMock(spec=PlanItem)
    mock_item.action = "add"
    mock_item.rel_posix = "test.py"

    # Mock plan_files result
    mock_plan_files.return_value = ([mock_item], {})

    # Create a dummy file
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')", encoding="utf-8")
    doc_uri = f"file://{test_file}"

    diagnostics = server.check_document(doc_uri, str(tmp_path))

    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag.severity == lsp_types.DiagnosticSeverity.Warning
    assert "File header is missing" in diag.message

    # Case 2: Header is correct
    mock_item.action = "skip-header-exists"
    mock_plan_files.return_value = ([mock_item], {})

    diagnostics = server.check_document(doc_uri, str(tmp_path))
    assert len(diagnostics) == 0

def test_cli_lsp_argument():
    """Test that --lsp argument is recognized (even if we don't run it)."""
    from autoheader.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["--lsp"])
    assert args.lsp is True
