"""
Relationship state classifier for KITA.
Classifies each contact into Active, Stable, Cooling, At Risk, Neglected, or One-Sided.
"""


def classify_relationships(features_dict: dict, scores_dict: dict) -> dict:
    """
    Classify each relationship into a structured state.

    Args:
        features_dict: Output from extract_features().
        scores_dict: Output from compute_health_scores().

    Returns:
        Dict mapping contact names to {state, confidence}
    """
    contacts = set(features_dict.keys()) & set(scores_dict.keys())
    return {
        contact: _classify_contact(
            features_dict.get(contact, {}),
            scores_dict.get(contact, {}),
        )
        for contact in contacts
    }


def _classify_contact(features: dict, scores: dict) -> dict:
    """Classify one contact. First matching condition wins (priority order)."""
    inactivity_days = features.get("inactivity_days", 0)
    health_score = scores.get("health_score", 0)
    decay_risk_score = scores.get("decay_risk_score", 0)
    reciprocity_index = features.get("reciprocity_index", 0.5)
    engagement_slope = features.get("engagement_slope", 0)
    response_time_trend = features.get("response_time_trend", 0)

    if _is_neglected(inactivity_days):
        state = "Neglected"
        confidence = min(inactivity_days / 30, 1)
    elif _is_at_risk(health_score, decay_risk_score):
        state = "At Risk"
        confidence = decay_risk_score
    elif _is_one_sided(reciprocity_index):
        state = "One-Sided"
        confidence = min(abs(reciprocity_index - 0.5) * 2, 1)
    elif _is_cooling(engagement_slope, health_score, response_time_trend):
        state = "Cooling"
        confidence = min(abs(engagement_slope) / 5, 1)
    elif _is_active(health_score, decay_risk_score, engagement_slope):
        state = "Active"
        confidence = health_score / 100
    else:
        state = "Stable"
        confidence = 0.5

    return {
        "state": state,
        "confidence": round(min(max(confidence, 0), 1), 3),
    }


def _is_neglected(inactivity_days: int) -> bool:
    """Neglected: inactivity_days > 21"""
    return inactivity_days > 21


def _is_at_risk(health_score: float, decay_risk_score: float) -> bool:
    """At Risk: health_score < 40 OR decay_risk_score > 0.45"""
    return health_score < 40 or decay_risk_score > 0.45


def _is_one_sided(reciprocity_index: float) -> bool:
    """One-Sided: reciprocity_index > 0.7 OR reciprocity_index < 0.3"""
    return reciprocity_index > 0.7 or reciprocity_index < 0.3


def _is_cooling(
    engagement_slope: float,
    health_score: float,
    response_time_trend: float,
) -> bool:
    """Cooling: (engagement_slope < 0 AND 40 <= health_score <= 65) OR response_time_trend > 0.1"""
    return (
        (engagement_slope < 0 and 40 <= health_score <= 65)
        or response_time_trend > 0.1
    )


def _is_active(
    health_score: float,
    decay_risk_score: float,
    engagement_slope: float,
) -> bool:
    """Active: health_score >= 75 AND decay_risk_score < 0.15 AND engagement_slope >= 0"""
    return (
        health_score >= 75
        and decay_risk_score < 0.15
        and engagement_slope >= 0
    )


if __name__ == "__main__":
    import sys

    from features.features import extract_features
    from preprocessing.parser import preprocess_data
    from scoring.health_model import compute_health_scores

    file_path = "data/KITA_large_synthetic_chat.csv"
    if len(sys.argv) > 1:
        file_path = sys.argv[1]

    preprocessed = preprocess_data(file_path)
    features_dict = extract_features(preprocessed)
    scores_dict = compute_health_scores(features_dict)
    classifications = classify_relationships(features_dict, scores_dict)

    if classifications:
        sample_contact = next(iter(classifications))
        print(f"Sample contact '{sample_contact}': {classifications[sample_contact]}")
