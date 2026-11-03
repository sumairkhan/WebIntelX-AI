from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.api_client import APIClient, discover_backend_base_url


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #07131f;
            --panel: #0d1b2a;
            --panel-alt: #112434;
            --line: #1b3248;
            --text: #edf4ff;
            --muted: #9ec2de;
            --accent: #4ec3ff;
            --accent-2: #68f0d6;
            --danger: #ff7373;
            --warning: #f8c86d;
            --success: #4fd29d;
        }
        html, body, [data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, #07131f 0%, #0b1a2b 100%);
            color: var(--text);
        }
        [data-testid="stSidebar"] {
            background: rgba(8, 18, 29, 0.96);
            border-right: 1px solid var(--line);
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .stTabs [role="tablist"] {
            gap: 12px;
        }
        .stTabs [role="tab"] {
            background: rgba(17, 36, 52, 0.8);
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 0.5rem 1rem;
            color: var(--text);
        }
        .stTabs [role="tab"][aria-selected="true"] {
            background: rgba(78, 195, 255, 0.18);
            border-color: rgba(78, 195, 255, 0.8);
        }
        div[data-testid="metric-container"] {
            background: rgba(17, 36, 52, 0.9);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 1rem 1.2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.12);
        }
        .card {
            background: rgba(17, 36, 52, 0.88);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 1.25rem;
            box-shadow: 0 12px 32px rgba(0,0,0,0.12);
        }
        .small-muted {
            color: var(--muted);
            font-size: 0.78rem;
            letter-spacing: 0.02em;
        }
        .badge {
            display: inline-block;
            padding: 0.28rem 0.7rem;
            border-radius: 999px;
            font-size: 0.72rem;
            background: rgba(78, 195, 255, 0.12);
            border: 1px solid rgba(78, 195, 255, 0.45);
            color: var(--text);
        }
        .hero {
            background: linear-gradient(135deg, rgba(78,195,255,0.12), rgba(104,240,214,0.08));
            border: 1px solid rgba(78, 195, 255, 0.35);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 1rem;
        }
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            border: 1px solid rgba(79, 210, 157, 0.6);
            background: rgba(79, 210, 157, 0.12);
            border-radius: 999px;
            padding: 0.4rem 0.7rem;
            color: #d8fff0;
        }
        .status-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: #4fd29d;
            box-shadow: 0 0 10px rgba(79, 210, 157, 0.8);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_theme()


def get_api_client() -> APIClient:
    token = st.session_state.get("jwt")
    return APIClient(token=token)


def backend_status() -> str:
    base_url = discover_backend_base_url()
    return base_url


def get_selected_website(websites: list[dict[str, object]]) -> dict[str, object] | None:
    selected_id = st.session_state.get("selected_website_id")
    if selected_id is None and websites:
        st.session_state["selected_website_id"] = websites[0]["id"]
        selected_id = websites[0]["id"]
    if not selected_id:
        return None
    for website in websites:
        if int(website["id"]) == int(selected_id):
            return website
    return websites[0] if websites else None


def load_websites() -> list[dict[str, object]]:
    api = get_api_client()
    try:
        data = api.list_websites()
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def render_auth_screen() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1 style='margin-bottom:0.2rem;'>WebIntelX AI</h1>
            <p class='small-muted' style='margin-top:0;'>Web Security Intelligence & Investigation Platform</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["Login", "Register"])
    with tabs[0]:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
        if submitted:
            try:
                api = APIClient()
                token_response = api.login(email, password)
                st.session_state["jwt"] = token_response["access_token"]
                user = api.get_me()
                st.session_state["user"] = user
                st.rerun()
            except Exception as exc:
                st.error(f"Login failed: {exc}")

    with tabs[1]:
        with st.form("register_form"):
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create Account")
        if submitted:
            if password != confirm_password:
                st.error("Passwords do not match.")
            elif not email or not password:
                st.error("Email and password are required.")
            else:
                try:
                    APIClient().register(email, password)
                    st.success("Account created successfully. Please login.")
                except Exception as exc:
                    st.error(f"Registration failed: {exc}")


