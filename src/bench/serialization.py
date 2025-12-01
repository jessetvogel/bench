import hashlib
import json
from typing import Protocol, Self, TypeAlias, TypeVar

# Data type that can be serialized easily
Data: TypeAlias = str | int | float | bool | None | list["Data"] | dict[str, "Data"]


class Serializable(Protocol):
    """Protocol for serializable objects.

    Serializable classes should implement an :py:meth:`encode` and :py:meth:`decode`
    method.
    """

    def encode(self) -> Data: ...

    @classmethod
    def decode(cls, data: Data) -> Self: ...


S = TypeVar("S", bound=Serializable)


def to_json(object: Serializable) -> str:
    return json.dumps(object.encode())


def from_json(cls: type[S], data: str) -> S:
    return cls.decode(json.loads(data))


def serializable_id(object: Serializable) -> str:
    if not hasattr(object, "_id"):
        setattr(object, "_id", hashlib.sha256(json.dumps(object.encode(), sort_keys=True, ensure_ascii=True).encode()))
    return getattr(object, "_id")


# TODO: Create class `SerializableData` that implements a default `encode` and `decode` class
