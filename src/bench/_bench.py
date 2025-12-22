from collections.abc import Callable, Iterable

from bench.logging import get_logger
from bench.templates import Method, Result, Task, Token

_LOGGER = get_logger("bench")


class Bench:
    """Specification of the benchmark.

    Args:
        name: Name of the benchmark.
    """

    def __init__(self, name: str) -> None:
        self._name = name
        self._task_types: list[type[Task]] = []
        self._method_types: list[type[Method]] = []
        self._result_types: list[type[Result]] = [Result]
        self._handler_run: Callable[[Task, Method], Result | Token] | None = None
        self._handler_poll: Callable[[Token], Result | None] | None = None

    def add_task_types(self, *types: type[Task]) -> None:
        for task_type in types:
            if _check_user_type(Task, task_type):
                self._task_types.extend(types)

    def add_method_types(self, *types: type[Method]) -> None:
        for method_type in types:
            if _check_user_type(Method, method_type):
                self._method_types.extend(types)

    def add_result_types(self, *types: type[Result]) -> None:
        for result_type in types:
            if _check_user_type(Result, result_type):
                self._result_types.extend(types)

    def on_run(self, handler: Callable[[Task, Method], Result | Token]) -> None:
        """Set handler for executing tasks with a method.

        Args:
            handler: Function that executes a task with a method. The function should return
                a :py:class:`Result` instance if the task can be completed at once.
                Otherwise, a :py:class:`Token` instance is returned which can be used
                to obtain the result at a later time.
        """
        # TODO: validate handler
        self._handler_run = handler

    def run(self, task: Task, method: Method) -> Result | Token:
        if self._handler_run is None:
            msg = "No run handler was registered. Use the `on_run` method to register a handler."
            raise RuntimeError(msg)
        return self._handler_run(task, method)

    def on_poll(self, handler: Callable[[Token], Result | None]) -> None:
        """Set handler for polling a result.

        Args:
            handler: Function that checks if the execution of the task is completed.
                This function should return a :py:class:`Result` instance if the task
                is completed, and :py:const:`None` otherwise.
        """
        # TODO: validate handler
        self._handler_poll = handler

    def poll(self, token: Token) -> Result | None:
        if self._handler_poll is None:
            msg = "No poll handler was registered. Use the `on_poll` method to register a handler."
            raise RuntimeError(msg)
        return self._handler_poll(token)

    @property
    def name(self) -> str:
        """Name of the benchmark."""
        return self._name

    @property
    def task_types(self) -> Iterable[type[Task]]:
        return iter(self._task_types)

    @property
    def method_types(self) -> Iterable[type[Method]]:
        return iter(self._method_types)

    @property
    def result_types(self) -> Iterable[type[Result]]:
        return iter(self._result_types)

    def get_task_type(self, name: str) -> type[Task]:
        for task_type in self._task_types:
            if task_type.type_label() == name:
                return task_type
        msg = f"Unknown task type '{name}'"
        raise ValueError(msg)

    def get_method_type(self, name: str) -> type[Method]:
        for method_type in self._method_types:
            if method_type.type_label() == name:
                return method_type
        msg = f"Unknown method type '{name}'"
        raise ValueError(msg)

    def get_result_type(self, name: str) -> type[Result]:
        for result_type in self._result_types:
            if result_type.type_label() == name:
                return result_type
        msg = f"Unknown result type '{name}'"
        raise ValueError(msg)


def _check_user_type(cls: type[Task | Method | Result], user_type: type) -> bool:
    """Check if `user_type` is a valid task, method or result type."""
    # Check if derives from `cls`
    if not issubclass(user_type, cls):
        _LOGGER.warning(
            "Class '%s' must derive from `%s.%s` to be used as %s type",
            user_type.__name__,
            cls.__module__,
            cls.__name__,
            cls.__name__.lower(),
        )
        return False
    # Check if abstract methods are implemented
    user_type_abstract_methods = user_type.__abstractmethods__  # type: ignore[attr-defined]
    if user_type_abstract_methods:
        _LOGGER.warning(
            "Class '%s' must implement the following methods before it can be used: %s",
            user_type.__name__,
            ", ".join([f"'{f}'" for f in user_type_abstract_methods]),
        )
        return False
    return True
