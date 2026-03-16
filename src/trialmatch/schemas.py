from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TrialStudy:
    nct_id: str
    brief_title: str
    official_title: str
    brief_summary: str
    conditions: list[str]
    interventions: list[str]
    phases: list[str]
    status: str
    minimum_age_years: int | None
    maximum_age_years: int | None
    sex: str
    eligibility_text: str
    locations: list[str] = field(default_factory=list)
    source_condition: str | None = None

    @property
    def display_title(self) -> str:
        return self.brief_title or self.official_title or self.nct_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "nct_id": self.nct_id,
            "brief_title": self.brief_title,
            "official_title": self.official_title,
            "brief_summary": self.brief_summary,
            "conditions": self.conditions,
            "interventions": self.interventions,
            "phases": self.phases,
            "status": self.status,
            "minimum_age_years": self.minimum_age_years,
            "maximum_age_years": self.maximum_age_years,
            "sex": self.sex,
            "eligibility_text": self.eligibility_text,
            "locations": self.locations,
            "source_condition": self.source_condition,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TrialStudy":
        return cls(
            nct_id=payload["nct_id"],
            brief_title=payload.get("brief_title", ""),
            official_title=payload.get("official_title", ""),
            brief_summary=payload.get("brief_summary", ""),
            conditions=list(payload.get("conditions", [])),
            interventions=list(payload.get("interventions", [])),
            phases=list(payload.get("phases", [])),
            status=payload.get("status", ""),
            minimum_age_years=payload.get("minimum_age_years"),
            maximum_age_years=payload.get("maximum_age_years"),
            sex=payload.get("sex", "ALL"),
            eligibility_text=payload.get("eligibility_text", ""),
            locations=list(payload.get("locations", [])),
            source_condition=payload.get("source_condition"),
        )


@dataclass(slots=True)
class PatientProfile:
    patient_id: str
    age: int
    sex: str
    conditions: list[str]
    keywords: list[str] = field(default_factory=list)
    desired_interventions: list[str] = field(default_factory=list)
    target_conditions: list[str] = field(default_factory=list)
    gold_nct_ids: list[str] = field(default_factory=list)
    notes: str = ""

    def to_query_text(self) -> str:
        parts = [
            " ".join(self.conditions),
            " ".join(self.keywords),
            " ".join(self.desired_interventions),
            self.notes,
        ]
        return " ".join(part for part in parts if part).strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "age": self.age,
            "sex": self.sex,
            "conditions": self.conditions,
            "keywords": self.keywords,
            "desired_interventions": self.desired_interventions,
            "target_conditions": self.target_conditions,
            "gold_nct_ids": self.gold_nct_ids,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PatientProfile":
        return cls(
            patient_id=payload["patient_id"],
            age=int(payload["age"]),
            sex=payload["sex"],
            conditions=list(payload.get("conditions", [])),
            keywords=list(payload.get("keywords", [])),
            desired_interventions=list(payload.get("desired_interventions", [])),
            target_conditions=list(payload.get("target_conditions", [])),
            gold_nct_ids=list(payload.get("gold_nct_ids", [])),
            notes=payload.get("notes", ""),
        )


@dataclass(slots=True)
class MatchResult:
    study: TrialStudy
    rank: int
    score: float
    bm25_score: float
    semantic_score: float
    condition_overlap: float
    intervention_overlap: float
    age_ok: bool
    sex_ok: bool
    explanation: str
    caution: str
    evidence_snippets: list[str]
