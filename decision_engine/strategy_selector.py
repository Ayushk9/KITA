"""
Strategy selector for KITA interventions.
Selects intervention strategy based on state, scores, and features.
"""


def select_strategies(
    features_dict: dict,
    scores_dict: dict,
    states_dict: dict,
) -> dict:
    """
    Select intervention strategy per contact.

    Args:
        features_dict: Output from extract_features().
        scores_dict: Output from compute_health_scores().
        states_dict: Output from classify_relationships().

    Returns:
        Dict mapping contact names to {strategy_type, priority, reason}
    """
    contacts = (
        set(features_dict.keys())
        & set(scores_dict.keys())
        & set(states_dict.keys())
    )
    return {
        contact: _select_strategy(
            features_dict.get(contact, {}),
            scores_dict.get(contact, {}),
            states_dict.get(contact, {}),
        )
        for contact in contacts
    }


def _select_strategy(
    features: dict,
    scores: dict,
    state_info: dict,
) -> dict:
    """Select strategy for one contact based on state and context."""
    state = state_info.get("state", "Stable")
    decay_risk_score = scores.get("decay_risk_score", 0)
    inactivity_days = features.get("inactivity_days", 0)
    response_time_trend = features.get("response_time_trend", 0)
    reciprocity_index = features.get("reciprocity_index", 0.5)
    total_messages = features.get("total_messages", 0)

    if state == "Active":
        strategy = "No Action"
        priority = "Low"
        reason = "Active engagement."
    elif state == "Stable":
        strategy = "Maintain Light Touch"
        priority = "Low"
        reason = "Stable interaction pattern."
    elif state == "Cooling":
        if inactivity_days > 7:
            strategy = "Encouraging Reconnect"
            priority = "Medium"
            reason = "High inactivity detected."
        elif response_time_trend > 0.2:
            strategy = "Plan Follow-Up"
            priority = "Medium"
            reason = "Engagement declining with increasing response delay."
        else:
            strategy = "Maintain Light Touch"
            priority = "Low"
            reason = "Moderate cooling detected."
    elif state == "At Risk":
        if decay_risk_score > 0.6:
            strategy = "High-Priority Reconnect"
            priority = "High"
            reason = "High decay risk detected."
        else:
            strategy = "Encouraging Reconnect"
            priority = "High"
            reason = "Relationship at risk."
    elif state == "Neglected":
        if total_messages > 40:
            strategy = "Nostalgia Reignite"
            reason = "Long history with extended inactivity."
        else:
            strategy = "High-Priority Reconnect"
            reason = "High inactivity detected."
        priority = "High"
    elif state == "One-Sided":
        if reciprocity_index > 0.75:
            strategy = "Reciprocity Rebalance"
            priority = "Medium"
            reason = "Effort imbalance observed."
        else:
            strategy = "Maintain Light Touch"
            priority = "Low"
            reason = "Moderate effort imbalance."
    else:
        strategy = "Maintain Light Touch"
        priority = "Low"
        reason = "Stable interaction pattern."

    return {
        "strategy_type": strategy,
        "priority": priority,
        "reason": reason,
    }


if __name__ == "__main__":
    import sys

    from features.features import extract_features
    from preprocessing.parser import preprocess_data
    from scoring.health_model import compute_health_scores
    from state_engine.classifier import classify_relationships

    file_path = "data/KITA_large_synthetic_chat.csv"
    if len(sys.argv) > 1:
        file_path = sys.argv[1]

    preprocessed = preprocess_data(file_path)
    features_dict = extract_features(preprocessed)
    scores_dict = compute_health_scores(features_dict)
    states_dict = classify_relationships(features_dict, scores_dict)
    strategies = select_strategies(features_dict, scores_dict, states_dict)

    if strategies:
        sample_contact = next(iter(strategies))
        print(f"Sample contact '{sample_contact}': {strategies[sample_contact]}")
