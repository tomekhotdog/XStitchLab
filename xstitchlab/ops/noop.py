"""No-op pattern operation, used by tests."""

from pydantic import BaseModel

NAME = "noop"
KIND = "pattern"
GROUP = "test"
TITLE = "No-op"
DESCRIPTION = "Returns the pattern unchanged (used by tests)."


class Params(BaseModel):
    times: int = 1


def apply(pattern, params):
    return pattern
