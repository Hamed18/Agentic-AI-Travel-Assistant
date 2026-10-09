import uuid
import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from graph import app

st.set_page_config(
    page_title="MULTI-AGENT Personalized TRAVEL Assistant",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
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
    st.session_state.all_threads = []

# --- Premium Dark UI CSS (theme-agnostic overrides) ---
st.markdown(
    """
    <style>
    /* ══════════════════════════════════════════════
       0. FORCE DARK THEME ON EVERY STREAMLIT ELEMENT
       ══════════════════════════════════════════════ */
    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"],
    .main, .block-container {
        background-color: #090d16 !important;
        color: #e2e8f0 !important;
    }
    .stApp > header,
    [data-testid="stHeader"] { background: transparent !important; }

    /* ══════════════════════════════════════════════
       1. GLOBAL LAYOUT
       ══════════════════════════════════════════════ */
    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 9rem !important;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
    }

    /* ══════════════════════════════════════════════
       2. HERO SECTION
       ══════════════════════════════════════════════ */
    .hero-container {
        background: linear-gradient(160deg, rgba(16,24,48,0.92) 0%, rgba(9,13,22,0.97) 100%),
                    url('https://images.unsplash.com/photo-1436491865332-7a61a109cc05?q=80&w=1600&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        border-radius: 20px;
        padding: 3rem 2rem 2.5rem 2rem;
        text-align: center;
        margin-bottom: 2rem;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 20px 50px -10px rgba(0,0,0,0.8);
    }
    .hero-badge {
        display: inline-block;
        background: rgba(37,99,235,0.25);
        color: #93c5fd;
        border: 1px solid rgba(96,165,250,0.4);
        padding: 0.45rem 1.25rem;
        border-radius: 9999px;
        font-size: 0.88rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        margin-bottom: 1.1rem;
        text-transform: uppercase;
    }
    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        color: #f8fafc;
        margin: 0 0 0.85rem 0;
        line-height: 1.2;
        letter-spacing: -0.02em;
    }
    .hero-title span { color: #60a5fa; }
    .hero-subtitle {
        font-size: 1.08rem;
        color: #94a3b8;
        max-width: 760px;
        margin: 0 auto;
        line-height: 1.7;
        font-weight: 400;
    }

    /* ══════════════════════════════════════════════
       3. SECTION LABELS
       ══════════════════════════════════════════════ */
    .section-label {
        font-size: 0.82rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.1em !important;
        color: #60a5fa !important;
        margin-bottom: 0.9rem !important;
        text-transform: uppercase !important;
        display: flex !important;
        align-items: center !important;
        gap: 0.45rem !important;
    }

    /* ══════════════════════════════════════════════
       4. ALL MAIN-AREA BUTTONS — UNIVERSAL DARK FIX
          This is the KEY selector that actually works.
          Targets every stButton in the main content,
          excluding the sidebar.
       ══════════════════════════════════════════════ */
    section.main .stButton > button,
    [data-testid="stMain"] .stButton > button,
    .block-container .stButton > button {
        background-color: #1a2540 !important;
        color: #e2e8f0 !important;
        border: 1px solid #2d3f5e !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 0.93rem !important;
        transition: all 0.22s ease !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.35) !important;
    }
    section.main .stButton > button:hover,
    [data-testid="stMain"] .stButton > button:hover,
    .block-container .stButton > button:hover {
        background-color: #1e3a5f !important;
        color: #93c5fd !important;
        border-color: #3b82f6 !important;
        box-shadow: 0 6px 20px rgba(59,130,246,0.25) !important;
        transform: translateY(-2px) !important;
    }
    section.main .stButton > button:focus,
    section.main .stButton > button:active,
    [data-testid="stMain"] .stButton > button:focus,
    [data-testid="stMain"] .stButton > button:active {
        background-color: #1e3a5f !important;
        color: #93c5fd !important;
        border-color: #3b82f6 !important;
        outline: none !important;
        box-shadow: 0 6px 20px rgba(59,130,246,0.25) !important;
    }

    /* ══════════════════════════════════════════════
       5. DESTINATION CARD IMAGES
          Lock uniform image height across all 5 cards
       ══════════════════════════════════════════════ */
    div[data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
        gap: 0.6rem !important;
    }
    div[data-testid="column"] {
        display: flex !important;
        flex-direction: column !important;
        background: #111827 !important;
        border-radius: 16px !important;
        overflow: hidden !important;
        border: 1px solid #1e293b !important;
        transition: box-shadow 0.25s ease, transform 0.25s ease !important;
        min-width: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="column"]:hover {
        box-shadow: 0 8px 28px rgba(59,130,246,0.22) !important;
        transform: translateY(-3px) !important;
    }
    div[data-testid="column"] div[data-testid="stImage"] {
        height: 130px !important;
        max-height: 130px !important;
        min-height: 130px !important;
        overflow: hidden !important;
        border-radius: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        flex-shrink: 0 !important;
    }
    div[data-testid="column"] div[data-testid="stImage"] img {
        height: 130px !important;
        max-height: 130px !important;
        min-height: 130px !important;
        width: 100% !important;
        object-fit: cover !important;
        object-position: center !important;
        border-radius: 0 !important;
        display: block !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="column"] .stButton {
        margin: 0 !important;
        padding: 0 !important;
        flex: 1 !important;
    }
    /* Card label buttons - seamless bottom of card */
    div[data-testid="column"] .stButton > button {
        border-radius: 0 0 14px 14px !important;
        border-top: 1px solid #1e293b !important;
        border-left: none !important;
        border-right: none !important;
        border-bottom: none !important;
        background-color: #111827 !important;
        height: 44px !important;
        min-height: 44px !important;
        max-height: 44px !important;
        width: 100% !important;
        font-weight: 700 !important;
        transform: none !important;
    }
    div[data-testid="column"] .stButton > button:hover {
        background-color: #1e3a5f !important;
        transform: none !important;
        border-color: #3b82f6 !important;
    }

    /* ══════════════════════════════════════════════
       6. CHAT INPUT
       ══════════════════════════════════════════════ */
    div[data-testid="stBottom"] {
        bottom: 28px !important;
        background: transparent !important;
    }
    div[data-testid="stChatInput"],
    [data-testid="stChatInput"] {
        background-color: #0d1322 !important;
        border: 1px solid #334155 !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6) !important;
    }
    div[data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] textarea {
        background: transparent !important;
        color: #f1f5f9 !important;
        font-size: 0.98rem !important;
        caret-color: #60a5fa !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder {
        color: #475569 !important;
    }

    /* ══════════════════════════════════════════════
       7. FIXED BOTTOM FOOTER
       ══════════════════════════════════════════════ */
    .bottom-fixed-footer {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        height: 28px !important;
        line-height: 28px !important;
        background: #060911 !important;
        border-top: 1px solid #1e293b !important;
        text-align: center !important;
        font-size: 0.76rem !important;
        color: #64748b !important;
        z-index: 999999 !important;
    }
    .bottom-fixed-footer a {
        color: #60a5fa !important;
        text-decoration: none !important;
        font-weight: 600 !important;
    }
    .bottom-fixed-footer a:hover { text-decoration: underline !important; }

    /* ══════════════════════════════════════════════
       8. SIDEBAR
       ══════════════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background-color: #0b0f1a !important;
        border-right: 1px solid #1e293b !important;
    }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    /* Sidebar history buttons */
    [data-testid="stSidebar"] .stButton > button {
        background-color: #1e293b !important;
        color: #e2e8f0 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transform: none !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #1e3a5f !important;
        border-color: #3b82f6 !important;
        color: #93c5fd !important;
        transform: none !important;
    }
    /* Sidebar New Chat primary button */
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(37,99,235,0.4) !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
        box-shadow: 0 6px 18px rgba(37,99,235,0.5) !important;
        color: #ffffff !important;
    }

    /* ══════════════════════════════════════════════
       9. CHAT MESSAGES & EXPANDERS
       ══════════════════════════════════════════════ */
    [data-testid="stChatMessage"] {
        background: #111827 !important;
        border: 1px solid #1e293b !important;
        border-radius: 16px !important;
    }
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3,
    [data-testid="stChatMessage"] h4 { color: #e2e8f0 !important; }
    [data-testid="stExpander"] {
        background: #111827 !important;
        border: 1px solid #1e293b !important;
        border-radius: 12px !important;
    }

    /* ══════════════════════════════════════════════
       10. GENERAL TEXT & INPUT OVERRIDES
       ══════════════════════════════════════════════ */
    h1, h2, h3, h4, h5, h6 { color: #f1f5f9 !important; }
    p, li, label { color: #cbd5e1 !important; }
    .stMarkdown p { color: #cbd5e1 !important; }
    hr { border-color: #1e293b !important; }
    [data-testid="stRadio"] label { color: #cbd5e1 !important; }
    [data-testid="stTextArea"] textarea {
        background: #0d1322 !important;
        color: #e2e8f0 !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
    }
    [data-testid="stTextInput"] input {
        background: #0d1322 !important;
        color: #e2e8f0 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    /* Info/warning banners */
    [data-testid="stInfo"] {
        background: rgba(37,99,235,0.15) !important;
        border: 1px solid rgba(96,165,250,0.3) !important;
        color: #93c5fd !important;
        border-radius: 10px !important;
    }

    /* ══════════════════════════════════════════════
       11. RESPONSIVE
       ══════════════════════════════════════════════ */
    @media screen and (max-width: 900px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; padding-bottom: 8rem !important; }
        .hero-title { font-size: 1.9rem !important; }
        div[data-testid="column"] div[data-testid="stImage"],
        div[data-testid="column"] div[data-testid="stImage"] img {
            height: 100px !important; max-height: 100px !important; min-height: 100px !important;
        }
        div[data-testid="column"] .stButton > button { height: 38px !important; min-height: 38px !important; font-size: 0.82rem !important; }
    }
    @media screen and (max-width: 600px) {
        .hero-title { font-size: 1.5rem !important; }
        .hero-container { padding: 2rem 1rem 1.75rem 1rem !important; border-radius: 14px !important; }
        div[data-testid="column"] div[data-testid="stImage"],
        div[data-testid="column"] div[data-testid="stImage"] img {
            height: 85px !important; max-height: 85px !important; min-height: 85px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Sidebar Configuration ---
with st.sidebar:
    st.markdown("## ✈️ Travel Assistant")
    st.divider()

    # New Chat Button
    if st.button("✏️  New Chat", use_container_width=True, type="primary"):
        new_tid = f"user_{uuid.uuid4().hex[:8]}"
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
        st.session_state.pop("trigger_query", None)
        st.session_state.pop("waiting_for_approval", None)
        st.session_state.pop("latest_result", None)
        st.rerun()

    # Recent Chats List
    if st.session_state.all_threads:
        st.markdown("#### 🕘 Recent Chats")
        for i, thread in enumerate(st.session_state.all_threads):
            is_active = thread["thread_id"] == st.session_state.thread_id
            label = ("▶ " if is_active else "") + thread["title"]
            if st.button(label, key=f"thread_{i}", use_container_width=True):
                st.session_state.thread_id = thread["thread_id"]
                st.session_state.chat_history = []
                st.session_state.pop("waiting_for_approval", None)
                st.rerun()

    st.divider()

    with st.expander("⚙️ Settings"):
        user_id = st.text_input("User ID", value="demo_user")
        st.caption(f"Thread: `{st.session_state.thread_id}`")

    st.markdown(
        """
        <div style='font-size:0.75rem;color:#64748b;margin-top:0.8rem;line-height:1.4;'>
            Developed by <a href="https://www.linkedin.com/in/devhamed/" target="_blank" style="color:#60a5fa;text-decoration:none;font-weight:600;">Hamed Hasan</a><br>
            Powered by LangGraph + Qwen + MCP
        </div>
        """,
        unsafe_allow_html=True,
    )

if "user_id" not in dir():
    user_id = "demo_user"

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# --- Hero Section Banner ---
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-badge">✦ Multi-Agent AI System</div>
        <div class="hero-title">✈️ AI <span>Travel</span> Planner</div>
        <div class="hero-subtitle">
            Four specialized agents work together — searching flights, hotels, weather forecasts, and building a fully personalized itinerary just for you.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Popular Destinations Grid ---
st.markdown('<div class="section-label">🌟 Popular Destinations</div>', unsafe_allow_html=True)
dest_col1, dest_col2, dest_col3, dest_col4, dest_col5 = st.columns(5)

with dest_col1:
    st.image("https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?q=80&w=600&h=380&auto=format&fit=crop", use_container_width=True)
    if st.button("Tokyo", use_container_width=True, key="dest_tokyo"):
        st.session_state.trigger_query = "Plan a complete 7-day trip to Tokyo, Japan including flights, hotels, weather forecast, and sightseeing."
        st.rerun()

with dest_col2:
    st.image("https://images.unsplash.com/photo-1502602898657-3e91760cbb34?q=80&w=600&h=380&auto=format&fit=crop", use_container_width=True)
    if st.button("Paris", use_container_width=True, key="dest_paris"):
        st.session_state.trigger_query = "Plan a 5-day romantic Paris getaway with boutique hotels, cafe visits, and museum passes."
        st.rerun()

with dest_col3:
    st.image("https://images.unsplash.com/photo-1508009603885-50cf7c579365?q=80&w=600&h=380&auto=format&fit=crop", use_container_width=True)
    if st.button("Bangkok", use_container_width=True, key="dest_bangkok"):
        st.session_state.trigger_query = "Plan a 6-day cultural trip to Bangkok, Thailand focusing on street food, temples, and night markets."
        st.rerun()

with dest_col4:
    st.image("https://images.unsplash.com/photo-1552832230-c0197dd311b5?q=80&w=600&h=380&auto=format&fit=crop", use_container_width=True)
    if st.button("Rome", use_container_width=True, key="dest_rome"):
        st.session_state.trigger_query = "Plan a 5-day historical trip to Rome, Italy with central hotel stays, weather, and guided tours."
        st.rerun()

with dest_col5:
    st.image("https://images.unsplash.com/photo-1512453979798-5ea266f8880c?q=80&w=600&h=380&auto=format&fit=crop", use_container_width=True)
    if st.button("Dubai", use_container_width=True, key="dest_dubai"):
        st.session_state.trigger_query = "Plan a 4-day weekend trip to Dubai, UAE including desert safari and skyline hotels."
        st.rerun()


# --- Describe Your Trip (Quick Prompt Starter Buttons) ---
st.markdown('<div class="section-label" style="margin-top:1.5rem;">🗺️ Describe Your Trip</div>', unsafe_allow_html=True)
q_col1, q_col2, q_col3, q_col4 = st.columns(4)

with q_col1:
    if st.button("7-day Japan trip", use_container_width=True, key="start_japan"):
        st.session_state.trigger_query = "Plan a 7-day Japan trip with hotels, weather forecast, and no overnight flights."
        st.rerun()

with q_col2:
    if st.button("Paris trip for 5 days", use_container_width=True, key="start_paris"):
        st.session_state.trigger_query = "Plan a 5-day Paris trip with central hotels, museums, and weather forecast."
        st.rerun()

with q_col3:
    if st.button("Dubai weekend trip", use_container_width=True, key="start_dubai"):
        st.session_state.trigger_query = "Plan a 3-day weekend trip to Dubai with flights, city attractions, and weather."
        st.rerun()

with q_col4:
    if st.button("Bali backpacking 10 days", use_container_width=True, key="start_bali"):
        st.session_state.trigger_query = "Plan a 10-day Bali backpacking trip focusing on budget villas, beaches, and weather."
        st.rerun()


# --- Display Chat / Results History (Arrives on Top of the Bottom Query Box) ---
if st.session_state.get("chat_history"):
    st.divider()
    st.markdown("### 💬 Your Travel Plan & Conversation")
    
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
                    with st.expander("🤖 Supervisor's Agent Routing & Reasoning Plan", expanded=True):
                        st.write(f"**Reasoning:** {result.get('supervisor_reasoning', '')}")
                        agents_list = result.get('selected_agents', [])
                        if agents_list:
                            st.write(f"**Specialists Dispatched:** {', '.join(agents_list)}")
                        else:
                            st.write("**Specialists Dispatched:** None")

                    st.subheader("📝 Draft Itinerary")
                    if "__interrupt__" in result:
                        draft = result["__interrupt__"][0].value.get("draft_itinerary", "")
                    else:
                        draft = result.get("itinerary", "")
                    st.markdown(draft)

# --- Handle Human Approval (Inline in Conversation above the bottom bar) ---
if st.session_state.get("waiting_for_approval"):
    with st.chat_message("assistant"):
        st.subheader("🙋 Human Approval Required")
        st.info("Review the draft itinerary above. You can approve it immediately or provide revision instructions.")
        approved = st.radio("Approve this draft plan?", ["Yes, generate final plan", "No, revise it with feedback"], horizontal=True)
        feedback = st.text_area("Revision Feedback (optional):", disabled=(approved == "Yes, generate final plan"), placeholder="e.g. Please choose 4-star hotels instead or add a day trip...")

        if st.button("Submit Decision & Polish Plan", type="primary"):
            with st.spinner("Polishing final travel plan with your feedback..."):
                final_result = app.invoke(
                    Command(
                        resume={
                            "approved": (approved == "Yes, generate final plan"),
                            "feedback": feedback,
                        }
                    ),
                    config=config,
                )
            
            st.session_state.waiting_for_approval = False
            
            if final_result and final_result.get("final_response"):
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "type": "final_plan",
                    "content": f"### 🌟 Final Polished Travel Plan\n\n{final_result['final_response']}"
                })
            st.rerun()

# --- True Fixed Bottom Footer (Sits at the very bottom, below user query box) ---
st.markdown(
    """
    <div class="bottom-fixed-footer">
        Developed by <a href="https://www.linkedin.com/in/devhamed/" target="_blank">Hamed Hasan</a>
        &nbsp;·&nbsp; Powered by LangGraph, Qwen &amp; MCP
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Fixed Bottom Query Box (st.chat_input) ---
# Anchored directly above the bottom footer
prompt = st.chat_input(
    "Plan a 7-day trip, weekend getaway, or describe your dream vacation...",
    disabled=st.session_state.get("waiting_for_approval", False)
)

# Detect input from either bottom chat box or top quick-pick cards/buttons
active_query = None
if prompt:
    active_query = prompt
elif st.session_state.get("trigger_query"):
    active_query = st.session_state.pop("trigger_query")

# --- Execute Plan ---
if active_query:
    st.session_state.chat_history.append({"role": "user", "type": "text", "content": active_query})
    
    with st.chat_message("user"):
        st.markdown(active_query)

    with st.chat_message("assistant"):
        with st.spinner("🤖 Autonomous travel agents are searching flights, hotels, weather, and computing itinerary..."):
            result = app.invoke(
                {
                    "messages": [HumanMessage(content=active_query)],
                    "user_id": user_id,
                    "user_query": active_query,
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

        st.session_state.chat_history.append({"role": "assistant", "type": "draft_plan", "content": result})
        
        if "__interrupt__" in result:
            st.session_state.waiting_for_approval = True
            
        st.rerun()
