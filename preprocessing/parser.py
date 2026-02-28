"""
Preprocessing parser for KITA chat data.
Converts raw CSV into structured contact-wise conversation data.
"""

import pandas as pd
from pathlib import Path


REQUIRED_COLUMNS = ("timestamp", "sender", "receiver", "message")
USER_ID = "user"


def preprocess_data(file_path: str) -> dict:
    """
    Load and preprocess chat CSV into contact-wise conversation structure.

    Args:
        file_path: Path to the CSV file.

    Returns:
        Dict mapping contact names (lowercase) to lists of message dicts.
        Each message: {"timestamp", "sender", "message_length", "message"}

    Raises:
        ValueError: If file does not exist or required columns are missing.
    """
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")

    df = pd.read_csv(file_path)
    _validate_columns(df)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    df["sender"] = df["sender"].astype(str).str.strip().str.lower()
    df["receiver"] = df["receiver"].astype(str).str.strip().str.lower()
    df["message"] = df["message"].astype(str).str.strip()

    df = df[df["message"].notna() & (df["message"] != "")]

    result: dict[str, list[dict]] = {}

    for _, row in df.iterrows():
        sender = row["sender"]
        receiver = row["receiver"]
        contact = receiver if sender == USER_ID else sender
        msg_sender = "user" if sender == USER_ID else "contact"
        msg = row["message"]

        msg_dict = {
            "timestamp": row["timestamp"].to_pydatetime(),
            "sender": msg_sender,
            "message_length": len(msg),
            "message": msg,
        }

        if contact not in result:
            result[contact] = []
        result[contact].append(msg_dict)

    return result


def _validate_columns(df: pd.DataFrame) -> None:
    """Raise ValueError if required columns are missing."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


if __name__ == "__main__":
    import sys

    file_path = "data/KITA_large_synthetic_chat.csv"
    if len(sys.argv) > 1:
        file_path = sys.argv[1]

    data = preprocess_data(file_path)
    print(f"Contacts: {len(data)}")

    if data:
        sample_contact = next(iter(data))
        print(f"Sample contact '{sample_contact}': {len(data[sample_contact])} messages")
