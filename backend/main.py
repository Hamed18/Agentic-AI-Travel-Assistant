"""
main.py - Production FastAPI Backend for Agentic AI Travel Assistant
Decoupled API layer serving Server-Sent Events (SSE), Human-in-the-Loop workflows,
PDF generation, JWT Authentication (P1), Multi-Tenant Isolation (P2),
Episodic Memory (P3), and Admin Document Ingestion (P4).
"""

import os
import sys

# Ensure backend directory is in sys.path regardless of execution context
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import json
import uuid
import logging
import asyncio
import re
from typing import Optional, List, Dict, Any, AsyncGenerator

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, Response, Depends, UploadFile, File, Form
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

# Auth (P1)
from auth import (
    SecurityContext,
    get_security_context,
    require_admin,
    register_user,
    authenticate_user,
    create_access_token,
    create_guest_session,
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
)

# Multi-Tenant Isolation & Document Storage (P2)
from tenant_service import (
    save_tenant_file,
    list_tenant_files,
    delete_tenant_file,
    ingest_document_for_tenant,
    search_tenant_documents,
    list_tenant_documents,
    delete_tenant_document_by_name,
)

# Episodic Memory (P3)
from memory_service import (
    save_interaction,
    get_recent_interactions,
    format_memory_context_for_llm,
)

# TTL Reaper (P5)
from reaper_service import (
    purge_expired_guest_data,
    get_reaper_stats,
    start_reaper_background_task,
    stop_reaper_background_task,
)

# Profile Consolidation (P6)
from consolidation_service import (
    trigger_profile_consolidation,
    get_user_profile,
    format_profile_for_llm,
    summarize_and_consolidate,
)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("travel_api")

app = FastAPI(
    title="Agentic AI Travel Assistant API",
    description="Multi-Agent Travel Planning System powered by LangGraph, MCP, Distributed LLMs, and Multi-Tenant Auth",
    version="2.0.0",
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
raw_origins = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_origin_regex=r"https:\/\/.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def normalize_slashes_middleware(request: Request, call_next):
    """Normalize any repeated slashes in the path (e.g. //api/health -> /api/health)"""
    path = request.scope.get("path", "")
    if "//" in path:
        request.scope["path"] = re.sub(r"/+", "/", path)
    return await call_next(request)

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


class TextIngestRequest(BaseModel):
    title: str = Field(..., description="Document or Guide Title")
    content: str = Field(..., description="Text content to chunk, embed, and isolate for tenant")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ── Health & Info Endpoints ───────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "Agentic AI Travel Assistant API",
        "status": "running",
        "docs": "/docs",
        "version": "2.0.0",
        "features": [
            "P1: JWT Authentication & Bcrypt Hashing",
            "P2: Multi-Tenant Vector & File Isolation",
            "P3: Episodic Memory in Neon PostgreSQL",
            "P4: Admin Ingestion Interface",
            "P5: Automated 2-Hour TTL Guest Reaper",
            "P6: Ingestion Summarizer & Profile Consolidation",
        ],
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
        "auth": "JWT + Bcrypt enabled",
    }


