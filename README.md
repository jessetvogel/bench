<img src="img/banner.png" style="height: 80px;"/>

Bench is a Python framework for benchmarking.

## 📦 Installation

Bench can be installed directly using `pip`.

```sh
pip install "bench @ git+https://github.com/jessetvogel/bench.git@main"
```

Alternatively, bench can be installed by adding the following dependency to your
`pyproject.toml` file.

```toml
[project]
dependencies = [
  "bench @ git+https://github.com/jessetvogel/bench.git@main"
]
```

## 💬 Description

Bench is a Python framework for benchmarking. It handles data management and provides a user interface for starting experiments and comparing the results for different methods.

The user only has to provide what a *task* is, and what a *method* is, and how to execute a task given a method.

## 🚀 Getting started

Create a file `my_benchmark.py` with the following contents.

```python
from bench import Bench

from my_package import MyTask, MyMethod, MyResult

# Create `Bench` instance
bench = Bench("My benchmark")

# Add task, method and result types
bench.add_task_types(MyTask)
bench.add_method_types(MyMethod)
bench.add_result_types(MyResult)

# Define method for how to execute task using method
@bench.on_run
def run(task: MyTask, method: MyMethod) -> MyResult:
    # < your logic >
    return MyResult(...)
```

Run the command `bench-dashboard my_benchmark.py` to start the bench dashboard.

### Tasks

To create your own class of tasks, create a Python class that derives from the `bench.templates.Task` class.

```python
from bench.templates import Metric, Result, Task
from bench.serialization import PlainData
from typing import Self

class MyTask(Task):

    def encode(self) -> PlainData:
        ...

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        ...

    @classmethod
    def metrics(self) -> list[Metric]:
        ...

    def evaluate(self, result: Result) -> dict[str, Any]:
        ...
```

#### Optional

- Overwite `@classmethod type_label(cls) -> str` for displaying a custom name for the type of tasks.

- Overwrite `@classmethod type_description(cls) -> str` for displaying a custom name for the type of tasks.

- ...

### Methods

To create your own class of methods, create a Python class that derives from the [`bench.templates.Method`](https://jessetvogel.nl/bench/modules/bench.templates.html#bench.templates.Method) class. This class should at least implement the following methods:

- [`encode`](https://jessetvogel.nl/bench/modules/bench.templates.html#bench.templates.Method.encode) - ...

```python
from bench.templates import Method, Metric
from bench.serialization import PlainData
from typing import Self

class MyMethod(Method):

    def encode(self) -> PlainData:
        ...

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        ...
```
