from __future__ import annotations

import importlib
import inspect
import json
from typing import Any, Protocol, Self, TypeAlias, TypeVar, cast

PlainData: TypeAlias = str | int | float | bool | None | list["PlainData"] | dict[str, "PlainData"]

T = TypeVar("T")


def encode(object: Any) -> PlainData:
    """Encode object into plain data.

    Args:
        object: Object to encode.

    Returns:
        Plain data representing the object.
    """
    # None, bool, int, float, str
    if object is None or isinstance(object, (int, float, str)):
        return object
    # list
    if isinstance(object, list):
        return [encode(x) for x in object]
    # tuple
    if isinstance(object, tuple):
        return {"()": [encode(x) for x in object]}
    # dict
    if isinstance(object, dict):
        encoded = {}
        for key, value in object.items():
            if not isinstance(key, str):
                msg = f"Encoding dictionary with key of type '{type(key).__name__}' not implemented"
                raise NotImplementedError(msg)
            encoded[key] = encode(value)
            # TODO: { "{}": [..items..] }
        return encoded
    # Serializable
    if hasattr(object, "encode") and callable(object.encode):
        encoded = object.encode()
        encoded["__class__"] = _class_to_path(type(object))
        return encoded

    msg = f"Could not encode object '{object}' of type '{type(object).__name__}'"
    raise NotImplementedError(msg)


def decode(data: PlainData) -> Any:
    """Decode plain data into object.

    Args:
        data: Plain data to decode.

    Returns:
        Decoded object.
    """
    # None, bool, int, float, str
    if data is None or isinstance(data, (int, float, str)):
        return data
    # list
    if isinstance(data, list):
        return [decode(x) for x in data]

    if isinstance(data, dict):
        # tuple
        if "()" in data:
            return tuple(decode(x) for x in cast(list, data["()"]))
        # Serializable
        if "__class__" in data:
            cls = _class_from_path(cast(str, data.pop("__class__")))
            if not hasattr(cls, "decode") or not callable(cls.decode):
                msg = f"Could not decode object of type '{cls.__name__}' due to missing 'decode' method"
                raise DecodingError(msg)
            return cls.decode(data)
        # dict
        return {key: decode(value) for key, value in data.items()}

    msg = f"Could not decode object of type '{type(data)}'"
    raise NotImplementedError(msg)


class Serializable(Protocol):
    """Protocol for serializable objects.

    Serializable classes should implement an :py:meth:`encode` and :py:meth:`decode`
    method. These methods can be used to encode objects into plain data, and decode
    plain data into objects.
    """

    def encode(self) -> dict[str, PlainData]:
        """Encode object into plain data dictionary."""

    @classmethod
    def decode(cls, data: dict[str, PlainData]) -> Self:
        """Decode plain data dictionary into an object."""


class DefaultSerializable(Serializable):
    """Default implementation of serializability.

    This default implementation uses the signature of the :py:const:`__init__` method
    to determine which properties to encode for serialization, and how to reconstruct
    the object from it.
    """

    def encode(self) -> dict[str, PlainData]:
        # Inspect the signature of the `__init__` method of the class
        cls = self.__class__
        signature = inspect.signature(cls.__init__)
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
            # Encode attribute value
            value = getattr(self, param.name)
            encoded[param.name] = encode(value)
        return encoded

    @classmethod
    def decode(cls, data: dict[str, PlainData]) -> Self:
        # Inspect the signature of the `__init__` method of the class
        signature = inspect.signature(cls.__init__)
        params = [param for param in signature.parameters.values() if param.name != "self"]
        # Encode and store the property corresponding to each parameter in a dictionary
        values: dict[str, Any] = {}
        for param in params:
            # Variable-length parameters are not allowed
            if param.kind == param.VAR_POSITIONAL or param.kind == param.VAR_KEYWORD:
                msg = f"Cannot decode variable-length parameter '{param.name}'"
                raise DecodingError(msg)
            # Data should contain parameter name as key
            if param.name not in data:
                msg = f"Missing key '{param.name}', as expected by `{cls.__name__}.__init__`"
                raise ValueError(msg)
            # Store decoded value
            values[param.name] = decode(data[param.name])
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


def to_json(object: Serializable | None) -> str:
    """Serialize object into JSON."""
    if object is None:
        return "null"
    return json.dumps(object.encode())


S = TypeVar("S", bound=Serializable)


def from_json(cls: type[S], data: str) -> S:
    """Deserialize JSON into object."""
    return cls.decode(json.loads(data))


def _class_to_path(cls: type) -> str:
    """Convert class to path."""
    return f"{cls.__module__}.{cls.__name__}"


def _class_from_path(path: str) -> type:
    """Convert path to class."""
    module_name, class_name = path.rsplit(".", 1)
    # Resolve module
    if module_name == "":
        msg = "Module name must be non-empty"
        raise ValueError(msg)
    if module_name.startswith("."):
        msg = f"Module name '{module_name}' may not be relative"
        raise ValueError(msg)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as err:
        msg = f"Could not import module '{module_name}'"
        raise ModuleNotFoundError(msg) from err
    # Resolve class
    if not hasattr(module, class_name):
        msg = f"Class '{class_name}' not found in module '{module_name}'"
        raise ValueError(msg)
    cls = getattr(module, class_name, None)
    if not isinstance(cls, type):
        msg = f"Object '{class_name}' in module '{module_name}' is not a class"
        raise TypeError(msg)
    return cls


def _is_primitive(x: Any) -> bool:
    return x is None or isinstance(x, (int, float, str, list, dict))