# ── Authentication Endpoints (Phase 1) ─────────────────────────────────────────
@app.post("/api/auth/register", response_model=TokenResponse)
async def api_register(req: UserRegisterRequest):
    """Register new user with bcrypt password hashing in Neon DB and return JWT."""
    user = register_user(req)
    token = create_access_token({
        "sub": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "tenant_id": user["tenant_id"],
        "is_guest": False,
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_hours": 24,
        "user": user,
    }


@app.post("/api/auth/login", response_model=TokenResponse)
async def api_login(req: UserLoginRequest):
    """Authenticate existing user against bcrypt hash and return signed JWT."""
    user = authenticate_user(req)
    token = create_access_token({
        "sub": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "tenant_id": user["tenant_id"],
        "is_guest": False,
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_hours": 24,
        "user": user,
    }


@app.post("/api/auth/guest", response_model=TokenResponse)
async def api_guest_session():
    """Create an ephemeral guest session with 2-hour TTL."""
    guest_user = create_guest_session()
    from datetime import timedelta
    token = create_access_token(
        {
            "sub": guest_user["id"],
            "email": None,
            "name": guest_user["name"],
            "role": "guest",
            "tenant_id": guest_user["tenant_id"],
            "is_guest": True,
        },
        expires_delta=timedelta(hours=2)
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_hours": 2,
        "user": guest_user,
    }


@app.get("/api/auth/me")
async def api_get_me(context: SecurityContext = Depends(get_security_context)):
    """Return security context and privileges of current caller."""
    return {
        "user_id": context.user_id,
        "email": context.email,
        "name": context.name,
        "role": context.role,
        "tenant_id": context.tenant_id,
        "is_guest": context.is_guest,
        "is_admin": context.is_admin,
    }


# ── Multi-Tenant Ingestion & Document Endpoints (Phase 2 & Phase 4) ────────────
@app.post("/api/documents/upload")
async def upload_document_endpoint(
    file: UploadFile = File(...),
    context: SecurityContext = Depends(require_admin)
):
    """
    Admin-only endpoint to upload documents into namespaced tenant storage
    and index vector embeddings into tenant_documents table with owner_id = tenant_id.
    """
    content_bytes = await file.read()
    filename = file.filename or "uploaded_doc.txt"

    # Save to namespaced tenant directory
    saved_info = save_tenant_file(context.tenant_id, filename, content_bytes)

    # Decode text content for vector indexing
    try:
        text_content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text_content = content_bytes.decode("latin-1")
        except Exception:
            text_content = f"Binary file: {filename} ({len(content_bytes)} bytes)"

    # Chunk and embed into tenant_documents table with strict owner_id isolation
    doc_ids = ingest_document_for_tenant(
        tenant_id=context.tenant_id,
        filename=filename,
        content=text_content,
        metadata={"uploader": context.email or context.user_id, "role": context.role},
        file_path=saved_info["path"],
        file_size=saved_info["size_bytes"],
    )

    # Phase 6: Asynchronously synthesize and consolidate user profile
    trigger_profile_consolidation(context.tenant_id)

    return {
        "status": "success",
        "filename": filename,
        "size_bytes": saved_info["size_bytes"],
        "chunks_indexed": len(doc_ids),
        "owner_id": context.tenant_id,
    }


@app.post("/api/documents/ingest-text")
async def ingest_text_endpoint(
    req: TextIngestRequest,
    context: SecurityContext = Depends(require_admin)
):
    """Admin-only endpoint to ingest raw guidebooks, policy rules, or custom text."""
    filename = f"{re.sub(r'[^a-zA-Z0-9_-]', '_', req.title)}.txt"
    data = req.content.encode("utf-8")
    saved_info = save_tenant_file(context.tenant_id, filename, data)

    doc_ids = ingest_document_for_tenant(
        tenant_id=context.tenant_id,
        filename=filename,
        content=req.content,
        metadata=req.metadata,
        file_path=saved_info["path"],
        file_size=len(data),
    )

    # Phase 6: Asynchronously synthesize and consolidate user profile
    trigger_profile_consolidation(context.tenant_id)

    return {
        "status": "success",
        "title": req.title,
        "filename": filename,
        "chunks_indexed": len(doc_ids),
        "owner_id": context.tenant_id,
    }


@app.get("/api/documents")
async def list_documents_endpoint(context: SecurityContext = Depends(get_security_context)):
    """List documents isolated strictly to caller's tenant_id."""
    return {
        "tenant_id": context.tenant_id,
        "documents": list_tenant_documents(context.tenant_id),
    }


@app.delete("/api/documents/{filename}")
async def delete_document_endpoint(
    filename: str,
    context: SecurityContext = Depends(require_admin)
):
    """Admin-only deletion of a document for caller's tenant."""
    deleted_chunks = delete_tenant_document_by_name(context.tenant_id, filename)
    return {
        "status": "deleted",
        "filename": filename,
        "deleted_chunks": deleted_chunks,
        "tenant_id": context.tenant_id,
    }


# ── Episodic Memory Endpoints (Phase 3) ─────────────────────────────────────────
@app.get("/api/memory/history")
async def get_memory_history_endpoint(
    limit: int = 10,
    context: SecurityContext = Depends(get_security_context)
):
    """Retrieve recent episodic Q&A history isolated strictly to caller's tenant_id."""
    history = get_recent_interactions(context.tenant_id, limit=limit)
    return {
        "owner_id": context.tenant_id,
        "count": len(history),
        "history": history,
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
                if k not in ["messages"]
            },
            "is_interrupted": bool(snapshot.next),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load thread state: {str(e)}")


# ── Real-Time Streaming Chat Endpoint (SSE) ───────────────────────────────────
@app.post("/api/chat/stream")
async def stream_chat(
    req: ChatRequest,
    context: SecurityContext = Depends(get_security_context)
):
    """
    Initiates a trip planning request and streams real-time stage updates via Server-Sent Events (SSE).
    Injects episodic memory (P3) and tenant vector document context (P2).
    """
    thread_id = req.thread_id
    query = req.query.strip()
    owner_id = context.tenant_id
    user_id = context.user_id

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": get_callbacks(session_id=thread_id, user_id=user_id, tags=["chat-stream"])
    }

    # P3: Retrieve episodic memory history context
    episodic_context = format_memory_context_for_llm(owner_id, limit=4)

    # P6: Retrieve consolidated user profile context (cached, <2ms)
    user_profile_context = format_profile_for_llm(owner_id)

    # P2: Multi-tenant vector search for relevant uploaded tenant documents
    matched_docs = search_tenant_documents(owner_id, query, top_k=3, min_score=0.10)
    tenant_docs_str = ""
    if matched_docs:
        doc_lines = []
        for d in matched_docs:
            doc_lines.append(f"- [{d['filename']}] (relevance: {d['score']}): {d['content']}")
        tenant_docs_str = "\n".join(doc_lines)

    initial_state = {
        "user_query": query,
        "user_id": user_id,
        "owner_id": owner_id,
        "episodic_context": episodic_context,
        "tenant_docs_context": tenant_docs_str,
        "user_profile_context": user_profile_context,
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
        yield {
            "event": "start",
            "data": json.dumps({
                "thread_id": thread_id, 
                "query": query,
                "user_id": user_id,
                "is_guest": context.is_guest,
            })
        }

        latest_state = {}

        try:
            for chunk in graph_app.stream(initial_state, config=config, stream_mode="updates"):
                for node_name, node_update in chunk.items():
                    if isinstance(node_update, dict):
                        latest_state.update(node_update)

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

            # Check if paused at human-in-the-loop interrupt
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
                
                # P3: Save completed interaction into Neon episodic memory
                try:
                    save_interaction(
                        owner_id=owner_id,
                        thread_id=thread_id,
                        user_query=query,
                        assistant_response=final,
                        intent=intent,
                        metadata={
                            "response_type": resp_type,
                            "is_guest": context.is_guest,
                            "constraints": latest_state.get("trip_constraints", {})
                        }
                    )
                except Exception as save_err:
                    logger.warning(f"Episodic memory save failed: {save_err}")

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
async def resume_chat(
    req: ResumeRequest,
    context: SecurityContext = Depends(get_security_context)
):
    """
    Resumes a paused conversation after user approves or requests revisions.
    Streams final polishing or newly generated revision itinerary via SSE.
    """
    thread_id = req.thread_id
    is_approved = req.approved
    feedback = req.feedback.strip() if req.feedback else ""
    owner_id = context.tenant_id

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

                # P3: Record revision in episodic memory
                try:
                    save_interaction(
                        owner_id=owner_id,
                        thread_id=thread_id,
                        user_query=f"Revision request: {feedback}" if feedback else "Itinerary Approved",
                        assistant_response=final,
                        intent="trip_planning_revision",
                        metadata={"approved": is_approved, "is_guest": context.is_guest}
                    )
                except Exception as save_err:
                    logger.warning(f"Episodic memory save on resume failed: {save_err}")

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


# ── User Profile & Consolidation Endpoints (Phase 6) ──────────────────────────
@app.get("/api/profile")
async def get_profile_endpoint(context: SecurityContext = Depends(get_security_context)):
    """Fetch synthesized traveler profile for current user/tenant."""
    profile = get_user_profile(context.tenant_id)
    return {
        "owner_id": context.tenant_id,
        "has_profile": profile is not None,
        "profile": profile,
    }


@app.post("/api/profile/consolidate")
async def trigger_consolidation_endpoint(
    context: SecurityContext = Depends(get_security_context)
):
    """Manually trigger profile consolidation from ingested documents."""
    res = await summarize_and_consolidate(context.tenant_id)
    return {
        "status": "success" if res else "no_documents",
        "profile": res,
        "owner_id": context.tenant_id,
    }


# ── TTL Reaper Endpoints (Phase 5) ─────────────────────────────────────────────
@app.post("/api/admin/reaper/run")
async def trigger_reaper_endpoint(
    max_age_hours: float = 2.0,
    context: SecurityContext = Depends(require_admin)
):
    """Admin-only manual execution of the TTL Reaper."""
    stats = purge_expired_guest_data(max_age_hours=max_age_hours)
    return {
        "status": "completed",
        "details": stats,
    }


@app.get("/api/admin/reaper/status")
async def reaper_status_endpoint(
    context: SecurityContext = Depends(require_admin)
):
    """Admin-only telemetry of the TTL Reaper background worker."""
    return {
        "reaper_telemetry": get_reaper_stats(),
    }


# ── Lifecycle Events ──────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info("Initializing automated TTL Reaper background worker...")
    start_reaper_background_task(interval_seconds=1800, max_age_hours=2.0)


@app.on_event("shutdown")
def on_shutdown():
    logger.info("Stopping TTL Reaper background worker...")
    stop_reaper_background_task()
    logger.info("Flushing pending observability events before shutdown...")
    flush_observability()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
