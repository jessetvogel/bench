from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any, Generic, Iterator, Literal, Mapping, Protocol, Self, TypeVar

from bench.metrics import Metric
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
        type = {
            "bool": bool,
            "int": int,
            "float": float,
            "str": str,
        }.get(param.annotation, str)
        default = param.default if param.default != param.empty else None
        params.append(Param(name=name, type=type, default=default))
    return params


class Task(ABC, Serializable):
    """Abstract base class for a task."""

    @classmethod
    def type_name(cls) -> str:
        """Name of the class of tasks."""
        return cls.__name__

    @classmethod
    def params(cls) -> list[Param]:
        """Parameters to instantiate this task."""
        return _params_default(cls)

    def label(self) -> str:
        """Display name of the task."""
        return self.type_name()

    @classmethod
    @abstractmethod
    def metrics(self) -> Metrics:
        """Parse result into metrics."""

    @abstractmethod
    def evaluate(self, result: Result) -> dict[str, Any]:
        """Evaluate the result into metrics."""

    @abstractmethod
    def encode(self) -> PlainData: ...

    @classmethod
    @abstractmethod
    def decode(cls, data: PlainData) -> Self: ...


class Method(Serializable, Protocol):
    """Abstract base class for a method."""

    @classmethod
    def type_name(cls) -> str:
        """Name of the class of methods."""
        return cls.__name__

    @classmethod
    def params(cls) -> list[Param]:
        """Parameters to instantiate this method."""
        return _params_default(cls)

    def label(self) -> str:
        """Display name of the method."""
        return self.type_name()

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

    def __init__(self, data: Mapping[str, PlainData]) -> None:
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
        return cls(data)


class Metrics:
    """Metrics computed from a result for a task."""

    def __init__(self, **metrics: Metric) -> None:
        self._data = metrics

    def __getitem__(self, index: str) -> Metric:
        return self._data[index]

    def __setitem__(self, index: str, value: Metric) -> None:
        self._data[index] = value

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def items(self) -> Iterable[tuple[str, Metric]]:
        return self._data.items()


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
        assert isinstance(data, str)
        return cls(data)


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


class Bench(ABC):
    """Specification of the benchmark."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the benchmark."""

    @abstractmethod
    def task_types(self) -> Iterable[type[Task]]:
        """Iterable of supported task types."""
        raise NotImplementedError()

    @abstractmethod
    def method_types(self) -> Iterable[type[Method]]:
        """Iterable of supported method types."""
        raise NotImplementedError()

    @abstractmethod
    def run(self, task: Task, method: Method) -> Result | Token:
        """Run the given task with the given method.

        Args:
            task: Task to perform.
            method: Method to apply.

        Returns:
            A :py:class:`Result` instance if the task can be completed at once.
            Otherwise, a :py:class:`Token` instance is returned which can be used
            to obtain the result at a later time.
        """
        raise NotImplementedError()

    @abstractmethod
    def poll(self, token: Token) -> Result | None:
        """Poll the result of a task using a token.

        Args:
            token: Token returned by the :py:meth:`run` method.

        Returns:
            A :py:class:`Result` instance if the task is completed, otherwise :py:const:`None`.
        """
        raise NotImplementedError()
