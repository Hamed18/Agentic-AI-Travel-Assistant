import os
import time
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

def get_secret(key: str, default: str = None) -> str:
    # 1. Check os.environ (from .env file)
    val = os.getenv(key)
    if val:
        return val.strip().replace("\r", "").replace("\n", "")
    
    # 2. Check Streamlit Cloud st.secrets
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            s_val = str(st.secrets[key]).strip().replace("\r", "").replace("\n", "")
            os.environ[key] = s_val  # Make available to child processes & OS
            return s_val
    except Exception:
        pass
        
    return default

TAVILY_API_KEY = get_secret("TAVILY_API_KEY")
AVIATION_STACK_API_KEY = get_secret("AVIATION_STACK_API_KEY")
OPENWEATHER_API_KEY = get_secret("OPENWEATHER_API_KEY")
DATABASE_URL = get_secret("DATABASE_URL")
OPENROUTER_API_KEY = get_secret("OPENROUTER_API_KEY")

# Default free model: NVIDIA Nemotron 3 Super 120B (confirmed working, best free JSON quality)
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
# Fallback model: NVIDIA Nemotron Lightning (lighter, faster fallback)
FALLBACK_MODEL = "nvidia/nemotron-3.5-lightning:free"

def get_llm(model: str = None):
    """
    Returns a ChatOpenAI LLM instance configured for OpenRouter.
    - Uses OPENROUTER_MODEL from .env if set, otherwise DEFAULT_MODEL.
    - max_tokens capped at 8192 to stay within free tier limits.
    - max_retries=3 handles transient 429 / 502 errors automatically.
    - extra_headers tells OpenRouter which app is calling (for routing/debugging).
    """
    api_key = get_secret("OPENROUTER_API_KEY") or get_secret("OPENAI_API_KEY")
    selected_model = model or get_secret("OPENROUTER_MODEL", DEFAULT_MODEL)

    return ChatOpenAI(
        model=selected_model,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        max_tokens=8192,       # Cap tokens — free tier Gemma max output is ~8192
        max_retries=3,         # Auto-retry on transient 429/502 errors (with backoff)
        default_headers={
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "AI Travel Assistant",
        },
    )

def get_fallback_llm():
    """Returns fallback LLM when primary model is rate-limited."""
    api_key = get_secret("OPENROUTER_API_KEY") or get_secret("OPENAI_API_KEY")
    return ChatOpenAI(
        model=FALLBACK_MODEL,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        max_tokens=8192,
        max_retries=3,
        default_headers={
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "AI Travel Assistant",
        },
    )
