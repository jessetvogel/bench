from dataclasses import dataclass, field
from datetime import timedelta
from typing import Literal

from bench.serialization import Serializable, default_serialization


@default_serialization
@dataclass
class X(Serializable):
    x: int = 42


@default_serialization
@dataclass
class Y(Serializable):
    y: float = 3.1415


@default_serialization
@dataclass
class A(Serializable):
    n: None = None
    b: bool = True
    i: int = 1
    f: float = 2.0
    s: str = "3"
    x: X = field(default_factory=lambda: X())
    li: list[int] = field(default_factory=lambda: [4, 5])
    ls: list[str] = field(default_factory=lambda: ["6", "7"])
    dsi: dict[str, int] = field(default_factory=lambda: {"8": 9, "10": 11})
    dff: dict[float, float] = field(default_factory=lambda: {12.0: 13.0, 14.0: 15.0})
    u: X | None = field(default_factory=lambda: X())
    lu: list[X | Y] = field(default_factory=lambda: [X(), Y()])
    lit: Literal["a", "b", "c"] = "a"
    t: timedelta = field(default_factory=lambda: timedelta(days=1, seconds=2, microseconds=3))


def test_default_serialization() -> None:
    """Test encoding and decoding provided by DefaultSerializable."""
    a = A()
    encoded = a.encode()
    print(encoded)
    assert A.decode(encoded) == a
