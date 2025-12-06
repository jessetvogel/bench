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


def to_json(object: Serializable | None) -> str:
    """Serialize object into JSON."""
    if object is None:
        return "null"
    return json.dumps(object.encode())


def from_json(cls: type[S], data: str) -> S:
    """Deserialize JSON into object."""
    return cls.decode(json.loads(data))


# TODO: Create class `SerializableData` that implements a default `encode` and `decode` class
