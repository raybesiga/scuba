"""Revalidate one saved response offline; produces a new result directory."""

import argparse
import json
from pathlib import Path

from scuba.integrations.tabpfn_rest import IntegrationError
from scuba.integrations.tabpfn_revalidation import revalidate_saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = revalidate_saved(args.input, args.source, args.source_manifest_sha256, args.output)
    except (IntegrationError, FileExistsError) as exc:
        parser.exit(2, f"{exc}\n")
    print(json.dumps({key: result[key] for key in ("status", "evidence", "metrics")}, indent=2))


if __name__ == "__main__":
    main()
