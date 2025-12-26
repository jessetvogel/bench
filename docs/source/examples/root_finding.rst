Root finding
============

Let us create a benchmark for root finding using the :py:mod:`bench` framework.

First, we must define what a *task* is. In this example, we will consider only one type of tasks, which is to find roots of *cubic* functions, that is, functions of the form :math:`f(x) = ax^3 + bx^2 + cx + d` for some :math:`a, b, c, d \in \mathbb{R}`. We define the following class :py:class:`Cubic` derived from :py:class:`~bench.templates.Task`.

.. code-block:: python

    from datetime import timedelta
    from typing import Self, Any

    from bench.templates import Metric, Result, Task
    from bench.metrics import Time, Table
    from bench.serialization import PlainData

    class Cubic(Task):

        def __init__(self, a: float, b: float, c: float, d: float) -> None:
            self.a, self.b, self.c, self.d = a, b, c, d

        # Every task must have an `encode` and `decode` method, for reading
        # and writing the task to the database. Tasks of type `Cubic` can be
        # encoded and decoded by its properties `a`, `b`, `c` and `d`.
        def encode(self) -> PlainData:
            return {"a": self.a, "b": self.b, "c": self.c, "d": self.d}

        @classmethod
        def decode(cls, data: PlainData) -> Self:
            return cls(data["a"], data["b"], data["c"], data["d"])

        # Method to evaluate the cubic function
        def f(self, x: float) -> float:
            return self.a * x**3 + self.b * x**2 + self.c * x + self.d
        
        # The `metrics` method describes the metrics that can be derived from
        # the result of a task. The `evaluate` method computes the actual values
        # for these metrics from a result instance.
        @classmethod
        def metrics(self) -> list[Metric]:
            return [Time("time"), Table("x", "abs(y)", "calls to f(x)")]

        def evaluate(self, result: Result) -> dict[str, Any]:
            x = result["x"]
            y = self.f(x)
            return {
                "time": timedelta(seconds=result["seconds"]),
                "x": x,
                "abs(y)": abs(y),
                "calls to f(x)": result["num_evals"],
            }

Next, we need to define what a *method* is. In this example, we will implement two methods so that there is something to compare. The first method, :py:class:`RandomSolver`, try to find a root by randomly sampling points within an interval :math:`[x_\textup{min}, x_\textup{max}]`. The second method, :py:class:`NewtonSolver`, will be based on `Newton's method <https://en.wikipedia.org/wiki/Newton's_method>`__, where derivatives are approximated using finite differences.

.. code-block:: python

    import random
    from typing import Self

    from bench.templates import Method, Result
    from bench.serialization import PlainData
    
    class RandomSolver(Method):
        def __init__(self, x_min: float = -10.0, x_max: float = +10.0) -> None:
            self.x_min, self.x_max = x_min, x_max

        # Instances of type `RandomSolver` can be encoded and decoded
        # by its properties `x_min` and `x_max`.
        def encode(self) -> PlainData:
            return {"x_min": self.x_min, "x_max": self.x_max}

        @classmethod
        def decode(cls, data: PlainData) -> Self:
            return cls(data["x_min"], data["x_max"])

        # Method to find a root of a cubic by sampling it at 1,000
        # random points in the interval [x_min, x_max].
        def find_root(self, cubic: Cubic) -> Result:
            num_evals = 1_000
            best_x = None
            best_abs_y = float("+inf")
            for _ in range(num_evals):
                x = random.uniform(self.x_min, self.x_max)
                abs_y = abs(cubic.f(x))
                if abs_y < best_abs_y:
                    best_x, best_abs_y = x, abs_y
            return Result(x=best_x, num_evals=num_evals)


    class NewtonSolver(Method):
        def __init__(self, x_0: float = 0.0, eps: float = 0.01) -> None:
            self.x_0, self.eps = x_0, eps

        # Instances of type `NewtonSolver` can be encoded and decoded
        # by its properties `x_0` and `eps`.
        def encode(self) -> PlainData:
            return {"x_0": self.x_0, "eps": self.eps}

        @classmethod
        def decode(cls, data: PlainData) -> Self:
            return cls(data["x_0"], data["eps"])

        # Method to find a root of a cubic using 1,000 iterations of Newton's
        # method, where derivatives are estimated using finite differences.
        def find_root(self, cubic: Cubic) -> Result:
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
            return Result(x=x, num_evals=num_evals)

Create a file ``root_finding.py`` with the following contents.

.. code-block:: python

    import time
    
    from bench import Bench
    from bench.templates import Task, Method, Result

    # .. define or import `Cubic`, `RandomSolver`, `NewtonSolver` ..

    # Create `Bench` instance
    bench = Bench("Root finding")

    # Add the task types and method types
    bench.add_task_types(Cubic)
    bench.add_method_types(RandomSolver, NewtonSolver)

    # Define a callback method for executing a task with a method
    @bench.on_run
    def run(task: Task, method: Method) -> Result:
        assert isinstance(task, Cubic)
        assert isinstance(method, RandomSolver | NewtonSolver)

        start_time = time.perf_counter()
        result = method.find_root(task)
        end_time = time.perf_counter()
        result["seconds"] = end_time - start_time
        return result

Finally, run ``bench-dashboard root_finding.py`` to start the bench dashboard.
