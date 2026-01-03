<img src="img/banner.png" style="height: 80px;"/>

Bench is a Python framework for benchmarking. It provides an easy and fast way to set up a benchmark. It handles the data management side of the benchmark, and provides a user-friendly dashboard for running the benchmark and viewing the results.

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

## 🚀 Getting started

Create a file `my_benchmark.py` with the following contents.

```python
from bench import Bench

from my_package import MyTask, MyMethod, MyResult

# Create a Bench instance
bench = Bench("My benchmark")

# Add custom task, method and result types
bench.task(MyTask)
bench.method(MyMethod)
bench.result(MyResult)

# Define function for how to execute task using method
@bench.run
def run(task: MyTask, method: MyMethod) -> MyResult:
    # < your logic >
    return MyResult(...)
```

Run the command `bench-dashboard my_benchmark.py` to start the bench dashboard.
