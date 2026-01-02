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
    def metric_time(self, result: Result) -> dict[str, timedelta]:
        return {
            "time": timedelta(seconds=cast(float, result["sec"])),
        }

    @Table()
    def metric_table(self, result: Result) -> dict[str, Any]:
        return {
            "error": abs(self.x + self.y - cast(float, result["sum"])),
        }


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
    def metric_time(self, result: Result) -> dict[str, timedelta]:
        return {
            "time": timedelta(seconds=cast(float, result["sec"])),
        }

    @Table()
    def metric_table(self, result: Result) -> dict[str, int | float | str | None]:
        return {
            "error": abs(self.u * self.v - cast(float, result["prod"])),
        }


class MethodExact(Method):
    def __init__(self) -> None:
        pass

    def encode(self) -> PlainData:
        return None

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        return cls()

    def solve(self, task: Task) -> Result:
        if isinstance(task, TaskAdd):
            sum = task.x + task.y
            return Result(sum=sum)
        if isinstance(task, TaskProd):
            prod = task.u * task.v
            return Result(prod=prod)
        raise NotImplementedError()


class MethodApprox(Method):
    def __init__(self) -> None:
        pass

    def encode(self) -> PlainData:
        return None

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        return cls()

    def solve(self, task: Task) -> Result:
        if isinstance(task, TaskAdd):
            sum = task.x + task.y + random.uniform(-0.5, +0.5)
            return Result(sum=sum)
        if isinstance(task, TaskProd):
            prod = task.u * task.v + random.uniform(-0.5, +0.5)
            return Result(prod=prod)
        raise NotImplementedError()


bench = Bench("test")

bench.task(TaskAdd, TaskProd)
bench.method(MethodExact, MethodApprox)


@bench.run
def run(task: Task, method: Method) -> Result:
    assert isinstance(task, (TaskAdd, TaskProd))
    assert isinstance(method, (MethodExact, MethodApprox))
    start_time = time.perf_counter()
    result = method.solve(task)
    end_time = time.perf_counter()
    result["sec"] = end_time - start_time
    return result
