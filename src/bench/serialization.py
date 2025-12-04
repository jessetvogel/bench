import hashlib
import json
from typing import Protocol, Self, TypeAlias, TypeVar

PlainData: TypeAlias = str | int | float | bool | None | list["PlainData"] | dict[str, "PlainData"]


class Serializable(Protocol):
    """Protocol for serializable objects.

    Serializable classes should implement an :py:meth:`encode` and :py:meth:`decode`
    method. These methods can be used to encode objects into plain data, and decode
    plain data into objects.
    """

    def encode(self) -> PlainData:
        """Encode object into plain data."""

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        """Decode plain data into an object."""


S = TypeVar("S", bound=Serializable)


def to_json(object: Serializable) -> str:
    """Serialize object into JSON."""
    return json.dumps(object.encode())


def from_json(cls: type[S], data: str) -> S:
    """Deserialize JSON into object."""
    return cls.decode(json.loads(data))


def serializable_id(object: Serializable) -> str:
    if not hasattr(object, "_id"):
        setattr(
            object,
            "_id",
            hashlib.sha256(json.dumps(object.encode(), sort_keys=True, ensure_ascii=True).encode()).hexdigest()[:8],
        )
    return getattr(object, "_id")


# TODO: Create class `SerializableData` that implements a default `encode` and `decode` class
