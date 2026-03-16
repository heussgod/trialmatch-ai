from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Iterable

from .schemas import PatientProfile, TrialStudy

TOKEN_RE = re.compile(r"[a-z0-9]+")
AGE_RE = re.compile(r"(\d+)")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def age_to_years(raw_value: str | None) -> int | None:
    if not raw_value:
        return None
    value = raw_value.upper().strip()
    if value in {"N/A", "NONE"}:
        return None
    match = AGE_RE.search(value)
    if not match:
        return None
    amount = int(match.group(1))
    if "YEAR" in value:
        return amount
    if "MONTH" in value:
        return max(0, math.floor(amount / 12))
    if "WEEK" in value or "DAY" in value:
        return 0
    return amount


def study_to_document(study: TrialStudy) -> str:
    sections = [
        study.brief_title,
        study.official_title,
        " ".join(study.conditions),
        " ".join(study.interventions),
        study.brief_summary,
        study.eligibility_text,
        " ".join(study.locations),
    ]
    return normalize_whitespace(" ".join(section for section in sections if section))


def load_studies(path: Path) -> list[TrialStudy]:
    studies: list[TrialStudy] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            studies.append(TrialStudy.from_dict(json.loads(line)))
    return studies


def save_studies(path: Path, studies: Iterable[TrialStudy]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        for study in studies:
            handle.write(json.dumps(study.to_dict(), ensure_ascii=True) + "\n")


def load_profiles(path: Path) -> list[PatientProfile]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [PatientProfile.from_dict(item) for item in payload]


def save_profiles(path: Path, profiles: Iterable[PatientProfile]) -> None:
    ensure_parent(path)
    path.write_text(
        json.dumps([profile.to_dict() for profile in profiles], indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
