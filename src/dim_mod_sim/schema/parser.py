"""JSON schema parser."""

import json
from pathlib import Path

from dim_mod_sim.schema.models import SchemaSubmission


def parse_schema(source: str | Path | dict) -> SchemaSubmission:
    """Parse a schema submission from various sources.

    Args:
        source: JSON string, file path, or dictionary

    Returns:
        Validated SchemaSubmission
    """
    if isinstance(source, dict):
        data = source
    elif isinstance(source, Path):
        with open(source) as f:
            data = json.load(f)
    elif isinstance(source, str):
        # Try as file path first, then as JSON string
        path = Path(source)
        if path.exists():
            with open(path) as f:
                data = json.load(f)
        else:
            data = json.loads(source)
    else:
        raise TypeError(f"Unsupported source type: {type(source)}")

    return SchemaSubmission.model_validate(data)
