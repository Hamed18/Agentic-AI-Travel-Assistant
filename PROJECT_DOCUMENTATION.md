# Project Documentation: SagaTraveller:Agentic AI Travel Assistant

## Title
**Agentic AI Travel Assistant** – an autonomous multi‑agent system that generates travel itineraries and publishes a print‑ready PDF.

---

## Features
| Feature | Description |
|--------|-------------|
| **Itinerary Generation** | Users provide a travel query; a supervisor agent routes the request to specialist agents (flight, hotel, weather, budget, itinerary) which collaboratively produce a markdown itinerary.
| **PDF Generation Engine** | `pdf_generator.py` converts the markdown itinerary into a fully‑styled A4 PDF, rendering day‑wise cards, tables, a budget donut chart, and brand logo.
| **Streamlit Front‑end** | Interactive UI (`frontend.py`) for query entry, itinerary preview, and a **Download PDF** button.
| **LLM Guardrails** | Input guardrail (`supervisor_agent`) validates user queries; fallback LLM handling for rate‑limits.
| **Chart Rendering** | Budget allocation visualised via Pillow‑generated donut chart (`render_budget_pie_chart_image`).
| **Observability** | Prometheus metrics and structured logging expose latency, success/failure counts, and error categories.
| **Configuration** | `config.py` provides model selection, environment variables, and API keys.

---

## Challenges Overcome
| # | Challenge | Solution |
|---|-----------|----------|
| P0‑1 | **Missing tables & content in PDF** – earlier engine silently dropped tables. | Switched to `fpdf2.table` context manager and added explicit colour/font resets.
| P0‑2 | **Budget visualisation** – no chart previously. | Implemented Pillow‑based donut chart and integrated it into the PDF layout.
| P0‑3 | **Content parity** – UI preview showed data that PDF omitted. | Defined a **content‑parity specification** and added automated diff tests.
| P0‑4 | **Markdown parsing robustness** – malformed markdown caused crashes. | Added `FR‑8` markdown validation, strict JSON extraction, and graceful fallback placeholders.
| P0‑5 | **Performance** – PDF generation exceeded 2 s on larger itineraries. | Optimised layout loops, cached chart images, and limited resource usage.
| P0‑6 | **Error handling** – retries on transient failures only. | Categorised errors (validation, render, resource) and applied targeted retry logic.
| P1‑1 | **Pagination & overflow** – long tables caused clipping. | Implemented page‑break rules, header repetition, and orphan‑heading avoidance.
| P1‑2 | **Input safety & privacy** – potential HTML/file injection. | Sanitised markdown, blocked image paths, and enforced size limits.
| P1‑3 | **Internationalisation** – Unicode characters were garbled. | Bundled Noto Sans font with full Unicode coverage.

---

## Database Tables & Structure
> The current implementation is **stateless** and does **not** persist itinerary data in a database. All data flows in‑memory:
- **Markdown → Normalised Model → PDF**
- If a future version requires persistence, a simple relational schema could be:
```sql
CREATE TABLE itineraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    markdown TEXT NOT NULL
);

CREATE TABLE days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    itinerary_id INTEGER REFERENCES itineraries(id),
    day_number INTEGER,
    date TEXT,
    location TEXT,
    activities TEXT   -- JSON array of strings
);

CREATE TABLE budget (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    itinerary_id INTEGER REFERENCES itineraries(id),
    category TEXT,
    amount NUMERIC
);
```
> For now, the system relies on *runtime objects* defined in `state.py` (`TravelState`).

---

## UI/UX Overview
- **Landing page** – simple text box for the travel query and a **Generate** button.
- **Itinerary preview** – rendered markdown shown in a scrollable panel; colour‑coded day cards.
- **Download section** – once the markdown is ready, a **Download PDF** button appears with a spinner while the PDF is being generated.
- **Error handling** – toast notifications for validation errors or generation failures.
- **Branding** – SAGATRAVELLER logo and motto appear on the PDF cover page.