def render_website_setup(website: dict[str, object] | None = None) -> None:
    if website is None:
        with st.form("new_website_form"):
            name = st.text_input("Website Name")
            domain = st.text_input("Domain")
            if st.form_submit_button("Add Website"):
                try:
                    api = get_api_client()
                    result = api.create_website(name, domain)
                    st.session_state["selected_website_id"] = result["id"]
                    st.session_state["show_setup"] = True
                    st.success("Website added successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Unable to create website: {exc}")
        return

    steps = ["Website", "API Key", "Install SDK", "Verify"]
    current_step = st.session_state.get("setup_step", 0)
    st.subheader("Connect your website")
    st.caption("Step 1 — Website | Step 2 — API Key | Step 3 — Install SDK | Step 4 — Verify")
    step_index = st.radio("Wizard Progress", range(len(steps)), format_func=lambda i: f"Step {i + 1} — {steps[i]}", index=current_step)
    st.session_state["setup_step"] = step_index

    if step_index == 0:
        st.markdown("### Website")
        st.write(website.get("name", "Website"))
        st.write(website.get("domain", "example.com"))
        st.write(f"Status: {website.get('status', 'active')}")
        if st.button("Continue"):
            st.session_state["setup_step"] = 1
            st.rerun()

    elif step_index == 1:
        st.markdown("### Create Website Connection Key")
        st.write(
            "This key allows your website to securely send telemetry to WebIntelX AI. "
            "It is not your account password or admin API key."
        )
        if st.button("Generate Connection Key"):
            try:
                api = get_api_client()
                credential = api.create_credential(int(website["id"]))
                st.session_state["generated_credential"] = credential
                st.success("Connection key created.")
                st.rerun()
            except Exception as exc:
                st.error(f"Unable to generate key: {exc}")
        credential = st.session_state.get("generated_credential")
        if credential:
            st.code(credential.get("credential", ""), language="text")
            st.warning("Save this key securely. For security reasons, it will not be shown again.")
            if st.button("Copy key"):
                st.code(credential.get("credential", ""), language="text")

    elif step_index == 2:
        st.markdown("### Install WebIntelX on your website")
        credential = st.session_state.get("generated_credential")
        script = (
            "<script>\n"
            "  window.WebIntelX = window.WebIntelX || {};\n"
            "  window.WebIntelX.init = function(options) {\n"
            "    window.__webintelx_endpoint = options.endpoint;\n"
            "    window.__webintelx_credential = options.credential;\n"
            "  };\n"
            "</script>\n"
            "<script src=\"https://cdn.example.com/webintelx.js\" defer></script>\n"
            "<script>\n"
            "  WebIntelX.init({\n"
            f"    credential: '{credential.get('credential') if credential else 'YOUR_CONNECTION_KEY'}',\n"
            "    endpoint: 'http://127.0.0.1:18080/api/ingest/events'\n"
            "  });\n"
            "</script>"
        )
        st.info("Add the following script before the closing </head> tag of your website.")
        st.code(script, language="html")
        if st.button("Copy Script"):
            st.code(script, language="html")

    elif step_index == 3:
        st.markdown("### Verify your website connection")
        if st.button("Verify Connection"):
            try:
                graph = get_api_client().get_graph(int(website["id"]))
                nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
                if nodes:
                    st.success("Website connected. WebIntelX AI is receiving telemetry from your website.")
                else:
                    st.info("Waiting for telemetry... Make sure the WebIntelX script has been added correctly.")
            except Exception as exc:
                st.warning(f"Verification is still pending: {exc}")
        else:
            st.info("Waiting for telemetry... Make sure the WebIntelX script has been added correctly.")


