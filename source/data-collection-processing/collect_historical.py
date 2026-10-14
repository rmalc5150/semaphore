#!/usr/bin/env python3
"""Run the shared historical collection pipeline; use --dry-run to inspect scope."""
from collection_operations import main

if __name__ == "__main__":
    raise SystemExit(main("historical"))
