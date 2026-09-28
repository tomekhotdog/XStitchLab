"""`/api/ops`, `/api/recipes/defaults`, `/api/dmc`, `/api/prompt-template`: registry and reference data."""

from fastapi import APIRouter

from xstitchlab.core.pattern import DMCPalette, OpCall
from xstitchlab.ops import registry
from xstitchlab.ops.defaults import DEFAULTS
from xstitchlab.prompts.templates import get_template

from backend.app.deps import pattern_from_wire
from backend.app.schemas import ApplyRequest, ApplyResponse, OpSchema, PromptBody

router = APIRouter(prefix="/api", tags=["ops"])

HIDDEN_GROUPS = {"test"}
PROMPT_STYLE = "pixel_art"
PROMPT_SUBJECT = "<SUBJECT>"


@router.get("/ops", response_model=list[OpSchema])
def list_ops():
    return [OpSchema(**entry) for entry in registry.schemas() if entry["group"] not in HIDDEN_GROUPS]


@router.post("/ops/apply", response_model=ApplyResponse)
def apply_op(body: ApplyRequest):
    pattern = pattern_from_wire(body.pattern)
    result = registry.apply_one(pattern, OpCall(body.op, dict(body.params)))  # OpError -> 400 / 422
    return ApplyResponse(pattern=result.to_dict())


@router.get("/recipes/defaults", response_model=dict[str, list[dict]])
def default_recipes():
    return {name: [call.to_dict() for call in recipe] for name, recipe in DEFAULTS.items()}


@router.get("/dmc", response_model=list[dict])
def dmc_colors():
    return [{"code": c.code, "name": c.name, "rgb": list(c.rgb)} for c in DMCPalette()]


@router.get("/prompt-template", response_model=PromptBody)
def prompt_template():
    """The pixel-art brief template with `<SUBJECT>` where the landmark goes."""
    return PromptBody(text=get_template(PROMPT_STYLE, PROMPT_SUBJECT))
