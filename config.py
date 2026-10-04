import os
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

def get_llm():
    api_key = get_secret("OPENROUTER_API_KEY") or get_secret("OPENAI_API_KEY")
    model = get_secret("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct")
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )
