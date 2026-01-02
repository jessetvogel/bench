from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from bench.templates import Metric


@dataclass
class Table(Metric[dict[str, Any]]):
    def __init__(self) -> None:
        pass


@dataclass
class Time(Metric[dict[str, timedelta]]):
    title: str | None = None


@dataclass
class Graph(Metric[tuple[list[float], list[float]]]):
    title: str | None = None
    xlabel: str | None = None
    ylabel: str | None = None
    show_avg_std: bool = False
