from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Collection
from typing import Any, Generic, Literal, Self, TypeVar, cast

from bench.serialization import PlainData, Serializable

T = TypeVar("T", bound=int | float | str)


class Param(Generic[T]):
    """Class containing information about a parameter.

    Args:
        name: Name of the parameter.
        type: Type of the parameter.
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
        default: T | None = None,
        description: str | None = None,
        min: int | float | None = None,
        max: int | float | None = None,
    ) -> None:
        self._name = name
        self._type = type
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


def _params_default(cls) -> list[Param]:
    """Default implementation of `.params()` of `Task` and `Method` using type hints."""
    params: list[Param] = []
    signature = inspect.signature(cls.__init__)
    for name, param in signature.parameters.items():
        if name == "self":
            continue
        if param.kind is param.VAR_POSITIONAL or param.kind is param.VAR_KEYWORD:
            continue

        annotation = param.annotation
        if isinstance(annotation, type):
            annotation = annotation.__name__

        type_ = {
            "bool": bool,
            "int": int,
            "float": float,
            "str": str,
        }.get(annotation, str)

        default = param.default if param.default != param.empty else None
        params.append(Param(name=name, type=type_, default=default))
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
    def params(cls) -> list[Param]:
        """Parameters to instantiate this task."""
        return _params_default(cls)

    def label(self) -> str:
        """Display name of the task."""
        return self.type_label()

    def description(self) -> str:
        """Description of the task."""
        return f"Task instance of type {self.type_label()}"

    @classmethod
    @abstractmethod
    def metrics(self) -> Collection[Metric]:
        """Parse result into metrics."""

    @abstractmethod
    def evaluate(self, result: Result) -> dict[str, Any]:
        """Evaluate the result into metrics."""

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
    def params(cls) -> list[Param]:
        """Parameters to instantiate this method."""
        return _params_default(cls)

    def label(self) -> str:
        """Display name of the method."""
        return self.type_label()

    @abstractmethod
    def encode(self) -> PlainData: ...

    @classmethod
    @abstractmethod
    def decode(cls, data: PlainData) -> Self: ...


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


class Result(Serializable):
    """Result class."""

    def __init__(self, **data: PlainData) -> None:
        self._data = dict(data)

    def __getitem__(self, index: str) -> PlainData:
        return self._data[index]

    def __setitem__(self, index: str, value: PlainData) -> None:
        self._data[index] = value

    @classmethod
    def type_label(cls) -> str:
        return cls.__name__

    def encode(self) -> PlainData:
        return dict(self._data)

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        assert isinstance(data, dict)
        return cls(**data)


class BenchError(Exception, Serializable):
    """Exception raised for BENCH errors.

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


class Run:
    def __init__(self, id: str, task_id: str, method_id: str, result: None | Token | Result | BenchError) -> None:
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
    def result(self) -> None | Token | Result | BenchError:
        return self._result

    @result.setter
    def result(self, result: None | Token | Result | BenchError) -> None:
        self._result = result

    @property
    def status(self) -> Literal["pending", "running", "done", "failed"]:
        if self.result is None:
            return "pending"
        if isinstance(self.result, Token):
            return "running"
        if isinstance(self.result, Result):
            return "done"
        if isinstance(self.result, BenchError):
            return "failed"

        msg = f"Expected result of run to be `None`, `Token`, `Result` or `BenchError`, got `{type(self.result)}`"
        raise ValueError(msg)


class Metric:
    pass
