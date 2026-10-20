# Build a Multi-Agent Travel Planning System using LangGraph + MCP | Supervisor Agent + Guardrails + Human-in-the-Loop

---

# Requirements

## APIs

- Groq API: https://console.groq.com
- Tavily API: https://www.tavily.com/
- AviationStack API: https://aviationstack.com/
- OpenWeatherMap API: https://openweathermap.org/

## Tools

- PostgreSQL: https://www.postgresql.org/download/
- Tavily MCP Server: https://docs.tavily.com/documentation/mcp

---

# Step 1: Create Python Environment


    python -m venv langgraph_env3


Activate:


    langgraph_env3\Scripts\activate


---

# Step 2: Install Dependencies


    pip install langgraph langchain langchain-openai langchain-groq langchain-community langchain-tavily psycopg[binary] psycopg_pool python-dotenv tavily-python requests streamlit



    pip install -U "psycopg[binary,pool]" langgraph-checkpoint-postgres


---

# Step 3: Install PostgreSQL

Download PostgreSQL:

https://www.postgresql.org/download/

**Important:** Note your PostgreSQL password and port number during installation.

---

# Step 4: Create Database


    CREATE DATABASE langgraph_memory_demo;


---

# Step 5: Setup .env File

Create a `.env` file:

    GROQ_API_KEY=your_groq_api_key

    TAVILY_API_KEY=your_tavily_api_key

    AVIATIONSTACK_API_KEY=your_aviationstack_api_key

    DATABASE_URL=postgresql://postgres:postgres@localhost:5433/langgraph_memory_demo


---

# Step 6: Get API Keys

- Groq: https://console.groq.com
- Tavily: https://tavily.com
- AviationStack: https://aviationstack.com
- OpenWeatherMap: https://openweathermap.org/

---

# Setup AviationStack MCP Server (Local MCP Server)

Repository:

https://github.com/Pradumnasaraf/aviationstack-mcp

Open PowerShell:

    E:

    cd E:\Multi_agent_system_with_MCP


Clone repository:


    git clone https://github.com/Pradumnasaraf/aviationstack-mcp.git

    cd aviationstack-mcp


## Install UV

Check:

    uv --version


Install:

    pip install uv


If installation fails:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"


## Create .env File

    AVIATION_STACK_API_KEY=your_api_key_here


## Install Dependencies

    uv sync


This will:

- Create `.venv`
- Install dependencies
- Install AviationStack MCP package

## Activate Environment

    .venv\Scripts\activate


## Start MCP Server

    uv run -m aviationstack_mcp mcp run


or


    python -m aviationstack_mcp mcp run


The server will remain running and wait for MCP requests.

## Stop Server

    CTRL + C


---

# Setup Weather MCP Server

Get API key:

https://openweathermap.org/

Add the API key to your `.env` file.

Install dependencies:

    pip install mcp requests


---

# Run the Application

## Streamlit Web App
Run:

    streamlit run frontend.py


---

# Example Prompt

    Plan a complete 7 days Japan trip including flights, hotels and sightseeing under 2 lakhs.


---

# Features

- Multi-Agent Architecture using LangGraph
- PostgreSQL Memory
- Tavily Search Integration
- AviationStack MCP Integration
- Weather MCP Integration
- Streamlit Web App
- Real-Time Travel Planning
- Human in the loop
- Guardrails
- **Enterprise Observability & Tracing**: LangSmith DAG visualization, Langfuse token & cost analytics, and Sentry runtime crash monitoring

---

# Observability, Tracing & Monitoring Stack

The system incorporates an enterprise-grade multi-layer observability architecture designed to track multi-agent execution, latency bottlenecks, token consumption, cost analytics, and runtime exceptions.

## Features Added

