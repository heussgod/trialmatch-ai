from __future__ import annotations

import pandas as pd
import streamlit as st

from trialmatch.config import BENCHMARK_PATH, TRIAL_SNAPSHOT_PATH
from trialmatch.evaluate import evaluate
from trialmatch.match import TrialMatcher
from trialmatch.schemas import PatientProfile
from trialmatch.utils import load_profiles, load_studies

st.set_page_config(page_title="TrialMatch AI", page_icon=":microscope:", layout="wide")


@st.cache_resource
def load_matcher() -> TrialMatcher:
    return TrialMatcher(load_studies(TRIAL_SNAPSHOT_PATH))


@st.cache_data
def load_examples() -> list[PatientProfile]:
    return load_profiles(BENCHMARK_PATH)


matcher = load_matcher()
examples = load_examples()
metrics = evaluate(top_k=3)

st.title("TrialMatch AI")
st.caption("Explainable clinical trial matching with hybrid retrieval and structured eligibility checks.")

example_lookup = {profile.patient_id: profile for profile in examples}
default_profile = examples[0]
selected_example = st.sidebar.selectbox("Example patient", list(example_lookup), index=0)
profile = example_lookup.get(selected_example, default_profile)
scoring_mode = st.sidebar.selectbox("Scoring mode", ["hybrid", "bm25", "semantic"], index=0)

age = st.sidebar.slider("Age", min_value=18, max_value=90, value=profile.age)
sex = st.sidebar.selectbox("Sex", ["MALE", "FEMALE"], index=0 if profile.sex.upper() == "MALE" else 1)
conditions = st.sidebar.text_input("Conditions (comma separated)", value=", ".join(profile.conditions))
keywords = st.sidebar.text_input("Keywords", value=", ".join(profile.keywords))
interventions = st.sidebar.text_input("Desired interventions", value=", ".join(profile.desired_interventions))
top_k = st.sidebar.slider("Top results", min_value=3, max_value=10, value=5)

current_profile = PatientProfile(
    patient_id="interactive-profile",
    age=age,
    sex=sex,
    conditions=[item.strip() for item in conditions.split(",") if item.strip()],
    keywords=[item.strip() for item in keywords.split(",") if item.strip()],
    desired_interventions=[item.strip() for item in interventions.split(",") if item.strip()],
)

results = matcher.score(current_profile, mode=scoring_mode)[:top_k]

left, right = st.columns([2, 1])
with left:
    st.subheader("Top Trial Matches")
    table = pd.DataFrame(
        [
            {
                "rank": result.rank,
                "nct_id": result.study.nct_id,
                "title": result.study.display_title,
                "status": result.study.status,
                "phase": ", ".join(result.study.phases) or "N/A",
                "score": round(result.score, 3),
                "age_ok": result.age_ok,
                "sex_ok": result.sex_ok,
            }
            for result in results
        ]
    )
    st.dataframe(table, width="stretch", hide_index=True)

    for result in results:
        with st.expander(f"#{result.rank} {result.study.display_title} ({result.study.nct_id})"):
            st.markdown(f"**Why it surfaced:** {result.explanation}")
            if result.caution:
                st.warning(result.caution)
            st.markdown("**Evidence snippets**")
            for snippet in result.evidence_snippets:
                st.write(f"- {snippet}")
            st.markdown("**Study metadata**")
            st.write(
                {
                    "conditions": result.study.conditions,
                    "interventions": result.study.interventions,
                    "phase": result.study.phases,
                    "locations": result.study.locations[:4],
                }
            )
with right:
    st.subheader("Bundled Benchmark")
    selected_metrics = metrics[scoring_mode]
    metric_a, metric_b, metric_c = st.columns(3)
    metric_a.metric("Hit@3", f"{selected_metrics['hit_rate_at_k']:.2f}")
    metric_b.metric("MRR@3", f"{selected_metrics['mrr_at_k']:.2f}")
    metric_c.metric("Eligible@3", f"{selected_metrics['structured_pass_rate_at_k']:.2f}")
    st.caption("Scores come from 10 curated patient profiles with gold trial IDs.")
    st.markdown(
        """
        **How to read this**

        - `hit_rate_at_k`: fraction of patient profiles with at least one relevant, age/sex-eligible trial in the top-k.
        - `mrr_at_k`: how early the first relevant result appears.
        - `structured_pass_rate_at_k`: fraction of top-k results that pass age/sex checks.
        """
    )
    st.markdown(f"**Current mode:** `{scoring_mode}`")
    st.markdown(f"**Bundled snapshot:** `{len(matcher.studies)}` live public studies")
