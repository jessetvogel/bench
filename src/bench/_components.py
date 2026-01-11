import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from bench._process import Process
from bench.templates import Method, Result, Task, Token


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


@dataclass
class ExecutionProcess:
    process: Process
    task: Task
    method: Method
    num_runs: int
    created_at: datetime

    @property
    def id(self) -> str:
        return str(self.created_at)


def to_hash(object: Task | Method) -> str:
    if not hasattr(object, "_hash"):
        m = hashlib.sha256()
        m.update(object.type_label().encode())
        m.update(json.dumps(object.encode(), sort_keys=True, ensure_ascii=True).encode())
        setattr(object, "_hash", m.hexdigest()[:8])
    return getattr(object, "_hash")
