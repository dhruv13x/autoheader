import logging
import os
from pathlib import Path
from typing import List, Optional, Union, Tuple
import sys

try:
    from pygls.lsp.server import LanguageServer
    from lsprotocol import types as lsp_types
    HAS_PYGLS = True
except ImportError:
    HAS_PYGLS = False
    # Dummy class for type hinting if pygls is missing
    class LanguageServer:  # type: ignore
        def __init__(self, *args, **kwargs): pass
        def command(self, *args): return lambda x: x
        def feature(self, *args): return lambda x: x
        @property
        def workspace(self): return type("obj", (object,), {"root_path": None})

    # Dummy lsp_types
    class lsp_types: # type: ignore
        class Diagnostic: pass
        class DiagnosticSeverity:
            Warning = 2
        class Range: pass
        class Position: pass
        class DidOpenTextDocumentParams: pass
        class DidSaveTextDocumentParams: pass
        class CodeActionParams: pass
        class CodeAction: pass
        class CodeActionKind:
            QuickFix = "quickfix"
        class WorkspaceEdit: pass
        class TextEdit: pass
        class Command: pass # Added for type hinting when pygls is not present

from .core import plan_files
from .models import RuntimeContext, LanguageConfig
from .config import load_config_data, load_general_config, load_language_configs
from .constants import DEFAULT_EXCLUDES
from . import filesystem
from . import headerlogic
from . import planner # for helper functions

log = logging.getLogger("autoheader.lsp")

def _uri_to_path(uri: str) -> Path:
    if uri.startswith("file://"):
        import urllib.parse
        parsed = urllib.parse.urlparse(uri)
        path_str = urllib.parse.unquote(parsed.path)
        # If on windows (check drive letter), strip leading slash if present
        if os.name == 'nt' and path_str.startswith('/') and ':' in path_str:
            path_str = path_str[1:]
        return Path(path_str)
    else:
        return Path(uri)

def _load_config_context(root: Path) -> Tuple[List[LanguageConfig], RuntimeContext]:
    """Helper to load configuration and create runtime context."""
    toml_data, _ = load_config_data(root, None, 60.0)
    general_config = load_general_config(toml_data)
    languages = load_language_configs(toml_data, general_config)

    excludes = list(DEFAULT_EXCLUDES) + filesystem.load_gitignore_patterns(root)

    # Create context
    context = RuntimeContext(
        root=root,
        excludes=excludes,
        depth=None,
        override=False,
        remove=False,
        check_hash=False,
        timeout=10.0
    )
    return languages, context

