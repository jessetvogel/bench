import inspect
from collections.abc import Callable, Iterable
from typing import get_type_hints

from bench._logging import get_logger
from bench.templates import Method, Result, Task, Token

_LOGGER = get_logger("bench")


class Bench:
    """Benchmark specification class.

    This class contains information about the types of tasks, methods and results of a benchmark,
    as well as how to execute those tasks with those methods.

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
        """Add user-defined task types to the benchmark.

        Args:
            types: Task types to add.
        """
        for task_type in types:
            _check_user_type(Task, task_type)
        self._task_types.extend(types)

    def add_method_types(self, *types: type[Method]) -> None:
        """Add user-defined method types to the benchmark.

        Args:
            types: Method types to add.
        """
        for method_type in types:
            _check_user_type(Method, method_type)
        self._method_types.extend(types)

    def add_result_types(self, *types: type[Result]) -> None:
        """Add user-defined result types to the benchmark.

        Args:
            types: Result types to add.
        """
        for result_type in types:
            _check_user_type(Result, result_type)
        self._result_types.extend(types)

    def set_run(self, handler: Callable[[Task, Method], Result | Token]) -> None:
        """Set handler for executing tasks with a method.

        Args:
            handler: Function that executes a task with a method. The function should return
                a :py:class:`Result` instance if the task can be completed at once.
                Otherwise, a :py:class:`Token` instance is returned, which can be used
                to obtain the result at a later time using :py:meth:`poll`.
        """
        # TODO: validate handler
        self._handler_run = handler

    def run(self, task: Task, method: Method) -> Result | Token:
        """Execute the task with the method using the user-defined run handler set by :py:meth:`set_run`.

        Args:
            task: Task to perform.
            method: Method to perform the task with.

        Returns:
            A :py:class:`Result` instance if the task is completed at once, or a :py:class:`Token`
            instance to obtain the result at a later time using :py:meth:`poll`.
        """
        if self._handler_run is None:
            msg = "No run handler was registered. Use the `set_run` method to register a handler."
            raise RuntimeError(msg)
        return self._handler_run(task, method)

    def set_poll(self, handler: Callable[[Token], Result | None]) -> None:
        """Set handler for polling a result.

        Args:
            handler: Function that checks if the execution of the task is completed.
                This function should return a :py:class:`Result` instance if the task
                is completed, and :py:const:`None` otherwise.
        """
        # TODO: validate handler
        self._handler_poll = handler

    def poll(self, token: Token) -> Result | None:
        """Poll for a result using the poll handler set by :py:meth:`on_poll`.

        Args:
            token: Token instance returned from :py:meth:`run`.

        Returns:
            A :py:class:`Result` instance if the task is completed, otherwise :py:const:`None`.
        """
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
        """Iterable over all user-defined task types."""
        return iter(self._task_types)

    @property
    def method_types(self) -> Iterable[type[Method]]:
        """Iterable over all user-defined method types."""
        return iter(self._method_types)

    @property
    def result_types(self) -> Iterable[type[Result]]:
        """Iterable over all user-defined result types."""
        return iter(self._result_types)

    def get_task_type(self, name: str) -> type[Task]:
        """Get user-defined task type by name.

        Args:
            name: Name of task type.
        """
        for task_type in self._task_types:
            if task_type.type_label() == name:
                return task_type
        msg = f"Unknown task type '{name}'"
        raise ValueError(msg)

    def get_method_type(self, name: str) -> type[Method]:
        """Get user-defined method type by name.

        Args:
            name: Name of method type.
        """
        for method_type in self._method_types:
            if method_type.type_label() == name:
                return method_type
        msg = f"Unknown method type '{name}'"
        raise ValueError(msg)

    def get_result_type(self, name: str) -> type[Result]:
        """Get user-defined result type by name.

        Args:
            name: Name of result type.
        """
        for result_type in self._result_types:
            if result_type.type_label() == name:
                return result_type
        msg = f"Unknown result type '{name}'"
        raise ValueError(msg)


def _check_user_type(cls: type[Task | Method | Result], user_type: type) -> None:
    """Check if `user_type` is a valid task, method or result type."""
    # Check if derives from `cls`
    if not issubclass(user_type, cls):
        msg = (
            f"Class `{user_type.__name__}` must derive from `{cls.__module__}.{cls.__name__}` "
            f"to be used as {cls.__name__.lower()} type"
        )
        raise ValueError(msg)
    # Check if abstract methods are implemented
    user_type_abstract_methods = user_type.__abstractmethods__  # type: ignore[attr-defined]
    if user_type_abstract_methods:
        tmp = ", ".join([f"'{f}'" for f in user_type_abstract_methods])
        msg = f"Class `{user_type.__name__}` must implement the following methods before it can be used: {tmp}"
        raise ValueError(msg)
    # Check if `type_params` is compatible with `type_constructor`
    if issubclass(user_type, (Task, Method)):
        type_params = user_type.type_params()
        constructor = user_type.type_constructor()
        signature = inspect.signature(constructor)
        cons_params = [param for param in signature.parameters.values() if param.name != "self"]
        cons_type_hints = get_type_hints(constructor)
        has_cons_param_var_keyword = any(cons_param.kind == cons_param.VAR_KEYWORD for cons_param in cons_params)
        for cons_param in cons_params:
            if cons_param.kind == cons_param.VAR_KEYWORD:
                continue
            # Variable-length positional parameters are not allowed
            if cons_param.kind == cons_param.VAR_POSITIONAL:
                msg = (
                    f"Class `{user_type.__name__}` has variable-length positional parameter '{cons_param.name}' "
                    f"in constructor `{constructor.__qualname__}`, which is not allowed"
                )
                raise ValueError(msg)
            # Constructor parameter should appear in `type_params`
            type_param = next((type_param for type_param in type_params if type_param.name == cons_param.name), None)
            if type_param is None:
                msg = (
                    f"Missing parameter '{cons_param.name}' in `{user_type.__name__}.type_params()`, "
                    f"as expected by constructor `{constructor.__qualname__}`"
                )
                raise ValueError(msg)
            # Type hint for constructor parameter should match type of `type_param`
            if (
                type_hint := cons_type_hints.get(cons_param.name, None)
            ) is not None and type_hint is not type_param.type:
                _LOGGER.warning(
                    "Parameter '%s' as provided by `%s.type_params()` has type `%s`, "
                    "while type hint in constructor `%s` is `%s`",
                    cons_param.name,
                    user_type.__name__,
                    type_param.type.__name__,
                    constructor.__qualname__,
                    type_hint.__name__,
                )
        # Type parameters should appear in `cons_params` (if no variable-length keyword parameter)
        for type_param in type_params:
            if not has_cons_param_var_keyword and not any(
                cons_param.name == type_param.name for cons_param in cons_params
            ):
                msg = (
                    f"Parameter '{type_param.name}' in `{user_type.__name__}.type_params()` "
                    f"does not match any parameter of constructor `{constructor.__qualname__}`"
                )
                raise ValueError(msg)
