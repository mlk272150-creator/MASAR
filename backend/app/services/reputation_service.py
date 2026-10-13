import math
import re
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


_TOKEN_PATTERN = re.compile(r"[\w\u0600-\u06FF]+", flags=re.UNICODE)
_POSITIVE_TERMS = {
    "excellent", "good", "great", "reliable", "professional", "fast", "helpful",
    "ممتاز", "ممتازة", "جيد", "جيدة", "رائع", "رائعة", "ملتزم", "ملتزمة",
    "سريع", "سريعة", "محترف", "محترفة", "متعاون", "متعاونة", "امين", "أمين",
}
_NEGATIVE_TERMS = {
    "bad", "poor", "late", "unreliable", "rude", "unfinished", "slow",
    "سيء", "سيئة", "متأخر", "متأخرة", "غيرموثوق", "وقح", "وقحة",
    "بطيء", "بطيئة", "ناقص", "ناقصه", "غيرملتزم",
}
_NEGATIONS = {"not", "never", "no", "لم", "ليس", "ليست", "ما", "مش", "غير"}


def sentiment_score(reviews: list[str]) -> float:
    """Return a lexicon sentiment score between -1 and 1 for English and Arabic reviews."""
    if not reviews:
        return 0.0

    total = 0.0
    token_count = 0
    for review in reviews:
        tokens = [token.casefold() for token in _TOKEN_PATTERN.findall(review)]
        for index, token in enumerate(tokens):
            if token in _POSITIVE_TERMS:
                value = 1.0
            elif token in _NEGATIVE_TERMS:
                value = -1.0
            else:
                continue
            if any(previous in _NEGATIONS for previous in tokens[max(0, index - 3):index]):
                value *= -1
            total += value
            token_count += 1
    if token_count == 0:
        return 0.0
    return round(total / token_count, 4)


class ReputationService:
    """Score a submitted worker cohort using K-Means segmentation and review sentiment."""

    def evaluate(self, workers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(workers) < 2:
            raise ValueError("At least 2 worker profiles are required for cohort clustering.")
        worker_ids = [worker["worker_id"] for worker in workers]
        if len(set(worker_ids)) != len(worker_ids):
            raise ValueError("Worker IDs must be unique within the cohort.")

        sentiments = [sentiment_score(worker.get("reviews", [])) for worker in workers]
        features = np.asarray(
            [
                [
                    math.log1p(worker["completed_jobs"]),
                    worker["on_time_rate"],
                    worker["average_rating"] / 5.0,
                    (sentiment + 1.0) / 2.0,
                ]
                for worker, sentiment in zip(workers, sentiments)
            ],
            dtype=float,
        )
        scaled_features = StandardScaler().fit_transform(features)
        cluster_count = min(3, len(workers))
        raw_clusters = KMeans(n_clusters=cluster_count, n_init=10, random_state=42).fit_predict(
            scaled_features
        )

        # Rank clusters by their mean quality indicators for stable tier assignment.
        cluster_quality = {
            int(cluster): float(features[raw_clusters == cluster, 1:].mean())
            for cluster in np.unique(raw_clusters)
        }
        ranked_clusters = sorted(cluster_quality, key=cluster_quality.get)
        cluster_tiers = {
            cluster: ("emerging", "established", "trusted")[
                round(index * 2 / max(1, len(ranked_clusters) - 1))
            ]
            for index, cluster in enumerate(ranked_clusters)
        }

        results: list[dict[str, Any]] = []
        for worker, sentiment, cluster in zip(
            workers,
            sentiments,
            raw_clusters,
        ):
            experience = min(1.0, math.log1p(worker["completed_jobs"]) / math.log1p(100))
            score = (
                0.35 * (worker["average_rating"] - 1.0) / 4.0
                + 0.25 * worker["on_time_rate"]
                + 0.20 * experience
                + 0.20 * (sentiment + 1.0) / 2.0
            ) * 100.0
            results.append(
                {
                    "worker_id": worker["worker_id"],
                    "reputation_score": round(score, 2),
                    "trust_tier": cluster_tiers[int(cluster)],
                    "cohort_cluster": int(cluster),
                    "sentiment_score": sentiment,
                }
            )
        return results
