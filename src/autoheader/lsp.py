import logging
import os
from pathlib import Path
from typing import List, Optional
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

from .core import plan_files
from .models import RuntimeContext
from .config import load_config_data, load_general_config, load_language_configs, generate_default_config
from .constants import DEFAULT_EXCLUDES, ROOT_MARKERS, CONFIG_FILE_NAME
from . import filesystem

log = logging.getLogger("autoheader.lsp")

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

        # Convert URI to path
        if uri.startswith("file://"):
            import urllib.parse
            # On Windows, urlparse returns /C:/path, we need to strip leading /
            parsed = urllib.parse.urlparse(uri)
            path_str = urllib.parse.unquote(parsed.path)
            # If on windows (check drive letter), strip leading slash if present
            if os.name == 'nt' and path_str.startswith('/') and ':' in path_str:
                path_str = path_str[1:]
            file_path = Path(path_str)
        else:
            file_path = Path(uri)

        if not file_path.exists():
            return []

        # Determine root
        if root_path:
            root = Path(root_path)
        else:
            root = Path.cwd()

        # Try to find a config file in the root or upwards
        # For simplicity in this iteration, we use the passed root_path or cwd
        # In a real LSP, we might search up from the file_path

        # Load config
        try:
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

            # Plan for just this file
            plan, _ = plan_files(context, [file_path], languages, workers=1)

            for item in plan:
                if item.action in ("add", "override", "remove"): # remove implies header is present but wrong/unwanted?
                    # Actually "remove" action means user requested removal.
                    # But here we are checking compliance.
                    # If action is "add" or "override", the header is missing or incorrect.

                    # If action is 'add' or 'override', we should report an issue.
                    message = "File header is missing or incorrect."

                    # We can try to be more specific.
                    if item.action == "add":
                        message = "File header is missing."
                    elif item.action == "override":
                        message = "File header is incorrect."

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

    return server
