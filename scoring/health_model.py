"""
Health scoring model for KITA contacts.
Converts extracted features into health_score and decay_risk_score.
"""


def compute_health_scores(feature_dict: dict) -> dict:
    """
    Compute health and decay risk scores per contact.

    Args:
        feature_dict: Output from extract_features().
            Format: {contact: {frequency_per_week, inactivity_days, ...}}

    Returns:
        Dict mapping contact names to {health_score, decay_risk_score}
    """
    if not feature_dict:
        return {}

    return {
        contact: _compute_contact_scores(features)
        for contact, features in feature_dict.items()
    }


def _compute_contact_scores(features: dict) -> dict:
    """Compute health_score and decay_risk_score for one contact."""
    freq_norm = _normalize_frequency(features.get("frequency_per_week", 0))
    inactivity_penalty = _compute_inactivity_penalty(features.get("inactivity_days", 0))
    rt_norm = _normalize_response_time(features.get("avg_response_time_hours", 0))
    reciprocity_score = _compute_reciprocity_score(features.get("reciprocity_index", 0.5))
    trend_score = _compute_engagement_trend_score(features.get("engagement_slope", 0))
    rt_trend_penalty = _compute_response_time_trend_penalty(
        features.get("response_time_trend", 0)
    )

    health_score_raw = (
        (0.25 * freq_norm)
        + (0.25 * trend_score)
        + (0.15 * reciprocity_score)
        + (0.20 * rt_norm)
        - (0.10 * inactivity_penalty)
        - (0.05 * rt_trend_penalty)
    )
    health_score_raw = _clamp(health_score_raw, 0, 1)
    health_score = round(health_score_raw * 100, 2)

    reciprocity_index = features.get("reciprocity_index", 0.5)
    engagement_slope = features.get("engagement_slope", 0)
    decay_risk_raw = (
        (0.35 * inactivity_penalty)
        + (0.30 * max(-engagement_slope / 5, 0))
        + (0.20 * rt_trend_penalty)
        + (0.15 * abs(reciprocity_index - 0.5) * 2)
    )
    decay_risk_score = round(_clamp(decay_risk_raw, 0, 1), 3)

    return {
        "health_score": health_score,
        "decay_risk_score": decay_risk_score,
    }


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp value between low and high."""
    return max(low, min(high, value))


def _normalize_frequency(frequency_per_week: float) -> float:
    """freq_norm = min(frequency_per_week / 15, 1)"""
    return min(frequency_per_week / 15, 1)


def _compute_inactivity_penalty(inactivity_days: int) -> float:
    """Penalty based on inactivity days."""
    if inactivity_days <= 3:
        return 0
    if inactivity_days <= 7:
        return 0.2
    if inactivity_days <= 14:
        return 0.5
    return 0.8


def _normalize_response_time(avg_response_time_hours: float) -> float:
    """rt_norm = 1 - min(avg_response_time_hours / 48, 1)"""
    return 1 - min(avg_response_time_hours / 48, 1)


def _compute_reciprocity_score(reciprocity_index: float) -> float:
    """Ideal is 0.5. Clamp between 0 and 1."""
    score = 1 - abs(reciprocity_index - 0.5) * 2
    return _clamp(score, 0, 1)


def _compute_engagement_trend_score(engagement_slope: float) -> float:
    """Positive slope = 1, negative = max(1 + slope/5, 0)."""
    if engagement_slope >= 0:
        return 1
    return _clamp(1 + engagement_slope / 5, 0, 1)


def _compute_response_time_trend_penalty(response_time_trend: float) -> float:
    """Penalty when response time is increasing (positive trend)."""
    if response_time_trend <= 0:
        return 0
    return min(response_time_trend / 5, 0.5)


if __name__ == "__main__":
    import sys

    from features.features import extract_features
    from preprocessing.parser import preprocess_data

    file_path = "data/KITA_large_synthetic_chat.csv"
    if len(sys.argv) > 1:
        file_path = sys.argv[1]

    preprocessed = preprocess_data(file_path)
    features = extract_features(preprocessed)
    scores = compute_health_scores(features)

    if scores:
        sample_contact = next(iter(scores))
        print(f"Sample contact '{sample_contact}': {scores[sample_contact]}")
