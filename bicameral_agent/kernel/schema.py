"""Generate/check deterministic Kernel contracts."""
import argparse
import json
from pathlib import Path
from .models import KernelContracts
from .fixture import FixtureContracts
from ..contracts.base import Contract


class RuntimeContracts(Contract):
    authority: KernelContracts
    fixture: FixtureContracts


def schema_bytes():
    return (json.dumps(RuntimeContracts.model_json_schema(), sort_keys=True, indent=2) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--write', action='store_true')
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[2] / 'schemas' / 'kernel.schema.json'
    data = schema_bytes()
    if args.write:
        path.write_bytes(data)
    elif not path.exists() or path.read_bytes() != data:
        print('Kernel schema drift')
        return 1
    print('Kernel schema matches the models.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
