from __future__ import annotations

import inspect
import json
from datetime import timedelta
from types import UnionType
from typing import Any, Literal, Protocol, Self, TypeAlias, TypeVar, cast, get_args, get_origin, get_type_hints

from bench._logging import get_logger

PlainData: TypeAlias = str | int | float | bool | None | list["PlainData"] | dict[str, "PlainData"]
"""Type alias for plain data, that is, JSON-like data such as primitives, lists and string-keyed dictionaries."""

T = TypeVar("T")

_LOGGER = get_logger("bench")


def default_encode(cls: type[T], object: T) -> PlainData:
    """Encode `object` into plain data as an instance of `cls`.

    This method is implemented in such a way that :py:meth:`default_decode`
    will reconstruct the original object.

    Args:
        cls: Type as which to encode the object.
        object: Object to encode.

    Returns:
        Plain data representing the object as an instance of `cls`.
    """
    # Primitive types (`None`, `bool`, `int`, `float`, `str`) are always encoded as themselves
    # independent of the value of `cls`. This cannot lead to ambiguity.
    if object is None or isinstance(object, (int, float, str)):
        return object

    cls_origin: type = get_origin(cls) or cls
    cls_args: tuple[Any, ...] = get_args(cls) or tuple()

    # `list[A]`
    if cls_origin is list:
        assert isinstance(object, list), "object is not of type list"
        assert len(cls_args) == 1, "list requires precisely one argument"
        item_cls = cast(type, cls_args[0])
        return [default_encode(item_cls, x) for x in object]

    # `tuple[?]`
    # TODO: understand the tuple generic

    # `dict[K, V]`
    if cls_origin is dict:
        assert isinstance(object, dict), "object is not of type dict"
        assert len(cls_args) == 2, "dict requires precisely two arguments"
        key_cls, value_cls = cast(tuple[type, ...], cls_args)

        # `dict[str, V]`
        if key_cls is str:
            return {key: default_encode(value_cls, value) for key, value in object.items()}

        # `dict[K, V]`
        return [[default_encode(key_cls, key), default_encode(value_cls, value)] for key, value in object.items()]

    # `types.UnionType[...]`
    # TODO: If `object` matches multiple `cls_arg`, then an error must be raised for being ambigious
    if cls_origin is UnionType:
        for cls_arg in cls_args:
            cls_arg_origin = get_origin(cls_arg) or cls_arg
            if isinstance(object, cls_arg_origin):
                return [cls_arg_origin.__name__, default_encode(cls_arg, object)]
        msg = f"Object '{object}' does not match type '{cls}'"
        raise ValueError(msg)

    # `typing.Literal[...]`
    if cls_origin is Literal:
        assert object in cls_args
        return object  # type: ignore[return-value]

    # `timedelta`
    if cls_origin is timedelta:
        assert isinstance(object, timedelta)
        return {"sec": object.total_seconds()}

    # `cls` implementing `Serializable`
    if is_serializable(cls_origin):
        assert isinstance(object, cls_origin)
        return getattr(cls_origin, "encode")(object)

    msg = f"Could not encode object '{object}' as an instance of type '{cls.__name__}'"
    raise NotImplementedError(msg)


def default_decode(cls: type[T], data: PlainData) -> T:
    """Decode plain data `data` into an object as an instance of `cls`.

    Args:
        cls: Type as which to decode the object.
        data: Plain data to decode.

    Returns:
        Decoded object as an instance of `cls`.
    """
    # Primitive types (`None`, `bool`, `int`, `float`, `str`) are always encoded as themselves
    # independent of the value of `cls`. This cannot lead to ambiguity.
    if data is None or isinstance(data, (int, float, str)):
        return cast(T, data)

    cls_origin: type = get_origin(cls) or cls
    cls_args: tuple[Any, ...] = get_args(cls) or tuple()

    # `list[A]`
    if cls_origin is list:
        assert len(cls_args) == 1
        assert isinstance(data, list)
        item_cls = cls_args[0]
        return [default_decode(item_cls, x) for x in data]  # type: ignore[return-value]

    # `tuple[?]`
    # TODO: understand the tuple generic

    # `dict[K, V]`
    if cls_origin is dict:
        assert len(cls_args) == 2, "dict requires precisely two arguments"
        key_cls, value_cls = cls_args

        # `dict[str, V]`
        if key_cls is str:
            assert isinstance(data, dict)
            return {key: default_decode(value_cls, value) for key, value in data.items()}  # type: ignore[return-value]

        # `dict[K, V]`
        assert isinstance(data, list)
        return {  # type: ignore[return-value]
            default_decode(key_cls, key_data): default_decode(value_cls, value_data)
            for (key_data, value_data) in cast(list[list[PlainData]], data)
        }

    # `types.UnionType[...]`
    # TODO: If `name` matches multiple `cls_arg`, then an error must be raised for being ambigious
    if cls_origin is UnionType:
        assert isinstance(data, list)
        name, subdata = data
        for cls_arg in cls_args:
            if name == (get_origin(cls_arg) or cls_arg).__name__:
                return default_decode(cls_arg, subdata)
        msg = f"Expected type '{name}' to match '{cls}'"
        raise DecodingError(msg)

    # `typing.Literal[...]`
    if cls_origin is Literal:
        assert data in cls_args
        return data  # type: ignore[return-value]

    # `timedelta`
    if cls_origin is timedelta:
        assert isinstance(data, dict)
        return timedelta(seconds=cast(float, data["sec"]))  # type: ignore[return-value]

    # `cls` implementing `Serializable`
    if is_serializable(cls_origin):
        return getattr(cls_origin, "decode")(data)

    msg = f"Could not decode object as instance of type '{cls}'"
    raise NotImplementedError(msg)


