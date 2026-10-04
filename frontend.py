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

# --- Responsive Modern Dark UI CSS ---
st.markdown(
    """
    <style>
    /* Global layout & theme */
    .stApp {
        background: #090d16;
        color: #e2e8f0;
    }
    
    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 8.5rem !important; /* Plenty of space above the sticky chat input */
        padding-left: 1.5rem;
        padding-right: 1.5rem;
    }
    
    /* Hero Section Banner */
    .hero-container {
        background: linear-gradient(180deg, rgba(16, 24, 40, 0.85) 0%, rgba(9, 13, 22, 0.95) 100%),
                    url('https://images.unsplash.com/photo-1436491865332-7a61a109cc05?q=80&w=1600&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        border-radius: 20px;
        padding: 3rem 2rem 2.5rem 2rem;
        text-align: center;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 15px 35px -10px rgba(0, 0, 0, 0.7);
    }
    
    .hero-badge {
        display: inline-block;
        background: rgba(37, 99, 235, 0.25);
        color: #93c5fd;
        border: 1px solid rgba(96, 165, 250, 0.4);
        padding: 0.45rem 1.25rem;
        border-radius: 9999px;
        font-size: 0.95rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-bottom: 1.25rem;
        backdrop-filter: blur(8px);
    }
    
    .hero-subtitle {
        font-size: 1.15rem;
        color: #cbd5e1;
        max-width: 780px;
        margin: 0 auto;
        line-height: 1.65;
        font-weight: 400;
    }
    
    /* Section Headings */
    .section-label {
        font-size: 0.88rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #60a5fa;
        margin-bottom: 0.85rem;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    /* Equal & Proper Alignment for Destination Cards */
    div[data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
    }

    div[data-testid="column"] {
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
    }

    /* Force all 5 destination image wrappers to exact identical height */
    div[data-testid="column"] div[data-testid="stImage"] {
        height: 120px !important;
        max-height: 120px !important;
        min-height: 120px !important;
        overflow: hidden !important;
        border-radius: 14px 14px 0 0 !important;
        margin-bottom: 0 !important;
    }

    div[data-testid="column"] div[data-testid="stImage"] img {
        height: 120px !important;
        max-height: 120px !important;
        min-height: 120px !important;
        width: 100% !important;
        object-fit: cover !important;
        object-position: center !important;
        border-radius: 14px 14px 0 0 !important;
        display: block !important;
    }

    /* Card button seamless integration with image */
    div[data-testid="column"] .stButton {
        margin-top: 0 !important;
    }

    div[data-testid="column"] .stButton > button {
        background-color: #131b2e !important;
        color: #f1f5f9 !important;
        border: 1px solid #1e293b !important;
        border-top: none !important;
        border-radius: 0 0 14px 14px !important;
        padding: 0.65rem 0.5rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease-in-out !important;
        width: 100% !important;
    }

    div[data-testid="column"] .stButton > button:hover {
        background-color: #1e293b !important;
        color: #60a5fa !important;
        border-color: #3b82f6 !important;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.25) !important;
    }

    /* Quick Starter prompt buttons */
    .starter-btn .stButton > button {
        background-color: #131b2e !important;
        color: #e2e8f0 !important;
        border: 1px solid #1e293b !important;
        border-radius: 12px !important;
        padding: 0.75rem 0.85rem !important;
        font-size: 0.92rem !important;
        font-weight: 600 !important;
        height: 52px !important;
        text-align: center !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
    }

    .starter-btn .stButton > button:hover {
        background-color: #1e293b !important;
        border-color: #3b82f6 !important;
        color: #60a5fa !important;
        transform: translateY(-2px) !important;
    }

    /* Sticky Bottom chat_input customization */
    div[data-testid="stBottom"] {
        bottom: 28px !important; /* Sits directly above the fixed footer */
        background: transparent !important;
    }

    div[data-testid="stChatInput"] {
        background-color: #0d1322 !important;
        border: 1px solid #1e293b !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6) !important;
    }

    div[data-testid="stChatInput"] textarea {
        color: #f8fafc !important;
        font-size: 0.98rem !important;
    }

    /* True Bottom Footer (Fixed below the query chatbox) */
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
    .bottom-fixed-footer a:hover {
        text-decoration: underline !important;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0b0f19 !important;
        border-right: 1px solid #1e293b !important;
    }
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    /* ── Responsive Mobile & Tablet Rules ── */
    @media screen and (max-width: 900px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1.25rem;
            padding-bottom: 7.5rem !important;
        }
        .hero-container {
            padding: 2.25rem 1.25rem 1.75rem 1.25rem;
            border-radius: 16px;
        }
        .hero-badge {
            font-size: 0.85rem;
            padding: 0.35rem 1rem;
        }
        .hero-subtitle {
            font-size: 1rem;
            line-height: 1.5;
        }
        div[data-testid="column"] div[data-testid="stImage"],
        div[data-testid="column"] div[data-testid="stImage"] img {
            height: 100px !important;
            max-height: 100px !important;
            min-height: 100px !important;
        }
        div[data-testid="column"] .stButton > button {
            font-size: 0.85rem !important;
            height: 38px !important;
            min-height: 38px !important;
        }
        .starter-btn .stButton > button {
            font-size: 0.85rem !important;
            height: 48px !important;
        }
    }

    @media screen and (max-width: 600px) {
        .hero-container {
            padding: 1.75rem 0.85rem 1.5rem 0.85rem;
            border-radius: 14px;
        }
        .hero-badge {
            font-size: 0.78rem;
            padding: 0.3rem 0.85rem;
            margin-bottom: 0.85rem;
        }
        .hero-subtitle {
            font-size: 0.92rem;
        }
        div[data-testid="column"] div[data-testid="stImage"],
        div[data-testid="column"] div[data-testid="stImage"] img {
            height: 85px !important;
            max-height: 85px !important;
            min-height: 85px !important;
        }
        div[data-testid="column"] .stButton > button {
            font-size: 0.78rem !important;
            height: 36px !important;
            min-height: 36px !important;
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
        <div class="hero-badge">✦ MULTI-AGENT Personalized TRAVEL Assistant</div>
        <div class="hero-subtitle">
            Four specialized agents work together — searching flights, hotels, weather and forcast of the destination building an itinerary, and delivering your personalized Travel Plan
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Popular Destinations Grid (Equal & Uniform 600x380 Landscape Alignment) ---
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

st.markdown("<br>", unsafe_allow_html=True)

# --- Describe Your Trip (Quick Prompt Starter Buttons) ---
st.markdown('<div class="section-label">🗺️ Describe Your Trip</div>', unsafe_allow_html=True)
q_col1, q_col2, q_col3, q_col4 = st.columns(4)

with q_col1:
    st.markdown('<div class="starter-btn">', unsafe_allow_html=True)
    if st.button("7-day Japan trip", use_container_width=True, key="start_japan"):
        st.session_state.trigger_query = "Plan a 7-day Japan trip with hotels, weather forecast, and no overnight flights."
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with q_col2:
    st.markdown('<div class="starter-btn">', unsafe_allow_html=True)
    if st.button("Paris trip for 5 days", use_container_width=True, key="start_paris"):
        st.session_state.trigger_query = "Plan a 5-day Paris trip with central hotels, museums, and weather forecast."
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with q_col3:
    st.markdown('<div class="starter-btn">', unsafe_allow_html=True)
    if st.button("Dubai weekend trip", use_container_width=True, key="start_dubai"):
        st.session_state.trigger_query = "Plan a 3-day weekend trip to Dubai with flights, city attractions, and weather."
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with q_col4:
    st.markdown('<div class="starter-btn">', unsafe_allow_html=True)
    if st.button("Bali backpacking 10 days", use_container_width=True, key="start_bali"):
        st.session_state.trigger_query = "Plan a 10-day Bali backpacking trip focusing on budget villas, beaches, and weather."
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

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
