"""Generate the P01 JSON Schema; --check detects committed-schema drift."""

import argparse
import json
from pathlib import Path

from .base import Contract
from .configuration import RunConfiguration
from .messages import Message
from .resolution import ResolutionContext


class P01Contracts(Contract):
    message: Message
    configuration: RunConfiguration
    resolution_context: ResolutionContext


def schema_bytes() -> bytes:
    schema = P01Contracts.model_json_schema(mode="validation")
    return (json.dumps(schema, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[2] / "schemas" / "p01.schema.json"
    generated = schema_bytes()
    if args.write:
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(generated)
        print("Wrote schemas/p01.schema.json from Pydantic models.")
        return 0
    if not path.exists() or path.read_bytes() != generated:
        print("Schema drift: review contracts, then regenerate with --write.")
        return 1
    print("P01 schema matches the models.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
