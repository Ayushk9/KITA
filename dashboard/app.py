"""
KITA (Keep In Touch AI) - Production Streamlit Dashboard
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from dashboard.ui import render_auth_forms, render_dashboard


def _inject_theme():
    st.markdown(
        """
        <style>
        body { font-family: 'Segoe UI', sans-serif; }
        .main { background-color: #F9FAFB; }
        .hero {
            background: linear-gradient(90deg, #2563EB, #1D4ED8);
            padding: 40px;
            border-radius: 14px;
            color: white;
            margin-bottom: 30px;
        }
        .card {
            padding: 24px;
            border-radius: 14px;
            border: 1px solid #E5E7EB;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            margin-top: 20px;
        }
        .priority-low { color: green; font-weight: bold; }
        .priority-medium { color: orange; font-weight: bold; }
        .priority-high { color: red; font-weight: bold; }
        .stButton>button {
            border-radius: 8px;
            padding: 0.5rem 1rem;
            background-color: #2563EB;
            color: white;
            border: none;
        }
        .stButton>button:hover { background-color: #1D4ED8; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title="KITA - Keep In Touch AI",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user" not in st.session_state:
        st.session_state.user = None

    _inject_theme()

    if not st.session_state.logged_in:
        render_auth_forms()
        return

    render_dashboard()


if __name__ == "__main__":
    main()
