"""
Supabase database module for KITA user authentication.
Replaces SQLite with persistent Supabase backend.
"""

import hashlib
import streamlit as st
from supabase import create_client
from postgrest.exceptions import APIError


# Initialize Supabase client from Streamlit secrets
def _get_supabase_client():
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["anon_key"],
    )


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username: str, email: str, password: str, phone: str = "") -> bool:
    """
    Create a new user.
    Returns True on success, False if username exists or error occurs.
    """
    try:
        supabase = _get_supabase_client()
        username_clean = username.strip().lower()

        # Check if username already exists
        existing = (
            supabase.table("users")
            .select("username")
            .eq("username", username_clean)
            .execute()
        )

        if existing.data:
            return False

        # Insert new user
        response = (
            supabase.table("users")
            .insert(
                {
                    "username": username_clean,
                    "email": email.strip(),
                    "phone": phone.strip(),
                    "password_hash": _hash_password(password),
                }
            )
            .execute()
        )

        return bool(response.data)

    except (KeyError, APIError, Exception):
        return False


def authenticate_user(username: str, password: str) -> dict | None:
    """
    Authenticate user.
    Returns user dict {username, email, phone} or None.
    """
    try:
        supabase = _get_supabase_client()
        username_clean = username.strip().lower()
        password_hash = _hash_password(password)

        response = (
            supabase.table("users")
            .select("username, email, phone")
            .eq("username", username_clean)
            .eq("password_hash", password_hash)
            .execute()
        )

        if response.data:
            user = response.data[0]
            return {
                "username": user.get("username"),
                "email": user.get("email"),
                "phone": user.get("phone"),
            }

        return None

    except (KeyError, APIError, Exception):
        return None