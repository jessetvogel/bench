from __future__ import annotations

import importlib.util
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from bench.cache import Cache
from bench.logging import get_logger
from bench.process import Process
from bench.templates import Bench, Method, Result, Run, Task
from bench.utils import hash_serializable


class Engine:
    """Engine / API

    Args:
        path: Path to Python module containing :py:class:`Bench` instance.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._logger = get_logger("bench")
        self._bench = load_bench(path)
        self._executions: list[Execution] = []

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
    def executions(self) -> Iterable[Execution]:
        """Currently running processes."""
        return tuple(self._executions)

    def create_task(self, task_type: type[Task], **kwargs: int | float | str) -> None:
        """Create task of given type with given arguments.

        Note: May raise an exception.
        """
        task = task_type(**kwargs)
        self.cache.insert_task(task)

    def launch_run(self, task: Task, method: Method) -> None:
        """Launch new process to execute a run based on the given task and method.

        Args:
            task: Task to execute.
            method: Method to apply to task.
        """
        # Make sure task and method are in the database
        self.cache.insert_task(task)
        self.cache.insert_method(method)

        # Create new run with status pending
        task_id = hash_serializable(task)
        method_id = hash_serializable(method)
        run = Run(
            id=secrets.token_hex(8),
            task_id=task_id,
            method_id=method_id,
            result=None,
        )
        self.cache.insert_or_update_run(run)

        # Execute the run as a separate process
        process = Process(["bench-run", str(self._path), run.id])
        self._executions.append(
            Execution(
                task=task,
                method=method,
                run=run,
                created_at=datetime.now(),
                process=process,
            )
        )

    def execute_run(self, run_id: str) -> None:
        """Execute run with given id.

        Args:
            run_id: ID of the run to execute.
        """
        run = self.cache.select_run(run_id)
        if run.status != "pending":
            msg = f"Expected run {run_id} to be pending, but is {run.status}"
            raise ValueError(msg)
        task = self.cache.select_task(run.task_id)
        method = self.cache.select_method(run.method_id)
        self._logger.info(f"Executing run {run_id} ..")
        run.result = self._bench.run(task, method)
        self.cache.insert_or_update_run(run)

    def evaluate_run(self, run: Run) -> dict[str, Any]:
        if not isinstance(run.result, Result):
            msg = f"Expected run with status 'done', but got {run.status}"
            raise ValueError(msg)

        if not hasattr(run, "_metrics"):
            task = self.cache.select_task(run.task_id)
            metrics = task.evaluate(run.result)
            setattr(run, "_metrics", metrics)

        return getattr(run, "_metrics")


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
class Execution:
    task: Task
    method: Method
    run: Run
    created_at: datetime
    process: Process
