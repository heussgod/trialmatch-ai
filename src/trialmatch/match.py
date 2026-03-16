from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

from .schemas import MatchResult, PatientProfile, TrialStudy
from .utils import study_to_document, tokenize

ScoringMode = Literal["hybrid", "bm25", "semantic"]


@dataclass(slots=True)
class TrialMatcher:
    studies: list[TrialStudy]
    documents: list[str] = field(init=False)
    tokenized_documents: list[list[str]] = field(init=False)
    bm25: BM25Okapi = field(init=False)
    vectorizer: TfidfVectorizer = field(init=False)
    svd: TruncatedSVD | None = field(init=False)
    doc_embeddings: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        if not self.studies:
            raise ValueError("TrialMatcher requires at least one study.")
        self.documents = [study_to_document(study) for study in self.studies]
        self.tokenized_documents = [tokenize(doc) for doc in self.documents]
        self.bm25 = BM25Okapi(self.tokenized_documents)
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.9,
        )
        tfidf = self.vectorizer.fit_transform(self.documents)
        max_components = min(96, tfidf.shape[0] - 1, tfidf.shape[1] - 1)
        if max_components >= 1:
            self.svd = TruncatedSVD(n_components=max_components, random_state=42)
            self.doc_embeddings = normalize(self.svd.fit_transform(tfidf))
        else:
            self.svd = None
            self.doc_embeddings = normalize(tfidf.toarray())

    def score(self, profile: PatientProfile, mode: ScoringMode = "hybrid") -> list[MatchResult]:
        query_text = profile.to_query_text()
        tokens = tokenize(query_text)
        bm25_scores = np.asarray(self.bm25.get_scores(tokens), dtype=float)
        semantic_scores = self._semantic_scores(query_text)

        bm25_norm = self._minmax(bm25_scores)
        semantic_norm = self._minmax(semantic_scores)

        results: list[MatchResult] = []
        for idx, study in enumerate(self.studies):
            condition_overlap = self._overlap(profile.conditions, study.conditions)
            intervention_overlap = self._overlap(
                profile.desired_interventions + profile.keywords,
                study.interventions,
            )
            age_ok, age_reason = self._age_check(profile.age, study)
            sex_ok, sex_reason = self._sex_check(profile.sex, study)
            eligibility_penalty = 1.0 if age_ok and sex_ok else 0.15

            if mode == "bm25":
                score = bm25_norm[idx]
            elif mode == "semantic":
                score = semantic_norm[idx]
            else:
                score = (
                    0.35 * bm25_norm[idx]
                    + 0.35 * semantic_norm[idx]
                    + 0.20 * condition_overlap
                    + 0.10 * intervention_overlap
                ) * eligibility_penalty

            explanation = self._build_explanation(
                study,
                condition_overlap,
                intervention_overlap,
                age_reason,
                sex_reason,
            )
            caution = "" if age_ok and sex_ok else "Structured eligibility mismatch. Manual review required."
            snippets = self._evidence_snippets(study, profile)
            results.append(
                MatchResult(
                    study=study,
                    rank=0,
                    score=float(score),
                    bm25_score=float(bm25_norm[idx]),
                    semantic_score=float(semantic_norm[idx]),
                    condition_overlap=float(condition_overlap),
                    intervention_overlap=float(intervention_overlap),
                    age_ok=age_ok,
                    sex_ok=sex_ok,
                    explanation=explanation,
                    caution=caution,
                    evidence_snippets=snippets,
                )
            )

        ranked = sorted(results, key=lambda item: item.score, reverse=True)
        for rank, item in enumerate(ranked, start=1):
            item.rank = rank
        return ranked

    def _semantic_scores(self, query_text: str) -> np.ndarray:
        query_tfidf = self.vectorizer.transform([query_text])
        if self.svd is None:
            query_embedding = normalize(query_tfidf.toarray())
        else:
            query_embedding = normalize(self.svd.transform(query_tfidf))
        return cosine_similarity(query_embedding, self.doc_embeddings).ravel()

    @staticmethod
    def _minmax(values: np.ndarray) -> np.ndarray:
        if values.size == 0:
            return values
        minimum = values.min()
        maximum = values.max()
        if maximum - minimum < 1e-9:
            return np.ones_like(values)
        return (values - minimum) / (maximum - minimum)

    @staticmethod
    def _overlap(left: list[str], right: list[str]) -> float:
        left_tokens = {token for value in left for token in tokenize(value)}
        right_tokens = {token for value in right for token in tokenize(value)}
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / len(left_tokens)

    @staticmethod
    def _age_check(age: int, study: TrialStudy) -> tuple[bool, str]:
        if study.minimum_age_years is not None and age < study.minimum_age_years:
            return False, f"Age {age} is below minimum {study.minimum_age_years}."
        if study.maximum_age_years is not None and age > study.maximum_age_years:
            return False, f"Age {age} is above maximum {study.maximum_age_years}."
        bounds = []
        if study.minimum_age_years is not None:
            bounds.append(f"min {study.minimum_age_years}")
        if study.maximum_age_years is not None:
            bounds.append(f"max {study.maximum_age_years}")
        if not bounds:
            return True, "No structured age limit listed."
        return True, "Age passes structured check (" + ", ".join(bounds) + ")."

    @staticmethod
    def _sex_check(sex: str, study: TrialStudy) -> tuple[bool, str]:
        normalized = sex.upper()
        allowed = study.sex.upper()
        if allowed in {"ALL", ""}:
            return True, "Open to all sexes."
        if normalized == allowed:
            return True, f"Sex passes structured check ({allowed})."
        return False, f"Study is limited to {allowed}."

    @staticmethod
    def _build_explanation(
        study: TrialStudy,
        condition_overlap: float,
        intervention_overlap: float,
        age_reason: str,
        sex_reason: str,
    ) -> str:
        condition_text = ", ".join(study.conditions[:3]) or "no condition metadata"
        intervention_text = ", ".join(study.interventions[:2]) or "no intervention metadata"
        return (
            f"Conditions align with {condition_text}. "
            f"Interventions mention {intervention_text}. "
            f"Condition overlap={condition_overlap:.2f}; intervention overlap={intervention_overlap:.2f}. "
            f"{age_reason} {sex_reason}"
        )

    @staticmethod
    def _evidence_snippets(study: TrialStudy, profile: PatientProfile) -> list[str]:
        query_terms = tokenize(profile.to_query_text())
        candidates = [segment.strip() for segment in study.eligibility_text.split("\n") if segment.strip()]
        scored: list[tuple[int, str]] = []
        for candidate in candidates:
            tokens = set(tokenize(candidate))
            overlap = sum(1 for term in query_terms if term in tokens)
            if overlap:
                scored.append((overlap, candidate))
        scored.sort(key=lambda item: item[0], reverse=True)
        snippets = [snippet for _, snippet in scored[:3]]
        if snippets:
            return snippets
        fallback = study.brief_summary or study.display_title
        return [fallback[:220]]
