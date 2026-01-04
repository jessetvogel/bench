from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Annotated, Any, Generic, Literal, Self, TypeVar, cast, get_args, get_origin, get_type_hints

from bench.serialization import PlainData, Serializable

T = TypeVar("T", bound=int | float | str)


class Param(Generic[T]):
    """Class containing information about a parameter.

    Args:
        name: Name of the parameter.
        type: Type of the parameter.
        options: List of allowed values of the parameter.
        default: Default value of the parameter.
        description: Description of the parameter.
        min: Minimum value of the parameter.
        max: Maximum value of the parameter.
    """

    def __init__(
        self,
        name: str,
        type: type[T],
        *,
        options: list[T] | None = None,
        default: T | None = None,
        description: str | None = None,
        min: int | float | None = None,
        max: int | float | None = None,
    ) -> None:
        self._name = name
        self._type = type
        self._options = options
        self._default = default
        self._description = description
        self._min = min
        self._max = max

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> type[T]:
        return self._type

    @property
    def options(self) -> list[T] | None:
        return self._options

    @property
    def default(self) -> T | None:
        return self._default

    @property
    def description(self) -> str | None:
        return self._description

    @property
    def min(self) -> int | float | None:
        return self._min

    @property
    def max(self) -> int | float | None:
        return self._max


def _params_default(constructor: Callable[..., Any]) -> list[Param]:
    """Default implementation of `.params()` of `Task` and `Method` using type hints."""
    params: list[Param] = []
    signature = inspect.signature(constructor)
    type_hints = get_type_hints(constructor)
    for name, param in signature.parameters.items():
        if name == "self":
            continue
        if param.kind is param.VAR_POSITIONAL or param.kind is param.VAR_KEYWORD:
            continue
        # Get type hint
        type_hint = type_hints.get(param.name, None)
        # Set `options` if type hint is `Literal`
        options = list(get_args(type_hint)) if get_origin(type_hint) is Literal else None
        # Type of `Param` is `int`, `float` or `str`, with `str` being the default
        if type_hint not in (int, float, str):
            type_hint = str
        # Determine default value
        default = param.default if param.default != param.empty else None
        # If annotation is `typing.Annotated[T, x]`, then interpret `x` as parameter description
        description: str | None = None
        if get_origin(param.annotation) is Annotated:
            annotation_args = get_args(param.annotation)
            if len(annotation_args) == 2:
                description = str(annotation_args[1])
        # Create `Param` from obtained information
        params.append(Param(name=name, type=type_hint, options=options, default=default, description=description))
    return params


class Task(ABC, Serializable):
    """Abstract base class for a task."""

    @classmethod
    def type_label(cls) -> str:
        """Display name of the class of tasks."""
        return cls.__name__

    @classmethod
    def type_description(cls) -> str:
        """Description of the class of tasks."""
        return ""

    @classmethod
    def type_constructor(cls) -> Callable[..., Self]:
        """Constructor for the class of tasks."""
        return cls

    @classmethod
    def type_params(cls) -> list[Param]:
        """Parameters to instantiate this task.

        The result of this function should be compatible with :py:meth:`type_constructor`.
        """
        if (constructor := cls.type_constructor()) is cls:
            return _params_default(cls.__init__)
        return _params_default(constructor)

    @classmethod
    def type_metrics(cls) -> tuple[Metric[Any]]:
        """Metrics of the class of tasks.

        The metrics are automatically detected as the methods of the class which are
        decorated with a `Metric` instance. Do not overwrite this method.
        """
        return tuple(
            metric
            for attr in cls.__dict__.values()
            if callable(attr) and (metric := getattr(attr, "_metric", None)) is not None
        )

    def label(self) -> str:
        """Display name of the task."""
        return self.type_label()

    def description(self) -> str:
        """Description of the task."""
        return f"Task instance of type {self.type_label()}"

    @abstractmethod
    def encode(self) -> PlainData: ...

    @classmethod
    @abstractmethod
    def decode(cls, data: PlainData) -> Self: ...


