"""YAML data contracts and their typed model (F03).

The contract is the single place thresholds live: required fields, per-field type/range/
allowed values, and the mapping from canonical logical fields onto each feed's raw_payload.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from src.errors import ContractError


class FieldSpec(BaseModel):
    type: str
    min: float | None = None
    max: float | None = None
    allowed: list[str] = []


class SupplierContract(BaseModel):
    required: list[str]
    fields: dict[str, FieldSpec]
    mapping: dict[str, str]


class ContractBundle(BaseModel):
    suppliers: dict[str, SupplierContract]


def load_contracts(contracts_dir: str | Path) -> dict[str, SupplierContract]:
    """Load every supplier contract from ``supplier_contract.yaml``."""
    path = Path(contracts_dir) / "supplier_contract.yaml"
    if not path.exists():
        raise ContractError(f"contract file missing: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return ContractBundle.model_validate(data).suppliers
    except Exception as exc:  # malformed YAML or schema drift — surface loudly
        raise ContractError(f"invalid contract file {path}: {exc}") from exc
