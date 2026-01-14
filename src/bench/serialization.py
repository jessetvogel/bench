from __future__ import annotations

import copy
import inspect
import json
from abc import update_abstractmethods
from datetime import timedelta
from types import UnionType
from typing import (
    Any,
    Literal,
    Protocol,
    Self,
    TypeAlias,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

PlainData: TypeAlias = str | int | float | bool | None | list["PlainData"] | dict[str, "PlainData"]
"""Type alias for plain data, that is, JSON-like data such as primitives, lists and string-keyed dictionaries."""

T = TypeVar("T")


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
    cls_args: tuple[Any, ...] | None = get_args(cls) or None

    # `list[A]`
    if cls_origin is list:
        assert isinstance(object, list), "object is not of type list"
        assert cls_args is not None and len(cls_args) == 1, "list requires precisely one argument"
        item_cls = cast(type, cls_args[0])
        return [default_encode(item_cls, x) for x in object]

    # `tuple[?]`
    # TODO: understand the tuple generic

    # `dict[K, V]`
    if cls_origin is dict:
        assert isinstance(object, dict), "object is not of type dict"
        assert cls_args is not None and len(cls_args) == 2, "dict requires precisely two arguments"
        key_cls, value_cls = cast(tuple[type, ...], cls_args)

        # `dict[str, V]`
        if key_cls is str:
            encoded: dict[str, PlainData] = {}
            for key, value in object.items():
                if not isinstance(key, str):
                    msg = f"Expected keys of type `str`, but got `{type(key).__name__}`"
                    raise EncodingError(msg)
                encoded[key] = default_encode(value_cls, value)
            return encoded

        # `dict[K, V]`
        return [[default_encode(key_cls, key), default_encode(value_cls, value)] for key, value in object.items()]

    # `types.UnionType[...]`
    # TODO: If `object` matches multiple `cls_arg`, then an error must be raised for being ambigious
    if cls_origin is UnionType:
        assert cls_args is not None
        for cls_arg in cls_args:
            cls_arg_origin = get_origin(cls_arg) or cls_arg
            if isinstance(object, cls_arg_origin):
                return [cls_arg_origin.__name__, default_encode(cls_arg, object)]
        msg = f"Object '{object}' does not match type '{cls}'"
        raise ValueError(msg)

    # `typing.Literal[...]`
    if cls_origin is Literal:
        msg = "Could not be literal, because then it should have been an int, float or str"
        raise EncodingError(msg)

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
    cls_args: tuple[Any, ...] | None = get_args(cls) or None

    # `list[A]`
    if cls_origin is list:
        assert cls_args is not None and len(cls_args) == 1
        assert isinstance(data, list)
        item_cls = cls_args[0]
        return [default_decode(item_cls, x) for x in data]  # type: ignore[return-value]

    # `tuple[?]`
    # TODO: understand the tuple generic

    # `dict[K, V]`
    if cls_origin is dict:
        assert cls_args is not None and len(cls_args) == 2, "dict requires precisely two arguments"
        key_cls, value_cls = cls_args[0], cls_args[1]

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
        assert cls_args is not None
        assert isinstance(data, list)
        name, subdata = data
        for cls_arg in cls_args:
            assert isinstance(cls_arg, type)
            if name == (get_origin(cls_arg) or cls_arg).__name__:
                return default_decode(cls_arg, subdata)
        msg = f"Expected type '{name}' to match '{cls}'"
        raise DecodingError(msg)

    # `typing.Literal[...]`
    if cls_origin is Literal:
        msg = f"Expected any of {cls_args}, but got '{data}'"
        raise DecodingError(msg)

    # `timedelta`
    if cls_origin is timedelta:
        assert isinstance(data, dict)
        return timedelta(seconds=cast(float, data["sec"]))  # type: ignore[return-value]

    # `cls` implementing `Serializable`
    if is_serializable(cls_origin):
        return getattr(cls_origin, "decode")(data)

    msg = f"Could not decode object as instance of type '{cls}'"
    raise NotImplementedError(msg)


def default_serialization(cls: type[T]) -> type[T]:
    """Decorator for adding default implementation of the :py:class:`Serializable` protocol.

    This decorator adds an :py:meth:`encode` and :py:meth:`decode` to the given class.
    An instance of the class will be encoded as a :py:const:`dict` containing the properties of the instance
    that are in the :py:const:`__init__` method of the class. Decoding is done by constructing a new instance
    of the class from these properties.

    To use this decorator, the class is required to have, for each parameter of the :py:const:`__init__` method,
    a property with the same name as the parameter. An instance of the class must be fully reproducible from these
    properties. The parameters must be equipped with a type hint, with the corresponding type being serializable
    as well.

    Args:
        cls: Class to implement default :py:meth:`encode` and :py:meth:`decode` methods for.
    """
    # Analyze `cls.__init__`
    param_types, param_defaults = _analyze_init(cls)

    def encode(self) -> PlainData:
        # Encode and store the property corresponding to each parameter in a dictionary
        encoded: dict[str, PlainData] = {}
        for name, param_type in param_types.items():
            # There should be a property with the same name as the parameter
            if not hasattr(self, name):
                msg = f"Missing attribute '{name}', as expected by `{cls.__name__}.__init__`"
                raise EncodingError(msg)
            # Encode attribute value
            value = getattr(self, name)
            try:
                encoded[name] = default_encode(param_type, value)
            except Exception as err:
                msg = f"Failed to encode property '{name}' of object of type `{self.__class__.__name__}`"
                raise EncodingError(msg) from err
        return encoded

    def decode(cls: type[T], data: PlainData) -> T:
        # Check type of `data`
        if not isinstance(data, dict):
            msg = (
                f"Failed to decode into object of type `{cls.__name__}`, "
                "expected `dict` but got `{type(data).__name__}`"
            )
            raise DecodingError(msg)
        # Decode each property and store them in a dictionary
        values: dict[str, Any] = {}
        for name, param_type in param_types.items():
            # Data should contain parameter name as key (if parameter has no default value)
            if name not in data:
                if name in param_defaults:
                    continue
                msg = f"Missing key '{name}', as expected by `{cls.__name__}.__init__`"
                raise DecodingError(msg)
            # Store decoded value
            try:
                values[name] = default_decode(param_type, data[name])
            except Exception as err:
                msg = f"Failed to decode property '{name}' for object of type `{cls.__name__}`"
                raise DecodingError(msg) from err
        # Construct class instance from values
        try:
            return cls(**values)
        except Exception as err:
            msg = f"Failed to instantiate object of type `{cls.__name__}` from decoded values"
            raise DecodingError(msg) from err

    # Set encode and decode methods (and update the __abstractmethods__ attribute)
    setattr(cls, "encode", encode)
    setattr(cls, "decode", classmethod(decode))
    update_abstractmethods(cls)

    return cls


def _analyze_init(cls: type[T]) -> tuple[dict[str, type], set[str]]:
    """Analyze the `__init__` method of `cls` and return the parameter types and parameters with default values."""
    # Inspect the signature of the `__init__` method of the class
    signature = inspect.signature(cls.__init__)
    type_hints = get_type_hints(cls.__init__)
    params = [param for param in signature.parameters.values() if param.name != "self"]
    param_types: dict[str, type] = {}
    param_defaults: set[str] = set()
    for param in params:
        # Variable-length parameters are not allowed
        if param.kind == param.VAR_POSITIONAL or param.kind == param.VAR_KEYWORD:
            msg = (
                f"Failed to implement default serialization for class `{cls.__name__}`: "
                f"variable-length parameter '{param.name}' not allowed in `{cls.__name__}'.__init__`"
            )
            raise ValueError(msg)
        # Store parameter type hints
        if (param_type := type_hints.get(param.name, None)) is None:
            msg = (
                f"Failed to implement default serialization for class `{cls.__name__}`: "
                f"missing type hint for parameter '{param.name}' in `{cls.__name__}'.__init__`"
            )
            raise ValueError(msg)
        param_types[param.name] = param_type
        # Store parameters with default value
        if param.default is not param.empty:
            param_defaults.add(param.name)

    return param_types, param_defaults


def is_serializable(cls: type) -> bool:
    return (
        (encode := getattr(cls, "encode", None)) is not None
        and callable(encode)
        and (decode := getattr(cls, "decode", None)) is not None
        and callable(decode)
    )


def is_plain_data(data: Any) -> bool:
    """Check if `data` is of type :py:class:`PlainData`."""
    if data is None or isinstance(data, (str, int, float)):
        return True
    if isinstance(data, list):
        return all(is_plain_data(x) for x in data)
    if isinstance(data, dict):
        return all(isinstance(key, str) and is_plain_data(value) for key, value in data.items())
    return False


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
        msg = f"Exception occurred during encoding `{cls.__name__}`"
        raise EncodingError(msg) from err
    if not is_plain_data(encoded):
        msg = f"Encoding of `{cls.__name__}` did not produce plain data"
        raise TypeError(msg)
    try:
        decoded = cls.decode(copy.deepcopy(encoded))
    except Exception as err:
        msg = f"Exception occurred during decoding `{cls.__name__}`"
        raise DecodingError(msg) from err
    try:
        assert decoded.encode() == encoded
    except Exception as err:
        msg = f"Second encoding of `{type(decoded).__name__}` does not match first encoding"
        raise AssertionError(msg) from err
