import importlib.util
import inspect
import secrets
import time
from pathlib import Path

from bench.cache import Cache
from bench.logging import get_logger
from bench.process import Process
from bench.templates import Bench, Method, Run, Task
from bench.utils import hash_serializable


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

    def create_run(self, task: Task, method: Method) -> None:
        """Create run based on the given task and method.

        Args:
            task: Task to execute.
            method: Method to apply to task.
        """
        # Make sure task and method are in the database
        self.cache.insert_task(task)
        self.cache.insert_method(method)

        # Create new run with status pending
        run = Run(
            id=secrets.token_hex(8),
            task_id=hash_serializable(task),
            method_id=hash_serializable(method),
            result=None,
        )
        self.cache.insert_or_update_run(run)

        print(f"STARTING RUN WITH ID = {run.id}")
        print(f"METHOD TYPE = {method.name()}")

        # TODO: Execute as a separate process!
        process = Process(["bench-run", "main.py", run.id])

        logger = get_logger("bench")

        while process.poll() is None:
            logger.debug("Waiting for subprocess ..")
            logger.debug(f" > stdout: {process.stdout}")
            time.sleep(0.5)

        logger.debug(f" > stdout: {process.stdout}")

        logger.debug("Subprocess completed!")

    def execute_run(self, run_id: str) -> None:
        run = self.cache.select_run(run_id)
        if run.status != "pending":
            msg = f"Expected run '{run_id}' to be pending, but is {run.status}"
            raise ValueError(msg)
        task = self.cache.select_task(run.task_id)
        method = self.cache.select_method(run.method_id)

        print(f"EXECUTING RUN WITH TASK {task.name()} AND METHOD {method.name()}")

        run.result = self._bench.run(task, method)
        self.cache.insert_or_update_run(run)


def create_engine_from_module(path: Path) -> Engine:
    """Create :py:class:`Engine` using the :py:class:`Bench` instance in the module given by the path.

    Args:
        path: Path to Python module containing :py:class:`Bench` instance.

    Returns:
        An :py:class:`Engine` instance.
    """
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)

    if spec is None:
        msg = f"Failed to load '{path}'"
        raise ValueError(msg)

    module = importlib.util.module_from_spec(spec)
    # sys.modules[module_name] = module  # optional but avoids edge cases TODO: necessary ?
    if spec.loader is None:
        msg = "spec.loader is none, why?"
        raise RuntimeError(msg)

    spec.loader.exec_module(module)

    for _, object in vars(module).items():
        if not inspect.isclass(object):
            continue
        if not issubclass(object, Bench):
            continue
        if object is Bench:
            continue
        if object.__module__ != module.__name__:
            continue

        bench = object()
        return Engine(bench)

    msg = f"Python module '{path}' contains no instance of `Bench`"
    raise ValueError(msg)