### Wireframe (placeholder)
![UI Mockup](file:///C:/Users/WALTON/.gemini/antigravity/brain/bf37c4dd-7c8c-4057-a181-2b053bdef338/media_1791130652803.png)

---

## Folder Structure
```
Multi_agent_system_part_3-main/
│   README.md                 # Project overview
│   requirements.txt          # Python dependencies
│   config.py                 # API keys, model selection
│   state.py                  # TravelState dataclass
│   agents.py                 # Supervisor & specialist agents
│   pdf_generator.py          # Core PDF rendering logic
│   frontend.py               # Streamlit UI
│   SOLVED_PROBLEMS_DOCUMENTATION.md
│   PRD.md                    # Product Requirements Document
│   project_documentation.md   # **This file**
│
├───.venv/                    # Virtual environment (ignored in repo)
├───.streamlit/               # Streamlit configuration
├───aviationstack-mcp/        # MCP server for aviation data
├───graph.py                  # Optional graph utilities
├───mcp_client.py             # MCP client wrappers (weather, etc.)
├───weather_mcp_server.py     # Weather MCP server
└───scratch/                  # Temporary files, test PDFs, charts
      page_3.png               # Budget donut chart used in docs
```

---

## System Architecture Diagram
```mermaid
flowchart TD
    subgraph UI [Streamlit Front‑end]
        A[User Query Input]
        B[Itinerary Preview]
        C[Download PDF Button]
    end

    subgraph AgentLayer [Multi‑Agent Core]
        D[Supervisor Agent]
        E[Flight Agent]
        F[Hotel Agent]
        G[Weather Agent]
        H[Budget Agent]
        I[Itinerary Agent]
    end

    subgraph Engine [PDF Generation Engine]
        J[Markdown Validator & Normaliser]
        K[Internal Itinerary Model]
        L[Layout Engine (pdf_generator.py)]
        M[Chart Renderer (Pillow)]
        N[PDF Bytes]
    end

    A --> D
    D --> E & F & G & H & I
    E --> J
    F --> J
    G --> J
    H --> J
    I --> J
    J --> K
    K --> L
    L --> M
    L --> N
    C --> N
    N -->|download| A
```
### Components & Importance
| Component | Role | What Happens If Removed |
|-----------|------|--------------------------|
| **Streamlit UI** | Collects user input, displays preview, triggers download. | No user interaction; system becomes a headless service.
| **Supervisor Agent** | Validates input, routes to specialist agents, applies guardrails. | Uncontrolled LLM calls; potential misuse or irrelevant processing.
| **Specialist Agents** (flight, hotel, weather, budget, itinerary) | Each provides domain‑specific data and populates markdown sections. | Missing sections (e.g., no flight table) → incomplete PDF.
| **Markdown Validator & Normaliser** | Ensures markdown conforms to the contract before rendering. | Malformed markdown could crash the PDF engine or produce missing content.
| **Internal Itinerary Model** | Canonical data representation used by UI and PDF engine. | Divergence between UI and PDF; loss of content parity.
| **Layout Engine (`pdf_generator.py`)** | Turns the model into a printable PDF with proper pagination. | No PDF output or broken layout (overlap, missing tables).
| **Chart Renderer** | Generates the budget donut chart image. | Budget visualisation disappears; chart placeholder shown.
| **Prometheus Metrics / Logging** | Observability for performance and error tracking. | No insight into failures; hard to meet SLA.

---

## API Integration
| API | Purpose | Used In |
|-----|---------|----------|
| **OpenAI** (via `openai` library) | LLM inference for routing and content generation. | `agents.py` – `_llm_text` helper.
| **Aviationstack MCP** | Real‑time flight data (airlines, airports). | `aviationstack_mcp_server.py` & `agents.py` flight agent.
| **Weather MCP** | Current weather & forecast. | `weather_mcp_server.py` & `agents.py` weather agent.
| **Tavily Search** | Web search fallback for missing information. | `agents.py` – used when other agents lack data.
| **Prometheus** | Metrics export. | `pdf_generator.py` and various utilities emit counters.

All calls are **server‑side only**; the front‑end never contacts external services directly.

---

## LLM Models Used
| Model | Provider | Role | Reason for Choice |
|-------|----------|------|-------------------|
| **NVIDIA Nemotron 3 Super 120B** | NVIDIA (via OpenAI compatible endpoint) | Primary LLM for guardrails, routing, and content generation. | Large context window, free tier, strong reasoning.
| **NVIDIA Nemotron 3.5 Lightning** | NVIDIA | Fallback when primary hits rate limits or out‑of‑credits. | Faster, cheaper, still high‑quality for continuation.

Both models are accessed through the `openai` Python client; the wrapper in `config.py` abstracts the endpoint and API key.

---

## Overall Project Documentation Summary
- **Title & Vision** – Provide a one‑click, brandable PDF itinerary that mirrors the interactive UI.
- **Features** – Multi‑agent planning, robust PDF rendering, chart visualisation, observability.
- **Challenges Solved** – Content loss, missing charts, performance, safety, internationalisation.
- **Data Model** – Currently in‑memory; a relational schema is outlined for future persistence.
- **UI/UX** – Simple Streamlit flow with real‑time preview and download.
- **Folder Layout** – Clear separation of agents, PDF engine, configuration, and temporary assets.
- **Architecture** – Diagram and component impact analysis provided.
- **APIs** – LLM, aviation, weather, search, and monitoring services.
- **LLM Stack** – Primary + fallback NVIDIA models with automatic failover.

