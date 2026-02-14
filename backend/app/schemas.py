from typing import Any, Literal

from pydantic import BaseModel, Field

Location = Literal[
    "top-left",
    "top",
    "top-right",
    "left",
    "center",
    "right",
    "bottom-left",
    "bottom",
    "bottom-right",
    "unknown",
]


class ObjectItem(BaseModel):
    name: str
    count: int | None = None
    location: Location = "unknown"
    relative_position: str | None = None
    attributes: list[str] = Field(default_factory=list)
    visible_text: list[str] = Field(default_factory=list)
    confidence: float | None = None  # 0-1, optional


class Inventory(BaseModel):
    objects: list[ObjectItem]
    scene_summary: str | None = None


class Ambiguity(BaseModel):
    ambiguous: bool
    reason: str | None = None
    candidates: list[str] = Field(default_factory=list)


class OnePassResponse(BaseModel):
    inventory: Inventory
    ambiguity: Ambiguity
    answer: str


class IterStartResponse(BaseModel):
    session_id: str
    inventory_brief: str
    ambiguity: Ambiguity
    clarification_question: str
    options: list[str]


class IterChooseRequest(BaseModel):
    session_id: str
    chosen: str


class IterChooseResponse(BaseModel):
    focused_answer: str
    followup_suggestions: list[str] = Field(default_factory=list)
    updated_state: dict[str, Any] = Field(default_factory=dict)


class SceneResponse(BaseModel):
    inventory: Inventory
    ambiguity: Ambiguity
