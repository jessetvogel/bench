from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Literal, Mapping, Protocol, Self, TypeAlias

from bench.serialization import PlainData, Serializable


class Task(ABC, Serializable):
    """Abstract base class for a task."""

    @classmethod
    def name(cls) -> str:
        return cls.__name__

    @abstractmethod
    def metrics(self, result: Result) -> Metrics: ...

    @abstractmethod
    def encode(self) -> PlainData: ...

    @classmethod
    @abstractmethod
    def decode(cls, data: PlainData) -> Self: ...


class Method(Serializable, Protocol):
    """Abstract base class for a method."""

    @classmethod
    @abstractmethod
    def name(cls) -> str: ...

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
    """Protocol for a result."""

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


RunStatus: TypeAlias = Literal["running", "done", "failed"]


class Run:
    def __init__(self, id: int, task_id: str, method_id: str, result: Token | Result | BenchError) -> None:
        self._id = id
        self._task_id = task_id
        self._method_id = method_id
        self._result = result

    @property
    def id(self) -> int:
        return self._id

    @property
    def task_id(self) -> str:
        return self._task_id

    @property
    def method_id(self) -> str:
        return self._method_id

    @property
    def result(self) -> Token | Result | BenchError:
        return self._result

    @result.setter
    def result(self, result: Token | Result | BenchError) -> None:
        self._result = result

    @property
    def status(self) -> RunStatus:
        if isinstance(self.result, Token):
            return "running"
        if isinstance(self.result, Result):
            return "done"
        if isinstance(self.result, BenchError):
            return "failed"

        msg = f"Expected result of run to be `Token`, `Result` or `BenchError`, got `{type(self.result)}`"
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
