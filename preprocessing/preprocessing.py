import pandas as pd
from datetime import datetime


REQUIRED_COLUMNS = {"timestamp", "sender", "receiver", "message"}


def preprocess_data(file_path: str, user_id: str) -> dict:
    """
    Orchestrate preprocessing of interaction logs for a single focal user.

    Parameters
    ----------
    file_path : str
        Path to the CSV file containing columns: timestamp, sender, receiver, message.
    user_id : str
        Identifier of the focal user; must not be hardcoded.

    Returns
    -------
    dict
        {
            "contact_id": [
                {
                    "timestamp": datetime,
                    "sender": "user" or "contact",
                    "message_length": int
                },
                ...
            ],
            ...
        }
    """
    df_raw = _load_data(file_path)

    df_user = _filter_user_interactions(df_raw, user_id)
    if df_user.empty:
        return {}

    df_time = _parse_timestamps(df_user)
    if df_time.empty:
        return {}

    df_prepared = _normalize_sender_and_length(df_time, user_id)

    df_for_history = df_prepared[["contact_id", "timestamp", "sender_role", "message_length"]].copy()
    history = _build_contact_history(df_for_history)

    return history


def _load_data(file_path: str) -> pd.DataFrame:
    """
    Load the raw CSV data and validate required columns.
    """
    df = pd.read_csv(file_path)

    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Missing required columns: {missing_list}")

    return df


def _filter_user_interactions(df: pd.DataFrame, user_id: str) -> pd.DataFrame:
    """
    Keep only interactions involving the focal user and exactly one other contact.

    Rules:
    - sender == user_id and receiver != user_id  -> keep, contact_id = receiver
    - receiver == user_id and sender != user_id  -> keep, contact_id = sender
    - otherwise                                  -> exclude
    """
    df_local = df.copy()

    sender_is_user = df_local["sender"] == user_id
    receiver_is_user = df_local["receiver"] == user_id

    valid_mask = (sender_is_user & ~receiver_is_user) | (receiver_is_user & ~sender_is_user)

    user_df = df_local.loc[valid_mask].copy()
    if user_df.empty:
        return user_df

    def _determine_contact_id(row) -> str:
        if row["sender"] == user_id:
            return row["receiver"]
        return row["sender"]

    user_df["contact_id"] = user_df.apply(_determine_contact_id, axis=1)

    return user_df


def _parse_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert timestamp column to datetime, logging any dropped rows.
    """
    df_local = df.copy()

    original_count = len(df_local)
    df_local["timestamp"] = pd.to_datetime(df_local["timestamp"], errors="coerce")

    valid_df = df_local.dropna(subset=["timestamp"])
    valid_count = len(valid_df)
    dropped = original_count - valid_count

    if dropped > 0:
        print(f"Dropped {dropped} rows due to invalid timestamps")

    return valid_df


def _normalize_sender_and_length(df: pd.DataFrame, user_id: str) -> pd.DataFrame:
    """
    Add sender_role ('user' or 'contact') and message_length (character count).
    """
    df_local = df.copy()

    df_local["sender_role"] = df_local["sender"].where(df_local["sender"] != user_id, other="user")
    df_local.loc[df_local["sender_role"] != "user", "sender_role"] = "contact"

    df_local["message"] = df_local["message"].fillna("").astype(str)
    df_local["message_length"] = df_local["message"].str.len().astype(int)

    return df_local


def _build_contact_history(df: pd.DataFrame) -> dict:
    """
    Build the final nested dictionary of interaction history per contact.
    """
    df_local = df.copy()

    df_local = df_local.sort_values(["contact_id", "timestamp"])

    result: dict = {}

    for contact_id, group_df in df_local.groupby("contact_id"):
        interactions = []

        for row in group_df.itertuples(index=False):
            ts = row.timestamp

            # Ensure native Python datetime, not pandas.Timestamp
            if hasattr(ts, "to_pydatetime"):
                ts = ts.to_pydatetime()
            elif not isinstance(ts, datetime):
                try:
                    ts = pd.to_datetime(ts).to_pydatetime()
                except Exception:
                    # Fallback: leave as-is if conversion fails unexpectedly
                    pass

            interactions.append(
                {
                    "timestamp": ts,
                    "sender": row.sender_role,
                    "message_length": int(row.message_length),
                }
            )

        result[str(contact_id)] = interactions

    return result

