import importlib.util
import secrets
from pathlib import Path

from bench.cache import Cache
from bench.logging import get_logger
from bench.process import Process
from bench.templates import Bench, Method, Run, Task
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

    def create_run(self, task: Task, method: Method) -> Process:
        """Create run based on the given task and method.

        Args:
            task: Task to execute.
            method: Method to apply to task.

        Returns:
            A :py:class:`Process` instance that executes the run.
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

        # Execute the run as a separate process
        return Process(["bench-run", str(self._path), run.id])

    def execute_run(self, run_id: str) -> None:
        run = self.cache.select_run(run_id)
        if run.status != "pending":
            msg = f"Expected run '{run_id}' to be pending, but is {run.status}"
            raise ValueError(msg)
        task = self.cache.select_task(run.task_id)
        method = self.cache.select_method(run.method_id)
        run.result = self._bench.run(task, method)
        self.cache.insert_or_update_run(run)


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
