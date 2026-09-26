"""No-op pattern operation, used by tests."""

from xstitchlab.ops.base import OpParams

NAME = "noop"
KIND = "pattern"
GROUP = "test"
TITLE = "No-op"
DESCRIPTION = "Returns the pattern unchanged (used by tests)."


class Params(OpParams):
    times: int = 1


def apply(pattern, params):
    return pattern
