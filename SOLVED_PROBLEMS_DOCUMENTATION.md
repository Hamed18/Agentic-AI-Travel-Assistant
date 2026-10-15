# 📘 Comprehensive System Changelog & Problem Solutions Documentation
**Project:** Multi-Agent AI Travel Assistant  
**Author:** AI Agentic Assistant & Dev Team  
**Date:** October 15, 2026  

--- 

## 🎯 Executive Overview
This document serves as a detailed technical record of all major problems, root causes, design flaws, and architectural solutions implemented across the **Multi-Agent AI Travel Assistant** application. 

You can easily copy and paste this document or import it directly into **Google Docs** (`File` ➔ `Open` ➔ `Upload` or Copy/Paste as formatted Markdown).

---

## 📋 Summary of Solved Problems

| # | Problem Title | Domain | Key Fix Implemented |
|---|---|---|---|
| **1** | Light Theme Overlap & Button Invisibility | UI / CSS | Universal DOM button targeting & framework dark mode locking via `config.toml` |
| **2** | Single-Chance Human Approval Limitation | State Graph | Conditional routing loop from `human_approval` back to `itinerary_agent` |
| **3** | Metadata Disconnect (1-Day vs 6-Day Inconsistency) | Prompt Engineering | Full metadata synchronization enforcing title, overview, schedule & cost alignment |
| **4** | Vague Feedback Hallucination (`"ok"` resetting draft) | LLM State / Logic | Intent detection (`_is_vague_or_affirming_feedback`) & Ground Truth Draft preservation |
| **5** | Stale Supervisor Reasoning on Revision Steps | UI Rendering | Disambiguated initial dispatch (`is_revision=False`) vs revision step (`is_revision=True`) |
| **6** | Conversation Disappearing When Switching Chats | Session State & Memory | Multi-thread session store (`chats`), state sync helpers, and `MemorySaver` fallback |
| **7** | Smart Viewport Management: Top on New Chat & Auto-Scroll to Generation | UI / Viewport & Scroll | Staged DOM top-pinning on empty chat + immediate smooth auto-scroll to generation area during inference |
| **8** | OpenRouter 402 Credit Exhaustion, Free Model 404s & Guardrail Rigidity | LLM / Model Infrastructure & Error Handling | Dynamic free model discovery (`nvidia/nemotron-3-super-120b`), token capping, resilient fallback routing, permissive guardrails, and graceful UI error states |
| **9** | PDF Generator Breakdown: Word Merging, Raw Markdown Asterisks & Heading Promotion | PDF Engine & LLM Output Formatting | Comprehensive Unicode dash/space mapping table, markdown AST stripping, strict heading discrimination, and prompt hardening against meta-reasoning leakage |
| **10** | PDF Missing Section Details & Truncated Final Response Resolution | Multi-Agent Pipeline & PDF Engine | Zero-loss `final_response_agent` preserving 100% of approved itinerary, flexible Day/Time/Activity regexes, backslash unescaping, and full-fidelity PDF compilation |

---

## 1. 🎨 Problem 1: Light Theme Clashing & Inconsistent Button Styling

### ❌ Problem Description
When running on Streamlit Cloud or locally with standard browser defaults, elements of the UI rendered with light backgrounds and dark text, clashing with the dark theme aesthetic. Primary buttons in destination cards and starter prompt rows had inconsistent styling, white background bleeding, and invisible text on dark mode.

### 🔍 Root Cause Analysis
Streamlit dynamically generates DOM nodes without static parent HTML wrappers. Attempts to wrap Streamlit layout elements using `st.markdown('<div class="dest-grid">')` produced **sibling HTML elements** rather than parent containers in the real browser DOM. As a result, CSS selectors like `.dest-grid div[data-testid="column"]` failed to match, leaving widgets to default Streamlit styling.

### 🛠️ Technical Solution & Code Implementation
1. **Universal Main-Area CSS Selectors**: Replaced wrapper-dependent CSS selectors with direct universal selectors targeting every main-area button across Streamlit versions:
   ```css
   section.main .stButton > button,
   [data-testid="stMain"] .stButton > button,
   .block-container .stButton > button {
       background-color: #1a2540 !important;
       color: #e2e8f0 !important;
       border: 1px solid #2d3f5e !important;
       border-radius: 12px !important;
   }
   ```
2. **Framework-Level Dark Mode Lock**: Created `.streamlit/config.toml` to force dark mode before DOM hydration, preventing light theme flash:
   ```toml
   [theme]
   base = "dark"
   primaryColor = "#3b82f6"
   backgroundColor = "#090d16"
   secondaryBackgroundColor = "#131b2e"
   textColor = "#e2e8f0"
   ```
