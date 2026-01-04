# This file does not contain any tests. Rather, it defines a `Bench` instance
# that can be used for other tests.

import random
import time
from datetime import timedelta
from typing import Any, Self, cast

from bench import Bench
from bench.metrics import Table, Time
from bench.serialization import PlainData
from bench.templates import Method, Result, Task

bench = Bench("test")


@bench.result
class OutcomeResult(Result):
    def __init__(self, outcome: float, seconds: float) -> None:
        self.outcome = outcome
        self.seconds = seconds

    def encode(self) -> PlainData:
        return {"outcome": self.outcome, "seconds": self.seconds}

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        assert isinstance(data, dict)
        return cls(outcome=cast(float, data["outcome"]), seconds=cast(float, data["seconds"]))


@bench.task
class TaskAdd(Task):
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def encode(self) -> PlainData:
        return {"x": self.x, "y": self.y}

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        assert isinstance(data, dict)
        return cls(cast(int, data["x"]), cast(int, data["y"]))

    @Time()
    def metric_time(self, result: OutcomeResult) -> dict[str, timedelta]:
        return {
            "time": timedelta(seconds=cast(float, result.seconds)),
        }

    @Table()
    def metric_table(self, result: OutcomeResult) -> dict[str, Any]:
        return {
            "error": abs(self.x + self.y - cast(float, result.outcome)),
        }


@bench.task
class TaskProd(Task):
    def __init__(self, u: int, v: int) -> None:
        self.u = u
        self.v = v

    def encode(self) -> PlainData:
        return {"u": self.u, "v": self.v}

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        assert isinstance(data, dict)
        return cls(cast(int, data["u"]), cast(int, data["v"]))

    @Time()
    def metric_time(self, result: OutcomeResult) -> dict[str, timedelta]:
        return {
            "time": timedelta(seconds=cast(float, result.seconds)),
        }

    @Table()
    def metric_table(self, result: OutcomeResult) -> dict[str, int | float | str | None]:
        return {
            "error": abs(self.u * self.v - cast(float, result.outcome)),
        }


@bench.method
class MethodExact(Method):
    def __init__(self) -> None:
        pass

    def encode(self) -> PlainData:
        return None

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        return cls()

    def solve(self, task: Task) -> float:
        if isinstance(task, TaskAdd):
            return task.x + task.y
        if isinstance(task, TaskProd):
            return task.u * task.v
        raise NotImplementedError()


@bench.method
class MethodApprox(Method):
    def __init__(self) -> None:
        pass

    def encode(self) -> PlainData:
        return None

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        return cls()

    def solve(self, task: Task) -> float:
        if isinstance(task, TaskAdd):
            return task.x + task.y + random.uniform(-0.5, +0.5)
        if isinstance(task, TaskProd):
            return task.u * task.v + random.uniform(-0.5, +0.5)
        raise NotImplementedError()


@bench.run
def run(task: Task, method: Method) -> Result:
    assert isinstance(task, (TaskAdd, TaskProd))
    assert isinstance(method, (MethodExact, MethodApprox))
    start_time = time.perf_counter()
    outcome = method.solve(task)
    end_time = time.perf_counter()
    result = OutcomeResult(
        outcome=outcome,
        seconds=end_time - start_time,
    )
    return result
