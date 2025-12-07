from collections.abc import Mapping
from datetime import timedelta
from types import MappingProxyType


class Metric:
    pass


class Table(Metric):
    def __init__(self, **kwargs: int | float | str) -> None:
        self._data = kwargs

    def data(self) -> Mapping[str, int | float | str]:
        return MappingProxyType(self._data)


class Time(Metric):
    def __init__(self, **kwargs: timedelta) -> None:
        self._data = kwargs

    def data(self) -> Mapping[str, timedelta]:
        return MappingProxyType(self._data)


class Graph(Metric):
    pass