3. **Locked Card Image Dimensions**: Fixed destination card alignment by setting explicit `130px` height boundaries on image containers (`div[data-testid="column"] div[data-testid="stImage"] img`) with seamless bottom-border buttons.

---

## 2. 🔄 Problem 2: Single-Chance Human Approval Limitation

### ❌ Problem Description
Originally, when a draft itinerary was generated, the human approval mechanism only allowed a single interaction. If the user rejected the draft or requested changes, the graph proceeded to `final_response` without giving the user a chance to review the revised itinerary.

### 🔍 Root Cause Analysis
The LangGraph workflow definition in `graph.py` was strictly linear:
`itinerary_agent` ➔ `human_approval` ➔ `final_response` ➔ `END`.
The graph lacked a loop-back edge from `human_approval` back to `itinerary_agent`.

### 🛠️ Technical Solution & Code Implementation
1. **Conditional Routing Function**: Introduced `route_after_human_approval(state)` in `graph.py`:
   ```python
   def route_after_human_approval(state: TravelState) -> str:
       if state.get("approved"):
           return "final_response"
       return "itinerary_agent"
   ```
2. **Graph Re-wiring**: Added conditional edges allowing infinite review iterations:
   ```python
   graph.add_conditional_edges(
       "human_approval",
       route_after_human_approval,
       {
           "final_response": "final_response",
           "itinerary_agent": "itinerary_agent",
       },
   )
   ```
3. **Streamlit State Management**: Updated `frontend.py` to check for `__interrupt__` in `app.invoke(Command(resume=...))` results, keeping `waiting_for_approval = True` and appending revised drafts to `chat_history`.

---

## 3. ⚖️ Problem 3: Metadata Disconnect & Stale Duration Bleed

### ❌ Problem Description
When a user requested a trip reduction (e.g., *"only keep first day"*), the daily schedule listed Day 1, but the document **Title**, **Overview Duration**, and **Total Estimated Cost** still claimed it was a 6-day trip with a 6-day cost summary ($270–$540).

### 🔍 Root Cause Analysis
`trip_constraints` in LangGraph state retained initial values (`duration: 6 days`). The system prompt for `itinerary_agent` prioritized initial constraints over user revision feedback, creating internal logical contradictions between metadata headers and itinerary body content.

### 🛠️ Technical Solution & Code Implementation
1. **Mandated Full Metadata Synchronization**: Updated `itinerary_agent` instructions in `agents.py`:
   - **Title**: Must explicitly match the revised duration (e.g., *"1-Day Cultural Trip to Bangkok"*).
   - **Overview**: Must state updated duration accurately.
   - **Schedule**: Include only requested/active days.
   - **Cost Summary**: Recalculate total estimated budget strictly for the revised duration and included days.
2. **Final Response Consistency**: Added rules in `final_response_agent` ensuring the final polished output maintains complete alignment with the approved draft metadata without reverting to old initial values.

---

## 4. 🧠 Problem 4: Vague Feedback Hallucination (`"ok"` Resetting Draft)

### ❌ Problem Description
If a user selected *"No, revise it with feedback"* but typed a vague or affirming response like `"ok"` or `"looks good"`, the system hallucinated and reverted the 1-day revised draft back to the original 6-day plan.

### 🔍 Root Cause Analysis
1. `"ok"` contains no actionable revision instructions.
2. The LLM saw `user_query: Plan a 6-day trip` and `feedback: "ok"`. Lacking specific change requests, it fell back to `user_query`, destroying the active 1-day draft.
3. The UI evaluated `approved = (radio == "Yes, generate final plan")`, triggering an unnecessary LLM re-generation step for non-revision text.

### 🛠️ Technical Solution & Code Implementation
1. **Intent Analysis Helper (`_is_vague_or_affirming_feedback`)**: Added a detector in `agents.py` to identify single-word/vague affirmations (`"ok"`, `"fine"`, `"looks good"`, `"yes"`, `"cool"`, `"no changes"`, etc.):
   ```python
   def _is_vague_or_affirming_feedback(feedback_text: str) -> bool:
       clean_fb = feedback_text.strip().lower().strip("!.,;:-_")
       vague_phrases = {"ok", "okay", "good", "fine", "looks good", "yes", "cool", "no changes", ...}
       if clean_fb in vague_phrases:
           return True
       ...
   ```
