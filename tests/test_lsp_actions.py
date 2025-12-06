import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

try:
    from lsprotocol import types as lsp_types
    from autoheader.lsp import AutoHeaderServer
    HAS_PYGLS = True
except ImportError:
    HAS_PYGLS = False

@pytest.mark.skipif(not HAS_PYGLS, reason="pygls not installed")
def test_code_action_returns_fix(tmp_path):
    """
    Test that requesting code actions on a file with 'Header missing' returns a fix.
    """
    # Setup real file system in tmp_path
    project_root = tmp_path / "project"
    project_root.mkdir()

    src_dir = project_root / "src"
    src_dir.mkdir()

    test_file = src_dir / "test.py"
    file_content = "print('hello')"
    test_file.write_text(file_content)

    (project_root / "autoheader.toml").write_text("")

    # Initialize server
    server = AutoHeaderServer()

    # Mock workspace property
    mock_workspace = MagicMock()
    mock_workspace.root_path = str(project_root)

    # Mock get_text_document to return an object with source attribute
    mock_doc = MagicMock()
    mock_doc.source = file_content
    mock_workspace.get_text_document.return_value = mock_doc

    with patch("autoheader.lsp.AutoHeaderServer.workspace", new_callable=PropertyMock) as mock_ws_prop:
        mock_ws_prop.return_value = mock_workspace

        # Mock parameters
        file_uri = test_file.as_uri()

        # Create a diagnostic that matches what we expect from check_document
        diagnostic = lsp_types.Diagnostic(
            range=lsp_types.Range(
                start=lsp_types.Position(line=0, character=0),
                end=lsp_types.Position(line=0, character=1)
            ),
            message="File header is missing.",
            severity=lsp_types.DiagnosticSeverity.Warning,
            source="autoheader"
        )

        params = lsp_types.CodeActionParams(
            text_document=lsp_types.TextDocumentIdentifier(uri=file_uri),
            range=lsp_types.Range(
                start=lsp_types.Position(line=0, character=0),
                end=lsp_types.Position(line=0, character=1)
            ),
            context=lsp_types.CodeActionContext(diagnostics=[diagnostic])
        )

        # Verify method exists (this assertion will fail first)
        if not hasattr(server, "code_action"):
            pytest.fail("Method 'code_action' not implemented on AutoHeaderServer")

        actions = server.code_action(params)

        assert len(actions) == 1
        action = actions[0]
        assert action.title == "Fix File Header"
        assert action.kind == lsp_types.CodeActionKind.QuickFix

        assert action.edit is not None
        assert file_uri in action.edit.changes
        edits = action.edit.changes[file_uri]
        assert len(edits) > 0
        new_text = edits[0].new_text

        # The new text should contain the header (which defaults to path in autoheader)
        assert "src/test.py" in new_text
        assert "print('hello')" in new_text
