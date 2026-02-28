"""
Action generator for KITA interventions.
Generates context-aware messages from template bank based on strategy.
"""


TEMPLATES = {
    "Encouraging Reconnect": [
        {"text": "Hey {name}, it's been a while — how have things been?", "min_inactivity": 3},
        {"text": "Realized we haven't caught up lately. Want to sync soon?", "min_inactivity": 5},
        {"text": "Life's been busy — how are you doing these days?", "min_inactivity": 2},
        {"text": "I miss our conversations. Free to catch up sometime?", "min_inactivity": 7},
        {"text": "Been meaning to check in — everything good on your end?", "min_inactivity": 4},
    ],
    "Maintain Light Touch": [
        {"text": "Hey {name}, hope your week's going well!", "min_inactivity": 0},
        {"text": "Quick check-in — how's everything?", "min_inactivity": 0},
        {"text": "Thought of you today, hope all's good!", "min_inactivity": 0},
        {"text": "How's your schedule looking this week?", "min_inactivity": 0},
        {"text": "Just saying hi — hope things are smooth!", "min_inactivity": 0},
    ],
    "Plan Follow-Up": [
        {"text": "About that plan we discussed — should we lock it in?", "min_inactivity": 2},
        {"text": "Still up for our plan? Let's confirm a time.", "min_inactivity": 3},
        {"text": "Should we finalize the plan this week?", "min_inactivity": 2},
        {"text": "Let's stop postponing and set a date.", "min_inactivity": 5},
        {"text": "Want to revisit that plan we mentioned?", "min_inactivity": 2},
    ],
    "High-Priority Reconnect": [
        {"text": "Hey {name}, I don't want us drifting apart — let's talk.", "min_inactivity": 10},
        {"text": "It's been too long. Can we catch up soon?", "min_inactivity": 14},
        {"text": "I value our connection — want to reconnect properly?", "min_inactivity": 12},
        {"text": "We haven't spoken in a while. Let's fix that.", "min_inactivity": 14},
        {"text": "Miss our chats — let's not lose touch.", "min_inactivity": 10},
    ],
    "Nostalgia Reignite": [
        {"text": "Remember our last crazy conversation? We need a sequel.", "min_inactivity": 15},
        {"text": "Randomly remembered our old chats — made me smile.", "min_inactivity": 14},
        {"text": "Feels like we haven't talked like we used to.", "min_inactivity": 20},
        {"text": "Miss the old vibe — let's bring it back.", "min_inactivity": 18},
        {"text": "Been thinking about our last hangout — we should repeat it.", "min_inactivity": 15},
    ],
    "Reciprocity Rebalance": [
        {"text": "Hey {name}, I'll let you take the lead this time 😊", "min_inactivity": 0},
        {"text": "Your turn to plan something!", "min_inactivity": 0},
        {"text": "I feel like I've been texting first a lot lately 😄", "min_inactivity": 0},
        {"text": "How about you pick the next plan?", "min_inactivity": 0},
        {"text": "I'll wait for your ping this time!", "min_inactivity": 0},
    ],
}


def generate_actions(
    strategies_dict: dict,
    features_dict: dict,
    previous_messages: dict | None = None,
) -> dict:
    """
    Generate intervention messages per contact based on strategy.

    Args:
        strategies_dict: Output from select_strategies().
        features_dict: Output from extract_features().
        previous_messages: Optional dict of {contact: last_template_index}.

    Returns:
        Dict mapping contact names to {final_message, strategy_type, priority}
    """
    previous_messages = previous_messages or {}
    contacts = set(strategies_dict.keys()) & set(features_dict.keys())
    result = {}

    for contact in contacts:
        strategy_info = strategies_dict[contact]
        features = features_dict[contact]
        last_index = previous_messages.get(contact)

        result[contact] = _generate_contact_action(
            contact,
            strategy_info,
            features,
            last_index,
        )

    return result


def _generate_contact_action(
    contact: str,
    strategy_info: dict,
    features: dict,
    last_index: int | None,
) -> dict:
    """Generate action for one contact."""
    strategy_type = strategy_info.get("strategy_type", "Maintain Light Touch")
    priority = strategy_info.get("priority", "Low")

    if strategy_type == "No Action":
        return {
            "final_message": "",
            "strategy_type": strategy_type,
            "priority": priority,
        }

    templates = TEMPLATES.get(strategy_type, TEMPLATES["Maintain Light Touch"])
    inactivity_days = features.get("inactivity_days", 0)

    indexed = list(enumerate(templates))
    candidates = [(i, t) for i, t in indexed if inactivity_days >= t["min_inactivity"]]
    if not candidates:
        candidates = indexed

    exclude_idx = {last_index} if last_index is not None else set()
    remaining = [(i, t) for i, t in candidates if i not in exclude_idx]
    if not remaining:
        remaining = candidates

    _, template = _select_template(remaining, inactivity_days)
    final_message = template["text"].format(name=contact.capitalize())

    return {
        "final_message": final_message,
        "strategy_type": strategy_type,
        "priority": priority,
    }


def _select_template(
    candidates: list[tuple[int, dict]],
    inactivity_days: int,
) -> tuple[int, dict]:
    """
    Select template deterministically: highest min_inactivity <= inactivity_days.
    If multiple, choose first.
    """
    eligible = [
        (orig_idx, t)
        for orig_idx, t in candidates
        if t["min_inactivity"] <= inactivity_days
    ]
    if not eligible:
        return candidates[0]

    eligible.sort(key=lambda x: -x[1]["min_inactivity"])
    return eligible[0]


if __name__ == "__main__":
    import sys

    from decision_engine.strategy_selector import select_strategies
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
    strategies_dict = select_strategies(features_dict, scores_dict, states_dict)
    actions = generate_actions(strategies_dict, features_dict)

    if actions:
        sample_contact = next(iter(actions))
        print(f"Sample contact '{sample_contact}': {actions[sample_contact]}")
