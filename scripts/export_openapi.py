#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from atlasqueue.api.main import create_app


def main() -> None:
    app = create_app()
    schema = app.openapi()
    output = Path("openapi.json")
    output.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
