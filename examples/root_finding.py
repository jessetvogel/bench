from __future__ import annotations

import random
import time
from datetime import timedelta
from typing import Annotated, Any, Self

from bench import Bench
from bench.metrics import Table, Time
from bench.serialization import PlainData
from bench.templates import Method, PlainResult, Task

# Create `Bench` instance
bench = Bench("Root finding")


# Add task type to benchmark
@bench.task
class Cubic(Task):
    def __init__(self, a: Annotated[float, "Parameter a"], b: float, c: float, d: float) -> None:
        self.a = a
        self.b = b
        self.c = c
        self.d = d

    def f(self, x: float) -> float:
        return self.a * x**3 + self.b * x**2 + self.c * x + self.d

    # The following two methods define metrics that are derived from
    # the result of a task.
    @Time()
    def time(self, result: PlainResult) -> dict[str, timedelta]:
        return {"time": timedelta(seconds=result["seconds"])}

    @Table()
    def table(self, result: PlainResult) -> dict[str, Any]:
        x = result["x"]
        y = self.f(x)
        return {
            "x": x,
            "abs(y)": abs(y),
            "calls to f(x)": result["num_evals"],
        }

    # Object of type `Cubic` can be encoded and decoded
    # by its properties `a`, `b`, `c` and `d`
    def encode(self) -> PlainData:
        return {"a": self.a, "b": self.b, "c": self.c, "d": self.d}

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        return cls(data["a"], data["b"], data["c"], data["d"])

    # Optional, custom label and description
    def label(self) -> str:
        return f"Cubic ({self.a}, {self.b}, {self.c}, {self.d})"

    def description(self) -> str:
        return (
            "The goal of this task is to find a root of the cubic function "
            f"f(x) = {self.a} x^3 + {self.b} x^2 + {self.c} x + {self.d}."
        )


# Add method type to benchmark
@bench.method
class RandomSolver(Method):
    def __init__(self, x_min: Annotated[float, "beschrijving"] = -10.0, x_max: float = +10.0) -> None:
        self.x_min = x_min
        self.x_max = x_max

    # Object of type `RandomSolver` can be encoded and decodedd
    # by its properties `x_min` and `x_max`
    def encode(self) -> PlainData:
        return {"x_min": self.x_min, "x_max": self.x_max}

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        return cls(data["x_min"], data["x_max"])

    def find_root(self, cubic: Cubic) -> PlainResult:
        # Sample the function at 1,000 random points
        # and keep track of the best x value
        num_evals = 1_000
        best_x = None
        best_abs_y = float("+inf")
        for _ in range(num_evals):
            x = random.uniform(self.x_min, self.x_max)
            abs_y = abs(cubic.f(x))
            if abs_y < best_abs_y:
                best_x, best_abs_y = x, abs_y
        return PlainResult(x=best_x, num_evals=num_evals)


@bench.method
class NewtonSolver(Method):
    def __init__(self, x_0: float = 0.0, eps: float = 0.01) -> None:
        self.x_0 = x_0
        self.eps = eps

    # Object of type `NewtonSolver` can be encoded and decodedd
    # by its properties `x_0` and `eps`
    def encode(self) -> PlainData:
        return {"x_0": self.x_0, "eps": self.eps}

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        return cls(data["x_0"], data["eps"])

    def find_root(self, cubic: Cubic) -> PlainResult:
        # Apply 1,000 iterations to update `x` with Newton's method
        num_iters = 1_000
        num_evals = 0
        x = self.x_0
        for _ in range(num_iters):
            df = (cubic.f(x + self.eps) - cubic.f(x - self.eps)) / (2 * self.eps)
            num_evals += 2
            if df == 0:
                break
            x -= cubic.f(x) / df
            num_evals += 1
        return PlainResult(x=x, num_evals=num_evals)


@bench.run
def run(cubic: Cubic, solver: RandomSolver | NewtonSolver) -> PlainResult:
    start_time = time.perf_counter()
    result = solver.find_root(cubic)
    end_time = time.perf_counter()
    result["seconds"] = end_time - start_time
    return result
