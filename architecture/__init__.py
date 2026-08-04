"""Architecture-aware GREEN-ECC design-space exploration interfaces."""

from .types import (
    CandidateRegistry,
    ECCConfiguration,
    MetricProvenance,
    Scenario,
    Workload,
)
from .traces import ScenarioTrace, TraceEpoch
from .transitions import ArchitectureDesign, ECCOperatingMode

__all__ = [
    "CandidateRegistry",
    "ECCConfiguration",
    "MetricProvenance",
    "Scenario",
    "Workload",
    "ScenarioTrace",
    "TraceEpoch",
    "ArchitectureDesign",
    "ECCOperatingMode",
]