class Method(ABC, Serializable):
    """Abstract base class for a method."""

    @classmethod
    def type_label(cls) -> str:
        """Display name of the class of methods."""
        return cls.__name__

    @classmethod
    def type_description(cls) -> str:
        """Description of the class of methods."""
        return ""

    @classmethod
    def type_constructor(cls) -> Callable[..., Self]:
        """Constructor for the class of methods."""
        return cls

    @classmethod
    def type_params(cls) -> list[Param]:
        """Parameters to instantiate this method.

        The result of this function should be compatible with :py:meth:`type_constructor`.
        """
        if (constructor := cls.type_constructor()) is cls:
            return _params_default(cls.__init__)
        return _params_default(constructor)

    def label(self) -> str:
        """Display name of the method."""
        return self.type_label()

    def description(self) -> str:
        """Description of the task."""
        return f"Method instance of type {self.type_label()}"

    @abstractmethod
    def encode(self) -> PlainData: ...

    @classmethod
    @abstractmethod
    def decode(cls, data: PlainData) -> Self: ...


class Result(ABC, Serializable):
    """Abstract base class for a result."""

    @classmethod
    def type_label(cls) -> str:
        return cls.__name__

    @abstractmethod
    def encode(self) -> PlainData: ...

    @classmethod
    @abstractmethod
    def decode(cls, data: PlainData) -> Self: ...


class PlainResult(Result):
    """Result class containing arbitrary plain data."""

    def __init__(self, **data: PlainData) -> None:
        self._data = dict(data)

    def __getitem__(self, index: str) -> PlainData:
        return self._data[index]

    def __setitem__(self, index: str, value: PlainData) -> None:
        self._data[index] = value

    def encode(self) -> PlainData:
        return dict(self._data)

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        assert isinstance(data, dict)
        return cls(**data)


class Token(Serializable):
    """Token class, can be used to poll for a result."""

    def __init__(self, data: PlainData) -> None:
        self._data = data

    @property
    def data(self) -> PlainData:
        return self._data

    def encode(self) -> PlainData:
        return self.data

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        return cls(data)


class BenchError(Exception, Serializable):
    """Exception raised for bench errors.

    Args:
        message: Error message.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self._message = message

    @property
    def message(self) -> str:
        return self._message

    def encode(self) -> PlainData:
        return self.message

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        return cls(cast(str, data))


MT = TypeVar("MT", bound=Task)
MR = TypeVar("MR", bound=Result)
MV = TypeVar("MV")


class Metric(Generic[MV]):
    """Base class for a metric."""

    def __call__(self, f: Callable[[MT, MR], MV]) -> Callable[[MT, MR], MV]:
        if hasattr(self, "_function"):
            msg = "Can only use once"  # FIXME: better error message
            raise RuntimeError(msg)
        self._function = f  # TODO: better variable name
        setattr(f, "_metric", self)
        return f

    def evaluate(self, task: Task, result: Result) -> MV:
        self._check_is_bound()
        return self._function(cast(Any, task), cast(Any, result))

    @property
    def name(self) -> str:
        self._check_is_bound()
        return self._function.__name__

    def _check_is_bound(self) -> None:
        if not hasattr(self, "_function"):
            msg = "Not bound yet"  # FIXME: better error message
            raise RuntimeError(msg)


class Run:
    def __init__(self, id: str, task_id: str, method_id: str, result: Result | Token) -> None:
        self._id = id
        self._task_id = task_id
        self._method_id = method_id
        self._result = result

    @property
    def id(self) -> str:
        return self._id

    @property
    def task_id(self) -> str:
        return self._task_id

    @property
    def method_id(self) -> str:
        return self._method_id

    @property
    def result(self) -> Result | Token:
        return self._result

    @result.setter
    def result(self, result: Result | Token) -> None:
        self._result = result

    @property
    def status(self) -> Literal["pending", "done", "failed"]:
        if isinstance(self.result, Token):
            return "pending"
        if isinstance(self.result, Result):
            return "done"

        msg = f"Expected result of run to be of type `Result` or `Token`, but got `{type(self.result)}`"
        raise ValueError(msg)