def is_serializable(cls: type) -> bool:
    return hasattr(cls, "encode") and callable(cls.encode)


class Serializable(Protocol):
    """Protocol for serializable objects.

    Serializable classes should implement an :py:meth:`encode` and :py:meth:`decode`
    method. These methods can be used to encode objects into plain data, and decode
    plain data into objects.
    """

    def encode(self) -> PlainData:
        """Encode object into plain data dictionary."""

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        """Decode plain data dictionary into an object."""


class DefaultSerializable(Serializable):
    """Default implementation of serializability.

    This default implementation uses the signature of the :py:const:`__init__` method
    to determine which properties to encode for serialization, and how to reconstruct
    the object from it.
    """

    def encode(self) -> PlainData:
        # Inspect the signature of the `__init__` method of the class
        cls = self.__class__
        signature = inspect.signature(cls.__init__)
        type_hints = get_type_hints(cls.__init__)
        params = [param for param in signature.parameters.values() if param.name != "self"]
        # Encode and store the property corresponding to each parameter in a dictionary
        encoded: dict[str, PlainData] = {}
        for param in params:
            # Variable-length parameters are not allowed
            if param.kind == param.VAR_POSITIONAL or param.kind == param.VAR_KEYWORD:
                msg = f"Cannot encode variable-length parameter '{param.name}'"
                raise EncodingError(msg)
            # There should be a property with the same name as the parameter
            if not hasattr(self, param.name):
                msg = f"Missing attribute '{param.name}', as expected by `{cls.__name__}.__init__`"
                raise AttributeError(msg)
            # Get type hint for parameter
            if (value_cls := type_hints.get(param.name, None)) is None:
                msg = f"Missing type hint for parameter '{param.name}' in '{cls.__name__}'.__init__"
                raise EncodingError(msg)
            # Encode attribute value
            value = getattr(self, param.name)
            encoded[param.name] = default_encode(value_cls, value)
        return encoded

    @classmethod
    def decode(cls, data: PlainData) -> Self:
        assert isinstance(data, dict)
        # Inspect the signature of the `__init__` method of the class
        signature = inspect.signature(cls.__init__)
        type_hints = get_type_hints(cls.__init__)
        params = [param for param in signature.parameters.values() if param.name != "self"]
        # Encode and store the property corresponding to each parameter in a dictionary
        values: dict[str, Any] = {}
        for param in params:
            # Variable-length parameters are not allowed
            if param.kind == param.VAR_POSITIONAL or param.kind == param.VAR_KEYWORD:
                msg = f"Cannot decode variable-length parameter '{param.name}'"
                raise DecodingError(msg)
            # Data should contain parameter name as key (only if parameter has no default value)
            if param.name not in data:
                if param.default is not param.empty:
                    continue
                msg = f"Missing key '{param.name}', as expected by `{cls.__name__}.__init__`"
                raise ValueError(msg)
            # Get type hint for parameter
            if (value_cls := type_hints.get(param.name, None)) is None:
                msg = f"Missing type hint for parameter '{param.name}' in '{cls.__name__}'.__init__"
                raise EncodingError(msg)
            # Store decoded value
            values[param.name] = default_decode(value_cls, data[param.name])
        # Construct class instance from values
        return cls(**values)


class EncodingError(Exception):
    """Error class for encoding exceptions."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class DecodingError(Exception):
    """Error class for decoding exceptions."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


S = TypeVar("S", bound=Serializable)


def to_json(object: Serializable | None) -> str:
    """Serialize object into JSON."""
    if object is None:
        return "null"
    return json.dumps(object.encode())


def from_json(cls: type[S], data: str) -> S:
    """Deserialize JSON into object."""
    return cls.decode(json.loads(data))


def check_serializable(object: Serializable) -> None:
    """Check if `object` can be encoded and decoded properly.

    Raises:
        EncodingError: If an exception occurs during encoding of the object.
        DecodingError: If an exception occurs during decoding of the encoding of the object.
    """
    cls = object.__class__
    try:
        encoded = object.encode()
    except Exception as err:
        msg = f"Exception occurred during encoding '{cls.__name__}'"
        raise EncodingError(msg) from err
    try:
        cls.decode(encoded)
    except Exception as err:
        msg = f"Exception occurred during decoding '{cls.__name__}'"
        raise DecodingError(msg) from err
