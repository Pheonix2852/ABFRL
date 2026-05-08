from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SearchPlan(BaseModel):
    intent: str = "recommendation"
    category: Optional[str] = None
    subcategory: Optional[str] = None
    style_mode: Optional[str] = None
    gender: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    colors: list[str] = Field(default_factory=list)
    occasion: Optional[str] = None
    style: Optional[str] = None
    allow_cross_category: bool = False
    explicit_constraints: list[str] = Field(default_factory=list)
    inferred_preferences: list[str] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
    soft_preferences: list[str] = Field(default_factory=list)
    confidence: float = 0.0
