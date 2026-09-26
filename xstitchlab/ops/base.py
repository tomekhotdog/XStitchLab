"""Operation protocol and shared result types for recipe ops."""

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from PIL import Image
from pydantic import BaseModel, ConfigDict

from xstitchlab.core.pattern import Pattern

Kind = Literal["image", "pixelate", "pattern"]
KINDS = ("image", "pixelate", "pattern")


class OpParams(BaseModel):
    """Base for every op's Params: unknown keys in a recipe fail loudly."""

    model_config = ConfigDict(extra="forbid")


class OpError(Exception):
    """Raised for unknown ops, invalid recipes/params, or failures inside an op."""

    def __init__(self, message: str, step_index: int | None = None, op: str | None = None):
        super().__init__(message)
        self.step_index = step_index
        self.op = op


@runtime_checkable
class Operation(Protocol):
    """Shape of an op module (or any object) the registry accepts."""

    NAME: str
    KIND: Kind
    GROUP: str          # "import" | "cleanup" | "kit" | "outline"
    TITLE: str
    DESCRIPTION: str
    Params: type[BaseModel]

    @staticmethod
    def apply(subject, params): ...   # image->image, image->Pattern, or Pattern->Pattern by KIND


@dataclass
class Step:
    """One executed recipe step and what it produced."""
    name: str
    params: dict
    result: "Image.Image | Pattern"
    stats: dict = field(default_factory=dict)


@dataclass
class RunResult:
    pattern: Pattern
    steps: list[Step]
