import inspect
from collections.abc import Callable, Sequence
from types import UnionType
from typing import Any, Generic, TypeVar, Union, cast, get_args, get_origin, get_type_hints

from bench._logging import get_logger

_LOGGER = get_logger("bench")


T = TypeVar("T")


class TypedFunction(Generic[T]):
    """
    Class that holds a function together its type hints.

    When the function is evaluated, a warning is logged whenever the type of an argument,
    or the type of the return value, is not compatible with the corresponding type hint.

    The type hints of the function, if provided, must satisfy the bounds as given by the
    `param_types` and `return_type` arguments. If this is not satisfied, a warning is logged.

    Args:
        func: Function to store.
        param_types: Tuple types of the parameters of the functions.
        return_type: Type of the return value of the function.
    """

    def __init__(
        self,
        func: Callable[..., Any],
        *,
        param_types: tuple[type | None, ...],
        return_type: type[T] | None,
    ) -> None:
        self._func = func
        self._param_types = param_types
        self._return_type = return_type
        self._warned_param_types: tuple[set[type], ...] = tuple(set() for _ in param_types)
        self._warned_return_types: set[type] = set()
        self._validate_function()

    @property
    def name(self) -> str:
        return cast(str, self._func.__name__) if hasattr(self._func, "__name__") else str(self._func)

    def _validate_function(self) -> None:
        # Get function parameters
        self._param_names = tuple(inspect.signature(self._func).parameters)

        # Check number of function parameters
        if len(self._param_names) != len(self._param_types):
            msg = f"Expected function with {len(self._param_types)} parameters, but got {len(self._param_names)}"
            raise ValueError(msg)

        # Validate and set type hints of parameters and return value
        type_hints = get_type_hints(self._func)
        self._param_type_hints: tuple[tuple[type, ...] | None] = tuple(
            self._validate_type_hint(param_name, type_hints.get(param_name, None), param_type)
            for param_name, param_type in zip(self._param_names, self._param_types)
        )
        self._return_type_hint = self._validate_type_hint("return", type_hints.get("return", None), self._return_type)

    def _validate_type_hint(self, name: str, type_hint: Any, type_bound: type | None) -> tuple[type, ...] | None:
        # Case no type hint
        if type_hint is None:
            return None

        # Case type hint is a type
        if isinstance(type_hint, type):
            if type_bound is None or issubclass(type_hint, type_bound):
                return (type_hint,)

        # Case type hint is a generic type
        else:
            type_hint_origin = get_origin(type_hint)
            type_hint_args = get_args(type_hint)

            if type_hint_origin is UnionType or type_hint_origin is Union:
                for type_hint_arg in type_hint_args:
                    # If `type_hint_arg` is not a type, no sensible check can be performed during `evaluate`
                    if not isinstance(type_hint_arg, type):
                        return None
                    # If `type_bound` is not none, `type_hint_arg` must be a subclass of `type_bound`
                    if type_bound is not None and not issubclass(type_hint_arg, type_bound):
                        break
                else:
                    return tuple(cast(Sequence[type], type_hint_args))

        # If `type_bound` was provided, log warning about type hint
        if type_bound is not None:
            subject = "Return value" if name == "return" else f"Parameter '{name}'"
            type_hint_str = type_hint.__name__ if isinstance(type_hint, type) else str(type_hint)
            _LOGGER.warning(
                f"{subject} of `{self._func_qualname()}` has type hint "
                f"`{type_hint_str}`, but expected a type hint that is "
                f"compatible with `{type_bound.__name__}`"
            )
        return None

    def _func_qualname(self) -> str:
        if hasattr(self._func, "__qualname__"):
            return cast(str, self._func.__qualname__)
        return str(self._func)

    def __call__(self, *args: Any) -> T:
        # Check number of arguments
        if len(args) != len(self._param_types):
            msg = f"Expected {self._param_types} arguments, but got {len(args)}"
            raise ValueError(msg)

        # Check if argument types match type hints
        for arg, param_name, param_type_hint, warned_types in zip(
            args, self._param_names, self._param_type_hints, self._warned_param_types
        ):
            if (
                param_type_hint is not None
                and (type_arg := type(arg)) not in warned_types
                and not issubclass(type_arg, param_type_hint)
            ):
                _LOGGER.warning(
                    f"Argument '{param_name}' passed to `{self._func_qualname()}` has type `{type_arg.__name__}`, "
                    f"which does not match the type hint `{self._type_hint_to_str(param_type_hint)}`"
                )
                warned_types.add(type_arg)

        # Check return type
        result = self._func(*args)
        if (
            self._return_type_hint is not None
            and (type_result := type(result)) not in self._warned_return_types
            and not issubclass(type_result, self._return_type_hint)
        ):
            _LOGGER.warning(
                f"Value returned from `{self._func_qualname()}` has type `{type_result.__name__}`, "
                f"which does not match the type hint `{self._type_hint_to_str(self._return_type_hint)}`"
            )
            self._warned_return_types.add(type_result)

        return result

    def _type_hint_to_str(self, type_hint: tuple[type, ...]) -> str:
        return " | ".join(t.__name__ for t in type_hint)
