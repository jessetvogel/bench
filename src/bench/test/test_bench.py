from typing import Any, Self

import pytest

from bench import Bench
from bench.serialization import PlainData
from bench.templates import Method, Metric, Result, Task


class T(Task):
    def __init__(self) -> None:
        pass

    def encode(self) -> PlainData:
        return {}

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        return cls()

    @classmethod
    def metrics(self) -> list[Metric]:
        return []

    def analyze(self, result: Result) -> dict[str, Any]:
        return {}


class M(Method):
    def __init__(self) -> None:
        pass

    def encode(self) -> PlainData:
        return {}

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        return cls()


class R(Result):
    pass


def test_bench_add_type_that_does_not_derive_from() -> None:
    """Check that an error is raised when a type is added that does not derive form `Task`, `Method` or `Result`."""
    bench = Bench("")

    class A: ...

    with pytest.raises(ValueError, match="must derive from"):
        bench.task(A)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must derive from"):
        bench.method(A)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must derive from"):
        bench.result(A)  # type: ignore[arg-type]


def test_bench_add_type_that_does_not_implement_abstract_methods() -> None:
    """Check that an error is raised when a type is added that does not implement all abstract methods."""
    bench = Bench("")

    class T(Task): ...

    class M(Method): ...

    with pytest.raises(ValueError, match="must implement"):
        bench.task(T)  # type: ignore[type-abstract]
    with pytest.raises(ValueError, match="must implement"):
        bench.method(M)  # type: ignore[type-abstract]


def test_bench_add_types_are_stored() -> None:
    """Check that types added to a bench instance are indeed stored."""
    bench = Bench("")

    @bench.task
    class T1(T): ...

    @bench.task
    class T2(T): ...

    @bench.method
    class M1(M): ...

    @bench.method
    class M2(M): ...

    @bench.result
    class R1(R): ...

    @bench.result
    class R2(R): ...

    assert list(bench.task_types) == [T1, T2]
    assert list(bench.method_types) == [M1, M2]
    assert list(bench.result_types) == [Result, R1, R2]
