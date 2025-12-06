import yaml
import os
from pathlib import Path

def test_action_yml_exists_and_valid():
    """
    Test that action.yml exists and has the correct structure for a GitHub Action.
    """
    action_path = Path("action.yml")

    # Fail if file doesn't exist
    assert action_path.exists(), "action.yml should exist in the root directory"

    with open(action_path, "r") as f:
        content = yaml.safe_load(f)

    # Check basic structure
    assert "name" in content
    assert "description" in content
    assert "inputs" in content
    assert "runs" in content

    # Check specific inputs
    inputs = content["inputs"]
    assert "args" in inputs
    assert "description" in inputs["args"]
    assert inputs["args"].get("default", "") == "--check"

    # Check runs configuration (Docker)
    runs = content["runs"]
    assert runs["using"] == "docker"
    assert runs["image"] == "Dockerfile"
    assert "args" in runs
