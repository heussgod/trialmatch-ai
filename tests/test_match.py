from trialmatch.match import TrialMatcher
from trialmatch.schemas import PatientProfile, TrialStudy


def build_studies() -> list[TrialStudy]:
    return [
        TrialStudy(
            nct_id="NCT1",
            brief_title="Heart Failure Exercise Program",
            official_title="",
            brief_summary="Exercise intervention for chronic heart failure.",
            conditions=["heart failure"],
            interventions=["exercise", "rehabilitation"],
            phases=["PHASE2"],
            status="RECRUITING",
            minimum_age_years=50,
            maximum_age_years=80,
            sex="ALL",
            eligibility_text="Adults with heart failure eligible for exercise rehabilitation.",
        ),
        TrialStudy(
            nct_id="NCT2",
            brief_title="Diabetes Nutrition Trial",
            official_title="",
            brief_summary="Diet coaching for type 2 diabetes.",
            conditions=["type 2 diabetes"],
            interventions=["nutrition coaching"],
            phases=["PHASE2"],
            status="RECRUITING",
            minimum_age_years=18,
            maximum_age_years=None,
            sex="ALL",
            eligibility_text="Adults with type 2 diabetes.",
        ),
    ]


def test_hybrid_match_prefers_condition_alignment() -> None:
    matcher = TrialMatcher(build_studies())
    profile = PatientProfile(
        patient_id="p1",
        age=67,
        sex="MALE",
        conditions=["heart failure"],
        keywords=["shortness of breath"],
        desired_interventions=["exercise"],
    )
    ranked = matcher.score(profile, mode="hybrid")
    assert ranked[0].study.nct_id == "NCT1"


def test_structured_age_mismatch_penalizes_result() -> None:
    matcher = TrialMatcher(build_studies())
    profile = PatientProfile(
        patient_id="p2",
        age=40,
        sex="MALE",
        conditions=["heart failure"],
        desired_interventions=["exercise"],
    )
    ranked = matcher.score(profile, mode="hybrid")
    heart_failure_result = next(result for result in ranked if result.study.nct_id == "NCT1")
    assert heart_failure_result.age_ok is False
    assert ranked[0].study.nct_id != "NCT1"
