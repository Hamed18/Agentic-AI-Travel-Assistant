"""
main.py - Production FastAPI Backend for Agentic AI Travel Assistant
Decoupled API layer serving Server-Sent Events (SSE), Human-in-the-Loop workflows,
and PDF generation for the modern React frontend (Vercel) & Render container deployment.
"""

import os
import sys
import json
import uuid
import logging
import asyncio
from typing import Optional, AsyncGenerator

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

# Project imports
from config import DATABASE_URL
from graph import build_graph
from langgraph.types import Command
from pdf_generator import create_pdf
from observability import get_callbacks, flush_observability

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("travel_api")

app = FastAPI(
    title="Agentic AI Travel Assistant API",
    description="Multi-Agent Travel Planning System powered by LangGraph, MCP, and Distributed LLMs",
    version="1.0.0",
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
# Allow React local dev (Vite: 5173, Next.js: 3000) and deployed Vercel domains
raw_origins = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# Allow any Vercel preview/production URL via regex pattern
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_origin_regex=r"https:\/\/.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Reusable LangGraph runtime instance
graph_app = build_graph()


# ── Request / Response Schemas ────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str = Field(..., description="User trip request or query")
    thread_id: Optional[str] = Field(default_factory=lambda: f"user_{uuid.uuid4().hex[:8]}")
    user_id: Optional[str] = Field(default="demo_user")


class ResumeRequest(BaseModel):
    thread_id: str = Field(..., description="Active LangGraph thread session ID")
    approved: bool = Field(default=True, description="Approval decision: True to polish, False to revise")
    feedback: Optional[str] = Field(default="", description="User revision instructions if rejected")


class PDFRequest(BaseModel):
    itinerary_markdown: str = Field(..., description="Full approved itinerary markdown string")
    filename: Optional[str] = Field(default="Travel_Plan.pdf")


# ── Health & Info Endpoints ───────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "Agentic AI Travel Assistant API",
        "status": "running",
        "docs": "/docs",
        "version": "1.0.0",
        "tier": "Distributed (Groq LPU + Google Gemini Fallback)",
    }


@app.get("/health")
@app.get("/api/health")
async def health_check():
    db_status = "unconfigured"
    if DATABASE_URL:
        try:
            import psycopg
            conn = psycopg.connect(DATABASE_URL)
            conn.close()
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)[:100]}"
            logger.warning(f"Healthcheck database warning: {e}")

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "runtime": "FastAPI + LangGraph",
        "observability": "LangSmith + Langfuse v5 active",
    }


