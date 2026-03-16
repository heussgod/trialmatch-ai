from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path
from typing import Any

import requests

from .config import DEFAULT_CONDITIONS, OPEN_STATUSES, TRIAL_SNAPSHOT_PATH
from .schemas import TrialStudy
from .utils import age_to_years, save_studies

API_URL = "https://clinicaltrials.gov/api/v2/studies"


def parse_study(payload: dict[str, Any], source_condition: str) -> TrialStudy | None:
    protocol = payload.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    status_module = protocol.get("statusModule", {})
    description_module = protocol.get("descriptionModule", {})
    conditions_module = protocol.get("conditionsModule", {})
    design_module = protocol.get("designModule", {})
    eligibility_module = protocol.get("eligibilityModule", {})
    interventions_module = protocol.get("armsInterventionsModule", {})
    contacts_module = protocol.get("contactsLocationsModule", {})

    nct_id = identification.get("nctId")
    if not nct_id:
        return None

    status = status_module.get("overallStatus", "")
    if status and status not in OPEN_STATUSES:
        return None

    interventions = [
        intervention.get("name", "").strip()
        for intervention in interventions_module.get("interventions", [])
        if intervention.get("name")
    ]
    locations = []
    for location in contacts_module.get("locations", [])[:8]:
        facility = location.get("facility", "")
        city = location.get("city", "")
        country = location.get("country", "")
        parts = [part for part in [facility, city, country] if part]
        if parts:
            locations.append(", ".join(parts))

    return TrialStudy(
        nct_id=nct_id,
        brief_title=identification.get("briefTitle", "").strip(),
        official_title=identification.get("officialTitle", "").strip(),
        brief_summary=description_module.get("briefSummary", "").strip(),
        conditions=[item.strip() for item in conditions_module.get("conditions", []) if item],
        interventions=interventions,
        phases=[item.strip() for item in design_module.get("phases", []) if item],
        status=status,
        minimum_age_years=age_to_years(eligibility_module.get("minimumAge")),
        maximum_age_years=age_to_years(eligibility_module.get("maximumAge")),
        sex=eligibility_module.get("sex", "ALL").upper(),
        eligibility_text=eligibility_module.get("eligibilityCriteria", "").strip(),
        locations=locations,
        source_condition=source_condition,
    )


def fetch_condition_studies(condition: str, limit: int, session: requests.Session) -> list[TrialStudy]:
    studies: list[TrialStudy] = []
    page_token: str | None = None

    while len(studies) < limit:
        params = {
            "query.cond": condition,
            "pageSize": min(100, max(20, limit)),
            "format": "json",
        }
        if page_token:
            params["pageToken"] = page_token

        response = session.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        for raw_study in payload.get("studies", []):
            study = parse_study(raw_study, source_condition=condition)
            if study is not None:
                studies.append(study)
                if len(studies) >= limit:
                    break

        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    return studies


def fetch_snapshot(conditions: list[str], limit_per_condition: int) -> list[TrialStudy]:
    deduped: "OrderedDict[str, TrialStudy]" = OrderedDict()
    with requests.Session() as session:
        for condition in conditions:
            for study in fetch_condition_studies(condition, limit_per_condition, session):
                deduped.setdefault(study.nct_id, study)
    return list(deduped.values())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch open clinical trials into a local JSONL snapshot.")
    parser.add_argument("--condition", action="append", dest="conditions", help="Condition to query. Repeat for multiple.")
    parser.add_argument("--limit-per-condition", type=int, default=30, help="Max studies per condition.")
    parser.add_argument("--output", default=str(TRIAL_SNAPSHOT_PATH), help="Where to write the snapshot JSONL.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    conditions = args.conditions or DEFAULT_CONDITIONS
    output_path = Path(args.output)
    studies = fetch_snapshot(conditions=conditions, limit_per_condition=args.limit_per_condition)
    save_studies(output_path, studies)
    print(f"Fetched {len(studies)} studies into {output_path}")


if __name__ == "__main__":
    main()
