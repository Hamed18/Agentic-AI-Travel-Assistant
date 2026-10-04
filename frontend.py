import uuid
import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from graph import app

st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide"
)

@st.cache_data
def create_pdf(text):
    import markdown
    from fpdf import FPDF
    safe_text = text.encode('latin-1', 'replace').decode('latin-1')
    html = markdown.markdown(safe_text)
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.write_html(html)
    except Exception:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", size=12)
        pdf.multi_cell(0, 10, safe_text)
    return bytes(pdf.output())

# --- Initialise session state ---
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"user_{uuid.uuid4().hex[:8]}"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "all_threads" not in st.session_state:
    # Store list of {thread_id, title} for the sidebar history
    st.session_state.all_threads = []

# --- ChatGPT-style Sidebar ---
with st.sidebar:
    st.markdown(
        """
        <style>
        /* ── Sidebar dark background ── */
        [data-testid="stSidebar"] {
            background-color: #171717 !important;
        }
        div[data-testid="stSidebarContent"] {
            padding-top: 1rem;
        }

        /* ── All text inside sidebar ── */
        [data-testid="stSidebar"] * {
            color: #ececec !important;
        }

        /* ── Primary button (New Chat) ── */
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background-color: #2563eb !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 0.5rem 1rem !important;
        }
        [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
            background-color: #1d4ed8 !important;
        }

        /* ── Secondary / history buttons ── */
        [data-testid="stSidebar"] .stButton > button {
            background-color: #2a2a2a !important;
            color: #ececec !important;
            border: 1px solid #3a3a3a !important;
            border-radius: 8px !important;
            text-align: left !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background-color: #3a3a3a !important;
            border-color: #555 !important;
        }

        /* ── Divider ── */
        [data-testid="stSidebar"] hr {
            border-color: #333 !important;
        }

        /* ── Input box ── */
        [data-testid="stSidebar"] input {
            background-color: #2a2a2a !important;
            color: #ececec !important;
            border: 1px solid #444 !important;
        }

        /* ── Expander ── */
        [data-testid="stSidebar"] .streamlit-expanderHeader {
            background-color: #222 !important;
            color: #ececec !important;
        }

        /* ── Footer ── */
        .main-footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #0e1117;
            border-top: 1px solid #2a2a2a;
            text-align: center;
            padding: 0.5rem;
            font-size: 0.82rem;
            color: #888;
            z-index: 999;
        }
        .main-footer a {
            color: #60a5fa;
            text-decoration: none;
            font-weight: 600;
        }
        .main-footer a:hover { text-decoration: underline; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # App logo / title row
    st.markdown("## ✈️ AI Travel Planner")
    st.divider()

    # ── New Chat button ──
    if st.button("✏️  New Chat", use_container_width=True, type="primary"):
        new_tid = f"user_{uuid.uuid4().hex[:8]}"
        # Save current thread to history if it has messages
        if st.session_state.chat_history:
            first_user_msg = next(
                (m["content"] for m in st.session_state.chat_history if m["role"] == "user"),
                st.session_state.thread_id,
            )
            title = first_user_msg[:40] + "..." if len(first_user_msg) > 40 else first_user_msg
            st.session_state.all_threads.insert(0, {
                "thread_id": st.session_state.thread_id,
                "title": title,
            })
        st.session_state.thread_id = new_tid
        st.session_state.chat_history = []
        st.session_state.pop("waiting_for_approval", None)
        st.session_state.pop("latest_result", None)
        st.rerun()

    # ── Past Conversations list ──
    if st.session_state.all_threads:
        st.markdown("#### 🕘 Recent Chats")
        for i, thread in enumerate(st.session_state.all_threads):
            is_active = thread["thread_id"] == st.session_state.thread_id
            label = ("▶ " if is_active else "") + thread["title"]
            if st.button(label, key=f"thread_{i}", use_container_width=True):
                # Switching threads resets chat history display
                # (full restore would need DB query — out of scope here)
                st.session_state.thread_id = thread["thread_id"]
                st.session_state.chat_history = []
                st.session_state.pop("waiting_for_approval", None)
                st.rerun()

    st.divider()

    # ── User ID at the bottom ──
    with st.expander("⚙️ Settings"):
        user_id = st.text_input("User ID", value="demo_user")
        st.caption(f"Thread: `{st.session_state.thread_id}`")
    
    st.markdown(
        "<div style='font-size:0.72rem;color:#555;margin-top:0.5rem;'>Powered by LangGraph + Qwen</div>",
        unsafe_allow_html=True,
    )

# user_id fallback if settings expander not opened yet
if "user_id" not in dir():
    user_id = "demo_user"

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# ── Main area header ──
st.markdown("## 🌍 Real-World Multi-Agent Travel Planner")
st.caption("Ask me to plan any trip — flights, hotels, weather, budget & more.")

# ── Global footer ──
st.markdown(
    """
    <div class="main-footer">
        Developed by&nbsp;<a href="https://www.linkedin.com/in/devhamed/" target="_blank">Hamed Hasan</a>
        &nbsp;·&nbsp; Powered by LangGraph, Qwen &amp; MCP
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Display Chat History ---
for msg in st.session_state.get("chat_history", []):
    with st.chat_message(msg["role"]):
        if msg["type"] == "text":
            st.markdown(msg["content"])
        elif msg["type"] == "final_plan":
            st.markdown(msg["content"])
            pdf_bytes = create_pdf(msg["content"])
            st.download_button(
                label="📥 Download Plan as PDF",
                data=pdf_bytes,
                file_name="Final_Travel_Plan.pdf",
                mime="application/pdf",
                key=f"download_{id(msg)}"
            )
        elif msg["type"] == "draft_plan":
            result = msg["content"]
            if result.get("is_valid") is False:
                st.markdown(result.get("final_response", ""))
            else:
                with st.expander("🤖 Supervisor's Agent Routing Plan"):
                    st.write(f"**Reasoning:** {result.get('supervisor_reasoning', '')}")
                    agents = result.get('selected_agents', [])
                    if agents:
                        st.write(f"**Specialists Selected:** {', '.join(agents)}")
                    else:
                        st.write("**Specialists Selected:** None")

                st.subheader("📝 Draft Itinerary")
                if "__interrupt__" in result:
                    draft = result["__interrupt__"][0].value.get("draft_itinerary", "")
                else:
                    draft = result.get("itinerary", "")
                st.markdown(draft)

# --- Handle Human Approval ---
if st.session_state.get("waiting_for_approval"):
    with st.chat_message("assistant"):
        st.subheader("Human Approval Required")
        approved = st.radio("Approve this draft?", ["Yes", "No, revise it"], horizontal=True)
        feedback = st.text_area("Feedback", disabled=approved == "Yes")

        if st.button("Submit Approval"):
            with st.spinner("Creating final response..."):
                final_result = app.invoke(
                    Command(
                        resume={
                            "approved": approved == "Yes",
                            "feedback": feedback,
                        }
                    ),
                    config=config,
                )
            
            st.session_state.waiting_for_approval = False
            
            # Store final response in history
            if final_result and final_result.get("final_response"):
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "type": "final_plan",
                    "content": f"**Final Travel Plan:**\n\n{final_result['final_response']}"
                })
            st.rerun()

# --- Chat Input Box (Fixed at Bottom) ---
# Disable input if waiting for approval to avoid branching issues
prompt = st.chat_input("Plan a 7-day Japan trip under Rs. 2 lakh...", disabled=st.session_state.get("waiting_for_approval", False))

if prompt:
    # Add user message to history and show it
    st.session_state.chat_history.append({"role": "user", "type": "text", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agents are planning..."):
            result = app.invoke(
                {
                    "messages": [HumanMessage(content=prompt)],
                    "user_id": user_id,
                    "user_query": prompt,
                    "flight_results": "",
                    "hotel_results": "",
                    "weather_results": "",
                    "budget_results": "",
                    "itinerary": "",
                    "final_response": "",
                    "llm_calls": 0,
                },
                config=config,
            )

        # Save result to chat history for display
        st.session_state.chat_history.append({"role": "assistant", "type": "draft_plan", "content": result})
        
        # Check if an interrupt (human approval) was hit
        if "__interrupt__" in result:
            st.session_state.waiting_for_approval = True
            
        st.rerun()
