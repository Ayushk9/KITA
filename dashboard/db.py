"""
SQLite database module for KITA user authentication.
"""

import hashlib
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "kita_users.db"


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username: str, email: str, password: str, phone: str = "") -> bool:
    """
    Create a new user. Returns True on success, False if username exists.
    """
    _init_db()
    try:
        conn = _get_connection()
        conn.execute(
            "INSERT INTO users (username, email, phone, password_hash) VALUES (?, ?, ?, ?)",
            (username.strip().lower(), email.strip(), phone.strip(), _hash_password(password)),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def authenticate_user(username: str, password: str) -> dict | None:
    """
    Authenticate user. Returns user dict {username, email, phone} or None.
    """
    _init_db()
    conn = _get_connection()
    row = conn.execute(
        "SELECT username, email, phone FROM users WHERE username = ? AND password_hash = ?",
        (username.strip().lower(), _hash_password(password)),
    ).fetchone()
    conn.close()
    if row:
        return {"username": row["username"], "email": row["email"], "phone": row["phone"]}
    return None
