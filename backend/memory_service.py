"""
memory_service.py - Episodic Memory Service for Agentic Travel Assistant
Implements:
- Persistent Q&A interaction logging in Neon PostgreSQL
- Multi-tenant tenant/owner isolation on episodic memories
- Context formatting and prompt injection for LangGraph LLM agents
"""

import os
import uuid
import json
import logging
from typing import List, Dict, Any, Optional
import psycopg

from config import DATABASE_URL

logger = logging.getLogger("travel_memory")


def save_interaction(
    owner_id: str,
    thread_id: str,
    user_query: str,
    assistant_response: str,
    intent: str = "trip_planning",
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Saves a completed user interaction into Neon PostgreSQL episodic_memory table.
    """
    if not owner_id or not user_query:
        return ""

    memory_id = f"mem_{uuid.uuid4().hex[:12]}"
    meta = metadata or {}

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO episodic_memory (
                        id, owner_id, thread_id, user_query, 
                        assistant_response, intent, metadata, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
                    """,
                    (
                        memory_id,
                        owner_id,
                        thread_id,
                        user_query,
                        assistant_response or "",
                        intent or "trip_planning",
                        json.dumps(meta),
                    )
                )
                conn.commit()

        logger.info(f"Saved episodic memory {memory_id} for owner {owner_id} (thread: {thread_id})")
        return memory_id
    except Exception as e:
        logger.error(f"Failed to persist episodic memory: {e}")
        return ""


def get_recent_interactions(owner_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fetches recent episodic interactions strictly for the specified owner/tenant.
    """
    if not owner_id:
        return []

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, thread_id, user_query, assistant_response, intent, metadata, created_at
                    FROM episodic_memory
                    WHERE owner_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s;
                    """,
                    (owner_id, limit)
                )
                rows = cur.fetchall()

        interactions = []
        for r in rows:
            meta = r[5]
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            interactions.append({
                "id": r[0],
                "thread_id": r[1],
                "user_query": r[2],
                "assistant_response": r[3],
                "intent": r[4],
                "metadata": meta,
                "created_at": str(r[6]),
            })
        return interactions
    except Exception as e:
        logger.error(f"Failed to query episodic memories for owner {owner_id}: {e}")
        return []


def format_memory_context_for_llm(owner_id: str, limit: int = 4) -> str:
    """
    Formats past interactions into a concise context block for injection into LLM prompts.
    Provides personal continuity across conversation threads and sessions.
    """
    interactions = get_recent_interactions(owner_id, limit=limit)
    if not interactions:
        return ""

    lines = [
        "### Prior Traveler History & Episodic Context (Continuity Memory):",
        "The traveler previously interacted with the assistant on the following topics:",
    ]

    for idx, item in enumerate(reversed(interactions), 1):
        q = item["user_query"].strip().replace("\n", " ")
        # Truncate response to ~180 chars for prompt compactness
        resp = item["assistant_response"].strip().replace("\n", " ")
        if len(resp) > 200:
            resp = resp[:197] + "..."
        lines.append(f"{idx}. Traveler asked: \"{q}\"")
        if resp:
            lines.append(f"   Assistant noted/provided: {resp}")

    lines.append("\n*Use this episodic memory to provide consistent, personalized recommendations without contradicting earlier preferences.*")
    return "\n".join(lines)
