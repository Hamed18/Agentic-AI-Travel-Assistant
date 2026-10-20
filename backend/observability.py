"""
observability.py - Unified Tracing, Logging & Error Monitoring
Integrates:
1. LangSmith: Native LangChain/LangGraph execution tree and state tracing
2. Langfuse: Real-time LLM cost analytics, token counts, latency breakdowns, and sessions
3. Sentry: Runtime exception capturing, error alerts, and stack trace monitoring
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("observability")

# --- 1. Sentry Runtime Crash Monitoring ---
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN and SENTRY_DSN.startswith("http"):
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            environment=os.getenv("ENVIRONMENT", "development"),
        )
        logger.info("[Observability] Sentry initialized successfully.")
    except Exception as e:
        logger.warning(f"[Observability] Failed to initialize Sentry: {e}")
else:
    logger.info("[Observability] Sentry DSN not provided or invalid. Sentry disabled until DSN is set.")

# --- 2. LangSmith Tracing ---
LANGSMITH_KEY = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
if LANGSMITH_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_KEY
    if not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = "Agentic-AI-Travel-Assistant"
    logger.info(f"[Observability] LangSmith tracing active for project: {os.environ['LANGCHAIN_PROJECT']}")
else:
    logger.info("[Observability] LangSmith API key not configured.")

# --- 3. Langfuse Tracing ---
_LANGFUSE_CLIENT = None

def get_langfuse_client():
    global _LANGFUSE_CLIENT
    if _LANGFUSE_CLIENT is None:
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        if public_key and secret_key:
            try:
                from langfuse import Langfuse
                _LANGFUSE_CLIENT = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
            except Exception as e:
                logger.warning(f"[Observability] Could not initialize Langfuse client: {e}")
    return _LANGFUSE_CLIENT

def get_langfuse_callback(session_id: str = None, user_id: str = None, tags: list = None):
    """
    Returns an initialized Langfuse CallbackHandler for LangGraph / LangChain.
    Pass this into graph config: config = {'callbacks': [get_langfuse_callback(...)]}
    """
    client = get_langfuse_client()
    if not client:
        return None

    try:
        from langfuse.langchain import CallbackHandler
        from langfuse.types import TraceContext
        
        trace_context = None
        if session_id or user_id or tags:
            trace_context = TraceContext(
                session_id=session_id,
                user_id=user_id,
                tags=tags or ["travel-assistant"]
            )
            
        handler = CallbackHandler(trace_context=trace_context)
        return handler
    except Exception as e:
        logger.warning(f"[Observability] Could not create Langfuse callback: {e}")
        return None


def get_callbacks(session_id: str = None, user_id: str = None, tags: list = None):
    """
    Returns all active callback handlers for LangGraph execution.
    """
    callbacks = []
    lf_cb = get_langfuse_callback(session_id=session_id, user_id=user_id, tags=tags)
    if lf_cb:
        callbacks.append(lf_cb)
    return callbacks


def flush_observability():
    """Flushes any pending async traces (useful during shutdown or test scripts)."""
    client = get_langfuse_client()
    if client:
        try:
            client.flush()
        except Exception:
            pass
