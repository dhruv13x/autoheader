# tests/unit/test_v4_features.py

from pathlib import Path
from unittest.mock import patch, MagicMock
from autoheader import config
from autoheader import headerlogic
from autoheader import sarif
from autoheader.models import PlanItem

def test_remote_config():
    with patch("urllib.request.urlopen") as mock_urlopen:
        cm = MagicMock()
        cm.status = 200
        cm.read.side_effect = [b'[general]\nworkers = 4\n', b'']
        cm.__enter__.return_value = cm
        mock_urlopen.return_value = cm

        toml_data, _ = config.load_config_data(
            Path("/tmp"), "http://fake.url/autoheader.toml", timeout=10.0
        )
        assert toml_data["general"]["workers"] == 4

def test_tamper_detection():
    import hashlib
    content = "content"
    file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    lines = [f"# hash:{file_hash}", content]
    analysis = headerlogic.analyze_header_state(lines, f"# hash:{file_hash}", "#", False, "line", True)
    assert not analysis.has_tampered_header

    lines = [f"# hash:{file_hash}", "changed content"]
    analysis = headerlogic.analyze_header_state(lines, f"# hash:{file_hash}", "#", False, "line", True)
    assert analysis.has_tampered_header

def test_sarif_reporting():
    plan = [PlanItem(Path("/tmp/foo"), "foo", "add", "prefix", False, "template", "line")]
    report = sarif.generate_sarif_report(plan, "/tmp")
    assert '"uri": "foo"' in report

# def test_multiline_header():
#     lines = ["# line 1", "# line 2", "content"]
#     analysis = headerlogic.analyze_header_state(lines, "# line 1\n# line 2", "#", False)
#     assert analysis.has_correct_header
#
#     new_lines = headerlogic.build_new_lines(lines, "# new 1\n# new 2", analysis, True, 1)
#     assert new_lines[0] == "# new 1"
#     assert new_lines[1] == "# new 2"
#     assert new_lines[2] == ""
#
#     removed_lines = headerlogic.build_removed_lines(lines, analysis)
#     assert removed_lines[0] == "content"