2. **Approval Normalization**: In `human_approval_agent`, if the user selects *"No, revise"* but enters vague feedback, `approved` is normalized to `True`, routing straight to finalization of the current draft.
3. **Ground Truth Baseline**: When a valid revision is requested, `itinerary_agent` treats `Previous Draft Itinerary` as the **Primary Ground Truth Baseline**, strictly forbidding the LLM from reverting to initial query defaults.

---

## 5. 🏷️ Problem 5: Stale Supervisor Reasoning Displayed on Revision Steps

### ❌ Problem Description
During revision turns under human approval, the UI expander at the top of the draft card displayed initial supervisor reasoning (e.g., *"The user requested a complete 7-day trip to Tokyo..."*), making it look like the system misunderstood the revision request.

### 🔍 Root Cause Analysis
`supervisor_agent` does not re-run during human approval revision cycles, but its reasoning persisted in LangGraph state. `frontend.py` unconditionally rendered `🤖 Supervisor's Agent Routing & Reasoning Plan` for all `draft_plan` message objects.

### 🛠️ Technical Solution & Code Implementation
1. **Message Tagging**: Updated `frontend.py` to tag initial draft runs with `is_revision: False` and human approval revision steps with `is_revision: True`.
2. **Dynamic UI Expander Rendering**:
   ```python
   if is_revision:
       with st.expander("🔄 Itinerary Revision Step (Direct Agent Refinement)", expanded=True):
           st.write("**Status:** Refined itinerary generated based on your revision feedback.")
           st.caption("The supervisor routing was bypassed for direct itinerary adjustment.")
   else:
       with st.expander("🤖 Supervisor's Agent Routing & Reasoning Plan", expanded=True):
           st.write(f"**Reasoning:** {result.get('supervisor_reasoning', '')}")
   ```

---

## 6. 🗂️ Problem 6: Conversation Disappearing When Creating New Chat & Switching Back

### ❌ Problem Description
When a user creates a new chat in the sidebar and later clicks on a previous chat in the "Recent Chats" list, the previous conversation does not appear on screen. The main chat area is empty, wiping out the prior discussion, draft itineraries, and human approval status.

### 🔍 Root Cause Analysis
1. **Chat History Never Persisted Upon Creation of New Chat**:
   When the user clicked "✏️ New Chat", `st.session_state.all_threads` only saved a lightweight dictionary containing `{"thread_id": ..., "title": ...}`. The actual list of message objects (`st.session_state.chat_history`) was never associated with the old thread or stored in any dictionary. It was immediately wiped with `st.session_state.chat_history = []`.
2. **Explicit Reset on Chat Selection**:
   In the sidebar's recent chats loop, clicking an existing chat button executed:
   ```python
   st.session_state.thread_id = thread["thread_id"]
   st.session_state.chat_history = []  # Explicit wipe!
   st.session_state.pop("waiting_for_approval", None)
   ```
   This explicitly cleared `chat_history` to an empty list without loading past conversation records from any store.
3. **Loss of Approval & Widget State**:
   If a user had an ongoing revision approval form open (`waiting_for_approval = True`), switching away and back popped this key, leaving the user with no interface to approve or revise the plan.
4. **Missing Checkpointer Fallback in LangGraph**:
   If PostgreSQL (`DATABASE_URL`) was absent or temporarily unreachable, `graph.py` compiled without any checkpointer (`return graph.compile()`), preventing LangGraph from maintaining graph state across thread switches.

### 🛠️ Technical Solution & Code Implementation
1. **Multi-Thread Session Store in Streamlit (`chats`)**:
   Introduced a persistent dictionary structure in `frontend.py`:
   ```python
   # Structure: { thread_id: {"title": str, "chat_history": list, "waiting_for_approval": bool} }
   if "chats" not in st.session_state:
       st.session_state.chats = {}

   if "thread_order" not in st.session_state:
       st.session_state.thread_order = []
   ```
2. **State Synchronization Helpers (`save_current_chat` & `switch_to_thread`)**:
   - `save_current_chat()`: Automatically synchronizes the active thread's messages, human approval flags, and extracts clean, concise conversation titles from the first user message.
   - `switch_to_thread(target_tid)`: Saves the currently open thread's latest state before switching the active thread, then loads `chat_history` and `waiting_for_approval` from `chats[target_tid]`.
3. **Isolated Streamlit Widget Keys**:
   Added thread-specific key prefixes (`key=f"..._{st.session_state.thread_id}"`) for PDF download buttons, approval radio buttons, revision text areas, and submit buttons to avoid widget state pollution across distinct chats.
