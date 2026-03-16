"""Export the FastAPI OpenAPI schema to docs/openapi.json."""

import json
import sys
from pathlib import Path

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app


def main():
    schema = app.openapi()
    output = Path(__file__).resolve().parent.parent / "docs" / "openapi.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(schema, indent=2, default=str))
    print(f"OpenAPI schema exported to {output}")
    print(f"  paths: {len(schema.get('paths', {}))}")
    print(f"  schemas: {len(schema.get('components', {}).get('schemas', {}))}")


if __name__ == "__main__":
    main()