# ── Thread State Inspection ───────────────────────────────────────────────────
@app.get("/api/threads/{thread_id}/state")
async def get_thread_state(thread_id: str):
    """Retrieves current state snapshot and pending interrupts for a thread."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = graph_app.get_state(config)
        return {
            "thread_id": thread_id,
            "next": list(snapshot.next) if snapshot.next else [],
            "values": {
                k: v for k, v in snapshot.values.items()
                if k not in ["messages"]  # Exclude raw LangChain objects for clean JSON
            },
            "is_interrupted": bool(snapshot.next),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load thread state: {str(e)}")


# ── Real-Time Streaming Chat Endpoint (SSE) ───────────────────────────────────
@app.post("/api/chat/stream")
async def stream_chat(req: ChatRequest):
    """
    Initiates a trip planning request and streams real-time stage updates via Server-Sent Events (SSE).
    Streams agent completions (supervisor, parallel_specialists, budget, itinerary) and interrupts.
    """
    thread_id = req.thread_id
    user_id = req.user_id
    query = req.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": get_callbacks(session_id=thread_id, user_id=user_id, tags=["chat-stream"])
    }

    initial_state = {
        "user_query": query,
        "user_id": user_id,
        "messages": [],
        "flight_results": "",
        "hotel_results": "",
        "weather_results": "",
        "budget_results": "",
        "itinerary": "",
        "final_response": "",
        "approved": False,
        "human_feedback": "",
        "llm_calls": 0,
    }

    async def event_generator() -> AsyncGenerator[dict, None]:
        # 1. Emit start event
        yield {
            "event": "start",
            "data": json.dumps({"thread_id": thread_id, "query": query})
        }

        latest_state = {}

        try:
            # Run graph stream in a thread pool executor to maintain non-blocking async SSE
            loop = asyncio.get_event_loop()

            def _run_stream():
                chunks = []
                for chunk in graph_app.stream(initial_state, config=config, stream_mode="updates"):
                    chunks.append(chunk)
                return chunks

            # Stream graph updates
            # Note: We stream node-by-node updates to notify the frontend as each specialist completes
            for chunk in graph_app.stream(initial_state, config=config, stream_mode="updates"):
                for node_name, node_update in chunk.items():
                    if isinstance(node_update, dict):
                        latest_state.update(node_update)

                        # Emit stage-specific payloads
                        stage_payload = {
                            "node": node_name,
                            "thread_id": thread_id,
                        }

                        if node_name == "supervisor":
                            stage_payload["is_valid"] = node_update.get("is_valid", True)
                            stage_payload["intent"] = node_update.get("intent", "trip_planning")
                            stage_payload["response_type"] = node_update.get("response_type", "chat")
                            stage_payload["selected_agents"] = node_update.get("selected_agents", [])
                            stage_payload["trip_constraints"] = node_update.get("trip_constraints", {})
                            stage_payload["reasoning"] = node_update.get("supervisor_reasoning", "")
                            stage_payload["direct_response"] = node_update.get("direct_response", "")

                        elif node_name == "direct_response":
                            stage_payload["final_response"] = node_update.get("final_response", "")

                        elif node_name == "parallel_specialists":
                            stage_payload["has_flights"] = bool(node_update.get("flight_results"))
                            stage_payload["has_hotels"] = bool(node_update.get("hotel_results"))
                            stage_payload["has_weather"] = bool(node_update.get("weather_results"))

                        elif node_name == "budget_agent":
                            stage_payload["budget_results"] = node_update.get("budget_results", "")

                        elif node_name == "itinerary_agent":
                            stage_payload["itinerary"] = node_update.get("itinerary", "")

                        yield {
                            "event": "node_complete",
                            "data": json.dumps(stage_payload)
                        }

            # Check if execution paused at human-in-the-loop interrupt
            snapshot = graph_app.get_state(config)
            intent = latest_state.get("intent", "trip_planning")

            if snapshot.next and intent == "trip_planning":
                logger.info(f"[SSE] Thread {thread_id} paused at interrupt: {snapshot.next}")
                itinerary_draft = latest_state.get("itinerary") or snapshot.values.get("itinerary", "")
                yield {
                    "event": "interrupt",
                    "data": json.dumps({
                        "node": "human_approval",
                        "thread_id": thread_id,
                        "draft_itinerary": itinerary_draft,
                        "message": "Human approval required to polish and finalize plan."
                    })
                }
            else:
                final = latest_state.get("final_response") or latest_state.get("direct_response") or latest_state.get("itinerary", "")
                resp_type = latest_state.get("response_type", "itinerary" if latest_state.get("itinerary") else "chat")
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "thread_id": thread_id,
                        "final_response": final,
                        "itinerary": latest_state.get("itinerary", ""),
                        "intent": intent,
                        "response_type": resp_type,
                    })
                }

        except Exception as e:
            logger.exception(f"[SSE Error] Failed processing thread {thread_id}: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e), "thread_id": thread_id})
            }

        finally:
            flush_observability()

    return EventSourceResponse(event_generator())


# ── Human-in-the-Loop Resume Endpoint (SSE) ───────────────────────────────────
@app.post("/api/chat/resume")
async def resume_chat(req: ResumeRequest):
    """
    Resumes a paused conversation after the user approves or requests revisions.
    Streams final polishing or newly generated revision itinerary via SSE.
    """
    thread_id = req.thread_id
    is_approved = req.approved
    feedback = req.feedback.strip() if req.feedback else ""

    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": get_callbacks(session_id=thread_id, tags=["chat-resume"])
    }

    resume_payload = {
        "approved": is_approved,
        "feedback": feedback
    }

    async def resume_event_generator() -> AsyncGenerator[dict, None]:
        yield {
            "event": "resume_start",
            "data": json.dumps({"thread_id": thread_id, "approved": is_approved, "feedback": feedback})
        }

        latest_state = {}

        try:
            for chunk in graph_app.stream(
                Command(resume=resume_payload),
                config=config,
                stream_mode="updates"
            ):
                for node_name, node_update in chunk.items():
                    if isinstance(node_update, dict):
                        latest_state.update(node_update)

                        yield {
                            "event": "node_complete",
                            "data": json.dumps({
                                "node": node_name,
                                "thread_id": thread_id,
                                "data": {k: v for k, v in node_update.items() if k != "messages"}
                            })
                        }

            # Inspect if another interrupt occurred (e.g. user requested revision and new draft is ready)
            snapshot = graph_app.get_state(config)
            if snapshot.next:
                itinerary_draft = latest_state.get("itinerary") or snapshot.values.get("itinerary", "")
                yield {
                    "event": "interrupt",
                    "data": json.dumps({
                        "node": "human_approval",
                        "thread_id": thread_id,
                        "draft_itinerary": itinerary_draft,
                        "is_revision": True,
                        "message": "Revised plan ready for your review."
                    })
                }
            else:
                final = latest_state.get("final_response") or latest_state.get("itinerary", "")
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "thread_id": thread_id,
                        "final_response": final,
                        "itinerary": latest_state.get("itinerary", "")
                    })
                }

        except Exception as e:
            logger.exception(f"[SSE Resume Error] Failed resuming thread {thread_id}: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e), "thread_id": thread_id})
            }

        finally:
            flush_observability()

    return EventSourceResponse(resume_event_generator())


# ── PDF Generation Endpoint ───────────────────────────────────────────────────
@app.post("/api/pdf")
async def generate_pdf_endpoint(req: PDFRequest):
    """
    Renders publication-grade PDF from approved itinerary markdown with anti-aliased donut chart.
    Returns binary PDF stream with attachment header for instant browser download.
    """
    if not req.itinerary_markdown or not req.itinerary_markdown.strip():
        raise HTTPException(status_code=400, detail="itinerary_markdown cannot be empty.")

    try:
        pdf_bytes = create_pdf(req.itinerary_markdown)
        safe_filename = req.filename if req.filename.endswith(".pdf") else f"{req.filename}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}"',
                "Content-Length": str(len(pdf_bytes)),
            }
        )
    except Exception as e:
        logger.exception(f"PDF compilation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


# ── App Shutdown ──────────────────────────────────────────────────────────────
@app.on_event("shutdown")
def on_shutdown():
    logger.info("Flushing pending observability events before shutdown...")
    flush_observability()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