class AutoHeaderServer(LanguageServer):
    def __init__(self):
        super().__init__("autoheader-server", "v1")

    def check_document(self, uri: str, root_path: Optional[str] = None) -> List[lsp_types.Diagnostic]:
        """
        Run autoheader check on the document and return diagnostics.
        """
        if not HAS_PYGLS:
            return []

        diagnostics = []
        file_path = _uri_to_path(uri)

        if not file_path.exists():
            return []

        # Determine root
        if root_path:
            root = Path(root_path)
        else:
            root = Path.cwd()

        # Load config
        try:
            languages, context = _load_config_context(root)

            # Plan for just this file
            plan, _ = plan_files(context, [file_path], languages, workers=1)

            for item in plan:
                if item.action in ("add", "override", "remove"):
                    # Report issue
                    message = "File header is missing or incorrect."
                    if item.action == "add":
                        message = "File header is missing."
                    elif item.action == "override":
                        message = "File header is incorrect."
                    elif item.action == "remove":
                        message = "File header should be removed."

                    d = lsp_types.Diagnostic(
                        range=lsp_types.Range(
                            start=lsp_types.Position(line=0, character=0),
                            end=lsp_types.Position(line=0, character=1)
                        ),
                        message=message,
                        severity=lsp_types.DiagnosticSeverity.Warning,
                        source="autoheader"
                    )
                    diagnostics.append(d)

        except Exception as e:
            log.error(f"Error checking document {uri}: {e}")

        return diagnostics

    def code_action(self, params: lsp_types.CodeActionParams) -> List[Union[lsp_types.CodeAction, lsp_types.Command]]:
        """
        Handle code action requests.
        """
        if not HAS_PYGLS:
            return []

        document_uri = params.text_document.uri

        # Check if we have any autoheader diagnostics
        has_autoheader_diagnostic = False
        for d in params.context.diagnostics:
            if d.source == "autoheader":
                has_autoheader_diagnostic = True
                break

        if not has_autoheader_diagnostic:
            return []

        # Calculate the fix
        try:
            doc = self.workspace.get_text_document(document_uri)
            lines = doc.source.splitlines()

            file_path = _uri_to_path(document_uri)

            # Use root from workspace
            root_path = self.workspace.root_path
            if root_path:
                root = Path(root_path)
            else:
                root = Path.cwd()

            # Load config
            languages, context = _load_config_context(root)

            # Find language config
            lang = planner._get_language_for_file(file_path, languages)
            if not lang:
                return []

            # Calculate expected header
            rel_posix = file_path.relative_to(root).as_posix()

            # Analyze state
            content_str = doc.source

            analysis_prelim = headerlogic.analyze_header_state(
                lines, "", lang.prefix, lang.check_encoding, lang.analysis_mode
            )

            expected = headerlogic.header_line_for(
                rel_posix,
                lang.template,
                content=content_str,
                existing_header=analysis_prelim.existing_header_line,
                license_spdx=lang.license_spdx,
                license_owner=lang.license_owner,
            )

            analysis = headerlogic.analyze_header_state(
                lines, expected, lang.prefix, lang.check_encoding, lang.analysis_mode
            )

            # Generate new lines
            new_lines = headerlogic.build_new_lines(
                lines,
                expected,
                analysis,
                override=True, # Always override if we are fixing "incorrect" or "missing"
                blank_lines_after=1
            )

            new_text = "\n".join(new_lines) + "\n"

            # Create TextEdit
            # Replace the whole document
            edit = lsp_types.TextEdit(
                range=lsp_types.Range(
                    start=lsp_types.Position(line=0, character=0),
                    # End position must cover the entire original document
                    end=lsp_types.Position(line=len(lines) + 1, character=0)
                ),
                new_text=new_text
            )

            workspace_edit = lsp_types.WorkspaceEdit(changes={document_uri: [edit]})

            action = lsp_types.CodeAction(
                title="Fix File Header",
                kind=lsp_types.CodeActionKind.QuickFix,
                edit=workspace_edit,
                diagnostics=params.context.diagnostics
            )

            return [action]

        except Exception as e:
            log.error(f"Error generating code action for {document_uri}: {e}")
            return []


def create_server() -> AutoHeaderServer:
    if not HAS_PYGLS:
        raise ImportError("pygls is not installed. Run `pip install autoheader[lsp]`")

    server = AutoHeaderServer()

    @server.feature(lsp_types.TEXT_DOCUMENT_DID_OPEN)
    def did_open(ls: AutoHeaderServer, params: lsp_types.DidOpenTextDocumentParams):
        diagnostics = ls.check_document(params.text_document.uri, ls.workspace.root_path)
        ls.publish_diagnostics(params.text_document.uri, diagnostics)

    @server.feature(lsp_types.TEXT_DOCUMENT_DID_SAVE)
    def did_save(ls: AutoHeaderServer, params: lsp_types.DidSaveTextDocumentParams):
        diagnostics = ls.check_document(params.text_document.uri, ls.workspace.root_path)
        ls.publish_diagnostics(params.text_document.uri, diagnostics)

    # Register Code Action feature
    @server.feature(lsp_types.TEXT_DOCUMENT_CODE_ACTION)
    def code_action(ls: AutoHeaderServer, params: lsp_types.CodeActionParams):
        return ls.code_action(params)

    return server
