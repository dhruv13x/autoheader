
import pytest
from unittest.mock import MagicMock, patch, ANY, PropertyMock
import sys
from pathlib import Path

from autoheader.lsp import AutoHeaderServer, HAS_PYGLS
from autoheader.config import LanguageConfig
from autoheader.models import PlanItem
from autoheader.headerlogic import HeaderAnalysis

pytestmark = pytest.mark.skipif(not HAS_PYGLS, reason="pygls not installed")

# Protocol V3: Mock External Systems
# We need to mock pygls components to test logic without starting a real LS

# --- Fixtures ---

@pytest.fixture
def mock_ls_server():
    # Mocking the LanguageServer
    with patch("autoheader.lsp.LanguageServer") as MockLanguageServer:
        # Create a mock instance
        server = AutoHeaderServer()

        # Mock features that are used
        server.show_message = MagicMock()
        server.show_message_log = MagicMock()

        # Solution: patch `autoheader.lsp.AutoHeaderServer.workspace`
        with patch("autoheader.lsp.AutoHeaderServer.workspace", new_callable=PropertyMock) as mock_ws_prop:
            mock_workspace = MagicMock()
            mock_workspace.root_path = "/root"
            mock_ws_prop.return_value = mock_workspace
            yield server

@pytest.fixture
def mock_text_document_item():
    from lsprotocol.types import TextDocumentItem
    return TextDocumentItem(
        uri="file:///root/test.py",
        language_id="python",
        version=1,
        text="import os\n"
    )

@pytest.fixture
def mock_diagnostic():
    from lsprotocol.types import Diagnostic, Range, Position, DiagnosticSeverity
    return Diagnostic(
        range=Range(start=Position(line=0, character=0), end=Position(line=0, character=1)),
        message="File header is missing.",
        severity=DiagnosticSeverity.Warning,
        source="autoheader"
    )

# --- Tests ---

def test_check_document_missing_pygls():
    # If pygls is not present, check_document returns empty list
    with patch("autoheader.lsp.HAS_PYGLS", False):
        server = AutoHeaderServer()
        assert server.check_document("uri") == []

def test_check_document_file_not_found(mock_ls_server):
    with patch("autoheader.lsp._uri_to_path") as mock_to_path:
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_to_path.return_value = mock_path

        diags = mock_ls_server.check_document("file:///root/test.py")
        assert diags == []

def test_check_document_issues_found(mock_ls_server):
    # Test that diagnostics are generated when plan returns action items
    with patch("autoheader.lsp._uri_to_path") as mock_to_path, \
         patch("autoheader.lsp._load_config_context") as mock_load, \
         patch("autoheader.lsp.plan_files") as mock_plan:

        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_to_path.return_value = mock_path

        mock_load.return_value = ([], MagicMock()) # languages, context

        # Mock plan returning one item with action "add"
        # PlanItem definition:
        # class PlanItem:
        #    path: Path
        #    rel_posix: str
        #    action: str
        #    prefix: str
        #    check_encoding: bool
        #    template: str
        #    analysis_mode: str
        #    license_spdx: str | None = None
        #    license_owner: str | None = None
        #    reason: str = ""

        item = PlanItem(
            path=mock_path,
            rel_posix="test.py",
            action="add",
            prefix="#",
            check_encoding=False,
            template="# Header",
            analysis_mode="auto",
            reason="missing"
        )
        mock_plan.return_value = ([item], 1)

        diags = mock_ls_server.check_document("file:///root/test.py", root_path="/root")

        assert len(diags) == 1
        assert diags[0].message == "File header is missing."
        assert diags[0].source == "autoheader"

def test_code_action_no_diagnostic(mock_ls_server):
    from lsprotocol.types import CodeActionParams, TextDocumentIdentifier, Range, Position

    params = CodeActionParams(
        text_document=TextDocumentIdentifier(uri="file:///root/test.py"),
        range=Range(start=Position(line=0, character=0), end=Position(line=0, character=0)),
        context=MagicMock(diagnostics=[])
    )

    actions = mock_ls_server.code_action(params)
    assert actions == []

def test_code_action_fix_header(mock_ls_server, mock_diagnostic):
    from lsprotocol.types import CodeActionParams, TextDocumentIdentifier, Range, Position, CodeActionKind

    uri = "file:///root/test.py"

    params = CodeActionParams(
        text_document=TextDocumentIdentifier(uri=uri),
        range=Range(start=Position(line=0, character=0), end=Position(line=0, character=0)),
        context=MagicMock(diagnostics=[mock_diagnostic])
    )

    # Mock workspace.get_text_document
    doc_mock = MagicMock()
    doc_mock.source = "import os"
    mock_ls_server.workspace.get_text_document.return_value = doc_mock

    # Mock helpers
    with patch("autoheader.lsp._uri_to_path") as mock_to_path, \
         patch("autoheader.lsp._load_config_context") as mock_load, \
         patch("autoheader.lsp.planner._get_language_for_file") as mock_get_lang, \
         patch("autoheader.lsp.headerlogic.header_line_for") as mock_header_for, \
         patch("autoheader.lsp.headerlogic.analyze_header_state") as mock_analyze, \
         patch("autoheader.lsp.headerlogic.build_new_lines") as mock_build:

        mock_path = MagicMock(spec=Path)
        mock_path.relative_to.return_value.as_posix.return_value = "test.py"
        mock_to_path.return_value = mock_path

        # Mock language config
        lang_config = LanguageConfig(
            name="python", file_globs=["*.py"], template="# {path}", prefix="#", check_encoding=False, analysis_mode="auto"
        )
        mock_load.return_value = ([lang_config], MagicMock())
        mock_get_lang.return_value = lang_config

        mock_header_for.return_value = "# test.py"

        # Analyze returns
        mock_analyze.return_value = HeaderAnalysis(0, None, False)

        # Build new lines
        mock_build.return_value = ["# test.py", "", "import os"]

        actions = mock_ls_server.code_action(params)

        assert len(actions) == 1
        action = actions[0]
        assert action.title == "Fix File Header"
        assert action.kind == CodeActionKind.QuickFix
        assert action.edit is not None
        assert uri in action.edit.changes
        assert action.edit.changes[uri][0].new_text == "# test.py\n\nimport os\n"
