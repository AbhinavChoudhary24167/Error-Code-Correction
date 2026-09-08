"""GREEN Matrix v3.2 evidence-aware decision campaign."""

from .core import (
    ActivityCompleteness,
    GreenVector,
    GuardViolation,
    Objective,
    conditional_outcome_rate_per_hour,
    csci_kgco2e_per_correct_service,
    decision_admissibility,
    diagnostic_scalarization,
    exact_pareto_ids,
    fit_from_event_rate,
    mrcc_kgco2e_per_additional_correct_service,
    qualify_e5_activity,
    scenario_space_nondominance_fraction,
)

__all__ = [
    "ActivityCompleteness",
    "GreenVector",
    "GuardViolation",
    "Objective",
    "conditional_outcome_rate_per_hour",
    "csci_kgco2e_per_correct_service",
    "decision_admissibility",
    "diagnostic_scalarization",
    "exact_pareto_ids",
    "fit_from_event_rate",
    "mrcc_kgco2e_per_additional_correct_service",
    "qualify_e5_activity",
    "scenario_space_nondominance_fraction",
]
