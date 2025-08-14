"""Area estimation for ECC logic and memory overhead."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict


@dataclass
class ECCSpec:
    name: str
    data_bits: int
    check_bits: int
    corrects_adj2: bool = False
    corrects_adj3: bool = False


# Load NAND2 area table (mm^2 per NAND2 gate) from JSON
_AREA_TABLE: Dict[int, float] = json.load(
    open(Path(__file__).with_name("nand2_area.json"))
)

# Gate to NAND2 equivalents
_GATE_EQ = {"xor": 4, "and": 1, "adder": 6, "ff": 10}
_UTILIZATION = 0.75


def logic_gate_counts(spec: ECCSpec) -> dict:
    """Return gate counts for an ECC encoder/decoder."""
    data, check = spec.data_bits, spec.check_bits

    xor_enc = check * (data - 1)
    xor_dec = check * (data + check - 1)
    xors = xor_enc + xor_dec
    if spec.corrects_adj2:
        xors += data
    if spec.corrects_adj3:
        xors += 2 * data

    ands = data * check
    if spec.corrects_adj2:
        ands += data
    if spec.corrects_adj3:
        ands += 2 * data

    adders = check
    if spec.corrects_adj2:
        adders += data // 2
    if spec.corrects_adj3:
        adders += data

    ffs = data + check

    return {"xor": xors, "and": ands, "adder": adders, "ff": ffs}


def area_logic_mm2(spec: ECCSpec, node_nm: int, impl: str = "combinational") -> float:
    """Estimate logic area in mm^2 using NAND2 equivalents."""
    counts = logic_gate_counts(spec)
    nand2_area = _AREA_TABLE[str(node_nm)]
    total_nand2 = sum(counts[k] * _GATE_EQ[k] for k in counts)
    return total_nand2 * nand2_area / _UTILIZATION


def macro_ecc_overhead_bits(spec: ECCSpec) -> int:
    """Return extra ECC bits per word."""
    return spec.check_bits


def area_macro_mm2(
    spec: ECCSpec,
    capacity_gib: float,
    node_nm: int,
    bitcell_um2: float,
    periphery_overhead_frac: float = 0.20,
) -> float:
    """Area of extra ECC bitcells and periphery in mm^2."""
    capacity_bits = capacity_gib * (2 ** 30) * 8
    extra_bits = macro_ecc_overhead_bits(spec)
    ecc_cells = capacity_bits * extra_bits / spec.data_bits
    cell_area_mm2 = ecc_cells * bitcell_um2 * 1e-6
    return cell_area_mm2 * (1.0 + periphery_overhead_frac)
