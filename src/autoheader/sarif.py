# src/autoheader/sarif.py

from __future__ import annotations
import json
from typing import List
from .models import PlanItem

def generate_sarif_report(plan: List[PlanItem], root: str) -> str:
    """Generates a SARIF report from a plan."""
    results = []
    for item in plan:
        if item.action not in ["add", "remove", "override"]:
            continue
        results.append(
            {
                "message": {
                    "text": f"File '{item.rel_posix}' needs header '{item.action}'. Reason: {item.reason or 'default'}"
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": item.rel_posix},
                            "region": {"startLine": 1},
                        }
                    }
                ],
            }
        )

    sarif_log = {
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "autoheader"}},
                "results": results,
            }
        ],
    }
    return json.dumps(sarif_log, indent=2)
