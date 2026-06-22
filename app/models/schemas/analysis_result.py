"""Pydantic schemas for the AnalysisResult JSONB output stored in requirement_analyses.result.

All schema classes use Pydantic v2 model_config for strict validation.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Priority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Severity(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class GapType(str, Enum):
    MISSING = "Missing"
    AMBIGUOUS = "Ambiguous"
    CONFLICTING = "Conflicting"
    INCOMPLETE = "Incomplete"


class RiskCategory(str, Enum):
    PROJECT = "Project"
    REQUIREMENT = "Requirement"


class DependencyType(str, Enum):
    INTERNAL = "Internal"
    EXTERNAL = "External"


class FunctionalRequirement(BaseModel):
    id: str = Field(..., examples=["FR-001"])
    description: str
    source_ref: str = Field(..., description="e.g. 'BRD_v2.pdf p.4'")
    priority: Priority


class NonFunctionalRequirement(BaseModel):
    id: str = Field(..., examples=["NFR-001"])
    description: str
    source_ref: str
    category: str = Field(..., description="e.g. Performance, Security, Usability")


class Assumption(BaseModel):
    id: str = Field(..., examples=["A-001"])
    description: str
    source_ref: str


class Constraint(BaseModel):
    id: str = Field(..., examples=["C-001"])
    description: str
    source_ref: str


class Dependency(BaseModel):
    id: str = Field(..., examples=["D-001"])
    description: str
    type: DependencyType


class Gap(BaseModel):
    id: str = Field(..., examples=["G-001"])
    type: GapType
    description: str
    source_ref: str
    severity: Severity


class Risk(BaseModel):
    id: str = Field(..., examples=["R-001"])
    category: RiskCategory
    description: str
    severity: Severity
    rationale: str


class Recommendation(BaseModel):
    id: str = Field(..., examples=["REC-001"])
    gap_ref: str = Field(..., description="Reference to a Gap id, e.g. G-001")
    action: str
    priority: Priority


class AnalysisResult(BaseModel):
    """Top-level schema for the JSONB result column in requirement_analyses."""

    executive_summary: str
    project_summary: str
    business_objectives: List[str] = Field(default_factory=list)
    functional_requirements: List[FunctionalRequirement] = Field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = Field(default_factory=list)
    assumptions: List[Assumption] = Field(default_factory=list)
    constraints: List[Constraint] = Field(default_factory=list)
    dependencies: List[Dependency] = Field(default_factory=list)
    gaps: List[Gap] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list)

    def summary_stats(self) -> dict:
        """Return a lightweight dict of counts, useful for SSE progress events."""
        return {
            "functional_requirements": len(self.functional_requirements),
            "non_functional_requirements": len(self.non_functional_requirements),
            "gaps": len(self.gaps),
            "risks": len(self.risks),
            "recommendations": len(self.recommendations),
        }
