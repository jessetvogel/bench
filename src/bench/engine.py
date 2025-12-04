from bench.cache import Cache
from bench.templates import Bench, Task


class Engine:
    """Engine / API"""

    def __init__(self, bench: Bench) -> None:
        self._bench = bench

    @property
    def bench(self) -> Bench:
        """Underlying benchmark specification."""
        return self._bench

    @property
    def cache(self) -> Cache:
        """Cache for database I/O."""
        if not hasattr(self, "_cache"):
            self._cache = Cache(self._bench)
        return self._cache

    def create_task(self, task_type: type[Task], **kwargs: int | float | str) -> None:
        """Create task of given type with given arguments.

        Note: May raise an exception.
        """
        task = task_type(**kwargs)
        self.cache.insert_task(task)
