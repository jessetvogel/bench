from dataclasses import dataclass

from bench.templates import Metric


@dataclass(init=False)
class Table(Metric):
    keys: tuple[str, ...]

    def __init__(self, *keys: str) -> None:
        self.keys = keys


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
