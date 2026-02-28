"""
Feature extraction for KITA chat data.
Extracts behavioral and temporal features per contact.
"""

import numpy as np
from datetime import datetime


def extract_features(preprocessed_data: dict) -> dict:
    """
    Extract behavioral and temporal features per contact.

    Args:
        preprocessed_data: Output from preprocess_data().
            Format: {contact: [{timestamp, sender, message_length, message}, ...]}

    Returns:
        Dict mapping contact names to feature dicts with keys:
        frequency_per_week, inactivity_days, avg_response_time_hours,
        response_time_trend, reciprocity_index, engagement_slope, total_messages
    """
    if not preprocessed_data:
        return {}

    reference_date = _get_reference_date(preprocessed_data)
    result = {}

    for contact, messages in preprocessed_data.items():
        if not messages:
            result[contact] = _empty_features()
            continue
        result[contact] = _extract_contact_features(messages, reference_date)

    return result


def _get_reference_date(preprocessed_data: dict) -> datetime:
    """Latest timestamp across all contacts (used as 'current' date)."""
    return max(
        m["timestamp"]
        for msgs in preprocessed_data.values()
        for m in msgs
    )


def _empty_features() -> dict:
    """Default features for empty contact."""
    return {
        "frequency_per_week": 0.0,
        "inactivity_days": 0,
        "avg_response_time_hours": 0.0,
        "response_time_trend": 0.0,
        "reciprocity_index": 0.0,
        "engagement_slope": 0.0,
        "total_messages": 0,
    }


def _extract_contact_features(messages: list[dict], reference_date: datetime) -> dict:
    """Extract all features for a single contact."""
    total_messages = len(messages)
    timestamps = [m["timestamp"] for m in messages]
    first_ts = timestamps[0]
    last_ts = timestamps[-1]

    total_days_span = (last_ts - first_ts).days
    if total_days_span == 0:
        total_days_span = 1
    frequency_per_week = (total_messages / total_days_span) * 7

    inactivity_days = (reference_date - last_ts).days

    response_deltas_hours = _compute_response_deltas(messages)
    avg_response_time_hours = (
        float(np.mean(response_deltas_hours)) if response_deltas_hours else 0.0
    )
    response_time_trend = _compute_response_time_trend(response_deltas_hours)

    user_count = sum(1 for m in messages if m["sender"] == "user")
    reciprocity_index = user_count / total_messages if total_messages else 0.0

    engagement_slope = _compute_engagement_slope(messages)

    return {
        "frequency_per_week": round(frequency_per_week, 4),
        "inactivity_days": inactivity_days,
        "avg_response_time_hours": round(avg_response_time_hours, 4),
        "response_time_trend": round(response_time_trend, 4),
        "reciprocity_index": round(reciprocity_index, 4),
        "engagement_slope": round(engagement_slope, 4),
        "total_messages": total_messages,
    }


def _compute_response_deltas(messages: list[dict]) -> list[float]:
    """Response time deltas in hours, only when sender alternates."""
    deltas = []
    for i in range(1, len(messages)):
        if messages[i]["sender"] != messages[i - 1]["sender"]:
            delta_seconds = (messages[i]["timestamp"] - messages[i - 1]["timestamp"]).total_seconds()
            deltas.append(delta_seconds / 3600)
    return deltas


def _compute_response_time_trend(deltas: list[float]) -> float:
    """Linear regression slope on response time deltas. Positive = slowing."""
    if len(deltas) < 3:
        return 0.0
    x = np.arange(len(deltas))
    slope = np.polyfit(x, deltas, 1)[0]
    return float(slope)


def _compute_engagement_slope(messages: list[dict]) -> float:
    """Linear regression slope on weekly message counts. Positive = increasing."""
    if not messages:
        return 0.0

    first_ts = messages[0]["timestamp"]
    week_counts: dict[int, int] = {}

    for m in messages:
        week_idx = (m["timestamp"] - first_ts).days // 7
        week_counts[week_idx] = week_counts.get(week_idx, 0) + 1

    if len(week_counts) < 2:
        return 0.0

    weeks = sorted(week_counts.keys())
    counts = [week_counts[w] for w in weeks]
    slope = np.polyfit(weeks, counts, 1)[0]
    return float(slope)


if __name__ == "__main__":
    import sys

    from preprocessing.parser import preprocess_data

    file_path = "data/KITA_large_synthetic_chat.csv"
    if len(sys.argv) > 1:
        file_path = sys.argv[1]

    preprocessed = preprocess_data(file_path)
    features = extract_features(preprocessed)

    print(f"Contacts: {len(features)}")

    if features:
        sample_contact = next(iter(features))
        print(f"Sample contact '{sample_contact}': {features[sample_contact]}")
