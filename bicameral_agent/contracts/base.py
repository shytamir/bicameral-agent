"""Strict JSON boundary and canonical wire representation."""

from datetime import datetime
import json
import math
from typing import Annotated, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


Identifier = Annotated[str, Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Text = Annotated[str, Field(min_length=1)]
Positive = Annotated[int, Field(gt=0)]
Nonnegative = Annotated[int, Field(ge=0)]
LocalKey = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


def _utc(value: str) -> str:
    datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    return value


UTC = Annotated[
    str,
    Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"),
    AfterValidator(_utc),
]


def unique(values: tuple) -> tuple:
    keys = [canonical_bytes(value) for value in values]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate set member")
    return values


EventIDs = Annotated[tuple[Identifier, ...], AfterValidator(unique)]


def _members(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _json_value(value: object) -> None:
    if value is None or type(value) in (bool, int):
        return
    if type(value) is str:
        value.encode("utf-8", errors="strict")
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) in (list, tuple):
        for item in value:
            _json_value(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("JSON object keys must be strings")
            _json_value(key)
            _json_value(item)
        return
    raise ValueError("value is not finite UTF-8 JSON")


def load_json(raw: bytes) -> object:
    """Reject duplicate members at every depth before Pydantic sees JSON."""
    if type(raw) is not bytes:
        raise TypeError("wire input must be bytes")
    value = json.loads(raw.decode("utf-8", errors="strict"),
                       object_pairs_hook=_members, parse_constant=_constant)
    _json_value(value)
    return value


def canonical_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", exclude_none=False)
    _json_value(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


T = TypeVar("T", bound=Contract)


def parse(model: type[T], raw: bytes) -> T:
    value = load_json(raw)
    # JSON mode admits JSON arrays as immutable tuples, but not scalar coercion.
    return model.model_validate_json(canonical_bytes(value), strict=True)


class PayloadReference(Contract):
    """Opaque indirection permits later removal without retaining content hashes."""

    payload_id: Identifier
