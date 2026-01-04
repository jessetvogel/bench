from __future__ import annotations

import importlib.util
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, cast

from bench import Bench
from bench._cache import Cache
from bench._logging import get_logger
from bench._process import Process
from bench._utils import to_hash
from bench.serialization import check_serializable
from bench.templates import MV, BenchError, Method, Metric, Result, Run, Task, Token


class Engine:
    """Engine / API

    Args:
        path: Path to Python module containing :py:class:`Bench` instance.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._logger = get_logger("bench")
        self._bench = load_bench(path)
        self._execution_processes: list[ExecutionProcess] = []

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

    @property
    def execution_processes(self) -> Iterable[ExecutionProcess]:
        """Currently running processes."""
        return tuple(self._execution_processes)

    def create_task(self, task_type: type[Task], **kwargs: int | float | str) -> Task:
        """Create task of given type with given arguments.

        Note: May raise an exception.
        """
        task = task_type.type_constructor()(**kwargs)
        check_serializable(task)
        self.cache.insert_task(task)
        return task

    def create_method(self, method_type: type[Method], **kwargs: int | float | str) -> Method:
        """Create method of given type with given arguments.

        Note: May raise an exception.
        """
        method = method_type.type_constructor()(**kwargs)
        check_serializable(method)
        self.cache.insert_method(method)
        return method

    def execute_run_in_process(self, task: Task, method: Method, *, num_runs: int = 1) -> None:
        """Launch new process to execute a run based on the given task and method.

        Args:
            task: Task to execute.
            method: Method to apply to task.
            num_runs: Number of runs to execute.
        """
        # Make sure task and method are in the database
        self.cache.insert_task(task)
        self.cache.insert_method(method)

        # Create new run(s) with status "pending"
        task_id = to_hash(task)
        method_id = to_hash(method)

        # Execute the run as a separate process
        process = Process(
            ["bench-run", str(self._path), task_id, method_id, "-n", str(num_runs)],
            path_stdout=self.cache.temporary_file(),
        )
        self._execution_processes.append(
            ExecutionProcess(
                process=process,
                task=task,
                method=method,
                num_runs=num_runs,
                created_at=datetime.now(),
            )
        )

    def execute_run(self, task: Task, method: Method) -> Run | None:
        """Execute run from task and method.

        Args:
            task: Task to execute.
            method: Method to apply to task.
        """
        if (run_handler := self._bench.run_handler) is None:
            msg = "No run handler was registered. Use the `run` method to register a handler."
            raise RuntimeError(msg)

        # Perform task with method
        try:
            result = run_handler(task, method)
        except Exception:
            self._logger.exception("Run failed due to the following error:")
            return None

        # Create and store run from result
        self.cache.insert_or_update_run(
            run := Run(
                id=secrets.token_hex(8),
                task_id=to_hash(task),
                method_id=to_hash(method),
                result=result,
            )
        )

        return run

    def evaluate_metric(self, metric: Metric[MV], run: Run) -> MV:
        # Check that run has status 'done'
        if not isinstance(run.result, Result):
            msg = f"Expected run with status 'done', but got {run.status}"
            raise ValueError(msg)
        # Get task for run
        task = self.cache.select_task(run.task_id)
        # Cache metrics in run in private field "_metrics"
        if not hasattr(run, "_metrics"):
            setattr(run, "_metrics", {})
        metrics = cast(dict[str, Any], getattr(run, "_metrics"))
        if metric.name in metrics:
            return metrics[metric.name]
        # Evaluate metric with run result
        metric_value = metric.evaluate(task, run.result)
        metrics[metric.name] = metric_value
        return metric_value

    def delete_runs(self, runs: Iterable[Run]) -> None:
        self.cache.delete_runs(list(runs))

    def execute_poll(self, token: Token) -> Result | None:
        if (poll_handler := self._bench.poll_handler) is None:
            msg = "No poll handler was registered. Use the `Bench.poll` method to register a handler."
            raise RuntimeError(msg)

        # Perform task with method
        result: Result | BenchError | None
        try:
            result = poll_handler(token)
        except Exception as err:
            result = BenchError(str(err))
            self._logger.exception("Poll failed due to the following error:")

        # TODO: finish this function
        result = result
        return None

    def shutdown(self) -> None:
        self.cache.shutdown()


def load_bench(path: Path) -> Bench:
    """Load :py:class:`Bench` instance from the module given by the provided path.

    Args:
        path: Path to Python module containing :py:class:`Bench` instance.

    Returns:
        A :py:class:`Bench` instance.
    """
    if not path.exists():
        msg = f"File '{path}' does not exist"
        raise FileNotFoundError(msg)

    # Load module
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None:
        msg = f"Failed to load module '{path}'"
        raise ValueError(msg)
    module = importlib.util.module_from_spec(spec)
    # sys.modules[module_name] = module  # TODO: is this necessary ?
    assert spec.loader is not None  # TODO: can `spec.loader` be `None` ?
    spec.loader.exec_module(module)

    # Find `Bench` instance
    for _, object in vars(module).items():
        if isinstance(object, Bench):
            return object

    msg = f"Python module '{path}' contains no instance of `Bench`"
    raise ValueError(msg)


@dataclass
class ExecutionProcess:
    process: Process
    task: Task
    method: Method
    num_runs: int
    created_at: datetime

    @property
    def id(self) -> str:
        return str(self.created_at)
