"""
UI components and pipeline logic for KITA dashboard.
"""

import smtplib
from email.mime.text import MIMEText
from pathlib import Path

import streamlit as st

from action_generator.generator import generate_actions
from dashboard.db import authenticate_user, create_user
from dashboard.parsers import parse_to_standard_csv
from decision_engine.strategy_selector import select_strategies
from features.features import extract_features
from preprocessing.parser import preprocess_data
from scoring.health_model import compute_health_scores
from state_engine.classifier import classify_relationships


STATE_DESCRIPTIONS = {
    "Active": "Strong engagement with positive trends.",
    "Stable": "Consistent interaction pattern.",
    "Cooling": "Engagement declining or response times increasing.",
    "At Risk": "Relationship needs attention.",
    "Neglected": "Extended period without contact.",
    "One-Sided": "Effort imbalance in the relationship.",
}

PRIORITY_BG = {
    "Low": "#ECFDF5",
    "Medium": "#FEF3C7",
    "High": "#FEE2E2",
}


def render_auth_forms():
    st.markdown(
        """
        <div class="hero">
            <h1>💬 KITA — Keep In Touch AI</h1>
            <p>Autonomous Relationship Intelligence Engine</p>
            <p>Analyze communication patterns. Detect decay. Recommend meaningful action.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("Sign in or create an account to get started.")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                user = authenticate_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    with tab2:
        with st.form("signup_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_phone = st.text_input("Phone (optional)", placeholder="Optional")
            new_password = st.text_input("Password", type="password")
            if st.form_submit_button("Create Account"):
                if not new_username or not new_email or not new_password:
                    st.error("Username, email, and password are required.")
                elif create_user(new_username, new_email, new_password, new_phone):
                    st.success("Account created. Please log in.")
                else:
                    st.error("Username already exists.")


def _render_hero():
    st.markdown(
        """
        <div class="hero">
            <h1>💬 KITA — Keep In Touch AI</h1>
            <p>Autonomous Relationship Intelligence Engine</p>
            <p>Analyzing communication patterns. Detecting decay. Recommending meaningful action.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard():
    user = st.session_state.user
    _render_hero()

    col_user, col_logout = st.columns([4, 1])
    with col_user:
        st.markdown(f"## Welcome, {user['username']}")
    with col_logout:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()

    input_type, uploaded_file, user_identifier = render_input_section()
    if not uploaded_file:
        st.info("Upload a file to analyze your relationships.")
        _render_pipeline_overview()
        return

    with st.spinner("Processing your data..."):
        result = run_pipeline(uploaded_file, input_type, user_identifier)

    if result.get("error"):
        st.error(result["error"])
        return

    st.subheader("Relationship Insights")
    for contact, data in result.get("contacts", {}).items():
        _render_contact_card(contact, data, input_type, user["username"])

    if st.button("Send Email Summary", type="primary"):
        ok = send_email_notification(user["email"], result.get("contacts", {}), user["username"])
        if ok:
            st.success("📧 Email notification sent successfully.")
        else:
            st.error("Email sending failed. Check secrets configuration.")

    _render_pipeline_overview_expander(result)


def render_input_section():
    st.subheader("Data Source")
    input_type = st.radio(
        "Select Data Source",
        ["WhatsApp Export", "Conversation Log CSV", "Email Export CSV", "SMS Export CSV"],
        horizontal=True,
    )
    user_identifier = ""
    if input_type == "WhatsApp Export":
        user_identifier = st.text_input(
            "Your WhatsApp name or number (to identify you in the chat)",
            placeholder="e.g. John or +1234567890",
        )
    uploaded_file = st.file_uploader(
        "Upload file",
        type=["csv", "txt"],
        help="Upload WhatsApp .txt, or conversation .csv",
    )
    return input_type, uploaded_file, user_identifier or "user"


def run_pipeline(uploaded_file, input_type: str, user_identifier: str) -> dict:
    try:
        content = uploaded_file.read()
        csv_path = parse_to_standard_csv(content, input_type, user_identifier)
        preprocessed = preprocess_data(csv_path)
        Path(csv_path).unlink(missing_ok=True)
    except Exception as e:
        return {"error": str(e)}

    if not preprocessed:
        return {"error": "No valid conversation data found."}

    features_dict = extract_features(preprocessed)
    scores_dict = compute_health_scores(features_dict)
    states_dict = classify_relationships(features_dict, scores_dict)
    strategies_dict = select_strategies(features_dict, scores_dict, states_dict)
    actions = generate_actions(strategies_dict, features_dict)

    contacts = {}
    for contact in actions:
        contacts[contact] = {
            "features": features_dict.get(contact, {}),
            "scores": scores_dict.get(contact, {}),
            "state": states_dict.get(contact, {}),
            "strategy": strategies_dict.get(contact, {}),
            "action": actions.get(contact, {}),
        }
    return {"contacts": contacts}


def _adapt_message_style(message: str, input_type: str, contact: str, username: str) -> str:
    if input_type == "Email Export CSV":
        return f"Subject: Reconnecting\n\nHi {contact.capitalize()},\n\n{message}\n\nBest,\n{username}"
    if input_type == "SMS Export CSV":
        return message[:160] if len(message) > 160 else message
    if input_type == "WhatsApp Export" and message and not any(c in message for c in "😊🙂👍"):
        return message + " 🙂"
    return message


def _render_contact_card(contact: str, data: dict, input_type: str, username: str):
    features = data.get("features", {})
    state_info = data.get("state", {})
    strategy = data.get("strategy", {})
    action = data.get("action", {})

    inactivity_days = features.get("inactivity_days", 0)
    state = state_info.get("state", "Stable")
    priority = strategy.get("priority", "Low")
    strategy_type = action.get("strategy_type", "")
    raw_message = action.get("final_message", "")
    display_message = _adapt_message_style(raw_message, input_type, contact, username)
    display_msg_escaped = (
        display_message.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    )
    bg_color = PRIORITY_BG.get(priority, "#FFFFFF")

    st.markdown(f"### 👤 {contact.capitalize()}")

    st.markdown(
        f"""
        <div style="
            background-color: {bg_color};
            padding: 24px;
            border-radius: 14px;
            border: 1px solid #E5E7EB;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            margin-top: 20px;
        ">
            <div style="display:flex; justify-content: space-between;">
                <span><b>Last Interaction:</b> {inactivity_days} days ago</span>
                <span style="font-weight:bold;">Priority: {priority}</span>
            </div>
            <hr>
            <div style="text-align:center; font-size:18px; margin:20px 0;">
                {display_msg_escaped}
            </div>
            <div>
                <b>Status:</b> {state}
                <br>
                <b>Strategy:</b> {strategy_type}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.code(raw_message, language=None)


def send_email_notification(to_email: str, contacts: dict, username: str) -> bool:
    if not contacts:
        return False
    try:
        body_parts = []
        for contact, data in contacts.items():
            action = data.get("action", {})
            strategy = data.get("strategy", {})
            state_info = data.get("state", {})
            msg = action.get("final_message", "")
            priority = strategy.get("priority", "Low")
            state = state_info.get("state", "Stable")
            body_parts.append(
                f"--- {contact.capitalize()} ---\n"
                f"Strategy: {action.get('strategy_type', '')}\n"
                f"Priority: {priority}\n"
                f"State: {state}\n"
                f"Message: {msg}\n"
            )
        body = "KITA Relationship Summary\n\n" + "\n".join(body_parts)
        return _send_email_smtp(to_email, "KITA - Relationship Insights", body)
    except Exception:
        return False


def _send_email_smtp(to_email: str, subject: str, body: str) -> bool:
    try:
        cfg = st.secrets["email"]
        smtp_server = cfg["smtp_server"]
        smtp_port = int(cfg.get("smtp_port", 587))
        sender_email = cfg["sender_email"]
        sender_password = cfg["sender_password"]
    except (KeyError, TypeError):
        return False
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = to_email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception:
        return False


def _render_pipeline_overview():
    with st.expander("System Pipeline Overview"):
        st.markdown(
            """
            **KITA Pipeline (6 phases):**
            1. **Preprocessing** — Parse and normalize conversation data
            2. **Feature Extraction** — Frequency, inactivity, response time, reciprocity, engagement
            3. **Health Scoring** — Health score (0–100) and decay risk (0–1)
            4. **State Classification** — Active, Stable, Cooling, At Risk, Neglected, One-Sided
            5. **Strategy Selection** — Maintain, Reconnect, Follow-Up, etc.
            6. **Action Generation** — Context-aware message templates
            """
        )


def _render_pipeline_overview_expander(result: dict):
    with st.expander("System Pipeline Overview — Results"):
        contacts = result.get("contacts", {})
        for contact, data in contacts.items():
            scores = data.get("scores", {})
            state_info = data.get("state", {})
            strategy = data.get("strategy", {})
            action = data.get("action", {})
            st.markdown(f"**{contact.capitalize()}**")
            st.write(f"- Health Score: {scores.get('health_score', 0)}")
            st.write(f"- Decay Risk: {scores.get('decay_risk_score', 0)}")
            st.write(f"- State: {state_info.get('state', '')}")
            st.write(f"- Strategy: {action.get('strategy_type', '')}")
            st.write(f"- Message: {action.get('final_message', '')}")
            st.divider()
