from __future__ import annotations

import argparse
import json
from statistics import mean

from .config import BENCHMARK_PATH, TRIAL_SNAPSHOT_PATH
from .match import TrialMatcher
from .utils import load_profiles, load_studies


def evaluate(top_k: int = 5) -> dict[str, dict[str, float]]:
    studies = load_studies(TRIAL_SNAPSHOT_PATH)
    profiles = load_profiles(BENCHMARK_PATH)
    matcher = TrialMatcher(studies)

    metrics: dict[str, dict[str, float]] = {}
    for mode in ("bm25", "semantic", "hybrid"):
        hit_rates = []
        reciprocal_ranks = []
        structured_pass_rates = []
        for profile in profiles:
            ranked = matcher.score(profile, mode=mode)[:top_k]
            hits = []
            first_hit_rank = None
            structured_pass = 0
            gold_ids = set(profile.gold_nct_ids)
            for idx, result in enumerate(ranked, start=1):
                if result.study.nct_id in gold_ids and result.age_ok and result.sex_ok:
                    hits.append(result.study.nct_id)
                    if first_hit_rank is None:
                        first_hit_rank = idx
                if result.age_ok and result.sex_ok:
                    structured_pass += 1
            hit_rates.append(1.0 if hits else 0.0)
            reciprocal_ranks.append(0.0 if first_hit_rank is None else 1.0 / first_hit_rank)
            structured_pass_rates.append(structured_pass / top_k)
        metrics[mode] = {
            "hit_rate_at_k": round(mean(hit_rates), 4),
            "mrr_at_k": round(mean(reciprocal_ranks), 4),
            "structured_pass_rate_at_k": round(mean(structured_pass_rates), 4),
        }
    return metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality on the bundled patient benchmark.")
    parser.add_argument("--top-k", type=int, default=5, help="How many results to score.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    metrics = evaluate(top_k=args.top_k)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
