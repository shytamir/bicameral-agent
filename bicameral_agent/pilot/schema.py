"""Generate or check the separate 0.4 public contracts; preserve historical schemas."""
import argparse
import json
from pathlib import Path
from ..contracts.pilot import PilotContracts
from ..kernel.fixture import FixtureDefinition, ClockPlan
from .fixture import CompatibilityDefinition, CompatibilityClock


class DevelopmentContracts(PilotContracts):
    fixture: FixtureDefinition | CompatibilityDefinition
    clock: ClockPlan | CompatibilityClock


def schema_bytes():
    return (json.dumps(DevelopmentContracts.model_json_schema(mode='validation'), sort_keys=True, indent=2,
                       ensure_ascii=False) + '\n').encode()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    path = Path(__file__).resolve().parents[2] / 'schemas/pilot-0.4.schema.json'
    generated = schema_bytes()
    if args.write:
        path.write_bytes(generated)
    elif not path.exists() or path.read_bytes() != generated:
        raise SystemExit('0.4 schema drift; review contracts before --write')
    print('0.4 schema matches the contracts.')


if __name__ == '__main__':
    main()
