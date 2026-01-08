"""
Configuration loading for workflow definitions.

Handles loading and parsing YAML workflow files using Pydantic models.
"""

from pathlib import Path

import yaml

from .workflow import Workflow


def load_workflow(yaml_path: str | Path) -> Workflow:
    """
    Load a workflow definition from a YAML file.

    Args:
        yaml_path: Path to the YAML workflow file

    Returns:
        Parsed and validated Workflow object

    Raises:
        FileNotFoundError: If the YAML file doesn't exist
        yaml.YAMLError: If the YAML is malformed
        pydantic.ValidationError: If the workflow structure is invalid
    """
    path = Path(yaml_path)

    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        workflow_data = yaml.safe_load(f)

    # Pydantic will validate the structure
    return Workflow.model_validate(workflow_data)
