"""
Apex Banking — Customer Intelligence Assistant
Streamlit app powered by Databricks Genie Conversation API
"""
import time
import streamlit as st
from databricks.sdk import WorkspaceClient
import pandas as pd

# ── Page config — must be first Streamlit call ───────────────────────────────
st.set_page_config(
    page_title="Apex Banking — Customer Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Config ────────────────────────────────────────────────────────────────────
SPACE_ID = "01f123dcf761101b8b7b2398059e6c18"

PRESET_QUESTIONS = [
    "Which Premium customers are at highest churn risk right now?",
    "What is our retention policy for Premium customers with ATM fee complaints?",
    "Show me the AI customer brief for our top 5 at-risk customers",
    "Which segment has the highest average churn score?",
    "What is the total revenue at risk from high-risk customers?",
    "How many Premium customers are HIGH risk vs LOW risk?",
    "What does our complaint handling policy say about unauthorized transactions?",
]

# ── Databricks SDK client (uses auto-injected SP credentials in app runtime) ──
@st.cache_resource
def get_client():
    return WorkspaceClient()

# ── Genie API helpers ─────────────────────────────────────────────────────────

def start_conversation(question: str) -> dict:
    """Start a new Genie conversation with a question."""
    w = get_client()
    return w.api_client.do(
        "POST",
        f"/api/2.0/genie/spaces/{SPACE_ID}/start-conversation",
        body={"content": question},
    )

def send_message(conversation_id: str, question: str) -> dict:
    """Send a follow-up message in an existing conversation."""
    w = get_client()
    return w.api_client.do(
        "POST",
        f"/api/2.0/genie/spaces/{SPACE_ID}/conversations/{conversation_id}/messages",
        body={"content": question},
    )

def poll_message(conversation_id: str, message_id: str, timeout: int = 60) -> dict:
    """Poll until message is COMPLETED or FAILED."""
    w = get_client()
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = w.api_client.do(
            "GET",
            f"/api/2.0/genie/spaces/{SPACE_ID}/conversations/{conversation_id}/messages/{message_id}",
        )
        status = msg.get("status", "RUNNING")
        if status in ("COMPLETED", "FAILED", "CANCELLED"):
            return msg
        time.sleep(2)
    return {"status": "TIMEOUT"}

def get_query_result(conversation_id: str, message_id: str) -> dict | None:
    """Fetch tabular query result for a completed message."""
    w = get_client()
    try:
        return w.api_client.do(
            "GET",
            f"/api/2.0/genie/spaces/{SPACE_ID}/conversations/{conversation_id}/messages/{message_id}/query-result",
        )
    except Exception:
        return None

def ask_genie(question: str) -> dict:
    """
    Full ask-and-poll flow. Returns:
      {status, sql, text, dataframe, error}
    """
    # Start or continue conversation
    conv_id = st.session_state.get("conversation_id")
    try:
        if conv_id:
            resp = send_message(conv_id, question)
        else:
            resp = start_conversation(question)
            st.session_state["conversation_id"] = resp.get("conversation_id")

        message_id = resp.get("message_id") or resp.get("id")
        conv_id    = resp.get("conversation_id") or st.session_state["conversation_id"]

        # Poll
        msg = poll_message(conv_id, message_id)
        status = msg.get("status", "UNKNOWN")

        if status == "TIMEOUT":
            return {"status": "TIMEOUT", "error": "Query timed out. Try a simpler question."}

        if status == "FAILED":
            return {"status": "FAILED", "error": msg.get("error", "Genie could not answer this question.")}

        # Extract SQL and text response
        sql_text  = None
        text_resp = None
        attachments = msg.get("attachments") or []
        for a in attachments:
            if a.get("type") == "query" or "query" in a:
                sql_text = (a.get("query") or {}).get("query")
            if a.get("type") == "text" or "text" in a:
                text_resp = (a.get("text") or {}).get("content")

        # Try to get tabular result
        df = None
        result = get_query_result(conv_id, message_id)
        if result:
            sr = result.get("statement_response") or result
            manifest = sr.get("manifest", {})
            data     = sr.get("result", {})
            columns  = [c["name"] for c in manifest.get("schema", {}).get("columns", [])]
            rows     = data.get("data_array", [])
            if columns and rows:
                df = pd.DataFrame(rows, columns=columns)

        return {"status": "OK", "sql": sql_text, "text": text_resp, "dataframe": df}

    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.chat-user   { background:#1e3a5f; padding:12px 16px; border-radius:12px; margin:8px 0; color:white; }
.chat-bot    { background:#f0f4f8; padding:12px 16px; border-radius:12px; margin:8px 0; color:#1a1a2e; }
.sql-block   { background:#0d1117; padding:10px; border-radius:8px; font-size:12px; color:#a0d0ff; }
.badge-high  { background:#dc2626; color:white; padding:2px 8px; border-radius:4px; font-size:12px; }
.badge-med   { background:#f59e0b; color:white; padding:2px 8px; border-radius:4px; font-size:12px; }
.badge-low   { background:#16a34a; color:white; padding:2px 8px; border-radius:4px; font-size:12px; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "messages"         not in st.session_state: st.session_state["messages"]         = []
if "conversation_id"  not in st.session_state: st.session_state["conversation_id"]  = None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏦 Apex Banking")
    st.markdown("**Customer Intelligence Assistant**")
    st.markdown("---")
    st.markdown("### 💡 Try these questions")
    for q in PRESET_QUESTIONS:
        if st.button(q, key=f"preset_{q[:30]}", use_container_width=True):
            st.session_state["pending_question"] = q

    st.markdown("---")
    if st.button("🔄 New conversation", use_container_width=True):
        st.session_state["messages"]        = []
        st.session_state["conversation_id"] = None
        st.rerun()

    st.markdown("---")
    st.caption("Powered by Databricks Genie · finserv.banking")
    st.caption(f"Space: `{SPACE_ID[:16]}...`")

# ── Main header ───────────────────────────────────────────────────────────────
st.markdown("# 🏦 Apex Banking — Customer Intelligence")
st.markdown(
    "Ask anything about **churn risk**, **revenue exposure**, **at-risk customers**, "
    "or **internal policy guidance** in plain English."
)
st.markdown("---")

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-user">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-bot">', unsafe_allow_html=True)
        if msg.get("text"):
            st.markdown(f"🤖 {msg['text']}")
        if msg.get("dataframe") is not None:
            df = msg["dataframe"]
            # Style churn_risk_tier / churn_tier / ml_prob_pct columns if present
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"↑ {len(df):,} rows")
        if msg.get("sql"):
            with st.expander("📋 View generated SQL"):
                st.code(msg["sql"], language="sql")
        if msg.get("error"):
            st.error(msg["error"])
        st.markdown("</div>", unsafe_allow_html=True)

# ── Input ─────────────────────────────────────────────────────────────────────
question = st.chat_input("Ask a question about your customers, risk, or policy...")

# Handle preset button click
if "pending_question" in st.session_state:
    question = st.session_state.pop("pending_question")

if question:
    # Add user message
    st.session_state["messages"].append({"role": "user", "content": question})
    st.markdown(f'<div class="chat-user">🧑 {question}</div>', unsafe_allow_html=True)

    # Query Genie
    with st.spinner("Genie is thinking..."):
        result = ask_genie(question)

    # Build response message
    bot_msg = {
        "role":      "assistant",
        "content":   question,
        "text":      result.get("text"),
        "sql":       result.get("sql"),
        "dataframe": result.get("dataframe"),
        "error":     result.get("error") if result["status"] != "OK" else None,
    }
    st.session_state["messages"].append(bot_msg)
    st.rerun()
