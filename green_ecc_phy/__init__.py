"""Extensible, evidence-gated multi-ECC characterization framework."""

from .contracts import DecodeResult, DecodeStatus, EccAdapter
from .registry import EccRegistry

__all__ = ["DecodeResult", "DecodeStatus", "EccAdapter", "EccRegistry"]

