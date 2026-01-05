from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Annotated, Any, Generic, Literal, Self, TypeVar, cast, get_args, get_origin, get_type_hints

from bench.serialization import PlainData, Serializable, is_plain_data

T = TypeVar("T", bound=int | float | str)


class Param(Generic[T]):
    """Class containing information about a parameter.

    Args:
        name: Name of the parameter.
        type: Type of the parameter.
        options: List of allowed values of the parameter.
        default: Default value of the parameter.
        description: Description of the parameter.
    """

    def __init__(
        self,
        name: str,
        type: type[T],  # ty: ignore[invalid-type-form]
        *,
        options: list[T] | None = None,
        default: T | None = None,
        description: str | None = None,
    ) -> None:
        self._name = name
        self._type = type
        self._options = options
        self._default = default
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> type[T]:  # ty: ignore[invalid-type-form]
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
    def type_metrics(cls) -> tuple[Metric[Any], ...]:
        """Metrics of the class of tasks.

        The metrics are automatically detected as the methods of the class which are
        decorated with a :py:class:`Metric` instance. *Do not overwrite this method!*
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
    """Implementation of the :py:class:`~bench.templates.Result` class for arbitrary plain data.

    Args:
        data: Arbitrary plain data.
    """

    def __init__(self, **data: PlainData) -> None:
        self._data: dict[str, PlainData] = {}
        for key, value in data.items():
            self[key] = value

    def __getitem__(self, key: str) -> PlainData:
        return self._data[key]

    def __setitem__(self, key: str, value: PlainData) -> None:
        if not is_plain_data(value):
            msg = f"Failed to set property '{key}' of `PlainResult`, value is not plain data"
            raise ValueError(msg)
        self._data[key] = value

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
        return self._function.__name__  # ty: ignore[possibly-missing-attribute]

    def _check_is_bound(self) -> None:
        if not hasattr(self, "_function"):
            msg = "Not bound yet"  # FIXME: better error message
            raise RuntimeError(msg)

    @classmethod
    @abstractmethod
    def encode_value(cls, value: MV) -> PlainData: ...