### 1. LangSmith Tracing
- **Multi-Agent DAG Visualization**: Real-time graph execution visualization across LangGraph nodes (`supervisor_agent`, `parallel_specialists`, `budget_agent`, `itinerary_agent`, `human_approval_agent`, and `final_response_agent`).
- **State Transition Inspection**: Full visibility into intermediate state payloads passed across the pipeline.
- **Failover Tracing**: Real-time auditing of distributed model routing from Groq LPU (`qwen/qwen3.8-27b` / `openai/gpt-oss-120b`) to Google Gemini (`gemini-3.5-flash-lite`).
- **Prompt & Output Audit**: Granular inspection of prompts, token counts, and completions.

### 2. Langfuse Analytics (v5)
- **Token & Cost Analytics**: Real-time cost estimation per trip generation based on actual token usage.
- **Latency Breakdown Waterfall**: Precise per-agent and per-tool duration metrics (identifying slow MCP tool calls vs LLM synthesis).
- **Session & User Tracking**: Grouping traces by `session_id` and `user_id` to trace continuous user interactions across revisions.
- **Direct Cloud Telemetry**: Real-time streaming to the regional cloud endpoint (`https://jp.cloud.langfuse.com`).

### 3. Sentry Crash & Error Guard
- **Automated Exception Capture**: Intercepts unhandled errors, socket disconnects, and database connection drops with full stack traces.
- **Runtime Breadcrumbs**: Logs prior operations leading up to a failure for rapid debugging in deployed production environments.

---

## How to Run Observability

### 1. Running Locally

#### A. Run Dedicated Observability Verification Test:
Execute the standalone test script to verify that traces are successfully delivered to both LangSmith and Langfuse:
```powershell
.\.venv\Scripts\python.exe test_observability.py
```
This runs an isolated query through the Distributed LLM tier, triggers callbacks, and outputs verification links.

#### B. Run the Local Web App with Live Tracing:
```powershell
streamlit run frontend.py
```
Every prompt submitted through the UI automatically attaches `get_callbacks()` from `observability.py`. Traces for each agent step will immediately appear in your cloud dashboards.

#### C. Local Dashboard Access:
- **LangSmith**: Open [https://smith.langchain.com](https://smith.langchain.com) ➔ Select project **`Agentic-AI-Travel-Assistant`**.
- **Langfuse**: Open [https://jp.cloud.langfuse.com](https://jp.cloud.langfuse.com) ➔ Select project **`travel-assistant`** ➔ Click **Traces**.
- **Sentry**: Open [https://sentry.io](https://sentry.io) to review active issues.

---

### 2. Running in Production Deployed URL (Render + Vercel)

When deploying the backend to **Render** (Docker container) and frontend to **Vercel**:

#### Step 1: Set Environment Variables in Render Dashboard
Under your Render Web Service ➔ **Environment**:
```env
# LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=Agentic-AI-Travel-Assistant
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Langfuse
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_BASE_URL=https://jp.cloud.langfuse.com

# Sentry (Optional for error alerting)
SENTRY_DSN=your_sentry_project_dsn
```

#### Step 2: Automatic Production Tracing
- `observability.py` automatically detects these environment variables at container startup.
- All live production requests made to your deployed backend URL (`https://your-app.onrender.com/api/...`) stream real-time telemetry to LangSmith and Langfuse.
- If any specialist agent times out, hits rate limits, or crashes in production, Sentry and Langfuse record the exact failure point, input parameters, and stack trace without needing SSH or server access.

---

# how to run in fewer commands:
To run this project from scratch (for example, if you restart your computer or open a new terminal), you only need to run a couple of commands because all the heavy lifting (database setup, dependency installation, and MCP server configuration) is already done!

Here are the steps to launch the app:

**1. Open a terminal (PowerShell) and navigate to the project directory:**
```powershell
cd "E:\AI App\Multi Agent Tour Guide\Multi_agent_system_part_3-main\Multi_agent_system_part_3-main"
```

**2. Activate the virtual environment:**
```powershell
.\.venv\Scripts\activate
```

**3. Start the Streamlit application:**
```powershell
streamlit run frontend.py
```

*Note: Your PostgreSQL database runs in the background as a Windows service automatically, and the AviationStack and Weather servers are automatically booted up by the application itself when it needs them. So, these three commands above are the only ones you'll ever need to run!*"# Agentic-AI-Travel-Assistant" 