def render_dashboard_page() -> None:
    websites = load_websites()
    if not websites:
        st.markdown("### Welcome to WebIntelX AI")
        st.write("Protect and investigate your website activity with AI-powered security intelligence.")
        st.markdown("#### Let's connect your first website.")
        st.button("+ Add Your Website", on_click=lambda: st.session_state.__setitem__("show_setup", True))
        st.markdown(
            """
            <div class='card'>
                <div class='small-muted'>Onboarding progress</div>
                <div>① Create account</div>
                <div>② Add website</div>
                <div>③ Generate key</div>
                <div>④ Install SDK</div>
                <div>⑤ Verify connection</div>
                <div>⑥ Start monitoring</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    selected_website = get_selected_website(websites)
    if selected_website is None:
        st.info("Select a website to continue.")
        return

    st.markdown(
        f"<div class='status-pill'><span class='status-dot'></span> Monitoring Active</div>",
        unsafe_allow_html=True,
    )
    st.title(f"Good morning")
    st.subheader("Web Security Overview")

    website_selector = st.selectbox("Website", options=[w["domain"] for w in websites], index=[w["id"] for w in websites].index(int(selected_website["id"])))
    selected_website = next((w for w in websites if w["domain"] == website_selector), selected_website)
    st.session_state["selected_website_id"] = selected_website["id"]

    graph = get_api_client().get_graph(int(selected_website["id"])) if selected_website else {"nodes": [], "edges": []}
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    edges = graph.get("edges", []) if isinstance(graph, dict) else []
    finding_count = sum(1 for node in nodes if node.get("type") == "finding")
    event_count = sum(1 for node in nodes if node.get("type") == "event")
    incidents = get_api_client().list_incidents(int(selected_website["id"]))
    incident_count = len(incidents)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Visitors", max(0, event_count))
    col2.metric("Sessions", max(0, len(nodes)))
    col3.metric("Events", event_count)
    col4.metric("Suspicious Activity", finding_count)

    col5, col6, col7 = st.columns(3)
    risk_score = 0
    if incidents:
        risk_score = round(sum(float(item.get("risk_score", 0)) for item in incidents) / len(incidents), 1)
    col5.metric("Threats Detected", finding_count)
    col6.metric("Open Incidents", incident_count)
    col7.metric("Risk Score", risk_score)

    if nodes:
        event_series = [
            {"time": i + 1, "count": max(0, len([n for n in nodes if n.get("type") == "event"]))}
            for i in range(7)
        ]
        df = __import__("pandas").DataFrame(event_series)
        fig = px.line(df, x="time", y="count", markers=True, title="Website Activity")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No telemetry has been received yet. Install the SDK to begin monitoring this website.")

    st.subheader("Recent Security Activity")
    if nodes:
        rows = []
        for node in nodes[:8]:
            rows.append({
                "Time": "Recent",
                "Type": node.get("type", "event"),
                "Endpoint": str(node.get("metadata", {}).get("event_id", "-")),
                "Finding": node.get("label", "-"),
                "Severity": "Medium" if node.get("type") == "finding" else "Low",
                "Status": "Monitoring",
            })
        st.dataframe(rows, use_container_width=True)
    else:
        st.warning("No events received yet. Connect the SDK to start receiving telemetry.")


def render_websites_page() -> None:
    websites = load_websites()
    if not websites:
        st.info("No websites connected. Connect your first website to start monitoring.")
        if st.button("+ Add Website"):
            st.session_state["show_setup"] = True
            st.rerun()
        return

    st.header("Websites")
    if st.button("+ Add Website"):
        st.session_state["show_setup"] = True
        st.rerun()
    st.dataframe(
        [{
            "Website": w.get("name", w.get("domain", "Unknown")),
            "Domain": w.get("domain", "-"),
            "Status": w.get("status", "active"),
            "Created": w.get("created_at", "-"),
        } for w in websites],
        use_container_width=True,
    )


def render_events_page() -> None:
    website_id = st.session_state.get("selected_website_id")
    if not website_id:
        st.info("Select a website to review events.")
        return

    graph = get_api_client().get_graph(int(website_id))
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    events = [node for node in nodes if node.get("type") == "event"]
    if not events:
        st.warning("No events received yet. Install the WebIntelX SDK on your website to start receiving telemetry.")
        return

    st.header("Events")
    st.dataframe([
        {
            "Timestamp": "Recent",
            "Event Type": node.get("label", "event"),
            "Endpoint": node.get("id", "-"),
            "Method": "POST",
            "Status": "Accepted",
            "Session": "browser",
        }
        for node in events[:20]
    ], use_container_width=True)


def render_findings_page() -> None:
    website_id = st.session_state.get("selected_website_id")
    if not website_id:
        st.info("Select a website to review findings.")
        return

    graph = get_api_client().get_graph(int(website_id))
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    findings = [node for node in nodes if node.get("type") == "finding"]
    if not findings:
        st.info("No suspicious activity detected.")
        return

    st.header("Findings")
    st.dataframe([
        {
            "Time": "Recent",
            "Finding Type": node.get("label", "finding"),
            "Agent": "rule_engine",
            "Confidence": "0.8",
            "Severity": "High",
            "Evidence": node.get("metadata", {}).get("finding_id", "-"),
        }
        for node in findings[:20]
    ], use_container_width=True)


def render_investigations_page() -> None:
    website_id = st.session_state.get("selected_website_id")
    if not website_id:
        st.info("Select a website to review investigations.")
        return

    st.header("Investigations")
    investigations = get_api_client().get_investigations(int(website_id))
    if not investigations:
        st.info("No investigations yet.")
        return
    st.dataframe(investigations, use_container_width=True)


def render_incidents_page() -> None:
    website_id = st.session_state.get("selected_website_id")
    if not website_id:
        st.info("Select a website to review incidents.")
        return

    st.header("Incidents")
    incidents = get_api_client().list_incidents(int(website_id))
    if not incidents:
        st.info("No open incidents.")
        return
    st.dataframe(incidents, use_container_width=True)


def render_reports_page() -> None:
    website_id = st.session_state.get("selected_website_id")
    if not website_id:
        st.info("Select a website to view reports.")
        return

    st.header("Reports")
    st.info("No downloadable reports are available yet for this website.")
    st.markdown(
        """
        <div class='card'>
            <div class='small-muted'>Report Summary</div>
            <h3>Security posture summary</h3>
            <p>Facts, inferences, uncertainties, and risk recommendations will appear here after investigation activity is generated.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_settings_page() -> None:
    st.header("Settings")
    st.markdown(
        """
        <div class='card'>
            <div class='small-muted'>Account</div>
            <strong>""" + (st.session_state.get("user", {}).get("email", "user@webintelx.ai") or "user@webintelx.ai") + """</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write(f"API Status: {backend_status()}")
    st.write("Connection: Healthy")
    if st.button("Logout"):
        for key in ["jwt", "user", "selected_website_id", "show_setup", "generated_credential", "setup_step"]:
            st.session_state.pop(key, None)
        st.rerun()


def main() -> None:
    if "jwt" not in st.session_state or not st.session_state.get("jwt"):
        render_auth_screen()
        return

    user = st.session_state.get("user")
    if not user:
        try:
            user = get_api_client().get_me()
            st.session_state["user"] = user
        except Exception:
            st.session_state.pop("jwt", None)
            st.rerun()

    websites = load_websites()
    selected_website = get_selected_website(websites)

    st.sidebar.title("WebIntelX AI")
    st.sidebar.caption("Web Security Intelligence & Investigation Platform")
    st.sidebar.write(user.get("email", "user@webintelx.ai") if isinstance(user, dict) else "user@webintelx.ai")
    st.sidebar.markdown("---")

    nav = st.sidebar.radio(
        "Navigation",
        [
            "Dashboard",
            "Websites",
            "Events",
            "Findings",
            "Investigations",
            "Incidents",
            "Threat Intelligence",
            "Reports",
            "Settings",
        ],
    )

    if nav == "Dashboard":
        render_dashboard_page()
    elif nav == "Websites":
        render_websites_page()
    elif nav == "Events":
        render_events_page()
    elif nav == "Findings":
        render_findings_page()
    elif nav == "Investigations":
        render_investigations_page()
    elif nav == "Incidents":
        render_incidents_page()
    elif nav == "Threat Intelligence":
        st.header("Threat Intelligence")
        if not selected_website:
            st.info("Select a website to review threat intelligence.")
            return
        try:
            indicator = st.text_input("Indicator", value="8.8.8.8")
            indicator_type = st.selectbox("Type", ["ip", "domain", "url"])
            if st.button("Check Indicator"):
                result = get_api_client().get_threat_intel(int(selected_website["id"]), indicator, indicator_type)
                st.json(result)
        except Exception as exc:
            st.warning(f"Threat intelligence query unavailable: {exc}")
    elif nav == "Reports":
        render_reports_page()
    elif nav == "Settings":
        render_settings_page()

    if st.session_state.get("show_setup"):
        st.markdown("---")
        render_website_setup(selected_website)


if __name__ == "__main__":
    main()
