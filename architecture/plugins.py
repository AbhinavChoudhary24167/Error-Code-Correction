"""Plugin contracts for scenario-general GREEN-ECC extensions."""

from __future__ import annotations

from typing import Any, Callable, Generic, Mapping, Protocol, TypeVar


class FaultDistributionProvider(Protocol):
    provider_id: str

    def distribution(self, scenario: Mapping[str, object]) -> Mapping[str, float]: ...


class WorkloadProvider(Protocol):
    provider_id: str

    def resolve(self, scenario: Mapping[str, object]) -> Mapping[str, object]: ...


class TechnologyProvider(Protocol):
    provider_id: str

    def resolve_pvt(self, node_nm: int, vdd: float, temperature_c: float) -> Mapping[str, object]: ...


class CarbonTraceProvider(Protocol):
    provider_id: str

    def intensity_kgco2e_per_kwh(self, scenario: Mapping[str, object]) -> float: ...


class SelectionPolicy(Protocol):
    policy_id: str

    def select(self, candidates: list[Mapping[str, object]], constraints: Mapping[str, float]) -> str: ...


T = TypeVar("T")


class PluginRegistry(Generic[T]):
    """Runtime registry shared by fault, workload, technology, carbon, and policy plugins."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[..., T]] = {}

    def register(self, plugin_id: str, factory: Callable[..., T]) -> None:
        if plugin_id in self._factories:
            raise ValueError(f"Plugin already registered: {plugin_id}")
        self._factories[plugin_id] = factory

    def create(self, plugin_id: str, **kwargs: Any) -> T:
        try:
            factory = self._factories[plugin_id]
        except KeyError as exc:
            raise KeyError(f"Unknown plugin: {plugin_id}") from exc
        return factory(**kwargs)

    def available(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))