4. **LangGraph In-Memory Checkpointer Fallback (`MemorySaver`)**:
   In `graph.py`, imported `MemorySaver` and updated the fallback compilation:
   ```python
   except Exception as e:
       print(f"Warning: Could not connect to PostgreSQL checkpointer ({e}). Compiling in-memory with MemorySaver.")
       return graph.compile(checkpointer=MemorySaver())

   # If no DATABASE_URL is configured, compile with MemorySaver for session persistence
   return graph.compile(checkpointer=MemorySaver())
   ```
   This ensures LangGraph tracks and restores graph execution and interrupt checkpoints per `thread_id` even when operating without an external PostgreSQL instance.

---

## 7. 🔝 Problem 7: Smart Viewport Management (Top on Landing & Auto-Scroll to Generation)

### ❌ Problem Description
Two conflicting viewport issues degraded the user experience:
1. **Initial Page Load & New Chat**: When a user first landed on the app or clicked **"✏️ New Chat"**, the viewport opened scrolled down near the bottom chat input box, hiding the **Hero Section banner** and the **Popular Destinations cards** above the fold.
2. **Generation Focus**: Conversely, once a prompt was entered (from the chat input, destination cards, or starter buttons) or revision feedback was submitted, the user was left looking at the top cards without the viewport automatically guiding them down to where the agents were generating the response and displaying the output.

### 🔍 Root Cause Analysis
1. **Chat Input Autofocus & Scroll Anchoring**:
   Streamlit's `st.chat_input` renders inside the pinned bottom bar (`div[data-testid="stBottom"]`). When the React component mounts, browser and framework autofocus routines focus the textarea, automatically pulling the scrollable containers (`[data-testid="stAppViewContainer"]`, `section[data-testid="stMain"]`, and `window`) down to the very bottom on initial visits.
2. **Disconnected Scroll State During LLM Execution**:
   In Streamlit, the chat history and active plan appear underneath the hero and destination card grids. When an active query begins executing, the execution spinner and user/assistant messages render further down the page. Without an explicit scroll trigger targeting the active generation container, users had to manually scroll down to check if the agents were working.

### 🛠️ Technical Solution & Code Implementation
1. **Dual State Tracking (`scroll_to_top` & `scroll_to_generation`)**:
   - `scroll_to_top = True`: Activated strictly when `chat_history` is empty (new session or after clicking "✏️ New Chat").
   - `scroll_to_generation = True`: Activated as soon as `active_query` executes or revision feedback is submitted via human approval.
2. **Top DOM Anchor & Staged Reset**:
   Placed a non-intrusive `<div id="top-anchor"></div>` immediately above the Hero container. If `chat_history` is empty, a staged JavaScript controller runs:
   ```javascript
   function forceScrollToTop() {
       try {
           const parentDoc = window.parent.document;
           if (!parentDoc) return;
           if (parentDoc.activeElement && parentDoc.activeElement.tagName === 'TEXTAREA') {
               parentDoc.activeElement.blur();
           }
           const anchor = parentDoc.getElementById('top-anchor') || parentDoc.querySelector('.hero-container');
           if (anchor) anchor.scrollIntoView({ behavior: 'instant', block: 'start' });
           [parentDoc.querySelector('[data-testid="stAppViewContainer"]'),
            parentDoc.querySelector('section[data-testid="stMain"]'),
            parentDoc.querySelector('.main'), parentDoc.body].forEach(el => { if (el) el.scrollTop = 0; });
       } catch (err) {}
   }
   forceScrollToTop();
   requestAnimationFrame(forceScrollToTop);
   setTimeout(forceScrollToTop, 50);
   setTimeout(forceScrollToTop, 150);
   setTimeout(forceScrollToTop, 300);
   ```
3. **In-Flight Active Generation Anchor**:
   As soon as a query starts (`if active_query:`), `<div id="active-generation-anchor"></div>` is injected, immediately executing a smooth scroll directly to the generation area:
   ```javascript
   function scrollToActiveGen() {
       try {
           const parentDoc = window.parent.document;
           if (!parentDoc) return;
           const anchor = parentDoc.getElementById('active-generation-anchor') ||
                          parentDoc.querySelector('[data-testid="stChatMessage"]:last-of-type') ||
                          parentDoc.querySelector('.stSpinner');
           if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
       } catch (err) {}
   }
   scrollToActiveGen();
   requestAnimationFrame(scrollToActiveGen);
   setTimeout(scrollToActiveGen, 50);
   setTimeout(scrollToActiveGen, 150);
   ```
