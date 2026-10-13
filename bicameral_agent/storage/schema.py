"""Generate or check the closed P02 storage-record schema."""
import argparse
import json
from pathlib import Path
from .contracts import StorageContracts

def schema_bytes():
    return (json.dumps(StorageContracts.model_json_schema(), sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[2] / "schemas" / "p02.schema.json"
    expected = schema_bytes()
    if args.write:
        path.write_bytes(expected)
        print("Wrote schemas/p02.schema.json")
        return 0
    if not path.exists() or path.read_bytes() != expected:
        print("P02 schema drift")
        return 1
    print("P02 schema matches the models.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
