"""Validation rules resolving a bronze payload against its contract (F03).

Each rule emits :class:`Finding` objects carrying one of the closed ``ReasonCode`` values.
Rules run in priority order (required → type → range → duplicate); the first finding on a
row is its primary reason code.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.errors import ReasonCode
from src.quality.contracts import SupplierContract

Payload = dict[str, object]


@dataclass(frozen=True)
class Finding:
    reason: ReasonCode
    field: str
    detail: str


def as_text(value: object) -> str:
    """Render a payload value as the plain text it was delivered in."""
    if isinstance(value, bool):
        return str(value).lower()
    return "" if value is None else str(value)


def resolve_value(payload: Payload, path: str) -> object:
    """Follow a dotted path (e.g. ``attributes.size``) into the payload."""
    node: object = payload
    for key in path.split("."):
        if isinstance(node, dict):
            node = node.get(key, "")
        else:
            return ""
    return node


def _parse_int(value: object) -> int | None:
    try:
        return int(float(as_text(value)))
    except ValueError:
        return None


def _parse_bool(value: object) -> bool | None:
    text = as_text(value).strip().lower()
    if text in ("true", "1"):
        return True
    if text in ("false", "0"):
        return False
    return None


def check_required(contract: SupplierContract, payload: Payload, seen: set[str]) -> list[Finding]:
    del seen  # not used here
    return [
        Finding(ReasonCode.MISSING_REQUIRED, field, "required field is empty")
        for field in contract.required
        if as_text(resolve_value(payload, contract.mapping[field])).strip() == ""
    ]


def check_types(contract: SupplierContract, payload: Payload, seen: set[str]) -> list[Finding]:
    del seen  # not used here
    findings: list[Finding] = []
    for field, spec in contract.fields.items():
        value = resolve_value(payload, contract.mapping[field])
        text = as_text(value).strip()
        if not text:
            continue  # unknown/null values are allowed at the type level
        if spec.type == "integer" and _parse_int(value) is None:
            findings.append(Finding(ReasonCode.TYPE_MISMATCH, field, f"not an integer: {text!r}"))
        elif spec.type == "boolean" and _parse_bool(value) is None:
            findings.append(Finding(ReasonCode.TYPE_MISMATCH, field, f"not a boolean: {text!r}"))
        elif spec.type == "string" and spec.allowed and text not in spec.allowed:
            findings.append(
                Finding(ReasonCode.TYPE_MISMATCH, field, f"not an allowed value: {text!r}")
            )
    return findings


def check_ranges(contract: SupplierContract, payload: Payload, seen: set[str]) -> list[Finding]:
    del seen  # not used here
    findings: list[Finding] = []
    for field, spec in contract.fields.items():
        if spec.min is None and spec.max is None:
            continue
        value = _parse_int(resolve_value(payload, contract.mapping[field]))
        if value is None:
            continue  # unparseable values are the type rule's problem
        if spec.min is not None and value < spec.min:
            findings.append(Finding(ReasonCode.OUT_OF_RANGE, field, f"{value} < min {spec.min}"))
        elif spec.max is not None and value > spec.max:
            findings.append(Finding(ReasonCode.OUT_OF_RANGE, field, f"{value} > max {spec.max}"))
    return findings


def check_duplicates(contract: SupplierContract, payload: Payload, seen: set[str]) -> list[Finding]:
    sku = as_text(resolve_value(payload, contract.mapping["sku"])).strip()
    if not sku:
        return []
    if sku in seen:
        return [Finding(ReasonCode.DUPLICATE_SKU, "sku", f"already seen in this feed: {sku}")]
    seen.add(sku)
    return []


def check_row(contract: SupplierContract, payload: Payload, seen: set[str]) -> Finding | None:
    """Return the primary finding for one row, or ``None`` if it passes every rule."""
    for checker in (check_required, check_types, check_ranges, check_duplicates):
        findings = checker(contract, payload, seen)
        if findings:
            return findings[0]
    return None
