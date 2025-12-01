from abc import ABC, abstractmethod
from typing import Generic, Literal, Protocol, Self, TypeAlias, TypeVar

from bench.serialization import Data, Serializable


class Task(Serializable, Protocol):
    """Protocol for a task."""

    @property
    def name(self) -> str: ...


class Method(Serializable, Protocol):
    """Protocol for a method."""

    @property
    def name(self) -> str: ...


class Token(Serializable):
    """Token class, can be used to poll for a result."""

    def __init__(self, data: Data) -> None:
        self._data = data

    @property
    def data(self) -> Data:
        return self._data

    def encode(self) -> Data:
        return self.data

    @classmethod
    def decode(cls, data: Data) -> Self:
        return cls(data)


class Result(Serializable, Protocol):
    """Protocol for a result."""


class Metrics:
    """Metrics computed from a result for a task."""

    def __init__(self, data: dict[str, Data]) -> None:
        self._data = data

    @property
    def data(self) -> dict[str, Data]:
        return self._data

    def serialize(self) -> Data:
        return self.data

    @classmethod
    def deserialize(cls, data: Data) -> Self:
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

    def encode(self) -> Data:
        return self.message

    @classmethod
    def decode(cls, data: Data) -> Self:
        assert isinstance(data, str)
        return cls(data)


TASK = TypeVar("TASK", bound=Task)
METHOD = TypeVar("METHOD", bound=Method)
RESULT = TypeVar("RESULT", bound=Result)

RunStatus: TypeAlias = Literal["running", "done", "failed"]


class Run(Generic[RESULT]):
    def __init__(self, id: int, task_id: str, method_id: str, result: Token | RESULT | BenchError) -> None:
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
    def result(self) -> Token | RESULT | BenchError:
        return self._result

    @result.setter
    def result(self, result: Token | RESULT | BenchError) -> None:
        self._result = result

    @property
    def status(self) -> RunStatus:
        if isinstance(self.result, Token):
            return "running"
        if isinstance(self.result, BenchError):
            return "failed"

        return "done"

        # msg = f"Expected result of run to be `Token`, `Result` or `BenchError`, got `{type(self.result)}`"
        # raise ValueError(msg)


class Bench(ABC, Generic[TASK, METHOD, RESULT]):
    def __init__(self, task_type: type[TASK], method_type: type[METHOD], result_type: type[RESULT]) -> None:
        self._task_type = task_type
        self._method_type = method_type
        self._result_type = result_type

    @property
    def task_type(self) -> type[TASK]:
        return self._task_type

    @property
    def method_type(self) -> type[METHOD]:
        return self._method_type

    @property
    def result_type(self) -> type[RESULT]:
        return self._result_type

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, task: TASK, method: METHOD) -> Token | RESULT:
        """Run the given task with the given method."""
        raise NotImplementedError("Method `run` not implemented")

    @abstractmethod
    def poll(self, token: Token) -> RESULT | None:
        """Poll for a result using a token."""
        # TODO: Should this poll function also take a task or method?
        raise NotImplementedError("Method `poll` not implemented")

    @abstractmethod
    def metrics(self, task: TASK, result: RESULT) -> Metrics:
        """Compute metrics from a result for a given task."""
        raise NotImplementedError("Method `metrics` not implemented")
