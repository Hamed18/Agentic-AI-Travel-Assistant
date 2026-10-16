import os
import time
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

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

GROQ_API_KEY = get_secret("GROQ_API_KEY")
GEMINI_API_KEY = get_secret("GEMINI_API_KEY")

# Distributed Multi-Provider Model Slugs (100% Free Tier):
# Fast Tier (Guardrail / Routing): Groq Qwen 27B -> Google Gemini 3.5 Flash Lite
GROQ_FAST_MODEL = "qwen/qwen3.8-27b"

# Heavy Tier (Itinerary / Flights / Budget): Groq GPT-OSS 120B -> Google Gemini 3.5 Flash Lite
GROQ_HEAVY_MODEL = "openai/gpt-oss-120b"

# Google Gemini Flash Lite (Massive 1M TPM buffer, exceptional multi-day generation)
GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def _create_groq_llm(model: str, max_tokens: int = 4096, timeout: float = 25.0):
    if not GROQ_API_KEY:
        return None
    return ChatGroq(
        model_name=model,
        groq_api_key=GROQ_API_KEY,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=1,
    )


def _create_gemini_llm(max_tokens: int = 4096, timeout: float = 30.0):
    if not GEMINI_API_KEY:
        return None
    return ChatOpenAI(
        model=GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        base_url=GEMINI_BASE_URL,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=1,
    )


class DistributedLLM:
    """
    Resilient Multi-Provider LLM Executor:
    - Bypasses single-model RPM/TPM rate limits through automatic cross-provider failover.
    - Low-latency primary execution on Groq LPU (~1.5–3.5s).
    - High-capacity fallback on Google Gemini (~6–8s, 1M TPM buffer).
    - Completely eliminates slow and stalled single-provider models.
    """

    def __init__(self, tier: str = "heavy"):
        self.tier = tier

    def invoke(self, messages, **kwargs):
        candidates = []

        if self.tier == "fast":
            # Fast tier: Groq Qwen 27B (~1.8s) -> Gemini 3.5 Flash Lite (~6.8s)
            groq_client = _create_groq_llm(GROQ_FAST_MODEL, max_tokens=1024, timeout=12.0)
            gemini_client = _create_gemini_llm(max_tokens=2048, timeout=20.0)
            if groq_client:
                candidates.append(("Groq (Qwen 27B)", groq_client))
            if gemini_client:
                candidates.append(("Google Gemini (3.5 Flash Lite)", gemini_client))
        else:
            # Heavy tier: Groq GPT-OSS 120B (~3.5s) -> Gemini 3.5 Flash Lite (~6.8s)
            groq_client = _create_groq_llm(GROQ_HEAVY_MODEL, max_tokens=4096, timeout=25.0)
            gemini_client = _create_gemini_llm(max_tokens=4096, timeout=30.0)
            if groq_client:
                candidates.append(("Groq (GPT-OSS 120B)", groq_client))
            if gemini_client:
                candidates.append(("Google Gemini (3.5 Flash Lite)", gemini_client))

        last_error = None
        for name, client in candidates:
            try:
                t0 = time.time()
                response = client.invoke(messages, **kwargs)
                content = response.content if hasattr(response, "content") else str(response)
                if content and content.strip():
                    elapsed = round(time.time() - t0, 2)
                    print(f"  [OK] [{name}] responded successfully in {elapsed}s")
                    return response
                print(f"  [WARN] [{name}] returned empty content, trying fallback provider...")
            except Exception as e:
                last_error = e
                print(f"\n[DISTRIBUTED FAILOVER] Provider '{name}' hit limit or error: {e}")
                print(f"  --> Automatically routing to next distributed provider...\n")

        raise RuntimeError(f"All distributed LLM providers failed. Last error: {last_error}")


def get_llm(model: str = None):
    """Returns the primary DistributedLLM configured for heavy reasoning and itinerary synthesis."""
    return DistributedLLM(tier="heavy")


def get_fallback_llm():
    """Returns the fast DistributedLLM configured for lightweight routing and guardrails."""
    return DistributedLLM(tier="fast")
