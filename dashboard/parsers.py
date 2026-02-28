"""
Input parsers for different data sources.
Converts various formats to standard CSV for preprocess_data.
"""

import csv
import re
import tempfile
from datetime import datetime
from pathlib import Path


def parse_to_standard_csv(
    file_content: bytes | str,
    input_type: str,
    user_identifier: str = "user",
) -> str:
    """
    Parse uploaded file to standard CSV format.
    Returns path to temp CSV file.
    """
    if isinstance(file_content, bytes):
        content = file_content.decode("utf-8", errors="replace")
    else:
        content = str(file_content)

    if input_type == "WhatsApp Export":
        rows = _parse_whatsapp(content, user_identifier)
    else:
        rows = _parse_csv_variant(content, input_type)

    path = Path(tempfile.mkstemp(suffix=".csv")[1])
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "sender", "receiver", "message"])
        writer.writerows(rows)
    return str(path)


def _parse_whatsapp(content: str, user_id: str) -> list[tuple]:
    """
    Parse WhatsApp export format:
    [DD/MM/YYYY, HH:MM:SS] Name: Message
    or [DD/MM/YY, HH:MM:SS AM/PM] Name: Message
    """
    user_id_lower = (user_id or "user").strip().lower()
    pattern = re.compile(
        r"\[([^\]]+)\]\s*([^:]+):\s*(.+)$",
        re.DOTALL | re.MULTILINE,
    )
    raw_rows = []
    for m in pattern.finditer(content):
        dt_str, sender, message = m.groups()
        message = message.strip()
        if not message:
            continue
        dt_str = dt_str.strip()
        dt_parts = re.split(r"[\s,]+", dt_str, 2)
        date_str = dt_parts[0] if dt_parts else ""
        time_str = dt_parts[1] if len(dt_parts) > 1 else "00:00:00"
        try:
            dt = _parse_whatsapp_datetime(date_str, time_str)
        except (ValueError, TypeError):
            dt = datetime.now()
        raw_rows.append((dt, sender.strip(), message))
    if not raw_rows:
        return []
    participants = list({r[1].lower() for r in raw_rows})
    contact_name = next((p for p in participants if p != user_id_lower), "contact")
    rows = []
    for dt, sender, message in raw_rows:
        sender_lower = sender.lower()
        if sender_lower == user_id_lower:
            sender_out, receiver_out = "user", contact_name
        else:
            sender_out, receiver_out = sender, "user"
        rows.append((dt.strftime("%Y-%m-%d %H:%M:%S"), sender_out, receiver_out, message))
    return rows


def _parse_whatsapp_datetime(date_str: str, time_str: str) -> datetime:
    time_str = time_str.strip().upper()
    for fmt in [
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%y %I:%M:%S %p",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ]:
        try:
            return datetime.strptime(f"{date_str} {time_str}", fmt)
        except ValueError:
            continue
    return datetime.now()


def _parse_csv_variant(content: str, input_type: str) -> list[tuple]:
    """Parse CSV with flexible column mapping."""
    lines = content.strip().splitlines()
    if not lines:
        return []

    reader = csv.reader(lines)
    header = [h.strip().lower() for h in next(reader)]
    col_map = _map_columns(header)
    if not col_map:
        return []

    rows = []
    for row in reader:
        if len(row) < len(header):
            row.extend([""] * (len(header) - len(row)))
        ts = row[col_map["timestamp"]] if col_map["timestamp"] is not None else ""
        sender = row[col_map["sender"]] if col_map["sender"] is not None else "user"
        receiver = row[col_map["receiver"]] if col_map["receiver"] is not None else "contact"
        msg = row[col_map["message"]] if col_map["message"] is not None else ""
        if not msg or not ts:
            continue
        try:
            dt = _parse_flexible_datetime(ts)
            ts_out = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            ts_out = ts
        rows.append((ts_out, sender.strip(), receiver.strip(), msg.strip()))
    return rows


def _map_columns(header: list[str]) -> dict:
    mapping = {
        "timestamp": ["timestamp", "date", "datetime", "time", "created_at"],
        "sender": ["sender", "from", "author", "user", "source"],
        "receiver": ["receiver", "to", "recipient", "contact", "target"],
        "message": ["message", "body", "text", "content", "msg"],
    }
    result = {}
    for key, aliases in mapping.items():
        result[key] = None
        for alias in aliases:
            if alias in header:
                result[key] = header.index(alias)
                break
    if result["message"] is None or result["sender"] is None:
        return {}
    if result["timestamp"] is None:
        for i, h in enumerate(header):
            if "date" in h or "time" in h:
                result["timestamp"] = i
                break
    if result["timestamp"] is None:
        result["timestamp"] = 0
    if result["receiver"] is None:
        result["receiver"] = result["sender"]
    return result


def _parse_flexible_datetime(s: str) -> datetime:
    s = str(s).strip()
    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%H:%M:%S %Y-%m-%d",
    ]:
        try:
            return datetime.strptime(s[:19] if len(s) > 19 else s, fmt)
        except ValueError:
            continue
    return datetime.now()
