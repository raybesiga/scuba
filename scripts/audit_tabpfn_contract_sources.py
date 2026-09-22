"""Check the pinned contract snapshot against already-downloaded vendor sources.

Standard library only. Does not import the SDK, load credentials or use a network.
"""

import argparse
import ast
import hashlib
import json
import zipfile
from pathlib import Path


def audit(openapi, wheel, fixture):
    sources = fixture["sources"]
    if hashlib.sha256(openapi.read_bytes()).hexdigest() != sources["rest"]["sha256"]:
        raise ValueError("OpenAPI snapshot hash differs from the reviewed source")
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != sources["sdk"]["wheel_sha256"]:
        raise ValueError("SDK wheel hash differs from the reviewed source")
    with zipfile.ZipFile(wheel) as archive:
        models = archive.read("tabpfn_client/api_models.py")
        client = archive.read("tabpfn_client/client.py")
    for content, key in ((models, "api_models_sha256"), (client, "client_sha256")):
        if hashlib.sha256(content).hexdigest() != sources["sdk"][key]:
            raise ValueError("SDK module hash differs from the reviewed source")
    # Inspect declarations, never execute the wheel or trigger client authentication.
    classes = {node.name: node for node in ast.parse(models).body if isinstance(node, ast.ClassDef)}
    openapi_schemas = json.loads(openapi.read_text())["components"]["schemas"]
    for source, schemas in fixture["schemas"].items():
        for name, expected in schemas.items():
            if source == "rest":
                actual = {
                    "properties": list(openapi_schemas[name]["properties"]),
                    "required": openapi_schemas[name].get("required", []),
                }
            else:
                fields = [n for n in classes[name].body if isinstance(n, ast.AnnAssign)]
                actual = {
                    "properties": [n.target.id for n in fields],
                    "required": [n.target.id for n in fields if n.value is None],
                }
            if actual != expected:
                raise ValueError(f"Source declaration differs from fixture: {source}/{name}")
    return {
        "evidence": "offline_source_audit",
        "source_hashes_verified": True,
        "field_snapshots_verified": True,
        "sdk_executed": False,
        "live_server_contract_verified": False,
        "differences": {
            name: {
                "rest_only_fields": sorted(
                    set(fixture["schemas"]["rest"][name]["properties"])
                    - set(fixture["schemas"]["sdk"][name]["properties"])
                ),
                "sdk_only_fields": sorted(
                    set(fixture["schemas"]["sdk"][name]["properties"])
                    - set(fixture["schemas"]["rest"][name]["properties"])
                ),
            }
            for name in ("FitRequest", "PredictRequest", "ClassifierMetadata")
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openapi", type=Path, required=True)
    parser.add_argument("--sdk-wheel", type=Path, required=True)
    args = parser.parse_args()
    fixture_path = (
        Path(__file__).resolve().parents[1] / "tests/fixtures/tabpfn_contracts_2026_09_20.json"
    )
    try:
        print(
            json.dumps(
                audit(args.openapi, args.sdk_wheel, json.loads(fixture_path.read_text())), indent=2
            )
        )
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as exc:
        parser.exit(2, f"Contract source audit failed: {type(exc).__name__}\n")
