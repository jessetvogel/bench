from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from bench.templates import Metric


class Table(Metric):
    def __init__(self, **kwargs: int | float | str) -> None:
        self._data = kwargs

    def data(self) -> Mapping[str, int | float | str]:
        return MappingProxyType(self._data)


@dataclass(init=False)
class Time(Metric):
    keys: tuple[str, ...]

    def __init__(self, *keys: str) -> None:
        self.keys = keys


@dataclass
class Graph(Metric):
    key_xs: str
    key_ys: str
    title: str | None = None
    xlabel: str | None = None
    ylabel: str | None = None
    option_mean_std: bool = False
