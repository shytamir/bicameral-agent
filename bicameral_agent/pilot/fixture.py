"""Opt-in family/release compatibility; reuse the finite fixture's actions and gates."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from ..contracts.base import Contract, Positive, Text, load_json, parse
from ..kernel.fixture import Service, FixtureDefinition, ClockStep, ClockPlan, Fixture


class CompatibilityService(Service):
    family: Text
    release: Positive


class CompatibilityRule(Contract):
    family: Text
    release: Positive
    healthy_mode: Literal['PRIMARY', 'SECONDARY']


class CompatibilityDefinition(FixtureDefinition):
    kind: Literal['SERVICE_COMPATIBILITY_V1']
    services: Annotated[tuple[CompatibilityService, ...], Field(min_length=1)]
    snapshots: dict[str, tuple[CompatibilityService, ...]]
    rules: Annotated[tuple[CompatibilityRule, ...], Field(min_length=1)]

    @model_validator(mode='after')
    def compatibility(self):
        keys = {(r.family, r.release) for r in self.rules}
        if len(keys) != len(self.rules):
            raise ValueError('one compatibility rule per family/release')
        states = list(self.services) + [s for snapshot in self.snapshots.values() for s in snapshot]
        if any((s.family, s.release) not in keys for s in states):
            raise ValueError('service profile has no compatibility rule')
        return self


class CompatibilityStep(ClockStep):
    changes: tuple[CompatibilityService, ...]


class CompatibilityClock(ClockPlan):
    steps: tuple[CompatibilityStep, ...]


class CompatibilityFixture(Fixture):
    definition_model = CompatibilityDefinition
    service_model = CompatibilityService
    clock_model = CompatibilityClock

    @classmethod
    def validate_plan(cls, definition, clock):
        super().validate_plan(definition, clock)
        profiles = {(r.family, r.release) for r in definition.rules}
        if any((s.family, s.release) not in profiles for step in clock.steps for s in step.changes):
            raise ValueError('checkpoint profile has no compatibility rule')

    def healthy_mode(self, service):
        return next(r.healthy_mode for r in self.definition.rules
                    if (r.family, r.release) == (service.family, service.release))


def load_fixture(definition_raw, clock_raw):
    # An explicit two-way choice, not a plugin or tool-registration mechanism.
    value = load_json(definition_raw)
    kind = value.get('kind') if isinstance(value, dict) else None
    if kind not in {'SIMULATED_SERVICE', 'SERVICE_COMPATIBILITY_V1'}:
        raise ValueError('unsupported development fixture kind')
    cls = CompatibilityFixture if kind == 'SERVICE_COMPATIBILITY_V1' else Fixture
    definition = parse(cls.definition_model, definition_raw)
    clock = parse(cls.clock_model, clock_raw)
    cls.validate_plan(definition, clock)
    return cls, definition, clock
