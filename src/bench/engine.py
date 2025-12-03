from bench.cache import Cache
from bench.templates import Bench


class Engine:
    """Engine / API"""

    def __init__(self, bench: Bench) -> None:
        self._bench = bench

    @property
    def name(self) -> str:
        return self._bench.name

    @property
    def cache(self) -> Cache:
        if not hasattr(self, "_cache"):
            self._cache = Cache(self._bench)
        return self._cache
