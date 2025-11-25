
import json
from autoheader.sarif import generate_sarif_report
from autoheader.models import PlanItem


def test_generate_sarif_report_skip_action():
    plan = [
        PlanItem(
            path=None,
            rel_posix="test.py",
            action="skip",
            reason="Already up to date",
            prefix="#",
            check_encoding=True,
            template="# {path}",
            analysis_mode="line",
        )
    ]
    report = generate_sarif_report(plan, "/")
    sarif_data = json.loads(report)
    assert not sarif_data["runs"][0]["results"]
