"""Wire shapes. Patterns travel as `Pattern.to_dict()`; recipes as `[{op, params}]`."""

from pydantic import BaseModel, Field


class DesignSummary(BaseModel):
    slug: str
    title: str
    has_input: bool
    has_prompt: bool
    has_pattern: bool
    width: int | None = None
    height: int | None = None
    colors: int | None = None
    stitches: int | None = None
    thumbnail_png: str | None = None


class DesignDetail(BaseModel):
    slug: str
    title: str
    prompt: str
    has_input: bool
    pattern: dict | None
    history: str
    version: str | None = None  # design.json version; send it back on save


class CreateDesign(BaseModel):
    slug: str
    title: str


class PromptBody(BaseModel):
    text: str


class OpCallModel(BaseModel):
    op: str
    params: dict = Field(default_factory=dict)


class RunRequest(BaseModel):
    recipe: list[OpCallModel]


class StepOut(BaseModel):
    name: str
    params: dict
    kind: str
    preview_png: str
    stats: dict


class RunResponse(BaseModel):
    pattern: dict
    steps: list[StepOut]


class ApplyRequest(BaseModel):
    pattern: dict
    op: str
    params: dict = Field(default_factory=dict)


class ApplyResponse(BaseModel):
    pattern: dict


class SavePattern(BaseModel):
    pattern: dict
    version: str | None = None  # if given and design.json changed since, the save is refused (409)


class SaveResponse(BaseModel):
    pattern: dict
    version: str | None


class OpSchema(BaseModel):
    name: str
    kind: str
    group: str
    title: str
    description: str
    schema_: dict = Field(alias="schema")

    model_config = {"populate_by_name": True}


class ThreadsResponse(BaseModel):
    rows: list[dict]
    totals: dict