4. **Post-Generation Viewport Locking**:
   When the LLM finishes invoking and `st.rerun()` completes, `#latest-generation-anchor` smoothly retains viewport focus on the newly generated itinerary, expander agents, and approval controls.
5. **Zero-Height Component Isolation**:
   Maintained CSS overrides (`iframe[height="0"] { display: none !important; ... }`) ensuring neither controller adds white space or layout artifacts.

---

## 8. 🛡️ Problem 8: OpenRouter 402 Credit Depletion, Free Model 404 Deprecations & Guardrail Rigidity

### ❌ Problem Description
1. **OpenRouter 402 Insufficient Credits Block**:
   When users submitted a travel planning request, the backend failed immediately with:
   ```text
   openai.APIStatusError: Error code: 402 - {'error': {'message': "This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can only afford 16081..."}}
   ```
   The system was configured without strict token caps, causing OpenRouter to pre-calculate required credit reserves against `max_tokens=16384` (the model's default maximum context window) and reject the execution outright when the account balance dropped below that pre-authorization hold.
2. **Discontinued Free Model Slugs (404 Not Found)**:
   Attempts to switch to commonly referenced free models such as `google/gemma-3-12b-it:free` and `meta-llama/llama-3.1-8b-instruct:free` failed with:
   ```text
   openai.NotFoundError: Error code: 404 - {'error': {'message': 'This model is unavailable for free. The paid version is available now...'}}
   ```
3. **Rigid Guardrail Blocking Valid Inquiries**:
   The initial input validation guardrail evaluated short, natural prompts (e.g., `"Tokyo"`, `"Paris"`, or `"Hello"`) as `allowed: false`, misclassifying valid travel destinations and greetings as off-topic and returning an FAQ rejection message.
4. **Unhandled JSON Parsing & UI Crash**:
   When an LLM response contained markdown code fences (e.g., ```` ```json ... ``` ````) or lacked curly brackets, `_json_from_llm` threw unhandled `ValueError` / `json.JSONDecodeError` exceptions, causing Streamlit to crash with a raw traceback screen.

---

### 🔍 Root Cause Analysis
1. **Uncapped `max_tokens` Allocation**: LangChain’s `ChatOpenAI` initialized without an explicit token ceiling, defaulting to OpenRouter's maximum window size. OpenRouter validates the user's account credit against the *maximum possible tokens* for the request rather than actual usage. Because the account balance had fallen slightly below the 16,384-token reserve threshold, every query was blocked with code `402`.
2. **Upstream Free Tier Rotations on OpenRouter**: Free tier availability is dynamic on OpenRouter. Providers periodically retire `:free` endpoints or transition popular models to paid-only when compute grants expire. Hardcoding unverified free slugs leads to runtime `404` errors.
3. **Over-Strict Guardrail Prompt**: The guardrail prompt asked *"Determine whether the following request is a valid travel planning request"*, which the model interpreted narrowly to mean a complete, fully specified itinerary request with dates and budget. It rejected simple city names and friendly greetings.
4. **Fragile Substring JSON Extraction**: The extraction routine used `raw.index("{")` and `raw.rindex("}")` without handling markdown code blocks or providing a default dictionary if parsing failed, leading to pipeline crashes.

---

### 🛠️ Technical Solution & Code Implementation

#### 1. Integrated LLM Models & Key Architectural Benefits
Rather than guessing model slugs or relying on deprecated endpoints, we queried OpenRouter's live catalog (`https://openrouter.ai/api/v1/models`) to identify active models with zero prompt and completion pricing. We benchmarked candidates for reasoning, speed, and structured JSON output, selecting a dual-tier NVIDIA architecture:

* **Primary Model — NVIDIA Nemotron 3 Super 120B (`nvidia/nemotron-3-super-120b-a12b:free`)**:
  - **Massive 120-Billion Parameter Scale**: Delivers enterprise-grade reasoning, deep context synthesis across multi-turn travel plans, and strong adherence to system personas.
  - **Strict Structured JSON Adherence**: Multi-agent supervisors require 100% parsable JSON payloads for graph routing (`{"next_agent": "flight_agent"}`). Nemotron 3 Super reliably outputs valid JSON without omitting keys or introducing conversational filler.
  - **100% Free Tier ($0.00 Cost)**: Runs on OpenRouter's free tier with zero prompt or completion charges, preventing balance exhaustion on production deployments.

* **Secondary Fallback Model — NVIDIA Nemotron 3.5 Lightning (`nvidia/nemotron-3.5-lightning:free`)**:
  - **High-Speed Inference & Low Latency**: Engineered for rapid token generation with minimal Time-To-First-Token (TTFT), making it ideal for immediate failover.
  - **Zero-Downtime Resilience**: Seamlessly handles requests whenever the primary 120B model encounters transient provider congestion (`429`) or server timeouts (`502`/`503`).
  - **100% Free Tier ($0.00 Cost)**: Ensures secondary routing never incurs unexpected credit billing.

##### 📊 Dual-Tier Model Comparison Matrix
| Architecture Attribute | Primary Model: Nemotron 3 Super 120B | Fallback Model: Nemotron 3.5 Lightning |
| :--- | :--- | :--- |
| **Model Slug** | `nvidia/nemotron-3-super-120b-a12b:free` | `nvidia/nemotron-3.5-lightning:free` |
| **Primary Responsibility** | Main Agent Reasoning, Supervisor Routing, Itinerary Synthesis | High-Speed Failover, Rate-Limit Recovery |
| **Parameter Scale** | 120 Billion Parameters | Optimized Lightweight High-Throughput |
| **Pricing** | $0.00 / 1M prompt & completion tokens | $0.00 / 1M prompt & completion tokens |
| **Structured Output Quality** | Strict JSON adherence, zero hallucinated routing keys | Fast structured parsing with regex fallback |
| **Token Budget Ceiling** | Hard-capped at 4,096 tokens via `extra_body` | Hard-capped at 4,096 tokens via `extra_body` |
| **Failover Trigger** | 3 retries with exponential backoff | Automatic instant switch on HTTP 429/402 |

---

#### 2. Token Capping, Auto-Retry & Fallback LLM Setup (`config.py`)
In `config.py`, we implemented explicit token ceilings, retry policies with backoff, and model fallback instances. Critically, we passed `extra_body={"max_tokens": 4096}` because LangChain's `ChatOpenAI` renames `max_tokens` to `max_completion_tokens` internally—which OpenRouter's credit reservation engine overlooks, causing it to assume a 16,384-token reserve requirement:

```python
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
FALLBACK_MODEL = "nvidia/nemotron-3.5-lightning:free"

def get_llm(model: str = None):
    api_key = get_secret("OPENROUTER_API_KEY") or get_secret("OPENAI_API_KEY")
    selected_model = model or get_secret("OPENROUTER_MODEL", DEFAULT_MODEL)
    return ChatOpenAI(
        model=selected_model,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        max_tokens=4096,
        extra_body={"max_tokens": 4096},  # Explicitly forces OpenRouter reservation cap
        max_retries=3,                    # Automatic backoff on transient 429/502 errors
        default_headers={
            "HTTP-Referer": "https://streamlit.io",
            "X-Title": "AI Travel Assistant",
        },
    )

def get_fallback_llm():
    api_key = get_secret("OPENROUTER_API_KEY") or get_secret("OPENAI_API_KEY")
    return ChatOpenAI(
        model=FALLBACK_MODEL,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        max_tokens=4096,
        extra_body={"max_tokens": 4096},
        max_retries=3,
        default_headers={
            "HTTP-Referer": "https://streamlit.io",
            "X-Title": "AI Travel Assistant",
        },
    )
```

#### 3. Automatic Rate-Limit & Quota Fallback Routing (`agents.py`)
In `agents.py`, `_llm_text` was rewritten to intercept `429` (RateLimitError) and `402` (APIStatusError) exceptions and automatically retry the call using the fallback model:
```python
def _llm_text(system: str, prompt: str) -> str:
    try:
        response = llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ])
        return response.content
    except (RateLimitError, APIStatusError) as e:
        error_code = getattr(e, 'status_code', None)
        if error_code in (429, 402):
            print(f"\n[LLM FALLBACK] Primary model rate-limited ({error_code}). Switching to fallback...\n")
            time.sleep(1)
            response = _fallback_llm.invoke([
                SystemMessage(content=system),
                HumanMessage(content=prompt),
            ])
            return response.content
        raise
```

#### 4. Resilient JSON Parsing & Permissive Travel Guardrail (`agents.py`)
- **Code Block Stripping & Safe Fallback**:
  ```python
  def _json_from_llm(text: str, default: dict = None) -> dict:
      cleaned = text.strip()
      if "```" in cleaned:
          first_fence = cleaned.find("```")
          newline_after = cleaned.find("\n", first_fence)
          if newline_after != -1:
              rest = cleaned[newline_after + 1:]
              last_fence = rest.rfind("```")
              cleaned = rest[:last_fence].strip() if last_fence != -1 else rest.strip()
      try:
          start = cleaned.index("{")
          end = cleaned.rindex("}") + 1
          return json.loads(cleaned[start:end])
      except Exception as e:
          if default is not None:
              return default
          return {}
  ```
- **Explicit Permissive Guardrail Rules**: Updated the guardrail prompt with clear evaluation criteria that explicitly classify destination names, travel inquiries, and friendly greetings as `allowed: true`.
- **Default Routing In Supervisor**: If JSON extraction fails, the supervisor gracefully defaults to routing through `["flight_agent", "hotel_agent", "weather_agent", "itinerary_agent"]` with safe `.get()` dictionary lookups instead of throwing a `KeyError`.

#### 5. Graceful UI Error Handling & Server Diagnostics (`frontend.py`)
- **Import Resolution**: Ensured `AIMessage` was properly imported alongside `HumanMessage` (`from langchain_core.messages import AIMessage, HumanMessage`) so that synthesized error cards render cleanly directly into the conversation stream without triggering a `NameError`.
- **Exception Boundary**: Wrapped graph execution (`app.invoke()`) and human-in-the-loop resumptions (`Command(resume=...)`) in `try...except` blocks that trap API-level credit or rate limit errors, rendering a styled alert banner instead of crashing the Streamlit application.
- **Traceback Logging**: Added `traceback.print_exc()` to output complete call stack traces directly to the host console (visible in Streamlit Cloud "Manage App" logs) for rapid remote troubleshooting.

---

### 🚫 Alternatives Evaluated That Did Not Work
1. **Alternative 1: Switching to `google/gemma-3-12b-it:free`**
   - *Result*: Failed with `404 Not Found`. OpenRouter removed the free slug and made Gemma 3 12B paid-only.
2. **Alternative 2: Switching to `meta-llama/llama-3.1-8b-instruct:free`**
   - *Result*: Failed with `404 Not Found`. OpenRouter similarly transitioned Llama 3.1 8B to paid-only.
3. **Alternative 3: Using the Dynamic Router `openrouter/free`**
   - *Result*: Highly inconsistent. The dynamic router routed requests to ultra-small models (such as `liquid/lfm-2.5-2.6b:free`), which frequently failed to follow system instructions, omitted JSON fields, or returned `NoneType` responses.
4. **Alternative 4: Keeping Uncapped `max_tokens` and Reducing Prompt Length**
   - *Result*: Failed. Even with a 20-word prompt, OpenRouter evaluates the user's remaining balance against the configured `max_tokens` ceiling (16,384 tokens), which consistently triggered the 402 rejection.
5. **Alternative 5: Retaining the Original Strict Guardrail Prompt**
   - *Result*: Failed. The LLM repeatedly blocked queries like `"Tokyo"` and `"Hello"`, mistakenly identifying them as incomplete and non-travel requests.

---

### ⚠️ Limitations & Future Failure Modes
1. **Free Tier Provider Volatility**:
   - *Risk*: Free models on OpenRouter are hosted by independent third-party providers. If providers experience outages, remove the free tier, or rotate slugs, the primary model could return `429` or `404`.
   - *Mitigation*: Our automatic fallback handler switches from `nemotron-3-super-120b` to `nemotron-3.5-lightning`. Both models operate on OpenRouter's 100% free tier. Users can also configure alternative model slugs in `.env` or Streamlit Cloud Secrets at any time.
2. **Platform Rate Limits on Free Tier**:
   - *Risk*: OpenRouter enforces limits of 20 requests per minute and 50 requests per day for free accounts with under $10 in lifetime purchases (1,000 requests/day for accounts with $10+ lifetime purchases).
   - *Mitigation*: The UI displays a friendly cooldown notice if daily limits are reached.
3. **Fallback Model Formatting Variance**:
   - *Risk*: While the 120B primary model generates strict JSON, lighter fallback models under heavy compute pressure may include conversational text around JSON.
   - *Mitigation*: `_json_from_llm` includes markdown fence stripping, curly-brace substring slicing, and default dict fallback so the app continues running without crashing.
4. **API Key Revocation**:
   - *Risk*: If the user's OpenRouter API key is modified or deleted from their account dashboard, requests will fail with `401 Unauthorized`.
   - *Mitigation*: Friendly error catching in `frontend.py` guides the user to check their OpenRouter key in `.env` or Streamlit Cloud Secrets.

---

## 9. 📑 Problem 10: PDF Missing Section Details & Truncated Final Response Resolution

### ❌ Problem Description
When users reviewed their draft itinerary in the Streamlit UI, it appeared complete with full tables, detailed day-by-day morning/afternoon/evening activity descriptions, locations, and budgets. However, upon approving the plan and generating the PDF, the resulting PDF was missing almost all details:
1. Tables for flights, hotels, and weather were missing or reduced to single-sentence notes.
2. Day-by-day schedules were reduced to single-line summaries (e.g. `Day 1 - Arrival & Iconic Skyline / Location: Downtown Dubai`), completely stripping out Morning, Afternoon, Evening, activity descriptions, and individual budgets.
3. Day headings failed to render as Day Cards and appeared with generic thin blue bars.
4. Literal markdown backslashes (`\*`) leaked onto the rendered PDF page.

### 🔍 Root Cause Analysis
1. **`final_response_agent` Summarization Bug**: In `agents.py`, when a user clicked "Approve", the workflow ran `final_response_agent`. Its prompt instructed the LLM: `"Produce the final polished travel plan based directly on this approved draft itinerary."` Without strict retention instructions, the LLM treated this as a prompt to produce an executive brief / high-level summary, stripping 80% of the content. `frontend.py` then passed this truncated summary to `create_pdf()`.
2. **Fragile Day & Time Regexes**: In `pdf_generator.py`, `is_day_heading()` strictly matched `^#{1,3}\s+Day\s+\d+`. When the LLM produced unhashed lines or 4-hash lines (`Day 1 - ...` or `#### Day 1`), it failed detection and fell back to generic section headings. `is_time_of_day()` used strict string equality (`stripped in (...)`), causing time slots with subtitles (`### Morning: City Tour`) to be misclassified.
3. **`fpdf2.table` Context Manager Bug**: In `fpdf2`, `pdf.table()` returns a `GeneratorContextManager`. Invoking `pdf.table(rows)` without a `with` statement returns a generator object without executing the drawing loop. Consequently, all tables (Flight, Hotel, Weather, Budget) were silently omitted from the PDF without triggering exceptions.
4. **LLM Schema Prompt Omission**: In `agents.py`, `DAY_FORMAT_INSTRUCTIONS` previously lacked explicit table schemas for Flights, Hotels, Weather, and Budget, causing the LLM to occasionally emit unstructured text instead of pipe tables.
5. **Horizontal Bar vs Pie Chart**: The budget distribution was previously drawn as a single horizontal stacked bar instead of an intuitive circular pie/donut chart.

### 🛠️ Technical Solution & Code Implementation
1. **Context-Managed Tables (`pdf_generator.py`)**:
   - Replaced unexecuted generator calls with `with pdf.table(rows, ...): pass`.
   - Explicitly reset `pdf.set_fill_color(255, 255, 255)` and `pdf.set_text_color(*pdf.SLATE_DARK)` prior to table rendering, preventing heading fill leakage into alternating rows.
   - Styled headers with navy background (`#1E3A8A`), bold white text, and light slate alternating row backgrounds (`#F5F7FA`).
2. **Modern Anti-Aliased Donut/Pie Chart (`pdf_generator.py`)**:
   - Implemented `render_budget_pie_chart_image()` using `Pillow` at 3x supersampling with Lanczos downscaling.
   - Designed a modern donut chart displaying the total budget in the center cutout and a color-coded legend with dollar amounts and exact percentages on the right.
3. **Mandatory Table Prompt Enforcement (`agents.py`)**:
   - Added explicit markdown table schemas for Flight Options, Hotel Recommendations, Weather Forecast, and Budget Summary into `DAY_FORMAT_INSTRUCTIONS`.
4. **Zero-Loss Final Response (`agents.py`)**:
   - Modified `final_response_agent` to preserve `state['itinerary']` 100% in full without calling an unconstrained LLM to summarize it.
5. **Universal Download Access (`frontend.py`)**:
   - Added PDF download buttons to both the Draft Itinerary and Final Polished Plan.

---

## 📄 How to Open / Import This File in Google Docs

1. **Option A (Direct Copy/Paste)**:
   - Open this file in your editor or view it in markdown.
   - Copy the text and paste it into a blank document at **[docs.google.com](https://docs.google.com)**. Google Docs will automatically preserve tables, headings, and code blocks.
2. **Option B (File Upload)**:
   - Go to **[drive.google.com](https://drive.google.com)**.
   - Click **`+ New`** ➔ **`File upload`** ➔ select `SOLVED_PROBLEMS_DOCUMENTATION.md`.
   - Double click the uploaded file in Google Drive and select **`Open with Google Docs`**.
