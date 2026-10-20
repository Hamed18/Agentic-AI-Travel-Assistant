"""
test_observability.py - Verification script for LangSmith and Langfuse Tracing
Usage:
    .\\.venv\\Scripts\\python.exe test_observability.py
"""

import sys
import os
import uuid
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

sys.stdout.reconfigure(encoding="utf-8")

import observability
from config import get_fallback_llm, get_llm
from observability import get_callbacks, flush_observability

def test_tracing():
    print("=" * 60)
    print("🔍 TESTING OBSERVABILITY & TRACING")
    print("=" * 60)

    test_session_id = f"test-trace-{uuid.uuid4().hex[:6]}"
    print(f"\n[1/3] Generated Test Session ID: {test_session_id}")

    callbacks = get_callbacks(session_id=test_session_id, user_id="admin-test")
    print(f"[2/3] Active Callbacks configured: {[type(cb).__name__ for cb in callbacks]}")

    print("\n[3/3] Invoking Distributed LLM (Groq Qwen 27B) with LangSmith & Langfuse tracking...")
    llm = get_fallback_llm()
    
    t0 = time.time()
    response = llm.invoke(
        "Give a 1-sentence travel tip for visiting Tokyo, Japan in Autumn.",
        config={"callbacks": callbacks}
    )
    elapsed = round(time.time() - t0, 2)

    content = response.content if hasattr(response, "content") else str(response)
    print(f"\n✔ LLM Response ({elapsed}s):\n  \"{content.strip()}\"")

    flush_observability()
    print("\n" + "=" * 60)
    print("🎉 TRACES SENT SUCCESSFULLY!")
    print("=" * 60)
    print("\n👉 Check your dashboards now to view the real-time execution trace:")
    print("   1. LangSmith: https://smith.langchain.com")
    print("      Project: 'Agentic-AI-Travel-Assistant'")
    print("   2. Langfuse:  https://jp.cloud.langfuse.com")
    print("      Project: 'travel-assistant' -> Traces / Generations")
    print("=" * 60)

if __name__ == "__main__":
    test_tracing()
